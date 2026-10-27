"""The Ray Serve configs, compose files and analyser config agree with each other and with the plugins."""
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
RAY = ROOT / "inference_ray"

# Ray plugins switched off on purpose in a server config
DISABLED = {"deploy.dev.yml": {"bytetrack"}}


def ray_plugins():
    """Names registered with @AnalyserPluginManager.export (read from the source: importing needs torch)."""
    names = set()
    for path in (RAY / "src" / "inference_ray").rglob("*.py"):
        names |= set(re.findall(r'AnalyserPluginManager\.export\("([^"]+)"\)', path.read_text()))
    return names


def ray_config(name):
    return yaml.safe_load((RAY / name).read_text())


def applications(name):
    return {app["args"]["model"] for app in ray_config(name)["applications"]}


def dotenv():
    return dict(line.split("=", 1) for line in (ROOT / ".env").read_text().splitlines() if "=" in line and not line.startswith("#"))


@pytest.mark.parametrize("name", ["deploy.yml", "deploy.cuda.yml", "deploy.dev.yml", "deploy.prod.yml"])
def test_every_application_is_a_registered_plugin(name):
    config = ray_config(name)
    assert applications(name) <= ray_plugins()
    for app in config["applications"]:
        assert app["name"] == app["args"]["model"] and app["route_prefix"] == f"/{app['name']}"


def test_local_configs_deploy_the_same_plugins():
    assert applications("deploy.yml") == applications("deploy.cuda.yml")


@pytest.mark.parametrize("name", ["deploy.dev.yml", "deploy.prod.yml"])
def test_servers_deploy_every_local_plugin(name):
    """A plugin added to the local configs must be added to the server configs too."""
    missing = applications("deploy.cuda.yml") - applications(name) - DISABLED.get(name, set())
    assert not missing, f"{name} lacks {sorted(missing)}"


def test_local_stack_ray_port():
    port = int(dotenv()["INFERENCE_RAY_PORT"])
    assert ray_config("deploy.yml")["http_options"]["port"] == port
    assert ray_config("deploy.cuda.yml")["http_options"]["port"] == port


@pytest.mark.parametrize("env, port", [("dev", 8001), ("prod", 8000)])
def test_server_stack_uses_its_own_ray_config_and_port(env, port):
    compose = yaml.safe_load((ROOT / f"docker-compose.{env}.yml").read_text())
    services = compose["services"]
    assert f"/app/inference_ray/deploy.{env}.yml" in str(services["inference_ray"]["command"])
    assert f"INFERENCE_RAY_PORT={port}" in [e.split(" ")[0] for e in services["analyser"]["environment"]]
    assert ray_config(f"deploy.{env}.yml")["http_options"]["port"] == port
    for name, service in services.items():
        assert f"/opt/deploy/.env.{env}" in service.get("env_file", [f"/opt/deploy/.env.{env}"]), name
        assert "logging" in service, name


@pytest.mark.parametrize("name", ["docker-compose.yml", "docker-compose.cuda.yml",
                                  "docker-compose.dev.yml", "docker-compose.prod.yml"])
def test_containers_never_build_packages_at_startup(name):
    """The images install the workspace; a sync at startup makes every container build the
    packages in the shared bind-mounted sources at once, and they break each other's build/ dirs."""
    for service, config in yaml.safe_load((ROOT / name).read_text())["services"].items():
        command = config.get("command") or ""
        command = " ".join(command) if isinstance(command, list) else command
        runs = re.findall(r"\buv run\b[^\n&|;]*", re.sub(r"\s+", " ", command).replace("uv run", "\nuv run"))
        for run in runs:
            assert "--no-sync" in run and "--no-editable" not in run, f"{service}: {run}"


def test_images_install_the_workspace():
    assert "--no-install-workspace" not in (ROOT / "Dockerfile").read_text()
    assert "--no-install-workspace" not in (RAY / "Dockerfile").read_text()


def test_analyser_config_only_uses_variables_from_the_env_file():
    text = "\n".join(l for l in (ROOT / "analyser" / "config.yml").read_text().splitlines() if not l.lstrip().startswith("#"))
    assert set(re.findall(r"\$\{(\w+)\}", text)) <= set(dotenv())
