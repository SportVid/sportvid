"""Offline-Tests fuer den E2E-Test selbst (keine Netzwerkzugriffe).

Ausfuehren:  python -m unittest discover -s tests/e2e -v
"""

import os
import tempfile
import unittest
from types import SimpleNamespace

import config as cfg
import promql_checks as pc
import run_e2e
from sportvid_client import ApiError, SportvidClient


# --- Fakes --------------------------------------------------------------------

class FakeProm(pc.Prometheus):
    """Antwortet je nach Query-Inhalt; Default: Wert 5 (Last sichtbar)."""

    def __init__(self, up=None, values=None, fail=False):
        super().__init__("http://localhost:9090")
        # up: Target-Name -> Wert; None = keine Serie (Target fehlt ganz)
        self.up = up if up is not None else {t: 1 for t in cfg.PRECHECK_TARGETS}
        self.values = values or {}
        self.fail = fail
        self.queries = []

    def query(self, promql, at):
        self.queries.append(promql)
        if self.fail:
            raise pc.PrometheusError("connection refused")
        for name, selector in cfg.PRECHECK_TARGETS.items():
            if promql == pc.precheck_query(selector):
                v = self.up.get(name)
                return [] if v is None else [{"metric": {}, "value": [at, str(v)]}]
        for needle, value in self.values.items():
            if needle in promql:
                return [] if value is None else [{"metric": {}, "value": [at, str(value)]}]
        if "error" in promql or "failed" in promql or "5.." in promql or cfg.OOM_METRIC in promql:
            return [{"metric": {}, "value": [at, "0"]}]
        if "avg_over_time" in promql:  # Baseline
            return [{"metric": {}, "value": [at, "1"]}]
        return [{"metric": {}, "value": [at, "50"]}]


class FakeClient:
    def __init__(self, plugin_status="DONE", start_error=None):
        self.plugin_status = plugin_status
        self.start_error = start_error
        self.started = []
        self.deleted = []
        self.server_errors = []

    def upload_video(self, path, title, fields):
        return "vid1"

    def video_status(self, video_id):
        return "D"

    def start_plugin(self, plugin, video_id, parameters):
        if self.start_error and plugin == self.start_error:
            raise ApiError("plugin/run/new: validation_error Unknown plugin (HTTP 400)", 400)
        self.started.append((plugin, parameters))
        return f"run{len(self.started)}"

    def plugin_runs(self, video_id):
        return [{"id": f"run{i + 1}", "status": self.plugin_status} for i in range(len(self.started))]

    def timelines(self, video_id):
        return [{"id": "tl-shots", "name": cfg.SHOT_TIMELINE_NAME}, {"id": "tl-other", "name": "x"}]

    def delete_video(self, video_id):
        self.deleted.append(video_id)


def make_args(**kw):
    defaults = dict(video="clip.mp4", video_timeout=5, plugin_timeout=5, poll_interval=0,
                    settle=0, keep=False, grafana_url="http://localhost:3000")
    defaults.update(kw)
    return SimpleNamespace(**defaults)


class Clock:
    def __init__(self):
        self.t = 1_700_000_000.0

    def __call__(self):
        self.t += 30
        return self.t


def run(name, client, prom, **kw):
    return run_e2e.run_scenario(name, client, prom, make_args(**kw), sleep=lambda s: None, clock=Clock())


# --- Tests ----------------------------------------------------------------------

class GuardTests(unittest.TestCase):
    def test_prod_host_rejected(self):
        with self.assertRaises(SystemExit):
            run_e2e.check_targets("https://sportvid.dshs-koeln.de", "http://localhost:9090")

    def test_http_rejected(self):
        with self.assertRaises(SystemExit):
            run_e2e.check_targets("http://dev.sportvid.dshs-koeln.de", "http://localhost:9090")

    def test_remote_prometheus_rejected(self):
        with self.assertRaises(SystemExit):
            run_e2e.check_targets("https://dev.sportvid.dshs-koeln.de", "http://172.20.5.25:9090")

    def test_dev_accepted(self):
        run_e2e.check_targets("https://dev.sportvid.dshs-koeln.de", "http://127.0.0.1:9090")

    def test_dry_run_prod_rejected(self):
        with self.assertRaises(SystemExit):
            run_e2e.main(["--dry-run", "--base-url", "https://sportvid.dshs-koeln.de"])

    def test_foreign_connect_ip_rejected(self):
        with self.assertRaises(SystemExit):
            run_e2e.check_targets("https://dev.sportvid.dshs-koeln.de", "http://localhost:9090", "8.8.8.8")

    def test_local_connect_ip_accepted(self):
        run_e2e.check_targets("https://dev.sportvid.dshs-koeln.de", "http://localhost:9090", "127.0.0.1")


