import os
import re
import subprocess
import shutil
import time
import tarfile
import logging
import imageio
from pathlib import Path
from typing import Any
from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings

from backend.utils import media_dir_to_file, media_path_to_file, publish_video
from backend.utils.events import cancellation_watcher
from backend.models import Video
from backend.plugin_manager import PluginManager
from utils.video_converter import convert_to_hls, terminate_process_group
from utils.helper import remove_file, remove_dir


logger = logging.getLogger(__name__)

_POLL_INTERVAL = 2.0  # seconds between cancellation checks (fallback)
_DELETE_CHECK_INTERVAL = 5.0
_PROGRESS_STEP = 0.01  # only report conversion progress once it moved by at least 1%

# adds constants & regex for parsing FFmpeg progress
_FFMPEG_PROGRESS_KEYS = (
    "frame", "fps", "stream", "bitrate", "total_size", "out_time_us", "out_time_ms",
    "out_time", "dup_frames", "drop_frames", "speed", "progress",
)
_FFMPEG_PROGRESS_LINE = re.compile(
    r"^(" + "|".join(_FFMPEG_PROGRESS_KEYS) + r")[\w_]*="
)


def safe_delete(paths):
    if not isinstance(paths, (list, tuple, set)):
        paths = [paths]

    for fp in paths:
        if not fp:
            continue
        path = Path(fp)
        try:
            if path.is_file():
                path.unlink(missing_ok=True)
            elif path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            logger.debug(f"Deleted {path}")
        except Exception as e:
            logger.warning(f"Failed to delete {path}: {e}")

@shared_task
# TODO: get a cronjob running that cleans up orphaned videos.
def cleanup_upload_orphans(self):
    """ Delete files without DB Video record. """
    media_root = Path(settings.MEDIA_ROOT)
    db_files = set()
    
    # builds set of valid DB entries
    for video in Video.objects.filter(status__in=
        [Video.STATUS_UPLOADING, Video.STATUS_PROCESSING, Video.STATUS_ERROR]):
        db_files.add(str(media_path_to_file(video.file.hex, f".{video.ext}")))
    
    # scan filesystem
    for file_path in media_root.rglob('*.tar.gz'):
        if str(file_path) not in db_files:
            safe_delete(file_path)
            logger.info(f"Removed orphan: {file_path}")

def _report_conversion_progress(video_id_hex, progress):
    """Persist & push HLS conversion progress. 
    Uses the Queryset update on purpose, since the video may have been deleted mid-conversion.
    """
    progress = max(0.0, min(1.0, progress))
    updated = Video.objects.filter(id=video_id_hex).update(progress=progress)
    if updated:
        # .update() bypasses post_save, so the live event is sent explicitly.
        publish_video(video_id_hex)
    return updated

def _manifest_references_singlefile(asset_dir: Path, manifest: Path):
    if not manifest.is_file() or manifest.stat().st_size == 0:
        raise RuntimeError(
            f"Missing or empty HLS manifest: {manifest}"
        )
        
    manifest_text = manifest.read_text(encoding="utf-8")
    if "#EXTM3U" not in manifest_text:
        raise RuntimeError(
            f"Invalid HLS manifest header: {manifest}"
        )
    if "#EXT-X-ENDLIST" not in manifest_text:
        raise RuntimeError(
            f"Incomplete HLS manifest: {manifest}"
        )
    if "#EXT-X-MAP" not in manifest_text:
        raise RuntimeError(
            f"fMP4 manifest has no EXT-X-MAP: {manifest}"
        )

    media_uris = [
        line.strip()
        for line in manifest_text.splitlines()
        if line.strip()
        and not line.startswith("#")
    ]
    if not media_uris:
        raise RuntimeError(
            f"No media URI found in HLS manifest: {manifest}"
        )
    # single_file mode should reference one physical media resource
    if len(set(media_uris)) != 1:
        raise RuntimeError(
            "Expected one single-file media resource, found: "
            f"{sorted(set(media_uris))}"
        )

    media_path = (asset_dir / media_uris[0]).resolve()
    if media_path.parent != asset_dir.resolve():
        raise RuntimeError(
            f"Manifest references a path outside asset directory: "
            f"{media_path}"
        )
    if not media_path.is_file() or media_path.stat().st_size == 0:
        raise RuntimeError(
            f"Missing or empty HLS media file: {media_path}"
        )

    return str(media_path)

