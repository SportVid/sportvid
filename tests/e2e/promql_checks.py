"""PromQL-Checks, die nach einem E2E-Lauf die erwarteten Monitoring-Signale
im Zeitfenster [t_start, t_end] nachweisen.

Jeder Check ist reine Daten (Query-Template + Erwartung), damit neue Checks
ohne Code-Aenderung ergaenzt werden koennen. "{w}" wird durch die Laufdauer in
Sekunden ersetzt, die Query zum Zeitpunkt t_end ausgewertet.

hard=True  -> Nichterfuellung ergibt FAIL
hard=False -> Nichterfuellung ergibt nur WARN (z.B. bei noch nicht
              verifizierten Metriknamen oder geteilter GPU)
"""

from dataclasses import dataclass, field
from typing import Callable, List, Optional

import requests

import config as cfg

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"


class PrometheusError(Exception):
    pass


class Prometheus:
    def __init__(self, base_url: str, session: Optional[requests.Session] = None):
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()

    def query(self, promql: str, at: float) -> List[dict]:
        try:
            res = self.session.get(
                f"{self.base_url}/api/v1/query",
                params={"query": promql, "time": f"{at:.3f}"},
                timeout=30,
            )
            res.raise_for_status()
            body = res.json()
        except (requests.RequestException, ValueError) as e:
            raise PrometheusError(f"query failed: {promql}: {e}") from e
        if body.get("status") != "success":
            raise PrometheusError(f"query failed: {promql}: {body.get('error')}")
        return body["data"]["result"]

    def scalar(self, promql: str, at: float) -> Optional[float]:
        """Erster Wert eines Instant-Vektors, None bei leerem Ergebnis."""
        result = self.query(promql, at)
        if not result:
            return None
        return float(result[0]["value"][1])


@dataclass
class Check:
    name: str
    query: str
    # bekommt (wert, baseline) und liefert True, wenn erfuellt
    expect: Callable[[Optional[float], Optional[float]], bool]
    expectation: str
    hard: bool = True
    # Query fuer den Vergleichswert vor dem Lauf ("{w}" = BASELINE_WINDOW)
    baseline_query: Optional[str] = None
    # Leeres Ergebnis als 0 werten (Fehler-Counter existieren erst nach dem 1. Fehler)
    empty_as_zero: bool = False
    note: str = ""


@dataclass
class CheckResult:
    name: str
    status: str
    value: Optional[float]
    baseline: Optional[float]
    expectation: str
    query: str
    note: str = ""


def _gt0(v, _b):
    return v is not None and v > 0


def _eq0(v, _b):
    return v is not None and v == 0


def _above_baseline(min_delta: float):
    def check(v, b):
        if v is None:
            return False
        return v >= (b or 0.0) + min_delta

    return check


def _info(_v, _b):
    return True


ENV = cfg.ENV_LABEL
CONTAINERS = f'name=~"{cfg.DEV_CONTAINER_REGEX}"'


def precheck_query(selector: str) -> str:
    # min: ein einziges ausgefallenes Target (z.B. einer der Ray-Ports) reicht fuer "nicht UP"
    return f"min({selector})"


