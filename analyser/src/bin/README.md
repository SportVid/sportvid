
## Standalone Scripts

Contains some standalone scripts to trigger specific plugins, or to check the status of a current job, etc..

Example usage:
```sh
# on job success, export data to /media
docker-compose exec analyser python3 /app/analyser/analyser/bin/export_on_success.py --job_id <JOB_ID>
```