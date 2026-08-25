from __future__ import annotations

import logging
import os
import signal
import subprocess
import ffmpeg
from collections.abc import Mapping
from typing import Any


logger = logging.getLogger(__name__)


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

    for name in (
        "hwaccel",
        "hwaccel_output_format",
        "extra_hw_frames",
    ):
        value = kwargs.get(name)
        if value is not None: input_kwargs[name] = value

    input_stream = ffmpeg.input(file_in, **input_kwargs)
    output_kwargs = {
        "format": kwargs.get("format", "hls"),
        "threads": kwargs.get("threads"),
        "start_number": 0,
        "hls_time": kwargs.get(
            "hls_time",
            kwargs.get("segment_time", 5),
        ),
        "hls_list_size": kwargs.get("hls_list_size", 0),
        "hls_playlist_type": kwargs.get(
            "hls_playlist_type",
            "vod",
        ),
        "hls_segment_type": kwargs.get(
            "hls_segment_type",
            "mpegts",
        ),
        "hls_flags": kwargs.get(
            "hls_flags",
            "independent_segments",
        ),
        "hls_segment_filename": kwargs.get(
            "hls_segment_filename"
        ),
        "hls_fmp4_init_filename": kwargs.get(
            "hls_fmp4_init_filename"
        ),
        "vcodec": kwargs.get("vcodec"),
        "acodec": kwargs.get("acodec"),
        "audio_bitrate": kwargs.get("audio_bitrate"),
        "preset": kwargs.get("preset"),
        "crf": kwargs.get("crf"),
        "rc": kwargs.get("rc"),
        "cq": kwargs.get("cq"),
        "g": kwargs.get("g", kwargs.get("gop")),
        "keyint_min": kwargs.get(
            "keyint_min",
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

    return [
        command[0],
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        str(kwargs.get("loglevel", "warning")),
        *command[1:],
    ]


def convert_to_hls(
    file_in: str,
    manifest_path: str,
    asynchronous: bool = True,
    **kwargs: Any,
) -> subprocess.Popen[str] | subprocess.CompletedProcess[str]:
    """Convert a media file to HLS using FFmpeg.

    Asynchronous mode returns a running Popen instance. FFmpeg's stderr is
    inherited by the worker/container logger, avoiding a pipe-buffer
    deadlock. The process starts in its own session so callers can terminate
    its entire process group using `terminate_process_group()`.
    """
    command = _build_command(file_in, manifest_path, kwargs)
    logger.debug("FFmpeg command: %s", " ".join(command))

    if asynchronous:
        return subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=None,
            start_new_session=True,
            text=True,
        )

    completed = subprocess.run(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        raise RuntimeError(
            f"FFmpeg exited with code {completed.returncode}: "
            f"{stderr[-4000:]}"
        )

    return completed