# CI/CD Runner Setup für SportVid (dev-Branch)

## Goal
A GitHub Actions Runner on the server should automatically restart the `sportvid_dev service` (via `systemctl`) whenever a push is made to `deploy-dev`.

## Current Status (as of 30.10.2025)

- GitHub Actions Runner installed on the server (`/home/hmoeller/actions-runner`)
- Workflow file `.github/workflows/deploy-dev.yml` created & pushed
- `sportvid_dev` service is restarted correctly via `systemctl`
- runner successfully triggers the restart on push
-	runner currently running manually in a terminal session

## How to Start the runner (non-persistent)
`./run.sh`

Note: The terminal must remain open. Looking for a persistent solution.

## `.github/workflows/deploy-dev.yml`

```yaml
name: Deploy Dev

on:
  push:
    branches:
      - deploy-dev

jobs:
  restart-dev:
    runs-on: [self-hosted, linux, x64]
    steps:
      - name: Restart sportvid_dev via systemd
        run: |
          systemctl restart sportvid_dev
```

## Next Steps

- runner is currently not persistent, it only runs in an open terminal -> solution via tmux, screen, or systemd?
- further workflow steps to be included (Build Verification, Health Checks)