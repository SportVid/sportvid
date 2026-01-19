import logging

import imageio.v3 as iio
import av
import numpy as np


def parse_meta_av(video_object):
    """
    Parse metadata from HLS archive or regular video file.
    No frame decoding required.
    """
    try:
        meta_data = {}
        # check if this is an archive wrapper with nested tar
        if hasattr(video_object, 'is_archive') and video_object.is_archive():
            files = video_object.list_files()
            
            segment_files = sorted([f for f in files if f.endswith(('.ts', '.m4s', '.mp4'))])
            if not segment_files: return {}
            
            # loop through segments and get metadata from first one
            for i, segment_file in enumerate(segment_files):
                seg = video_object.open_nested(segment_file)
                container = av.open(seg)
                stream = container.streams.video[0]

                if i == 0:
                    meta_data = {
                        "fps": float(stream.average_rate) if stream.average_rate else None,
                        "width": stream.codec_context.width,
                        "height": stream.codec_context.height,
                        "size": (stream.codec_context.width, stream.codec_context.height),
                        "duration": float(stream.duration * stream.time_base),
                        "codec": stream.codec_context.name,
                    }
                
                if stream.duration and stream.time_base:
                    meta_data["duration"] += float(stream.duration * stream.time_base)
                
                container.close()
            
        else: # regular video file
            fh = av.open(video_object)
            stream = fh.streams.video[0]
            meta_data = {
                "fps": float(stream.average_rate) if stream.average_rate else None,
                "width": stream.codec_context.width,
                "height": stream.codec_context.height,
                "size": (stream.codec_context.width, stream.codec_context.height),
                "duration": float(stream.duration * stream.time_base),
                "codec": stream.codec_context.name,
            }
        
            fh.close()
        return meta_data
            
    except Exception as e:
        return {}


class VideoDecoder:
    def __init__(self, video_object, max_dimension=None, fps=None, ref_id=None, **kwargs):
        """Provides an iterator over the frames of a video.

        Args:
            video_object (ArchiveFileWrapper): Handle 
            max_dimension (Union[List, int], optional): Resize the video by providing either
                - a list of shape [width, height] or
                - an int that depicts the longer side of the frame.
                Defaults to None.
            fps (int, optional): Frames per second. Defaults to None.
        """
        self._video_object = video_object
        self._max_dimension = max_dimension
        self._fps = fps
        self._ref_id = ref_id

        self._meta = parse_meta_av(self._video_object)
        self._size = self._meta.get("size")
        self._real_fps = self._meta.get("fps")
        self._duration = self._meta.get("duration")

        self._kwargs = kwargs

    def __iter__(self):
        filter_sequence = []

        if self._fps is not None:
            filter_sequence.append(("fps", {"fps": f"{self._fps}", "round": "up"}))

        if self._max_dimension is not None:
            if isinstance(self._max_dimension, (list, tuple)):
                res = self._max_dimension
            else:
                res = max(self._size[1], self._size[0])
                scale = min(self._max_dimension / res, 1)
                res = (round(self._size[0] * scale), round(self._size[1] * scale))
            filter_sequence.append(("scale", {"width": f"{res[0]}", "height": f"{res[1]}"}))
        
        fps = self._real_fps if self._fps is None else self._fps
        
        if hasattr(self._video_object, 'is_archive') and self._video_object.is_archive():
            files = self._video_object.list_files()
            segment_files = sorted([f for f in files if f.endswith(('.ts', '.m4s', '.mp4'))])
            
            frame_index = 0
            
            for segment_file in segment_files:
                file_obj = self._video_object.open_nested(segment_file)
                container = av.open(file_obj)
                
                # Decode frames with manual filtering
                stream = container.streams.video[0]
                
                for frame in container.decode(video=0):
                    # Apply transformations manually instead of using filter graph
                    frame = frame.reformat(format="rgb24")
                    
                    # Manual FPS filtering - skip frames if needed
                    if self._fps is not None:
                        target_frame_time = frame_index / self._fps
                        actual_frame_time = float(frame.pts * stream.time_base) if frame.pts else 0
                        
                        # Skip this frame if we're ahead of schedule
                        if actual_frame_time < target_frame_time - (0.5 / self._fps):
                            continue
                    
                    # Manual scaling using PIL or frame.reformat
                    if self._max_dimension is not None:
                        if isinstance(self._max_dimension, (list, tuple)):
                            res = self._max_dimension
                        else:
                            res_calc = max(frame.height, frame.width)
                            scale = min(self._max_dimension / res_calc, 1)
                            res = (round(frame.width * scale), round(frame.height * scale))
                        
                        # Use PyAV's reformat with size
                        from fractions import Fraction
                        frame = frame.reformat(width=res[0], height=res[1], format="rgb24")
                    
                    yield {
                        "time": int(float(frame_index / fps) * 1000),
                        "index": frame_index,
                        "frame": frame.to_ndarray(),
                        "ref_id": self._ref_id,
                        "delta_time": float(frame_index / fps)
                    }
                    frame_index += 1
                
                container.close()
        else:
            video_reader = iio.imiter(
                self._path,
                plugin="pyav",
                format="rgb24",
                filter_sequence=filter_sequence,
                **self._kwargs,
            )

            for i, frame in enumerate(video_reader):
                yield {
                    "time": int(float(i / fps) * 1000),
                    "index": i,
                    "frame": frame,
                    "ref_id": self._ref_id,
                    "delta_time": float(i / fps)
                }

    def __len__(self):
        return (self.duration() / 1000) * self.fps()

    def fps(self):
        return float(self._real_fps if self._fps is None else self._fps)

    def duration(self):
        return self._duration


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

        if len(cache) >= self.batch_size:
            yield {
                "time": [x["time"] for x in cache],
                "index": [x["index"] for x in cache],
                "frame": np.stack([x["frame"] for x in cache]),
                "ref_id": [x["ref_id"] for x in cache],
            }

    def fps(self):
        return self.video_decoder._fps

    def duration(self):
        return self.video_decoder._duration
