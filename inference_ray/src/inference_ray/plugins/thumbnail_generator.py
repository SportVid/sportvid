import logging

from inference_ray.plugin import AnalyserPlugin, AnalyserPluginManager

from utils import VideoDecoder
from data import ImageData, VideoAssetData, ImagesData
from utils import VideoDecoder
from data import DataManager, Data

from typing import Callable, Optional, Dict


default_config = {"data_dir": "/data"}


default_parameters = {"fps": 5.0, "max_dimension": 128}

requires = {
    "video": VideoAssetData,
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
        with inputs["video"] as input_data, data_manager.create_data("ImagesData") as output_data:
            f_video = input_data.open_video()
            try:
                video_decoder = VideoDecoder(
                    video_object=f_video,
                    fps=parameters.get("fps"),
                    max_dimension=parameters.get("max_dimension"),
                    extension=f".{input_data.ext}",
                )
                num_frames = (video_decoder.duration() / 1000.) * video_decoder.fps()
                for i, frame in enumerate(video_decoder):
                    self.update_callbacks(callbacks, progress=i / num_frames)
                    output_data.save_image(
                        frame.get("frame"), ext="jpg", time=frame.get("time"), delta_time=1000 / parameters.get("fps")
                    )
                self.update_callbacks(callbacks, progress=1.0)
            finally:
                if hasattr(f_video, 'close'):
                    f_video.close()

            # with input_data.open_video() as f_video:
            #     video_decoder = VideoDecoder(
            #         video_object=f_video,
            #         fps=parameters.get("fps"),
            #         max_dimension=parameters.get("max_dimension"),
            #         extension=f".{input_data.ext}",
            #     )

            #     num_frames = (video_decoder.duration() / 1000.) * video_decoder.fps()
            #     for i, frame in enumerate(video_decoder):
            #         self.update_callbacks(callbacks, progress=i / num_frames)

            #         output_data.save_image(
            #             frame.get("frame"), ext="jpg", time=frame.get("time"), delta_time=1000 / parameters.get("fps")
            #         )

            #     self.update_callbacks(callbacks, progress=1.0)
            
            return {"images": output_data}
