import ffmpeg

# $ ffmpeg -i in.mp4 -codec: copy -start_number 0 -hls_time 10 -hls_list_size 0 -f hls out.m3u8
def convert_to_hls(input_path, file_ext, out_path):
    input_stream = ffmpeg.input(input_path, f=file_ext)
    output_stream = ffmpeg.output(input_stream, 
        filename=out_path,
        format='hls', start_number=0, hls_time=5, hls_list_size=0)
    ffmpeg.run(output_stream)