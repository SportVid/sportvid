import logging
from typing import Callable, Optional, Dict

from data import (
    DataManager, Data,
    ImageData, VideoAssetData, ImagesData
)
from inference_ray.plugin import AnalyserPlugin, AnalyserPluginManager
from utils import VideoDecoder


default_config = {
    "data_dir": "/data"
}

default_parameters = {
    "fps": 5.0, 
    "max_dimension": 128
}

requires = {
    "video": VideoData,
}

provides = {
    "images": ImageData,
}


@AnalyserPluginManager.export("thumbnail_generator")
class ThumbnailGenerator(
    AnalyserPlugin,
    config=default_config,
    parameters=default_parameters,
    version="0.1",
    requires=requires,
    provides=provides,
):
    def __init__(self, config=None, **kwargs):
        super().__init__(config, **kwargs)

    def call(
        self,
        inputs: Dict[str, Data],
        data_manager: DataManager,
        parameters: Dict = None,
        callbacks: Callable = None,
    ) -> Dict[str, Data]:
        with inputs["video"] as input_data:
            f_video = input_data.open_video()
            try:
                video_decoder = VideoDecoder(
                    f_video,
                    fps=parameters.get("fps"),
                    extension=f".{input_data.ext}",
                    ref_id=input_data.id,
                )

                duration_ms = video_decoder.duration()
                sample_fps = video_decoder.fps()

                if duration_ms is None or sample_fps is None or duration_ms <= 0 or sample_fps <= 0:
                    raise RuntimeError(
                        f"Invalid video metadata: duration_ms={duration_ms}, fps={sample_fps}"
                    )

                num_frames = int((duration_ms / 1000.0) * sample_fps)
                if num_frames <= 0:
                    raise RuntimeError(
                        f"Video has no decodable frames: duration_ms={duration_ms}, fps={sample_fps}"
                    )

                with data_manager.create_data("ImagesData") as output_data:
                    for i, frame in enumerate(video_decoder):
                        self.update_callbacks(callbacks, progress=i / num_frames)
                        output_data.save_image(
                            frame.get("frame"),
                            ext="jpg",
                            time=frame.get("time"),
                            delta_time=1000 / parameters.get("fps"),
                        )
                self.update_callbacks(callbacks, progress=1.0)
                
                return {"images": output_data}
            finally:
                if hasattr(f_video, "close"):
                    try:
                        f_video.close()
                    except Exception:
                        pass

            