def _manifest_references_segments(manifest: Path) -> tuple[Path, list[Path]]:
    """ Validate if all media files have been written properly to the asset dir. """
    text = manifest.read_text(encoding="utf-8")
    manifest_dir = manifest.parent.resolve()

    map_match = re.search(
        r'#EXT-X-MAP:URI="([^"]+)"',
        text,
    )

    if not map_match:
        raise RuntimeError(
            f"fMP4 manifest has no EXT-X-MAP: {manifest}"
        )

    init_path = (manifest_dir / map_match.group(1)).resolve()
    if init_path.parent != manifest_dir:
        raise RuntimeError("Manifest references an unsafe init path")
    if not init_path.is_file():
        raise RuntimeError(f"Missing fMP4 init segment: {init_path}")

    segments: list[Path] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        segment = (manifest_dir / line).resolve()
        if segment.parent != manifest_dir:
            raise RuntimeError(
                "Manifest references an unsafe segment path"
            )
        segments.append(segment)

    if not segments:
        raise RuntimeError(
            f"No media segments listed in manifest: {manifest}"
        )

    missing = [str(path) for path in segments if not path.is_file()]
    if missing:
        raise RuntimeError(f"Missing HLS segments: {missing}")

    return init_path, segments

def _metadata(file_in: Path) -> tuple[float, float | None, Any]:
    with imageio.get_reader(str(file_in)) as reader:
        meta = reader.get_meta_data()

        fps = float(meta["fps"])
        duration = meta.get("duration")
        duration_ms = (
            float(duration) * 1000.0
            if duration is not None
            else None
        )

        return fps, duration_ms, meta.get("size")