def default_checks() -> List[Check]:
    return [
        Check(
            name="Ray Serve HTTP-Requests",
            query=f"sum(increase(ray_serve_num_http_requests_total{{{ENV}}}[{{w}}s]))",
            expect=_gt0,
            expectation="> 0",
        ),
        Check(
            name="Ray Serve HTTP-Fehler",
            query=f"sum(increase(ray_serve_num_http_error_requests_total{{{ENV}}}[{{w}}s]))",
            expect=_eq0,
            expectation="== 0",
            empty_as_zero=True,
        ),
        Check(
            name="Ray Serve Deployment-Fehler",
            query=f"sum(increase(ray_serve_deployment_error_counter_total{{{ENV}}}[{{w}}s]))",
            expect=_eq0,
            expectation="== 0",
            empty_as_zero=True,
        ),
        Check(
            name="GPU-Auslastung (Ray)",
            query=f"max(max_over_time(ray_node_gpus_utilization{{{ENV}}}[{{w}}s]))",
            baseline_query=f"max(avg_over_time(ray_node_gpus_utilization{{{ENV}}}[{{w}}s]))",
            expect=_above_baseline(cfg.GPU_UTIL_MIN_DELTA),
            expectation=f">= Baseline + {cfg.GPU_UTIL_MIN_DELTA:g} %-Pkt",
            # Weich, weil die GPU vermutlich mit prod geteilt wird (Baseline
            # kann durch prod-Last verzerrt sein) - siehe docs/e2e-tests.md.
            hard=False,
        ),
        Check(
            name="GPU-Speicher (Ray)",
            query=f"max(max_over_time(ray_node_gram_used{{{ENV}}}[{{w}}s]))",
            baseline_query=f"max(avg_over_time(ray_node_gram_used{{{ENV}}}[{{w}}s]))",
            expect=_above_baseline(0.0),
            expectation=">= Baseline",
            hard=False,
        ),
        Check(
            name="Container-CPU dev (cAdvisor)",
            query=(
                "max(max_over_time(sum(rate(container_cpu_usage_seconds_total"
                f"{{{CONTAINERS}}}[1m]))[{{w}}s:15s]))"
            ),
            baseline_query=(
                "max(avg_over_time(sum(rate(container_cpu_usage_seconds_total"
                f"{{{CONTAINERS}}}[1m]))[{{w}}s:15s]))"
            ),
            expect=_above_baseline(cfg.CPU_MIN_DELTA_CORES),
            expectation=f">= Baseline + {cfg.CPU_MIN_DELTA_CORES:g} Kerne",
        ),
        Check(
            name="Container-RAM dev (cAdvisor)",
            query=(
                "max(max_over_time(sum(container_memory_working_set_bytes"
                f"{{{CONTAINERS}}})[{{w}}s:15s]))"
            ),
            expect=_info,
            expectation="nur Info",
            hard=False,
        ),
        Check(
            name="Celery Tasks erfolgreich",
            query=f"sum(increase(celery_task_succeeded_total{{{ENV}}}[{{w}}s]))",
            expect=_gt0,
            expectation="> 0",
        ),
        Check(
            name="Celery Tasks fehlgeschlagen",
            query=f"sum(increase(celery_task_failed_total{{{ENV}}}[{{w}}s]))",
            expect=_eq0,
            expectation="== 0",
            empty_as_zero=True,
        ),
        Check(
            name="Django 5xx",
            query=(
                "sum(increase(django_http_responses_total_by_status_total"
                f'{{job="sportvid_backend_dev",status=~"5.."}}[{{w}}s]))'
            ),
            expect=_eq0,
            expectation="== 0",
            empty_as_zero=True,
            note="zaehlt alle dev-Requests im Fenster, nicht nur die des Tests",
        ),
        Check(
            name="OOM-Kills dev (cAdvisor)",
            query=f"sum(increase({cfg.OOM_METRIC}{{{CONTAINERS}}}[{{w}}s]))",
            expect=_eq0,
            expectation="== 0",
            empty_as_zero=True,
            # Weich, bis verifiziert ist, dass cAdvisor die Metrik liefert.
            hard=False,
        ),
    ]


def run_checks(
    prom: Prometheus,
    checks: List[Check],
    t_start: float,
    t_end: float,
) -> List[CheckResult]:
    window = max(int(t_end - t_start), 60)
    results = []
    for check in checks:
        query = check.query.replace("{w}", str(window))
        baseline = None
        note = check.note
        try:
            value = prom.scalar(query, t_end)
            if value is None and check.empty_as_zero:
                value = 0.0
                note = _join(note, "Metrik ohne Daten, als 0 gewertet")
            if check.baseline_query:
                baseline = prom.scalar(
                    check.baseline_query.replace("{w}", str(cfg.BASELINE_WINDOW)),
                    t_start,
                )
        except PrometheusError as e:
            results.append(
                CheckResult(check.name, FAIL if check.hard else WARN, None, None,
                            check.expectation, query, str(e))
            )
            continue

        ok = check.expect(value, baseline)
        if (
            check.name.startswith("GPU-Auslastung")
            and baseline is not None
            and baseline >= cfg.GPU_BASELINE_SATURATED
        ):
            note = _join(note, "Baseline bereits gesaettigt, Vergleich nicht aussagekraeftig")
        status = PASS if ok else (FAIL if check.hard else WARN)
        results.append(
            CheckResult(check.name, status, value, baseline, check.expectation, query, note)
        )
    return results


def _join(a: str, b: str) -> str:
    return f"{a}; {b}" if a else b
