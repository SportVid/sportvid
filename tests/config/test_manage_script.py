"""manage.sh never switches a working copy to another deploy branch by accident.

Each case runs the script in a throwaway repo without a remote: a refused run stops before
`git checkout`, an allowed one stops at `git fetch origin`, so no docker command is reached.
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def working_copy(tmp_path):
    shutil.copy(ROOT / "manage.sh", tmp_path / "manage.sh")
    git(tmp_path, "init", "-q", "-b", "deploy-dev")
    git(tmp_path, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "init")
    git(tmp_path, "branch", "deploy-prod")
    return tmp_path


def manage(repo, *args, switch=False):
    env = {k: v for k, v in os.environ.items() if k != "SPORTVID_SWITCH_BRANCH"}
    if switch:
        env["SPORTVID_SWITCH_BRANCH"] = "1"
    return subprocess.run(["bash", "manage.sh", *args], cwd=repo, env=env, capture_output=True, text=True)


@pytest.mark.parametrize("environment", ["shared", "prod"])
def test_refuses_to_switch_the_dev_copy_to_deploy_prod(working_copy, environment):
    result = manage(working_copy, environment, "rebuild")
    assert result.returncode != 0 and "Refusing to run" in result.stderr
    assert git(working_copy, "branch", "--show-current") == "deploy-dev"


def test_refuses_to_switch_the_prod_copy_to_deploy_dev(working_copy):
    git(working_copy, "checkout", "-q", "deploy-prod")
    result = manage(working_copy, "dev", "migrate")
    assert result.returncode != 0 and "Refusing to run" in result.stderr
    assert git(working_copy, "branch", "--show-current") == "deploy-prod"


def test_refuses_on_a_detached_head(working_copy):
    git(working_copy, "checkout", "-q", "--detach")
    result = manage(working_copy, "dev", "up")
    assert result.returncode != 0 and "(detached HEAD)" in result.stderr


def test_runs_on_its_own_branch(working_copy):
    result = manage(working_copy, "dev", "up")
    assert "Refusing to run" not in result.stderr and "Failed to fetch" in result.stderr


def test_switches_only_when_asked(working_copy):
    result = manage(working_copy, "shared", "up", switch=True)
    assert "Refusing to run" not in result.stderr and "Failed to fetch" in result.stderr
    assert git(working_copy, "branch", "--show-current") == "deploy-prod"
