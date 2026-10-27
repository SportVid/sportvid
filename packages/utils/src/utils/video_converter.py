from __future__ import annotations

import functools
import logging
import os
import signal
import subprocess
import ffmpeg
from collections.abc import Mapping
from typing import Any


logger = logging.getLogger(__name__)

# HLS_ENCODER values: "auto" picks NVENC when this machine can encode with it, else libx264
HLS_ENCODERS = ("auto", "nvenc", "x264")

# encoder-specific output options; everything else in the HLS call is shared
_ENCODER_ARGS = {
    # crf: constant rate factor [0-51], lower means higher quality and larger files
    "x264": {"vcodec": "libx264", "crf": 23},
    # preset trades encoding speed against compression [p1-p7]; vbr with cq 23 is close to crf 23
    "nvenc": {"vcodec": "h264_nvenc", "preset": "p4", "rc": "vbr", "cq": 23},
}


@functools.lru_cache(maxsize=1)
def nvenc_available() -> bool:
    """Whether h264_nvenc works here, checked once per process.

    `ffmpeg -encoders` only shows build support, so this encodes a few black frames:
    that also needs an NVIDIA GPU and the driver's video capability in the container.
    """
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin",
        "-f", "lavfi", "-i", "color=c=black:s=256x256:d=0.2",
        "-c:v", "h264_nvenc", "-f", "null", "-",
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as e:
        logger.info("NVENC probe failed, using libx264: %s", e)
        return False
    if result.returncode != 0:
        logger.info("NVENC not available, using libx264: %s", result.stderr.strip()[-300:])
        return False
    return True


def resolve_hls_encoder(setting: str | None) -> str:
    """Map an HLS_ENCODER value to "nvenc" or "x264"."""
    value = (setting or "auto").strip().lower()
    if value not in HLS_ENCODERS:
        raise ValueError(f"HLS_ENCODER must be one of {HLS_ENCODERS}, got {setting!r}")
    if value == "auto":
        return "nvenc" if nvenc_available() else "x264"
    return value


def hls_encoder_args(encoder: str) -> dict[str, Any]:
    return dict(_ENCODER_ARGS[encoder])


def terminate_process_group(
    process: subprocess.Popen[str],
    grace_seconds: float = 10.0,
) -> None:
    """Terminate FFmpeg and any children started in its process group."""
    if process.poll() is not None: return

    try: os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError: return

    try:
        process.wait(timeout=grace_seconds)
        return
    except subprocess.TimeoutExpired: pass

    try: os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError: return

    try: process.wait()
    except ChildProcessError: pass


def _build_command(
    file_in: str,
    manifest_path: str,
    kwargs: Mapping[str, Any],
) -> list[str]:
    input_kwargs: dict[str, Any] = {}

    # NOTE: Defining these offloads encoding to the GPU via CUDA.
    input_args = [
        # "hwaccel",
        # "hwaccel_output_format",
        # "extra_hw_frames",
    ]
    for name in input_args:
        value = kwargs.get(name)
        if value is not None: input_kwargs[name] = value

    input_stream = ffmpeg.input(file_in, **input_kwargs)
    output_kwargs = {
        "format": kwargs.get("format", "hls"),
        "threads": kwargs.get("threads"),
        "start_number": 0,
        "hls_time": kwargs.get("hls_time",
            kwargs.get("segment_time", 5),
        ),
        "hls_list_size": kwargs.get("hls_list_size", 0),
        "hls_playlist_type": kwargs.get("hls_playlist_type",
            "vod",
        ),
        "hls_segment_type": kwargs.get("hls_segment_type",
            "mpegts",
        ),
        "hls_flags": kwargs.get("hls_flags",
            "independent_segments",
        ),
        "hls_segment_filename": kwargs.get("hls_segment_filename"),
        "hls_fmp4_init_filename": kwargs.get("hls_fmp4_init_filename"),
        "vcodec": kwargs.get("vcodec"),
        "acodec": kwargs.get("acodec"),
        "audio_bitrate": kwargs.get("audio_bitrate"),
        "preset": kwargs.get("preset"),
        "crf": kwargs.get("crf"),
        "rc": kwargs.get("rc"),
        "cq": kwargs.get("cq"),
        "g": kwargs.get("g", kwargs.get("gop")),
        "keyint_min": kwargs.get("keyint_min",
            kwargs.get("g", kwargs.get("gop")),
        ),
        "sc_threshold": kwargs.get("sc_threshold"),
        "pix_fmt": kwargs.get("pix_fmt"),
        "movflags": kwargs.get("movflags"),
        "bf": kwargs.get("bf"),
        "surfaces": kwargs.get("surfaces"),
    }

    output_kwargs = {
        key: value
        for key, value in output_kwargs.items()
        if value is not None
    }

    output_stream = ffmpeg.output(
        input_stream,
        manifest_path,
        **output_kwargs,
    )
    output_stream = ffmpeg.overwrite_output(output_stream)

    command = [str(value) for value in ffmpeg.compile(output_stream)]
    if not command: raise RuntimeError("FFmpeg command was empty.")

    base = [
        command[0],
        "-progress",
        "pipe:1",
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        str(kwargs.get("loglevel", "warning")),
        *command[1:]   
    ]
    
    return base


def convert_to_hls(
    file_in: str,
    manifest_path: str,
    **kwargs: Any,
) -> subprocess.Popen[str] | subprocess.CompletedProcess[str]:
    """Convert a media file to HLS using FFmpeg.

    Returns a running Popen instance. 
    FFmpeg's stderr is inherited by the worker/container logger, avoiding a pipe-buffer
    deadlock. The process starts in its own session so callers can terminate
    its entire process group using `terminate_process_group`.
    
    Caller must drain stdout to avoid blocking FFmpeg.
    """
    command = _build_command(file_in, manifest_path, kwargs)
    logger.debug("FFmpeg command: %s", " ".join(command))

    return subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=None,
        start_new_session=True,
        text=True,
    )


def probe_media_start(file_path: str) -> float:
    """First presentation timestamp of a media file, in seconds.

    Used to verify that a converted HLS asset actually starts at the timeline
    position its playlist advertises -- see the guard in convert_video.py.
    """
    info = ffmpeg.probe(file_path)
    start = info.get("format", {}).get("start_time")
    return float(start) if start is not None else 0.0
