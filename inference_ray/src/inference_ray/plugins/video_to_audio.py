from inference_ray.plugin import AnalyserPlugin, AnalyserPluginManager
from data import AudioData, VideoData, DataManager, Data


from typing import Callable, Optional, Dict

default_config = {"data_dir": "/data/"}


default_parameters = {"sample_rate": 48000, "sample_format": "pcm_s16le", "layout": "mono", "extension": "wav"}

requires = {
    "video": VideoData,
}

provides = {
    "audio": AudioData,
}


@AnalyserPluginManager.export("video_to_audio")
class VideoToAudio(
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
        import av

        def mux_audio(in_container, out_stream, out_container):
            in_stream = in_container.streams.audio[0]
            for frame in in_container.decode(in_stream):
                for packet in out_stream.encode(frame):
                    out_container.mux(packet)

        with inputs["video"] as input_data, data_manager.create_data("AudioData") as output_data:
            output_data.ext = parameters.get("extension")

            with input_data.open_video() as f_video, output_data.open_audio("w") as f_audio:
                with av.open(f_audio, "w", output_data.ext) as out_container:
                    out_stream = out_container.add_stream(
                        parameters.get("sample_format"),
                        rate=parameters.get("sample_rate"),
                        layout=parameters.get("layout"),
                    )

                    # Videos are cached either as one plain container file, or -- for
                    # HLS-style ingests -- as a tar bundle of .ts/.m4s/.mp4 segments (see
                    # utils.video_decoder.parse_meta_av/VideoDecoder, which split on the same
                    # is_archive() check to read frames). Mirror that here instead of
                    # assuming a single container: feeding the tar's raw bytes straight to
                    # av.open() fails with "Invalid data found when processing input". Also
                    # don't trust input_data.ext as a demuxer `format=` hint (it's whatever
                    # extension the file happened to be cached under, not reliably a valid
                    # PyAV format name) -- let PyAV sniff the real container from content,
                    # same as every other video-consuming plugin already does.
                    if hasattr(f_video, "is_archive") and f_video.is_archive():
                        segment_files = sorted(
                            f for f in f_video.list_files() if f.endswith((".ts", ".m4s", ".mp4"))
                        )
                        for segment_file in segment_files:
                            seg = f_video.open_nested(segment_file)
                            with av.open(seg, metadata_errors="ignore") as in_container:
                                mux_audio(in_container, out_stream, out_container)
                    else:
                        with av.open(f_video, metadata_errors="ignore") as in_container:
                            mux_audio(in_container, out_stream, out_container)

                    # Flush whatever the encoder is still holding onto internally.
                    for packet in out_stream.encode(None):
                        out_container.mux(packet)

            return {"audio": output_data}
