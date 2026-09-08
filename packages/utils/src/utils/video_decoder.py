import logging
from pathlib import Path

import imageio.v3 as iio
import av
import numpy as np


def _resolve_video_source(video_object):
    if hasattr(video_object, "is_archive") and video_object.is_archive():
        return {"mode": "archive", "object": video_object}
    if hasattr(video_object, "media_path") and callable(video_object.media_path):
        return {"mode": "path", "path": str(video_object.media_path())}
    if isinstance(video_object, (str, Path)):
        return {"mode": "path", "path": str(video_object)}
    if hasattr(video_object, "read"):
        return {"mode": "fileobj", "fileobj": video_object}
    raise ValueError(f"Unsupported video source: {type(video_object)}")

def parse_meta_av(video_object):
    """
    Parse metadata from:
    - legacy archive wrapper,
    - plain video path,
    - file-like object,
    - VideoAssetData/media-path backed object.
    """
    try:
        src = _resolve_video_source(video_object)

        if src["mode"] == "archive":
            meta_data = {}
            files = src["object"].list_files()
            segment_files = sorted([f for f in files if f.endswith((".ts", ".m4s", ".mp4"))])
            if not segment_files:
                return {}

            total_duration = 0.0
            for i, segment_file in enumerate(segment_files):
                seg = src["object"].open_nested(segment_file)
                container = av.open(seg)
                stream = container.streams.video[0]

                seg_duration = 0.0
                if stream.duration and stream.time_base:
                    seg_duration = float(stream.duration * stream.time_base)
                total_duration += seg_duration

                if i == 0:
                    meta_data = {
                        "fps": float(stream.average_rate) if stream.average_rate else None,
                        "width": stream.codec_context.width,
                        "height": stream.codec_context.height,
                        "size": (stream.codec_context.width, stream.codec_context.height),
                        "duration": 0.0,
                        "codec": stream.codec_context.name,
                    }

                container.close()

            meta_data["duration"] = total_duration
            return meta_data

        if src["mode"] == "path":
            fh = av.open(src["path"])
        else:
            fh = av.open(src["fileobj"])

        stream = fh.streams.video[0]
        meta_data = {
            "fps": float(stream.average_rate) if stream.average_rate else None,
            "width": stream.codec_context.width,
            "height": stream.codec_context.height,
            "size": (stream.codec_context.width, stream.codec_context.height),
            "duration": float(stream.duration * stream.time_base) if stream.duration and stream.time_base else None,
            "codec": stream.codec_context.name,
        }
        fh.close()
        return meta_data

    except Exception:
        logging.exception("Failed to parse video metadata")
        return {}

class VideoDecoder:
    def __init__(self, video_object, max_dimension=None, fps=None, ref_id=None, **kwargs):
        self._video_object = video_object
        self._max_dimension = max_dimension
        self._fps = fps
        self._ref_id = ref_id
        self._kwargs = kwargs

        self._source = _resolve_video_source(video_object)

        self._meta = parse_meta_av(self._video_object)
        self._size = self._meta.get("size")
        self._real_fps = self._meta.get("fps")
        self._duration = self._meta.get("duration")

    def _compute_resize(self, width, height):
        if self._max_dimension is None:
            return width, height

        if isinstance(self._max_dimension, (list, tuple)):
            return self._max_dimension[0], self._max_dimension[1]

        res_calc = max(height, width)
        scale = min(self._max_dimension / res_calc, 1)
        return round(width * scale), round(height * scale)

    def __iter__(self):
        fps = self._real_fps if self._fps is None else self._fps
        frame_index = 0

        if self._source["mode"] == "archive":
            files = self._video_object.list_files()
            segment_files = sorted([f for f in files if f.endswith((".ts", ".m4s", ".mp4"))])

            for segment_file in segment_files:
                file_obj = self._video_object.open_nested(segment_file)
                container = av.open(file_obj)
                stream = container.streams.video[0]

                for frame in container.decode(video=0):
                    frame = frame.reformat(format="rgb24")

                    if self._fps is not None:
                        target_frame_time = frame_index / self._fps
                        actual_frame_time = float(frame.pts * stream.time_base) if frame.pts is not None else 0.0
                        if actual_frame_time < target_frame_time - (0.5 / self._fps):
                            continue

                    if self._max_dimension is not None:
                        w, h = self._compute_resize(frame.width, frame.height)
                        frame = frame.reformat(width=w, height=h, format="rgb24")

                    yield {
                        "time": int(float(frame_index / fps) * 1000),
                        "index": frame_index,
                        "frame": frame.to_ndarray(),
                        "ref_id": self._ref_id,
                        "delta_time": float(frame_index / fps),
                    }
                    frame_index += 1

                container.close()
            return

        if self._source["mode"] == "path":
            input_source = self._source["path"]
        else:
            input_source = self._source["fileobj"]

        container = av.open(input_source)
        stream = container.streams.video[0]

        for frame in container.decode(video=0):
            frame = frame.reformat(format="rgb24")

            if self._fps is not None:
                target_frame_time = frame_index / self._fps
                actual_frame_time = float(frame.pts * stream.time_base) if frame.pts is not None else 0.0
                if actual_frame_time < target_frame_time - (0.5 / self._fps):
                    continue

            if self._max_dimension is not None:
                w, h = self._compute_resize(frame.width, frame.height)
                frame = frame.reformat(width=w, height=h, format="rgb24")

            yield {
                "time": int(float(frame_index / fps) * 1000),
                "index": frame_index,
                "frame": frame.to_ndarray(),
                "ref_id": self._ref_id,
                "delta_time": float(frame_index / fps),
            }
            frame_index += 1

        container.close()

    def __len__(self):
        if self.duration() is None or self.fps() is None:
            return 0
        return int((self.duration() / 1000) * self.fps())

    def fps(self):
        return float(self._real_fps if self._fps is None else self._fps)

    def duration(self):
        if self._duration is None:
            return 0
        return self._duration * 1000 if self._duration < 10000 else self._duration


class VideoBatcher:
    def __init__(self, video_decoder: VideoDecoder, batch_size=8):
        self.video_decoder = video_decoder
        self.batch_size = batch_size

    def __iter__(self):
        cache = []
        for x in self.video_decoder:
            cache.append(x)

            if len(cache) >= self.batch_size:
                yield {
                    "time": [x["time"] for x in cache],
                    "index": [x["index"] for x in cache],
                    "frame": np.stack([x["frame"] for x in cache]),
                    "ref_id": [x["ref_id"] for x in cache],
                }
                cache = []

        if len(cache) > 0:
            yield {
                "time": [x["time"] for x in cache],
                "index": [x["index"] for x in cache],
                "frame": np.stack([x["frame"] for x in cache]),
                "ref_id": [x["ref_id"] for x in cache],
            }

    def fps(self):
        return self.video_decoder.fps()

    def duration(self):
        return self.video_decoder.duration()