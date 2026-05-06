import ffmpeg


def convert_to_hls(input_path, file_ext, out_path, asynchronous = True, **kwargs):
    """
    Start HLS conversion and return the running subprocess (Popen object).
    The caller is responsible for waiting on it and handling termination.
    """
    input_stream = ffmpeg.input(input_path, f=file_ext)    
    # fmpeg -i in.mp4 -codec: copy -start_number 0 -hls_time 10 -hls_list_size 0 -f hls out.m3u8
    output_stream = ffmpeg.output(
        input_stream, 
        filename=out_path,
        format=kwargs.get('format', 'hls'), 
        hls_time=kwargs.get('segment_time', 5),
        hls_list_size=0,
        hls_playlist_type=kwargs.get('hls_playlist_type', 'vod'),
        hls_segment_type=kwargs.get('hls_segment_type', 'mpegts'),
        hls_flags=kwargs.get('hls_flags', 'independent_segments'),
        # hls_segment_filename=kwargs.get('hls_segment_filename', out_path)
        start_number=0,
        vcodec=kwargs.get('vcodec', None),
        acodec=kwargs.get('acodec', None),
        audio_bitrate=kwargs.get('audio_bitrate', None),
        preset=kwargs.get('preset', None),
        crf=kwargs.get('crf', 23),
        g=kwargs.get('gop'),
        keyint_min=kwargs.get('gop'),
        sc_threshold=kwargs.get('sc_threshold', 0),
        pix_fmt=kwargs.get('pix_fmt', None),
        movflags=kwargs.get('movflags', None)
    )
    if asynchronous:
        return ffmpeg.run_async(output_stream, pipe_stderr=True)
    else:
        ffmpeg.run(output_stream)
    