class PinHostTests(unittest.TestCase):
    def test_only_target_host_redirected(self):
        import urllib3.util.connection as conn

        seen = []
        original = conn.create_connection
        conn.create_connection = lambda address, *a, **kw: seen.append(address)
        try:
            from sportvid_client import pin_host

            pin_host("dev.sportvid.dshs-koeln.de", "127.0.0.1")
            conn.create_connection(("dev.sportvid.dshs-koeln.de", 443))
            conn.create_connection(("github.com", 443))
        finally:
            conn.create_connection = original
        self.assertEqual(seen, [("127.0.0.1", 443), ("github.com", 443)])


class ScenarioTests(unittest.TestCase):
    def test_standard_pass_and_cleanup(self):
        client = FakeClient()
        res = run("standard", client, FakeProm())
        self.assertEqual(res.status, pc.PASS, res.errors)
        self.assertEqual([p for p, _ in client.started], ["shotdetection"])
        self.assertEqual(client.deleted, ["vid1"])

    def test_plugins_pass_timeline_id(self):
        client = FakeClient()
        res = run("plugins", client, FakeProm())
        self.assertEqual(res.status, pc.PASS, res.errors)
        started = dict(client.started)
        self.assertEqual(list(started), ["shotdetection", "shot_type_classification", "face_clustering"])
        self.assertEqual(started["shot_type_classification"]["shot_timeline_id"], "tl-shots")
        # Config-Objekt darf nicht mutiert werden
        self.assertNotIn("shot_timeline_id", cfg.SHOT_TYPE_CLASSIFICATION["parameters"])

    def test_missing_target_inconclusive_without_upload(self):
        client = FakeClient()
        up = {t: 1 for t in cfg.PRECHECK_TARGETS}
        up["inference_ray_dev"] = 0
        res = run("standard", client, FakeProm(up=up))
        self.assertEqual(res.status, run_e2e.INCONCLUSIVE)
        self.assertEqual(client.started, [])
        self.assertIsNone(res.video_id)

    def test_absent_target_inconclusive(self):
        # keine up-Serie (z.B. falsches job-Label) zaehlt wie "nicht UP"
        up = {t: 1 for t in cfg.PRECHECK_TARGETS}
        up["inference_ray_dev"] = None
        res = run("standard", FakeClient(), FakeProm(up=up))
        self.assertEqual(res.status, run_e2e.INCONCLUSIVE)
        self.assertTrue(any("inference_ray_dev" in e for e in res.errors))

    def test_prometheus_down_inconclusive(self):
        res = run("standard", FakeClient(), FakeProm(fail=True))
        self.assertEqual(res.status, run_e2e.INCONCLUSIVE)

    def test_plugin_error_fails_but_cleans_up(self):
        client = FakeClient(plugin_status="ERROR")
        res = run("standard", client, FakeProm())
        self.assertEqual(res.status, pc.FAIL)
        self.assertEqual(client.deleted, ["vid1"])

    def test_unknown_plugin_fails_but_cleans_up(self):
        client = FakeClient(start_error="face_clustering")
        res = run("plugins", client, FakeProm())
        self.assertEqual(res.status, pc.FAIL)
        self.assertTrue(any("Unknown plugin" in e for e in res.errors))
        self.assertEqual(client.deleted, ["vid1"])

    def test_keep_skips_cleanup(self):
        client = FakeClient()
        run("standard", client, FakeProm(), keep=True)
        self.assertEqual(client.deleted, [])

    def test_no_ray_requests_fails(self):
        prom = FakeProm(values={"ray_serve_num_http_requests_total": None})
        res = run("standard", FakeClient(), prom)
        self.assertEqual(res.status, pc.FAIL)

    def test_server_errors_fail(self):
        client = FakeClient()
        client.server_errors.append("video/get: HTTP 502")
        res = run("standard", client, FakeProm())
        self.assertEqual(res.status, pc.FAIL)


class CheckTests(unittest.TestCase):
    def results(self, prom):
        return {r.name: r for r in pc.run_checks(prom, pc.default_checks(), 1000.0, 1400.0)}

    def test_queries_rendered(self):
        prom = FakeProm()
        self.results(prom)
        for q in prom.queries:
            self.assertNotIn("{w}", q)
            self.assertNotIn("{{", q)
        self.assertIn('sum(increase(ray_serve_num_http_requests_total{environment="dev"}[400s]))', prom.queries)
        # Baseline-Fenster = BASELINE_WINDOW
        self.assertTrue(any(f"[{cfg.BASELINE_WINDOW}s" in q and "avg_over_time" in q for q in prom.queries))

    def test_empty_error_counter_counts_as_zero(self):
        prom = FakeProm(values={"ray_serve_num_http_error_requests_total": None})
        r = self.results(prom)["Ray Serve HTTP-Fehler"]
        self.assertEqual(r.status, pc.PASS)
        self.assertIn("als 0 gewertet", r.note)

    def test_errors_fail(self):
        prom = FakeProm(values={"celery_task_failed_total": 2})
        self.assertEqual(self.results(prom)["Celery Tasks fehlgeschlagen"].status, pc.FAIL)

    def test_gpu_below_baseline_only_warns(self):
        prom = FakeProm(values={"max_over_time(ray_node_gpus_utilization": 5})
        self.assertEqual(self.results(prom)["GPU-Auslastung (Ray)"].status, pc.WARN)

    def test_gpu_saturated_baseline_noted(self):
        prom = FakeProm(values={"avg_over_time(ray_node_gpus_utilization": 95})
        r = self.results(prom)["GPU-Auslastung (Ray)"]
        self.assertIn("gesaettigt", r.note)

    def test_unverified_oom_metric_only_warns(self):
        prom = FakeProm(values={cfg.OOM_METRIC: 3})
        self.assertEqual(self.results(prom)["OOM-Kills dev (cAdvisor)"].status, pc.WARN)


