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

@shared_task
# TODO: get cronjob with cleaning of orphaned videos working...
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
def convert_video_to_fmp4(self, video_id_hex, original_ext, analyzers=None):
    s = time.time()
    
    archive_path = None
    hls_dir = None
    video_db = None
    
    try:
        video_db = Video.objects.get(id=video_id_hex)
        
        output_root = media_dir_to_file(video_id_hex)
        file_in = media_path_to_file(video_id_hex, original_ext)
        
        asset_dir = os.path.join(output_root, video_id_hex)
        manifest_path = os.path.join(asset_dir, f'stream.m3u8')
        os.makedirs(asset_dir, exist_ok=True)
        logger.debug(f'out={output_root}, asset_dir={asset_dir}, file_in={file_in}, manifest_path={manifest_path}')

        # extract metadata
        with imageio.get_reader(str(file_in)) as reader:
            meta = reader.get_meta_data()
            fps = float(meta["fps"])
            duration = float(meta["duration"]) * 1000.
            size = meta['size']
            
        segment_time = 5
        gop = max(1, int(round(fps * segment_time)))
        
        logger.info(f"Starting HLS conversion for {video_id_hex} from {file_in} to {manifest_path}")

        conversion_args = {
            "format": "hls",
            "hls_playlist_type": "vod",
            "hls_segment_type": "fmp4",
            "hls_flags" : "single_file+independent_segments",
            # "hls_segment_filename" : "stream.m4s",
            "segment_time" : segment_time,
            "vcodec" : "libx264",
            "acodec" : "aac",
            "audio_bitrate" : "128k",
            "g": gop, # GOP size should match segment duration
            "keyint_min": gop, # same as GOP
            "sc_threshold": 0, # no unpredictable keyframe insertions
            "crf": 23, # constant rate factor [0-51], lower: higher quality & larger file; higher: more compression & lower quality 
            "preset" : "medium", # controls encoding speed --vs.-- compression trade-off ["ultrafast" - "veryslow"]
            "pix_fmt": "yuv420p", # pixel format of the output
        }
        
        convert_to_hls(
            file_in,
            # original_ext.split(sep=".")[-1].lstrip("."), # NOTE: we do not need to provide the file extension.
            manifest_path,
            asynchronous=False, # TODO
            **conversion_args
        )
        
        # TODO: After being successful with this approach, make it async!
        # NOTE: alternative solution to allow logging of ffmpeg conversion process.
        """
        while True:
            if ffmpeg_proc.poll() is not None:
                break
            
            if ffmpeg_proc.stderr: 
                try:
                    # reads stderr out chunk by chunk to prevent the Popen process from blocking when using pipe_stderr=True
                    chunk = ffmpeg_proc.stderr.read1(4096).decode(errors="replace")
                    if chunk:
                        logger.debug(chunk.rstrip())
                except Exception:
                    pass
                
            if not Video.objects.filter(id=video_id_hex).exists():
                logger.info("Video deleted during HLS conversion, killing ffmpeg.")
                ffmpeg_proc.kill()
                ffmpeg_proc.wait()
                return
            
            time.sleep(_POLL_INTERVAL)
        """
        
        # TODO: safe way to check if all the segments have been written to the asset dir?
        media_candidates = list(asset_dir.glob("*.m4s")) + list(asset_dir.glob("*.mp4"))
        if not media_candidates:
            raise RuntimeError(f"No media file generated in {asset_dir}")
        media_path = media_candidates[0]

        # extract metadata
        reader      = imageio.get_reader(str(file_in))
        fps         = reader.get_meta_data().get('fps')
        duration    = reader.get_meta_data().get('duration') * 1000.0
        size        = reader.get_meta_data().get('size')

        # update DB (use update_fields to avoid re-inserting a deleted record)
        Video.objects.filter(id=video_id_hex).update(
            ext=".video_asset",
            fps=fps,
            duration=duration,
            width=size[0] if size else None,
            height=size[1] if size else None,
            status=Video.STATUS_DONE,
            asset_dir = str(asset_dir),
            manifest_path = str(manifest_path),
            media_path = str(media_path)
        )

        e = time.time()
        logger.info(f"HLS conversion took: {e-s}")

        # run plugins (thumbnail + any analyzers)
        plugin_manager = PluginManager()
        plugins = ["thumbnail"]
        if analyzers:
            plugins += analyzers
        for plugin in plugins:
            try:
                plugin_manager(plugin, video=video_db, user=video_db.owner)
            except Exception:
                logger.exception(f"Failed to schedule plugin {plugin}")
        
        delete_source = True

    except Exception:
        logger.exception("Video conversion failed")
        if video_db is not None:
            Video.objects.filter(id=video_id_hex).update(status=Video.STATUS_ERROR)
        safe_delete([archive_path, hls_dir])
        delete_source = True
    
    finally:
        if delete_source:  # cleanup routine
            try:
                remove_file(file_in)
                logger.debug(f"{file_in} removed successfully!")
            except Exception:
                logger.exception("Failed to remove original file")

