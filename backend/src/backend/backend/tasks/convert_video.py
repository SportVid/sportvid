import os
import shutil
import tarfile
import logging
from pathlib import Path

import imageio
from celery import shared_task
from django.conf import settings

from backend.utils import media_dir_to_file, media_path_to_file
from utils.video_converter import convert_to_hls
from utils.helper import remove_file, remove_dir
from backend.models import Video
from backend.plugin_manager import PluginManager

logger = logging.getLogger(__name__)

@shared_task
def cleanup_upload_orphans():
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
def convert_video(video_id_hex, original_ext, analyzers=None):
    
    archive_path = ""; hls_dir = ""
    try:
        video_db = Video.objects.get(id=video_id_hex)
        output_dir = media_dir_to_file(video_id_hex)
        file_in = media_path_to_file(video_id_hex, original_ext)

        file_out = f"{output_dir}{video_id_hex}/{video_id_hex}.m3u8"
        os.makedirs(f"{output_dir}{video_id_hex}", exist_ok=True)

        logger.info(f"Starting conversion for {video_id_hex} from {file_in} to {file_out}")

        convert_to_hls(file_in, original_ext.split(sep='.')[-1].lstrip('.'), file_out)

        # create archive
        ext = '.tar.gz'
        archive_path = Path(f"{output_dir}{video_id_hex}{ext}")
        hls_dir = Path(f"{output_dir}{video_id_hex}/")

        with tarfile.open(archive_path, 'w:gz') as tar:
            tar.add(hls_dir, arcname='.', recursive=True)

        # extract metadata
        reader = imageio.get_reader(str(file_in))
        fps = reader.get_meta_data().get('fps')
        duration = reader.get_meta_data().get('duration') * 1000.0
        size = reader.get_meta_data().get('size')

        # update DB
        video_db.ext = ext
        video_db.fps = fps
        video_db.duration = duration
        video_db.width = size[0]
        video_db.height = size[1]
        video_db.status = Video.STATUS_DONE
        video_db.save()

        # cleanup
        try:
            if remove_file(file_in):
                logger.debug(f"{file_in} removed successfully!")
        except Exception:
            logger.exception("Failed to remove original file")

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

    except Exception:
        logger.exception("Video conversion failed")
        try:
            video_db = Video.objects.get(id=video_id_hex)
            video_db.status = Video.STATUS_ERROR
            video_db.save()
        except Exception:
            logger.exception("Failed to mark video as error")
        finally:
            safe_delete([archive_path, hls_dir])


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