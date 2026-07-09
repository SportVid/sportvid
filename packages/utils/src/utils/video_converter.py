import ffmpeg
import subprocess
import logging

def convert_to_hls(file_in, manifest_path, asynchronous = True, **kwargs):
    """
    Start HLS conversion using the ffmpeg python wrapper.
    Returns a running subprocess (via Popen).
    Caller is responsible for waiting on the subprocess & handling termination.
    """
    input_stream = ffmpeg.input(
        file_in,
        # NOTE: offloads encoding to the GPU via CUDA.
        hwaccel=kwargs.get("hwaccel"),
        hwaccel_output_format=kwargs.get("hwaccel_output_format"),    
    )  
    
    output_kwargs = {
        "format": kwargs.get("format", "hls"),
        "threads": kwargs.get("threads"),
        "start_number": 0,
        "hls_time": kwargs.get("hls_time", kwargs.get("segment_time", 5)),
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
        "sc_threshold": kwargs.get("sc_threshold", 0), # NOTE: x264 encoder lib option
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

    # print("FFmpeg command:", " ".join(cmd))

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
        if completed.returncode != 0:
            raise RuntimeError(f"ffmpeg exited with code {completed.returncode}: {completed.stderr}")
        return completed
    
