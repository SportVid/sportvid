#!/usr/bin/env python3

import argparse
import os
import sys
import logging

from analyser.analyser.client import AnalyserClient

def parse_args():
    parser = argparse.ArgumentParser(description="Run ByteTrack object tracking on a video")
    parser.add_argument("--video", type=str, required=True, help="Path to the input video file or data_id")
    parser.add_argument("--fps", type=int, default=5, help="Run plugin at specified framerate")
    parser.add_argument("--host", type=str, default="localhost")
    parser.add_argument("--port", type=int, default=50051, help="Port to connect to the analyser / GRPC port")
    return parser.parse_args()


def main():
    args = parse_args()
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s", datefmt="%d-%m-%Y %H:%M:%S", level=logging.INFO)
    
    client = AnalyserClient(args.host, args.port)

    if args.video.endswith(".mp4"):
        logging.info("Detected .mp4 input file. Trigger upload ...")
 
        if not os.path.exists(args.video):
            logging.error(f"Error: Video file {args.video} does not exist")
            sys.exit(1)

        logging.info(f"Start uploading")
        data_id = client.upload_file(args.video)
        logging.info(f"Upload done: {data_id}")
    else:
        logging.info(f"Detected data_id {args.video}")
        data_id = args.video

    # TODO: force re-run
    job_id = client.run_plugin(
        plugin="bytetrack", 
        inputs=[{"id": data_id, "name": "video"}], 
        parameters=[{"name": "fps", "value": args.fps}],
        )
    logging.info(f"Job started: {job_id}")

    result = client.get_plugin_results(job_id)
    logging.info(f"Job finished: {result}")

    if result is None:
        logging.error("Job failed")
        sys.exit(1)

    exit(0)

if __name__ == "__main__":
    main()
