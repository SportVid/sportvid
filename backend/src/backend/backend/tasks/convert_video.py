import os
import subprocess
import shutil
import time
import tarfile
import logging
import imageio
from pathlib import Path
from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings

from backend.utils import media_dir_to_file, media_path_to_file
from backend.models import Video
from backend.plugin_manager import PluginManager
from utils.video_converter import convert_to_hls,  terminate_process_group
from utils.helper import remove_file, remove_dir


logger = logging.getLogger(__name__)
_POLL_INTERVAL = 2.0  # seconds between cancellation checks
_DELETE_CHECK_INTERVAL = 5.0 


def safe_delete(paths):
    if not isinstance(paths, (list, tuple, set)):
        paths = [paths]
    
    for fp in paths:
        if not fp: continue
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

def _manifest_references(manifest: Path) -> tuple[Path, list[Path]]:
    """ Validate if all media files have been written properly to the asset dir. """
    text = manifest.read_text(encoding="utf-8")
    manifest_dir = manifest.parent.resolve()

    import re

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

@shared_task(bind=True, time_limit=7200, soft_time_limit=5400)
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
        asset_dir = output_root / video_id_hex
        manifest = asset_dir / f"{video_id_hex}.m3u8"
        asset_dir.mkdir(parents=True, exist_ok=True)

        fps, duration_ms, size = _metadata(file_in)
        segment_time = 5
        gop = max(1, round(fps * segment_time))
        
        # TODO: dynamic decoding based on GPU availability and deployment mode.
        fmp4 = True
        
        conversion_args = {
            "format": "hls",
            "threads": 1, # TODO: check thread count for HLS conversion. Queue 2-3 video uploads, check ffmpeg processes and CPU usage. 
                # ps -ef | grep ffmpeg
                # top -H -p <ffmpeg_pid>
            "hls_playlist_type": "vod",
            "segment_time" : segment_time,
            # -------- input: hardware acceleration
            # NOTE: uncomment these lines if running without a GPU.
            "hwaccel": "cuda",
            "hwaccel_output_format": "cuda",
            # -------- output: video/audio options
            "vcodec" : "h264_nvenc", # NOTE: use "h264_nvenc" for GPU conversion via NVENC.
            "acodec" : "aac",
            "audio_bitrate" : "128k",
            # -------- HLS stuff
            "g": gop, # GOP size should match segment duration
            "keyint_min": gop, # same as GOP
            # "sc_threshold": 0, # no unpredictable keyframe insertions
            # "crf": 23,  # NOTE: comment in for "libx264". This is the constant rate factor [0-51], lower: higher quality & larger file; higher: more compression & lower quality 
            # -------- NVENC tuning
            "preset": "p4", # NOTE: uncomment if using GPU conversion. This controls encoding speed --vs.-- compression trade-off [p1-p7].
            "rc": "vbr",
            "cq": 23,
            # -------- output compat
            # "pix_fmt": "yuv420p", # pixel format of the output
            "loglevel": "error"
        }
        
        conversion_args.update({
            "hls_flags" : "independent_segments",
            "hls_segment_filename": os.path.join(asset_dir, "segment_%05d.m4s")
        })
        if fmp4:
            conversion_args.update({ 
                "hls_segment_type": "fmp4",
                "hls_fmp4_init_filename": "init.mp4",
            })
        else:
            conversion_args.update({ 
                "hls_segment_type": "mpegts",
            })
            
        logger.info(
            "Starting HLS conversion for %s: %s -> %s",
            video_id_hex,
            file_in,
            manifest,
        )
            
        ffmpeg_proc = convert_to_hls(
            str(file_in),
            str(manifest),
            asynchronous=True,
            **conversion_args,
        )
        
        last_delete_check = 0.
        while True:
            rc = ffmpeg_proc.poll()
            if rc is not None: break
        
            now = time.monotonic()
            if now - last_delete_check >= _DELETE_CHECK_INTERVAL:
                last_delete_check = now
                if not Video.objects.filter(id=video_id_hex).exists():
                    logger.info(
                        "Video %s deleted; terminating FFmpeg",
                        video_id_hex,
                    )
                    terminate_process_group(ffmpeg_proc)
                    return

            time.sleep(_POLL_INTERVAL)
        
        if rc != 0:
            raise RuntimeError(
                f"FFmpeg exited with code {rc}"
            )
            
        if not manifest.is_file() or manifest.stat().st_size == 0:
            raise RuntimeError(f"Missing or empty HLS manifest: {manifest}")
        
        # try:
        #     while True:
        #         try:
        #             _, stderr = ffmpeg_proc.communicate(timeout=_POLL_INTERVAL)
        #             if ffmpeg_proc.returncode != 0:
        #                 raise RuntimeError(
        #                     f"ffmpeg exited with code {ffmpeg_proc.returncode}"
        #                 )
        #             if stderr:
        #                 for line in stderr.splitlines():
        #                     logger.error("[ffmpeg] %s", line)
        #             break
        #         except subprocess.TimeoutExpired:
        #             if not Video.objects.filter(id=video_id_hex).exists():
        #                 logger.info(
        #                     "Video %s deleted during HLS conversion, killing ffmpeg.",
        #                     video_id_hex,
        #                 )
        #                 ffmpeg_proc.kill()
        #                 ffmpeg_proc.wait()
        #                 return
        # finally:
        #     if ffmpeg_proc.stderr:
        #         ffmpeg_proc.stderr.close()                   
        
        
        if fmp4:
            init_path, _ = _manifest_references(manifest)
            media_path_for_db = str(manifest)
        else:
            segment_candidates = sorted(asset_dir.glob("*.ts"))
            if not segment_candidates:
                raise RuntimeError(
                    f"No MPEG-TS segments generated in {asset_dir}."
                )
            media_path_for_db = str(manifest)
        
        # NOTE: Creates the archive to be transfered.
        # TODO: Eventually we can remove putting everything into archives to send them around via gRPC.
        #       See "video_asset_manager.py", and "video_asset_data.py" -> use manifest_path & media_path.
        #       Requires no packing/unpacking after each send/receive.
        ext = ".tar.gz"
        archive_path = Path(f"{output_root}{video_id_hex}{ext}")
        temporary_archive = archive_path.with_suffix(".tar.gz.partial")

        with tarfile.open(temporary_archive, "w:gz") as tar:
            tar.add(asset_dir, arcname=".", recursive=True)
        os.replace(temporary_archive, archive_path)
        
        upd = Video.objects.filter(id=video_id_hex).update(
            ext=ext,
            fps=fps,
            duration=duration,
            width=size[0] if size else None,
            height=size[1] if size else None,
            status=Video.STATUS_DONE,
            asset_dir = str(asset_dir),
            manifest_path = str(manifest),
            media_path = media_path_for_db
        )

        if not updated:
            raise RuntimeError(
                f"Video disappeared before completion: {video_id_hex}"
            )

        logger.info(
            "HLS conversion took %.2f seconds for %s",
            time.monotonic() - started,
            video_id_hex,
        )

        # NOTE: Add comma-separated plugin names to run automatically on video upload.
        # plugin_manager = PluginManager()
        # plugins = [] 
        # if analyzers:
        #     plugins += analyzers
        # for plugin in plugins:
        #     try:
        #         plugin_manager(plugin, video=video_db, user=video_db.owner)
        #     except Exception:
        #         logger.exception(f"Failed to schedule plugin {plugin}")

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
        safe_delete([archive_path, asset_dir])
        raise

    except Exception:
        logger.exception("Video conversion failed: %s", video_id_hex)
        if video_db is not None:
            Video.objects.filter(id=video_id_hex).update(
                status=Video.STATUS_ERROR,
            )
        if ffmpeg_proc is not None:
            terminate_process_group(ffmpeg_proc)
        safe_delete([archive_path, asset_dir])
        raise

    finally:
        if ffmpeg_proc is not None:
            terminate_process_group(ffmpeg_proc)

        if file_in is not None:
            safe_delete(file_in)