@shared_task(bind=True)
def convert_video_to_hls(self, video_id_hex, original_ext, analyzers=None):
    s = time.time()
    
    archive_path = None
    hls_dir = None
    video_db = None
    
    try:
        video_db = Video.objects.get(id=video_id_hex)
        
        output_root = media_dir_to_file(video_id_hex)
        file_in = media_path_to_file(video_id_hex, original_ext)

        hls_dir = os.path.join(output_root, video_id_hex)
        manifest_path = os.path.join(hls_dir, f'{video_id_hex}.m3u8')
        os.makedirs(hls_dir, exist_ok=True)
        logger.debug(f'out={output_root}, hls_dir={hls_dir}, file_in={file_in}, manifest_path={manifest_path}')

        # extract metadata
        with imageio.get_reader(str(file_in)) as reader:
            meta = reader.get_meta_data()
            fps = float(meta["fps"])
            duration = float(meta["duration"]) * 1000.
            size = meta['size']
            
        segment_time = 5
        gop = max(1, int(round(fps * segment_time)))

        logger.info(f"Starting HLS conversion for {video_id_hex} from {file_in} to {manifest_path}")

        conversion_args = {
            "vid_fps" : fps,
            "format": "hls",
            "hls_playlist_type": "vod",
            "hls_segment_type": "mpegts",
            "hls_flags" : "independent_segments",
            # "hls_segment_filename" : "stream.m4s",
            "segment_time" : segment_time,
            "vcodec" : "libx264",
            "acodec" : "aac",
            "audio_bitrate" : "128k",
            "g": gop, # GOP size should match segment duration
            "keyint_min": gop, # same as GOP
            "sc_threshold": 0, # no unpredictable keyframe insertions
            "crf": 23, # constant rate factor [0-51], lower: higher quality & larger file; higher: more compression & lower quality 
            "preset" : "medium", # controls encoding speed --vs.-- compression trade-off ["ultrafast" - "veryslow"]
            "pix_fmt": "yuv420p", # pixel format of the output
        }

        ffmpeg_proc = convert_to_hls(
            str(file_in),
            # original_ext.split(sep=".")[-1].lstrip("."), # NOTE: we do not need to provide the file extension.
            str(manifest_path),
            asynchronous=True,
            **conversion_args
        )
        
        # NOTE: alternative solution to allow logging of ffmpeg conversion process.
        """
        while True:
            if ffmpeg_proc.poll() is not None:
                break
            
            if ffmpeg_proc.stderr: 
                try:
                    # reads stderr out chunk by chunk to prevent the Popen process from blocking when using pipe_stderr=True
                    chunk = ffmpeg_proc.stderr.read1(4096).decode(errors="replace")
                    if chunk:
                        logger.debug(chunk.rstrip())
                except Exception:
                    pass
                
            if not Video.objects.filter(id=video_id_hex).exists():
                logger.info("Video deleted during HLS conversion, killing ffmpeg.")
                ffmpeg_proc.kill()
                ffmpeg_proc.wait()
                return
            
            time.sleep(_POLL_INTERVAL)
        """
        while True:
            try: # poll for ffmpeg completion; check for cancellation (video deleted) each interval
                ffmpeg_proc.wait(timeout=_POLL_INTERVAL)
                break
            except subprocess.TimeoutExpired:
                if not Video.objects.filter(id=video_id_hex).exists():
                    logger.info(f"Video {video_id_hex} deleted during HLS conversion, killing ffmpeg.")
                    ffmpeg_proc.kill()
                    ffmpeg_proc.wait()
                    return

        if ffmpeg_proc.returncode != 0:
            stderr = ""
            if ffmpeg_proc.stderr:
                stderr = ffmpeg_proc.stderr.read().decode(errors="replace")
            raise RuntimeError(f"ffmpeg exited with code {ffmpeg_proc.returncode}: {stderr}")

        # check if video was deleted while we were converting
        if not Video.objects.filter(id=video_id_hex).exists():
            logger.info(f"Video {video_id_hex} deleted during conversion, aborting.")
            return

        # creates the archive to be transfered
        ext = '.tar.gz'
        archive_path = Path(f"{output_root}{video_id_hex}{ext}")
        with tarfile.open(archive_path, 'w:gz') as tar:
            tar.add(hls_dir, arcname='.', recursive=True)

        # update DB (use update_fields to avoid re-inserting a deleted record)
        Video.objects.filter(id=video_id_hex).update(
            ext=ext,
            fps=fps,
            duration=duration,
            width=size[0],
            height=size[1],
            status=Video.STATUS_DONE,
        )

        e = time.time()
        logger.info(f"HLS conversion took: {e-s}")

        # run plugins (thumbnail + any analyzers)
        plugin_manager = PluginManager()
        plugins = ["thumbnail"]
        if analyzers:
            plugins += analyzers
        for plugin in plugins:
            try:
                plugin_manager(plugin, video=video_db, user=video_db.owner)
            except Exception:
                logger.exception(f"Failed to schedule plugin {plugin}")
        
        delete_source = True
   
    except Exception:
        logger.exception("Video conversion failed")
        if video_db is not None:
            Video.objects.filter(id=video_id_hex).update(status=Video.STATUS_ERROR)
        safe_delete([archive_path, hls_dir])
        delete_source = True

    finally:
        if delete_source:  # cleanup routine
            try:
                remove_file(file_in)
                logger.debug(f"{file_in} removed successfully!")
            except Exception:
                logger.exception("Failed to remove original file")

def safe_delete(file_path):
    if type(file_path) == type([]): 
        for fp in file_path:
            path = Path(fp)
            try:
                if path.is_file():
                    path.unlink(missing_ok=True)
                elif path.is_dir():
                    shutil.rmtree(path, ignore_errors=True)
                logger.debug(f"Deleted {file_path}")
            except Exception as e:
                logger.warning(f"Failed to delete {file_path}: {e}")