@shared_task(bind=True, time_limit=7200, soft_time_limit=5400, queue="gpu")
def convert_video_to_hls(self, video_id_hex, original_ext, analyzers=None):
    started = time.monotonic()
    video_db = None
    ffmpeg_proc: subprocess.Popen[str] | None = None
    archive_path: Path | None = None
    asset_dir: Path | None = None
    file_in: Path | None = None

    try:
        video_db = Video.objects.get(id=video_id_hex)

        output_root = Path(media_dir_to_file(video_id_hex))
        file_in = Path(media_path_to_file(video_id_hex, original_ext))
        
        asset_dir = Path(os.path.join(output_root,video_id_hex))
        manifest = Path(os.path.join(asset_dir, f'{video_id_hex}.m3u8'))
        asset_dir.mkdir(parents=True, exist_ok=True)

        fps, duration_ms, size = _metadata(file_in)
        segment_time = 5
        gop = max(1, round(fps * segment_time))
        
        # TODO: dynamic decoding based on GPU availability and deployment mode.
        fmp4 = True
        
        conversion_args = {
            "format": "hls",
            "threads": 0, # TODO: Check thread count for HLS conversion.
                # $ ps -ef | grep ffmpeg
                # $ top -H -p <ffmpeg_pid>
            "hls_playlist_type": "vod",
            "segment_time" : segment_time,
            # -------- input: hardware acceleration
            # NOTE: uncomment these lines if running without a GPU.
            # "hwaccel": "cuda",
            # "hwaccel_output_format": "cuda",
            # -------- output: video/audio options
            "vcodec" : "libx264", # NOTE: use "libx264" for CPU conversion.
            # "vcodec" : "h264_nvenc" # NOTE: Use "h264_nvenc" for GPU conversion via NVENC
            "acodec" : "aac",
            "audio_bitrate" : "128k",
            # -------- HLS stuff
            "g": gop, # GOP size should match segment duration
            "keyint_min": gop, # same as GOP
            # "sc_threshold": 0, # no unpredictable keyframe insertions
            "crf": 23,  # NOTE: Comment this line in for "libx264". Constant rate factor [0-51] --> lower: higher quality & larger file; higher: more compression & lower quality. 
            # -------- NVENC tuning
            # "preset": "p4", # NOTE: Uncomment if using GPU conversion. Controls encoding speed --vs.-- compression trade-off [p1-p7].
            "rc": "vbr",
            "cq": 23,
            # -------- output compat
            # "pix_fmt": "yuv420p", # pixel format of the output
            "loglevel": "error"
        }
        
        if fmp4:
            conversion_args.update({ 
                "hls_segment_type": "fmp4",
                "hls_flags" : "single_file+independent_segments",
                "hls_fmp4_init_filename": "init.mp4",
                # "hls_flags" : "independent_segments", # TODO: Maybe switch to segmented files?
                # "hls_segment_filename": os.path.join(asset_dir, "segment_%05d.m4s")
            })
        else:
            conversion_args.update({ 
                "hls_segment_type": "mpegts",
                "hls_flags" : "independent_segments"
            })
            
        logger.info(
            "Starting HLS conversion for %s: %s -> %s",
            video_id_hex,
            file_in,
            manifest,
        )

        # FFmpeg conversion uses a dedicated progress pipe so stderr can remain inherited
        ffmpeg_proc = convert_to_hls(
            str(file_in),
            str(manifest),
            asynchronous=True,
            **conversion_args,
        )
        
        # denominator for the conversion progress --> may be missing for some containers
        source_duration = duration_ms / 1000. if duration_ms is not None else None
        
        last_delete_check = 0.0
        last_reported = 0.0
        cancelled = False
        
        # listener thread reacts to VideoDelete and publishes a cancel request for this video to kill ffmpeg immediately
        # TODO: cancellation relies on Valkey
        # --> add a fallback timeout to kill FFmpeg if it appears stuck.
        with cancellation_watcher(
            "video",
            video_id_hex,
            on_cancel=lambda: terminate_process_group(ffmpeg_proc),
        ) as cancel_event:
            try:
                # drains ffmpeg's error & "-progress" output line by line
                while True:
                    # TODO: can block indefinitely if FFmpeg stops writing but hasn’t exited
                    # --> use a non-blocking reader (e.g. a separate thread or select/queue) for stderr
                    line = ffmpeg_proc.stdout.readline()
                    if not line:
                        if ffmpeg_proc.poll() is not None:
                            break
                        continue
        
                    line = line.rstrip()
                    is_progress_line = bool(_FFMPEG_PROGRESS_LINE.match(line)) # identifies progress lines
                    
                    if not is_progress_line:
                        # non-progress lines on stdout are unexpected; ignore quietly.
                        continue
                    
                    if line.startswith("out_time_us=") and source_duration:
                        try:
                            elapsed = int(line.split("=", 1)[1]) / 1_000_000.0
                        except ValueError:
                            elapsed = None
                        if elapsed is not None:
                            # reserves the last few percent for archive packing and writing metadata
                            progress = min(elapsed / float(source_duration), 1.0) * 0.95
                            if progress - last_reported >= _PROGRESS_STEP:
                                last_reported = progress
                                _report_conversion_progress(video_id_hex, progress)
                    
                    if line.startswith("progress="):
                        now = time.monotonic()
                        if now - last_delete_check >= _DELETE_CHECK_INTERVAL:
                            last_delete_check = now
                            # fallback existence check in case Valkey is unavailable.
                            if not Video.objects.filter(id=video_id_hex).exists():
                                logger.info(
                                    "Video %s deleted; terminating FFmpeg (fallback).",
                                    video_id_hex,
                                )
                                cancelled = True
                                terminate_process_group(ffmpeg_proc)
                                break
                                # Drain any remaining stdout after FFmpeg exits.
                # drains any remaining stdout after FFmpeg exits.
                rest = ffmpeg_proc.stdout.read()
                if rest:
                    for extra_line in rest.splitlines():
                        if not _FFMPEG_PROGRESS_LINE.match(extra_line):
                            logger.debug("[ffmpeg progress] %s", extra_line)    
            finally:
                if ffmpeg_proc.stdout:
                    ffmpeg_proc.stdout.close() 
                    
            cancelled = cancelled or cancel_event.is_set()
        
        # waits for the return code and raises on error if not cancelled
        rc = ffmpeg_proc.wait()
        if not cancelled and rc != 0:
            raise RuntimeError(
                f"FFmpeg exited with code {rc}"
            )        
            
        if not manifest.is_file() or manifest.stat().st_size == 0:
            raise RuntimeError(f"Missing or empty HLS manifest: {manifest}")
                        
        if fmp4:
            # NOTE: below line only relevant for segmented fmp4.
            # init_path, segments = _manifest_references_segments(manifest)
            media_path_for_db = _manifest_references_singlefile(asset_dir, manifest)
        else:
            segment_candidates = sorted(asset_dir.glob("*.ts"))
            if not segment_candidates:
                raise RuntimeError(
                    f"No MPEG-TS segments generated in {asset_dir}."
                )
            media_path_for_db = segment_candidates[0]
        
        # NOTE: Creates the archive to be transfered.
        # TODO: Eventually we can avoid wrapping everything into an .tar archive to send it around via gRPC.
        #       See "video_asset_manager.py", and "video_asset_data.py", manifest_path & media_path.
        #       Would requires no packing/unpacking after each send/receive, however bad solution if using segmented fmp4.
        ext = ".tar.gz"
        archive_path = output_root / f"{video_id_hex}{ext}"
        temporary_archive = archive_path.with_suffix(".tar.gz.partial")

        with tarfile.open(temporary_archive, "w:gz") as tar:
            tar.add(asset_dir, arcname=".", recursive=True)
        os.replace(temporary_archive, archive_path)
        
        upd = Video.objects.filter(id=video_id_hex).update(
            ext=ext,
            fps=fps,
            duration=duration_ms,
            width=size[0] if size else None,
            height=size[1] if size else None,
            status=Video.STATUS_DONE,
            progress=1.0,
            asset_dir=str(asset_dir),
            manifest_path=str(manifest),
            media_path=media_path_for_db,
        )

        if not upd:
            raise RuntimeError(
                f"Video disappeared before completion: {video_id_hex}"
            )

        # Queryset .update() doesn't fire post_save --> push the "done" state explicitly
        # so the gallery card resolves itself without a reload.
        publish_video(video_id_hex)

        logger.info(
            "HLS conversion took %.2f seconds for %s",
            time.monotonic() - started,
            video_id_hex,
        )

        # Kick off the automatic cover-thumbnail run now that the video is playable.
        # The gallery card stays in its "processing" look until a "thumbnail" plugin
        # run exists and finishes (VideoView.vue), so without this trigger the card
        # gets stuck on "video is being processed" until a manual reload.
        # These go through run_plugin on the default "io" queue -- thumbnail_generator
        # is CPU-only on the analyser side (inference_ray/deploy*.yml), so there is
        # nothing to gain from the "gpu" queue the conversion itself runs on.
        if video_db is not None and video_db.owner_id is not None:
            plugin_manager = PluginManager()
            # "thumbnail" always; plus any analyzers the upload asked for. dict.fromkeys
            # dedupes while keeping order in case "thumbnail" is passed explicitly.
            for plugin in dict.fromkeys(["thumbnail", *(analyzers or [])]):
                if not plugin:
                    continue
                try:
                    plugin_manager.run(
                        plugin,
                        video=video_db,
                        user=video_db.owner,
                        run_async=True,
                    )
                except Exception:
                    logger.exception(
                        "Failed to schedule automatic plugin %s for %s",
                        plugin,
                        video_id_hex,
                    )

    except SoftTimeLimitExceeded:
        logger.warning(
            "Soft time limit exceeded for video %s",
            video_id_hex,
        )
        
        if ffmpeg_proc is not None:
            terminate_process_group(ffmpeg_proc)
            
        if video_db is not None:
            Video.objects.filter(id=video_id_hex).update(
                status=Video.STATUS_ERROR,
            )
            publish_video(video_id_hex)
            
        safe_delete([archive_path, asset_dir])
        raise

    except Exception:
        logger.exception(
            "Video conversion failed: %s", 
            video_id_hex
        )
        
        if video_db is not None:
            Video.objects.filter(id=video_id_hex).update(
                status=Video.STATUS_ERROR,
            )
            publish_video(video_id_hex)
            
        if ffmpeg_proc is not None:
            terminate_process_group(ffmpeg_proc)

        safe_delete([archive_path, asset_dir])
        raise

    finally:
        if ffmpeg_proc is not None:
            terminate_process_group(ffmpeg_proc)

        if file_in is not None:
            safe_delete(file_in)