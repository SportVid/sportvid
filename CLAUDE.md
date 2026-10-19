# CLAUDE.md

## Server access

Never access the production/deploy server (sportvid01 / 172.20.5.25) via SSH or any other
automated/remote connection, including for read-only checks or testing. All testing and
verification must happen locally in this repo (e.g. via `docker compose up`).

If information from the server is needed (e.g. checking `.env` values, deploy paths, running
containers), give the user the exact command(s) to run themselves, and wait for them to paste
back the output.
