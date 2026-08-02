import os
import subprocess
import shutil
import time
import tarfile
import logging
import imageio
from pathlib import Path
from celery import shared_task
from django.conf import settings

from backend.utils import media_dir_to_file, media_path_to_file
from backend.models import Video
from backend.plugin_manager import PluginManager
from utils.video_converter import convert_to_hls
from utils.helper import remove_file, remove_dir


logger = logging.getLogger(__name__)
_POLL_INTERVAL = 2.0  # seconds between cancellation checks


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
    for video in Video.objects.filter(status__in=[Video.STATUS_UPLOADING, Video.STATUS_PROCESSING, Video.STATUS_ERROR]):
        db_files.add(str(media_path_to_file(video.file.hex, f".{video.ext}")))
    
    # scan filesystem
    for file_path in media_root.rglob('*.tar.gz'):
        if str(file_path) not in db_files:
            safe_delete(file_path)
            logger.info(f"Removed orphan: {file_path}")

@shared_task(bind=True, time_limit=7200, soft_time_limit=5400)
def convert_video_to_hls(self, video_id_hex, original_ext, analyzers=None):
    s = time.time()
    
    archive_path = None
    asset_dir = None
    video_db = None
    
    fmp4 = True
    async_ = True
    
    try:
        video_db = Video.objects.get(id=video_id_hex)
        
        output_root = media_dir_to_file(video_id_hex)
        file_in = media_path_to_file(video_id_hex, original_ext)
        
        asset_dir = os.path.join(output_root, video_id_hex)
        manifest_path = os.path.join(asset_dir, f'{video_id_hex}.m3u8')
        os.makedirs(asset_dir, exist_ok=True)
        logger.debug(f'out={output_root}, asset_dir={asset_dir}, file_in={file_in}, manifest_path={manifest_path}')

        # extract metadata
        with imageio.get_reader(str(file_in)) as reader:
            meta = reader.get_meta_data()
            fps = float(meta["fps"])

        segment_time = 5
        gop = max(1, int(round(fps * segment_time)))
        
        logger.info(f"Starting HLS conversion for {video_id_hex} from {file_in} to {manifest_path}")
        
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
        }
        
        if fmp4:
            conversion_args.update({ 
                "hls_segment_type": "fmp4",
                "hls_flags" : "independent_segments",
                "hls_fmp4_init_filename": "init.mp4",
                "hls_segment_filename": os.path.join(asset_dir, "segment_%05d.m4s")
            })
        else:
            conversion_args.update({ 
                "hls_segment_type": "mpegts",
                "hls_flags" : "independent_segments",
            })
            
        if async_:
            ffmpeg_proc = convert_to_hls(
                str(file_in),
                str(manifest_path),
                asynchronous=True,
                **conversion_args
            )
            try:
                while True:
                    try:
                        _, stderr = ffmpeg_proc.communicate(timeout=_POLL_INTERVAL)
                        if ffmpeg_proc.returncode != 0:
                            raise RuntimeError(
                                f"ffmpeg exited with code {ffmpeg_proc.returncode}"
                            )
                        if stderr:
                            for line in stderr.splitlines():
                                logger.error("[ffmpeg] %s", line)
                        break
                    except subprocess.TimeoutExpired:
                        if not Video.objects.filter(id=video_id_hex).exists():
                            logger.info(
                                "Video %s deleted during HLS conversion, killing ffmpeg.",
                                video_id_hex,
                            )
                            ffmpeg_proc.kill()
                            ffmpeg_proc.wait()
                            return
            finally:
                if ffmpeg_proc.stderr:
                    ffmpeg_proc.stderr.close()           
        else: 
            ffmpeg_done = convert_to_hls(
                str(file_in),
                str(manifest_path),
                asynchronous=False,
                **conversion_args
            )
        
        # ------------------------> Validation if all the files have been written properly to the asset dir.
        asset_dir = Path(asset_dir)
        manifest = Path(manifest_path)

        if not manifest.exists():
            raise RuntimeError(f"No HLS manifest generated: {manifest}")

        manifest_text = manifest.read_text(encoding="utf-8")

        if fmp4:
            if "#EXT-X-MAP" not in manifest_text:
                raise RuntimeError("fMP4 manifest missing #EXT-X-MAP")

            import re

            map_match = re.search(r'#EXT-X-MAP:URI="([^"]+)"', manifest_text)
            if not map_match:
                raise RuntimeError("Could not parse init segment from #EXT-X-MAP")

            init_name = map_match.group(1)
            init_path = asset_dir / init_name
            if not init_path.exists():
                raise RuntimeError(f"Init segment missing: {init_path}")

            segment_lines = [
                line.strip() for line in manifest_text.splitlines()
                if line.strip() and not line.startswith("#")
            ]
            media_segments = [asset_dir / line for line in segment_lines if line.endswith(".m4s")]
            if not media_segments:
                raise RuntimeError(f"No fMP4 media segments listed in manifest {manifest}")

            missing = [str(p) for p in media_segments if not p.exists()]
            if missing:
                raise RuntimeError(f"Missing fMP4 media segments: {missing}")

            media_path_for_db = str(init_path)

        else:
            segment_candidates = list(asset_dir.glob("*.ts"))
            if not segment_candidates:
                raise RuntimeError(f"No MPEG-TS segments generated in {asset_dir}")
            media_path_for_db = segment_candidates[0]

        # creates the archive to be transfered
        # TODO: Eventually we can remove putting everything into archives to send them around via gRPC.
        #       See "video_asset_manager.py", and "video_asset_data.py" -> use manifest_path & media_path.
        #       Requires no packing/unpacking after each send/receive.
        ext = '.tar.gz'
        archive_path = Path(f"{output_root}{video_id_hex}{ext}")
        with tarfile.open(archive_path, 'w:gz') as tar:
            tar.add(asset_dir, arcname='.', recursive=True)

        # extract metadata
        reader      = imageio.get_reader(str(file_in))
        fps         = reader.get_meta_data().get('fps')
        duration    = reader.get_meta_data().get('duration') * 1000.0
        size        = reader.get_meta_data().get('size')

        # update DB (use update_fields to avoid re-inserting a deleted record)
        Video.objects.filter(id=video_id_hex).update(
            ext=ext,
            fps=fps,
            duration=duration,
            width=size[0] if size else None,
            height=size[1] if size else None,
            status=Video.STATUS_DONE,
            asset_dir = str(asset_dir),
            manifest_path = str(manifest_path),
            media_path = str(media_path_for_db)
        )

        e = time.time()
        logger.info(f"HLS conversion took: {e-s}")

        # NOTE: add comma-separated plugin names to run automatically on video upload.
        # plugin_manager = PluginManager()
        # plugins = [] 
        # if analyzers:
        #     plugins += analyzers
        # for plugin in plugins:
        #     try:
        #         plugin_manager(plugin, video=video_db, user=video_db.owner)
        #     except Exception:
        #         logger.exception(f"Failed to schedule plugin {plugin}")

    except Exception:
        logger.exception("Video conversion failed")
        if video_db is not None:
            Video.objects.filter(id=video_id_hex).update(status=Video.STATUS_ERROR)
        safe_delete([archive_path, asset_dir])

    finally:
        try: # NOTE: final cleanup.
            safe_delete(file_in)
            logger.debug(f"{file_in} removed successfully!")
        except Exception:
            logger.exception("Failed to remove original file")