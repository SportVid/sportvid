import logging

from typing import Callable, Dict

from data import VideoData, VideoAssetData
from data import DataManager, Data

from inference_ray.plugin import AnalyserPlugin, AnalyserPluginManager

default_config = {
    "data_dir": "/data/",
    "host": "localhost",
    "port": 6379,
}

default_parameters = {
    "fmp4": True,
    "segment_time": 5,
}

requires = {
    "video": VideoData
}

provides = {
    "video_asset_data": VideoAssetData,
}


@AnalyserPluginManager.export("hls_convert")
class HLSConverter(
    AnalyserPlugin,
    config=default_config,
    parameters=default_parameters,
    version="0.1",
    requires=requires,
    provides=provides,
):
    def __init__(self, config=None, **kwargs):
        super().__init__(config, **kwargs)

        self.meta_dict = self._fresh_meta_dict()
        self.py_dict = {}
    
    def convert_video_to_hls(self, file_in, dir_out, fmp4=False, async_=False):
        import imageio
        import os
        import shutil
        import subprocess
        
        os.makedirs(dir_out, exist_ok=True)
        manifest_path = os.path.join(dir_out, f'stream.m3u8')

        # extract metadata
        with imageio.get_reader(str(file_in)) as reader:
            meta = reader.get_meta_data()
            fps = float(meta["fps"])
            # duration = float(meta["duration"]) * 1000.
            # size = meta['size']
        
        segment_time = 5
        gop = max(1, int(round(fps * segment_time)))
        
        if fmp4:
            conversion_args.update({ 
                "hls_segment_type": "fmp4",
                "hls_flags" : "single_file+independent_segments",
            })
        else:
            conversion_args.update({ 
                "hls_segment_type": "mpegts",
                "hls_flags" : "independent_segments",
            })
            
                
            conversion_args = {
                "format": "hls",
                "threads": 1, # TODO: check thread count for HLS conversion. Queue 2-3 video uploads, check ffmpeg processes and CPU usage. 
                    # ps -ef | grep ffmpeg
                    # top -H -p <ffmpeg_pid>
                "hls_playlist_type": "vod",
                "hls_segment_type": "fmp4",
                "hls_flags" : "single_file+independent_segments",
                "segment_time" : segment_time,
                # -------- input: hardware acceleration
                "hwaccel": "cuda",
                "hwaccel_output_format": "cuda",
                # -------- output: video/audio options
                "vcodec" : "h264_nvenc", # libx264
                "acodec" : "aac",
                "audio_bitrate" : "128k",
                # -------- HLS stuff
                "g": gop, # GOP size should match segment duration
                "keyint_min": gop, # same as GOP
                "sc_threshold": 0, # no unpredictable keyframe insertions
                # "crf": 23,              # constant rate factor [0-51], lower: higher quality & larger file; higher: more compression & lower quality 
                # -------- NVENC tuning
                "preset": "fast",       # controls encoding speed --vs.-- compression trade-off ["ultrafast" - "veryslow"]
                "rc": "vbr",
                "cq": 23,
                # -------- output compat
                # "pix_fmt": "yuv420p", # pixel format of the output
            }
        else:
            conversion_args = {
                "vid_fps" : fps,
                "format": "hls",
                "threads": 1, # TODO: check thread count for HLS conversion. Queue 2-3 video uploads, check ffmpeg processes and CPU usage. 
                                # ps -ef | grep ffmpeg
                                # top -H -p <ffmpeg_pid>
                "hls_playlist_type": "vod",
                "hls_segment_type": "mpegts",
                "hls_flags" : "independent_segments",
                "segment_time" : segment_time,
                # -------- input: hardware acceleration
                "hwaccel": "cuda",
                "hwaccel_output_format": "cuda",
                # -------- output: video/audio options
                "vcodec" : "h264_nvenc", # libx264
                "acodec" : "aac",
                "audio_bitrate" : "128k",
                # -------- HLS stuff
                "g": gop,               # GOP size should match segment duration
                "keyint_min": gop,      # same as GOP
                "sc_threshold": 0,      # no unpredictable keyframe insertions
                # "crf": 23,              # constant rate factor [0-51], lower: higher quality & larger file; higher: more compression & lower quality 
                # -------- NVENC tuning
                "preset": "fast",       # controls encoding speed --vs.-- compression trade-off ["ultrafast" - "veryslow"]
                "rc": "vbr",
                "cq": 23,
                # -------- output compat
                # "pix_fmt": "yuv420p", # pixel format of the output
            }
        
        if async_:
            ffmpeg_proc = convert_to_hls(
                str(file_in),
                str(manifest_path),
                asynchronous=True,
                **conversion_args
            )
            while True:
                try: # poll for ffmpeg completion; check for cancellation (video deleted) each interval
                    ffmpeg_proc.wait(timeout=2)
                    break
                except subprocess.TimeoutExpired:
                    ffmpeg_proc.kill()
                    ffmpeg_proc.wait()
                    return

            if ffmpeg_proc.returncode != 0:
                stderr = ""
                if ffmpeg_proc.stderr:
                    stderr = ffmpeg_proc.stderr.read().decode(errors="replace")
                raise RuntimeError(f"ffmpeg exited with code {ffmpeg_proc.returncode}: {stderr}")
        else: 
            self.convert_to_hls(
                file_in,
                manifest_path,
                asynchronous=False,
                **conversion_args
            )
    
    def convert_to_hls(self, file_in, manifest_path, asynchronous=True, **kwargs):
        """
        Start HLS conversion using the ffmpeg python wrapper.
        Returns a running subprocess (via Popen).
        Caller is responsible for waiting on the subprocess & handling termination.
        Example call: 
            $ fmpeg -i in.mp4 -codec: copy -start_number 0 -hls_time 10 -hls_list_size 0 -f hls out.m3u8
        """
        import ffmpeg
        
        input_stream = ffmpeg.input(
            file_in,
            hwaccel=kwargs.get("hwaccel"),
            hwaccel_output_format=kwargs.get("hwaccel_output_format"),    
        )  
        
        output_kwargs = {
            "format": kwargs.get("format", "hls"),
            "threads": kwargs.get("threads"),
            "start_number": 0,
            "hls_time": kwargs.get("hls_time", kwargs.get("segment_time", 10)),
            "hls_list_size": kwargs.get("hls_list_size", 0),
            "hls_playlist_type": kwargs.get("hls_playlist_type", "vod"),
            "hls_segment_type": kwargs.get("hls_segment_type", "mpegts"),
            "hls_flags": kwargs.get("hls_flags", "independent_segments"),
            "hls_segment_filename": kwargs.get("hls_segment_filename"),
            "vcodec": kwargs.get("vcodec"),
            "acodec": kwargs.get("acodec"),
            "audio_bitrate": kwargs.get("audio_bitrate"),
            "preset": kwargs.get("preset"),
            "crf": kwargs.get("crf", 23),
            "rc": kwargs.get("rc", "vbr"),
            "cq": kwargs.get("cq", 23),
            "g": kwargs.get("g", kwargs.get("gop")),
            "keyint_min": kwargs.get("keyint_min", kwargs.get("g", kwargs.get("gop"))),
            "sc_threshold": kwargs.get("sc_threshold", 0),
            "pix_fmt": kwargs.get("pix_fmt"),
            "movflags": kwargs.get("movflags"),
        }
        
        output_kwargs = {k: v for k, v in output_kwargs.items() if v is not None}

        output_stream = ffmpeg.output(input_stream, manifest_path, **output_kwargs)
        output_stream = ffmpeg.overwrite_output(output_stream)
        
        cmd = [str(x) for x in ffmpeg.compile(output_stream)]
        cmd.insert(1, "-nostdin")
        cmd.insert(2, "-loglevel")
        cmd.insert(3, "error")

        print("FFmpeg command:", " ".join(cmd))

        if asynchronous:
            return subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
            #     return ffmpeg.run_async(
            #         output_stream, 
            #         quiet=False,
            #         pipe_stderr=True,
            #         pipe_stdout=False,
            #         pipe_stdin=False
            #     )
        else:
            completed = subprocess.run(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            # return ffmpeg.run(output_stream)
            if completed.returncode != 0:
                raise RuntimeError(f"ffmpeg exited with code {completed.returncode}: {completed.stderr}")
            return completed
        
        
    def call(
        self,
        inputs: Dict[str, Data],
        data_manager: DataManager,
        parameters: Dict = None,
        callbacks: Callable = None,
    ) -> Dict[str, Data]: 
        
        with inputs["video"] as input_data, data_manager.create_data("VideoAssetData") as output_data:
            video_file = input_data.open_video()
            
            # TODO: actual conversion logic
            
            # TODO: write directly into media path?!
            # TODO: if not, delete redundant data created by this plugin
            
            self.update_callbacks(callbacks, progress=1.0)
            
        
        