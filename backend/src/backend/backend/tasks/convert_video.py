import os
import tarfile
import logging
from pathlib import Path

import imageio
from celery import shared_task

from backend.utils import media_dir_to_file, media_path_to_file
from utils.video_converter import convert_to_hls
from utils.helper import remove_file, remove_dir
from backend.models import Video
from backend.plugin_manager import PluginManager

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def convert_video(self, video_id_hex, original_ext, analyzers=None):
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
