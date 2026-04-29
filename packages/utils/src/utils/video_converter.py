import ffmpeg


def convert_to_hls(input_path, file_ext, out_path):
    """ fmpeg -i in.mp4 -codec: copy -start_number 0 -hls_time 10 -hls_list_size 0 -f hls out.m3u8 """
    """Start HLS conversion and return the running subprocess (Popen object).
    The caller is responsible for waiting on it and handling termination."""
    input_stream = ffmpeg.input(input_path, f=file_ext)
    output_stream = ffmpeg.output(
        input_stream, 
        filename=out_path,
        format='hls', 
        start_number=0,
        hls_time=5,
        hls_list_size=0
    )
    ffmpeg.run(output_stream)    
    
def convert_to_fmp4(input_path, file_ext, out_path):
    input_stream = ffmpeg.input(input_path, f=file_ext)

    stream = ffmpeg.output(
        input_stream,
        filename=out_path,
        format='hls',
        vcodec='libx264',
        acodec='aac',
        g=48,
        keyint_min=48,
        sc_threshold=0,
        start_number=0,
        hls_time=5,
        hls_list_size=0,
        hls_playlist_type='vod',
        hls_segment_type='fmp4',
        hls_flags='single_file+independent_segments',
        hls_segment_filename='stream.m4s',
    )
    return ffmpeg.run_async(stream, pipe_stderr=True)
    # ffmpeg.run(stream, overwrite_output=True)
