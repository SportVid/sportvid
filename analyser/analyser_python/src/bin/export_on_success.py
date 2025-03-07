from argparse import ArgumentParser
import sys

from analyser.analyser.client import AnalyserClient
from analyser.proto import analyser_pb2

args = ArgumentParser()
args.add_argument("--job_id", type=str, required=True)
args.add_argument("--host", type=str, default="localhost")
args.add_argument("--port", type=int, default=50051, help="Port to connect to the analyser / GRPC port")
args.add_argument("--output", type=str, default="/media", help="Output folder")
args = args.parse_args()

client = AnalyserClient(args.host, args.port)

status = client.get_plugin_status(args.job_id)
print(status)

if  status.status != analyser_pb2.GetPluginStatusResponse.DONE: 
    print("The job is not done.")
    sys.exit(1)

# generic function to get the result
result = client.get_plugin_results(args.job_id)
print(result)


for output in result.outputs:
    print(f"Download result data for {output.name} {output.id}")

    data = client.download_data(output.id, args.output)
    