class ReportTests(unittest.TestCase):
    def test_reports_written_and_overall(self):
        a = run("standard", FakeClient(), FakeProm())
        b = run("plugins", FakeClient(plugin_status="ERROR"), FakeProm())
        with tempfile.TemporaryDirectory() as d:
            overall = run_e2e.write_reports([a, b], d)
            self.assertEqual(overall, pc.FAIL)
            md = open(os.path.join(d, "report.md"), encoding="utf-8").read()
            self.assertIn("Szenario `plugins`: **FAIL**", md)
            self.assertIn("/d/rayServeDashboard?from=", md)
            self.assertTrue(os.path.isfile(os.path.join(d, "report.json")))


# --- Client gegen Fake-Session ------------------------------------------------

class FakeResponse:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self._body = body

    def json(self):
        if self._body is None:
            raise ValueError("no json")
        return self._body


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.headers = {}
        self.cookies = {}
        self.calls = []

    def get(self, url, **kw):
        self.calls.append(("GET", url, kw))
        if url.endswith("/user/csrf"):
            self.cookies["csrftoken"] = "tok"
        return self.responses.pop(0)

    def post(self, url, **kw):
        self.calls.append(("POST", url, kw))
        return self.responses.pop(0)


class ClientTests(unittest.TestCase):
    def test_login_sends_csrf_and_referer(self):
        s = FakeSession([FakeResponse(200, {"status": "ok"}), FakeResponse(200, {"status": "ok"})])
        c = SportvidClient("https://dev.sportvid.dshs-koeln.de", session=s)
        c.login("u", "p")
        method, url, kw = s.calls[1]
        self.assertEqual(url, "https://dev.sportvid.dshs-koeln.de/api/user/login")
        self.assertEqual(kw["headers"]["X-CSRFToken"], "tok")
        self.assertEqual(s.headers["Referer"], "https://dev.sportvid.dshs-koeln.de/")

    def test_5xx_tracked_and_raised(self):
        s = FakeSession([FakeResponse(502, None)])
        c = SportvidClient("https://dev.sportvid.dshs-koeln.de", session=s)
        with self.assertRaises(ApiError):
            c.video_status("x")
        self.assertEqual(len(c.server_errors), 1)

    def test_basic_auth_set_on_session(self):
        s = FakeSession([])
        SportvidClient("https://dev.sportvid.dshs-koeln.de", session=s, basic_auth=("nginx", "pw"))
        self.assertEqual(s.auth, ("nginx", "pw"))

    def test_missing_basic_auth_aborts(self):
        env = {"E2E_USER": "u", "E2E_PASSWORD": "p"}
        old = {k: os.environ.pop(k, None) for k in ("E2E_BASIC_USER", "E2E_BASIC_PASSWORD")}
        os.environ.update(env)
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp4") as video:
                with self.assertRaises(SystemExit) as ctx:
                    run_e2e.main(["--video", video.name])
            self.assertIn("E2E_BASIC_USER", str(ctx.exception))
        finally:
            for k in env:
                os.environ.pop(k, None)
            os.environ.update({k: v for k, v in old.items() if v is not None})

    def test_network_error_becomes_api_error(self):
        import requests

        class DownSession(FakeSession):
            def get(self, url, **kw):
                raise requests.ConnectionError("timed out")

        c = SportvidClient("https://dev.sportvid.dshs-koeln.de", session=DownSession([]))
        with self.assertRaises(ApiError) as ctx:
            c.video_status("x")
        self.assertIn("Verbindungsfehler", str(ctx.exception))

    def test_plugin_params_sent_as_dict(self):
        s = FakeSession([FakeResponse(200, {"status": "ok", "plugin_run_id": "r1"})])
        c = SportvidClient("https://dev.sportvid.dshs-koeln.de", session=s)
        self.assertEqual(c.start_plugin("shotdetection", "v", {"fps": 2}), "r1")
        import json
        sent = json.loads(s.calls[0][2]["data"])
        self.assertEqual(sent["parameters"], {"fps": 2})


if __name__ == "__main__":
    unittest.main()
