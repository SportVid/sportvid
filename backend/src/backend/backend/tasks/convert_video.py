import os
import subprocess
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

_POLL_INTERVAL = 2.0  # seconds between cancellation checks


@shared_task(bind=True)
def convert_video(self, video_id_hex, original_ext, analyzers=None):
    try:
        video_db = Video.objects.get(id=video_id_hex)
        output_dir = media_dir_to_file(video_id_hex)
        file_in = media_path_to_file(video_id_hex, original_ext)

        file_out = f"{output_dir}{video_id_hex}/{video_id_hex}.m3u8"
        os.makedirs(f"{output_dir}{video_id_hex}", exist_ok=True)

        logger.info(f"Starting conversion for {video_id_hex} from {file_in} to {file_out}")

        ffmpeg_proc = convert_to_hls(file_in, original_ext.split(sep='.')[-1].lstrip('.'), file_out)

        # Poll ffmpeg completion; check for cancellation (video deleted) each interval
        while True:
            try:
                ffmpeg_proc.wait(timeout=_POLL_INTERVAL)
                break  # ffmpeg finished normally
            except subprocess.TimeoutExpired:
                if not Video.objects.filter(id=video_id_hex).exists():
                    logger.info(f"Video {video_id_hex} deleted during conversion, killing ffmpeg")
                    ffmpeg_proc.kill()
                    ffmpeg_proc.wait()
                    return

        if ffmpeg_proc.returncode != 0:
            stderr = ffmpeg_proc.stderr.read() if ffmpeg_proc.stderr else b""
            raise Exception(f"ffmpeg exited with code {ffmpeg_proc.returncode}: {stderr.decode(errors='replace')}")

        # Guard: check if video was deleted while we were converting
        if not Video.objects.filter(id=video_id_hex).exists():
            logger.info(f"Video {video_id_hex} was deleted during conversion, aborting.")
            return

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

        # update DB (use update_fields to avoid re-inserting a deleted record)
        Video.objects.filter(id=video_id_hex).update(
            ext=ext,
            fps=fps,
            duration=duration,
            width=size[0],
            height=size[1],
            status=Video.STATUS_DONE,
        )
        video_db.ext = ext

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
