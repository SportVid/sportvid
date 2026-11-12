#!/usr/bin/env python3
"""Funktionaler E2E-Test fuer sportvid **dev** mit Monitoring-Verifikation.

Ablauf je Szenario:
  Login -> Prometheus-Vorcheck -> Plugin-Vorcheck -> Upload -> warten auf HLS-Konvertierung ->
  Plugins starten/abwarten -> Scrape abwarten -> PromQL-Checks -> Cleanup.

Ergebnis: PASS (Exit 0), FAIL (Exit 1), INCONCLUSIVE (Exit 2, z.B. Prometheus-
Targets fehlen - der Test sagt dann nichts ueber die App aus).

Nur manuell ausloesen (Workflow e2e-dev.yml, workflow_dispatch). Hintergrund
und Entscheidungen: Servermonitoring-Repo, docs/e2e-tests.md.

Beispiel (auf dem Runner):
  E2E_USER=... E2E_PASSWORD=... E2E_BASIC_USER=... E2E_BASIC_PASSWORD=... \
    python tests/e2e/run_e2e.py --scenario standard
"""

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import urlencode, urlparse

import config as cfg
from promql_checks import (
    FAIL,
    PASS,
    Prometheus,
    PrometheusError,
    default_checks,
    precheck_query,
    run_checks,
)
from sportvid_client import ApiError, SportvidClient, pin_host, wait_for

INCONCLUSIVE = "INCONCLUSIVE"
EXIT_CODES = {PASS: 0, FAIL: 1, INCONCLUSIVE: 2}

# Lokaler Fallback fuer Entwicklung. tests/e2e/data/ ist per .gitignore (**/data/)
# ausgeschlossen, die Videos werden nie committet.
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def video_dir() -> str:
    """E2E_VIDEO_DIR (im Workflow /opt/e2e-data auf sportvid01), sonst tests/e2e/data/."""
    return os.environ.get("E2E_VIDEO_DIR") or DATA_DIR


def video_for(scenario: str, args) -> str:
    """--video ueberschreibt fuer alle Szenarien, sonst das Video aus config.SCENARIO_VIDEOS."""
    if getattr(args, "video", None):
        return args.video
    return os.path.join(video_dir(), cfg.SCENARIO_VIDEOS[scenario])


@dataclass
class ScenarioResult:
    scenario: str
    status: str = PASS
    video_id: Optional[str] = None
    t_start: Optional[float] = None
    t_end: Optional[float] = None
    t_query: Optional[float] = None
    steps: List[str] = field(default_factory=list)
    plugin_runs: List[dict] = field(default_factory=list)
    checks: List[dict] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    grafana_links: dict = field(default_factory=dict)

    def log(self, msg: str) -> None:
        stamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
        line = f"[{stamp}] {self.scenario}: {msg}"
        print(line, flush=True)
        self.steps.append(line)

    def fail(self, msg: str) -> None:
        self.log(f"FEHLER: {msg}")
        self.errors.append(msg)
        self.status = FAIL


# --- Guards -------------------------------------------------------------------

def check_targets(base_url: str, prom_url: str, connect_ip: Optional[str] = None) -> None:
    """Hard-Guard: nur dev-App und lokales Prometheus. Bewusst ohne Override-Flag."""
    if connect_ip and connect_ip not in cfg.ALLOWED_CONNECT_IPS:
        raise SystemExit(
            f"Abbruch: --connect-ip '{connect_ip}' ist nicht erlaubt (nur {sorted(cfg.ALLOWED_CONNECT_IPS)})."
        )
    app_host = urlparse(base_url).hostname
    if app_host not in cfg.ALLOWED_APP_HOSTS:
        raise SystemExit(
            f"Abbruch: --base-url Host '{app_host}' ist nicht erlaubt "
            f"(nur {sorted(cfg.ALLOWED_APP_HOSTS)}). Der E2E-Test laeuft ausschliesslich gegen dev."
        )
    if urlparse(base_url).scheme != "https":
        raise SystemExit("Abbruch: --base-url muss https sein (Session-/CSRF-Cookies sind Secure).")
    prom_host = urlparse(prom_url).hostname
    if prom_host not in cfg.ALLOWED_PROM_HOSTS:
        raise SystemExit(
            f"Abbruch: --prom-url Host '{prom_host}' ist nicht erlaubt (nur {sorted(cfg.ALLOWED_PROM_HOSTS)})."
        )


# --- Ablauf -------------------------------------------------------------------

def precheck(prom: Prometheus, now: float) -> List[str]:
    """Liefert Liste fehlender/ausgefallener Targets (leer = alles ok)."""
    missing = []
    for name, selector in cfg.PRECHECK_TARGETS.items():
        value = prom.scalar(precheck_query(selector), now)
        if value is None or value < 1.0:
            missing.append(name)
    return missing


def run_scenario(name, client, prom, args, sleep=time.sleep, clock=time.time) -> ScenarioResult:
    res = ScenarioResult(scenario=name)
    plugins = cfg.SCENARIOS[name]

    try:
        missing = precheck(prom, clock())
    except PrometheusError as e:
        res.status = INCONCLUSIVE
        res.errors.append(str(e))
        res.log(f"INCONCLUSIVE: Prometheus nicht erreichbar ({e})")
        return res
    if missing:
        res.status = INCONCLUSIVE
        res.errors.append(f"Targets nicht UP: {missing}")
        res.log(f"INCONCLUSIVE: Targets nicht UP: {missing} - Test nicht gestartet")
        return res
    res.log("Prometheus-Vorcheck ok")

    # Plugin-Vorcheck: Plugins, deren Ray-Plugins auf dev nicht deployt sind, lehnt das
    # Backend mit "plugin_unavailable" ab (erster echter Lauf, 2026-11-12). Das ist eine
    # Deploy-Frage, kein App-Fehler -> INCONCLUSIVE, bevor ein Video hochgeladen wird.
    try:
        available = client.available_plugins()
    except ApiError as e:
        res.fail(f"Plugin-Vorcheck: {e}")
        return res
    if available is None:
        # Backend erreicht den Analyser nicht; der Lauf zeigt dann selbst, ob das stoert.
        res.log("WARN: plugin/available liefert null (Analyser nicht erreichbar), Vorcheck uebersprungen")
    else:
        unavailable = [s["plugin"] for s in plugins if s["plugin"] not in available]
        if unavailable:
            res.status = INCONCLUSIVE
            res.errors.append(f"Plugins auf dev nicht deployt: {unavailable} (verfuegbar: {available})")
            res.log(f"INCONCLUSIVE: Plugins auf dev nicht deployt: {unavailable} - Test nicht gestartet")
            return res
        res.log("Plugin-Vorcheck ok")

    res.t_start = clock()
    try:
        title = f"e2e-{name}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        res.video_id = client.upload_video(video_for(name, args), title, cfg.UPLOAD_FIELDS)
        res.log(f"Upload ok, video_id={res.video_id}")

        wait_for(
            lambda: client.video_status(res.video_id),
            done=lambda s: s == "D",
            failed=lambda s: s == "E",
            timeout=args.video_timeout,
            interval=args.poll_interval,
            what="HLS-Konvertierung",
            sleep=sleep,
        )
        res.log("HLS-Konvertierung fertig (Status D)")

        # Nacheinander in Config-Reihenfolge: ein Plugin kann per "needs" die
        # PluginRun-ID eines frueheren brauchen (team_clustering <- object_tracker).
        run_ids = {}
        for spec in plugins:
            params = dict(spec["parameters"])  # Config-Objekt nicht mutieren
            for param, source in spec.get("needs", {}).items():
                params[param] = run_ids[source]
            run_ids.update(_run_plugins(client, res, [{"plugin": spec["plugin"], "parameters": params}], args, sleep))
    except ApiError as e:
        res.fail(str(e))
    finally:
        res.t_end = clock()

    if client.server_errors:
        res.fail(f"HTTP-5xx bei API-Aufrufen: {client.server_errors}")

    # Prometheus braucht nach Lastende noch mind. einen Scrape.
    res.log(f"warte {args.settle}s auf letzte Scrapes")
    sleep(args.settle)
    res.t_query = clock()

    try:
        ray_apps = [app for spec in plugins for app in spec.get("ray_apps", [])]
        results = run_checks(prom, default_checks(ray_apps), res.t_start, res.t_query)
    except PrometheusError as e:
        results = []
        res.errors.append(str(e))
        if res.status == PASS:
            res.status = INCONCLUSIVE
    for r in results:
        res.checks.append(asdict(r))
        res.log(f"Check {r.status}: {r.name} = {_fmt(r.value)} (Baseline {_fmt(r.baseline)}, erwartet {r.expectation})")
        if r.status == FAIL:
            res.status = FAIL
            res.errors.append(f"Check fehlgeschlagen: {r.name}")

    res.grafana_links = grafana_links(args.grafana_url, res.t_start, res.t_query)

    if res.video_id and not args.keep:
        try:
            client.delete_video(res.video_id)
            res.log("Cleanup: Video geloescht (inkl. PluginRuns/Timelines)")
        except ApiError as e:
            # Cleanup-Fehler machen den Lauf nicht FAIL, muessen aber sichtbar sein.
            res.errors.append(f"Cleanup fehlgeschlagen: {e}")
            res.log(f"WARN: Cleanup fehlgeschlagen: {e}")
    return res


def _run_plugins(client, res, specs, args, sleep) -> dict:
    """Startet specs, wartet auf DONE und liefert {plugin: run_id}."""
    run_ids = {}
    for spec in specs:
        run_id = client.start_plugin(spec["plugin"], res.video_id, spec["parameters"])
        run_ids[run_id] = spec["plugin"]
        res.log(f"Plugin {spec['plugin']} gestartet, run_id={run_id}")

    def states():
        by_id = {r["id"]: r for r in client.plugin_runs(res.video_id)}
        return {rid: by_id.get(rid, {}).get("status", "MISSING") for rid in run_ids}

    final = wait_for(
        states,
        done=lambda st: all(s == "DONE" for s in st.values()),
        failed=lambda st: any(s in ("ERROR", "MISSING") for s in st.values()),
        timeout=args.plugin_timeout,
        interval=args.poll_interval,
        what=f"Plugins {sorted(run_ids.values())}",
        sleep=sleep,
    )
    for rid, status in final.items():
        res.plugin_runs.append({"plugin": run_ids[rid], "run_id": rid, "status": status})
    res.log(f"Plugins fertig: {sorted(run_ids.values())}")
    return {plugin: rid for rid, plugin in run_ids.items()}


def grafana_links(grafana_url: str, t_start: Optional[float], t_end: Optional[float]) -> dict:
    if not t_start or not t_end:
        return {}
    # 1 min Rand, damit Anstieg/Abfall im Panel sichtbar sind
    q = urlencode({"from": int((t_start - 60) * 1000), "to": int((t_end + 60) * 1000)})
    base = grafana_url.rstrip("/")
    return {name: f"{base}/d/{uid}?{q}" for name, uid in cfg.GRAFANA_DASHBOARDS.items()}


def _fmt(v) -> str:
    return "-" if v is None else f"{v:.3g}"


# --- Report -------------------------------------------------------------------

def overall_status(results: List[ScenarioResult]) -> str:
    statuses = {r.status for r in results}
    if FAIL in statuses:
        return FAIL
    if INCONCLUSIVE in statuses:
        return INCONCLUSIVE
    return PASS


def compare_scenarios(results: List[ScenarioResult]) -> Optional[str]:
    """Info: Lauf B (plugins) sollte mehr Ray-Serve-Requests erzeugen als Lauf A."""
    by_name = {r.scenario: r for r in results}
    if not {"standard", "plugins"} <= by_name.keys():
        return None

    def ray_requests(r):
        for c in r.checks:
            if c["name"] == "Ray Serve HTTP-Requests":
                return c["value"]
        return None

    a, b = ray_requests(by_name["standard"]), ray_requests(by_name["plugins"])
    if a is None or b is None:
        return None
    verdict = "ok" if b > a else "auffaellig"
    return f"Ray-Serve-Requests: standard={_fmt(a)}, plugins={_fmt(b)} -> {verdict} (nur Info)"


def render_markdown(results: List[ScenarioResult], overall: str, comparison: Optional[str]) -> str:
    lines = [f"# sportvid E2E (dev): **{overall}**", ""]
    if comparison:
        lines += [comparison, ""]
    for r in results:
        lines += [f"## Szenario `{r.scenario}`: **{r.status}**", ""]
        if r.t_start and r.t_query:
            start = datetime.fromtimestamp(r.t_start, timezone.utc).isoformat(timespec="seconds")
            end = datetime.fromtimestamp(r.t_query, timezone.utc).isoformat(timespec="seconds")
            lines += [f"Zeitfenster: {start} – {end}", ""]
        if r.errors:
            lines += ["**Fehler:**", ""] + [f"- {e}" for e in r.errors] + [""]
        if r.plugin_runs:
            lines += ["| Plugin | Run | Status |", "|---|---|---|"]
            lines += [f"| {p['plugin']} | `{p['run_id']}` | {p['status']} |" for p in r.plugin_runs]
            lines.append("")
        if r.checks:
            lines += ["| Check | Status | Wert | Baseline | Erwartung | Hinweis |", "|---|---|---|---|---|---|"]
            for c in r.checks:
                lines.append(
                    f"| {c['name']} | {c['status']} | {_fmt(c['value'])} | {_fmt(c['baseline'])} "
                    f"| {c['expectation']} | {c['note']} |"
                )
            lines.append("")
        if r.grafana_links:
            lines += ["Grafana (SSH-Tunnel auf Port 3000 noetig):", ""]
            lines += [f"- [{n}]({u})" for n, u in r.grafana_links.items()]
            lines.append("")
    return "\n".join(lines)


def write_reports(results, out_dir: str) -> str:
    overall = overall_status(results)
    comparison = compare_scenarios(results)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "report.json"), "w", encoding="utf-8") as fh:
        json.dump(
            {"overall": overall, "comparison": comparison, "scenarios": [asdict(r) for r in results]},
            fh,
            indent=2,
        )
    md = render_markdown(results, overall, comparison)
    with open(os.path.join(out_dir, "report.md"), "w", encoding="utf-8") as fh:
        fh.write(md)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(md + "\n")
    return overall


# --- CLI ----------------------------------------------------------------------

def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--scenario", choices=["standard", "plugins", "both"], default="standard")
    p.add_argument("--base-url", default=cfg.DEFAULT_BASE_URL)
    p.add_argument("--prom-url", default=cfg.DEFAULT_PROM_URL)
    p.add_argument("--grafana-url", default=cfg.DEFAULT_GRAFANA_URL)
    p.add_argument("--connect-ip", default=cfg.DEFAULT_CONNECT_IP,
                   help="TCP-Verbindung zur App auf diese IP lenken (Hairpin-Workaround, wie curl --resolve); "
                        "leer = normale DNS-Aufloesung")
    p.add_argument("--video", default=None,
                   help="ein Video fuer alle Szenarien statt config.SCENARIO_VIDEOS")
    p.add_argument("--out-dir", default="e2e-report")
    p.add_argument("--video-timeout", type=float, default=cfg.VIDEO_TIMEOUT)
    p.add_argument("--plugin-timeout", type=float, default=cfg.PLUGIN_TIMEOUT)
    p.add_argument("--poll-interval", type=float, default=cfg.POLL_INTERVAL)
    p.add_argument("--settle", type=float, default=cfg.SCRAPE_SETTLE)
    p.add_argument("--cooldown", type=float, default=cfg.BASELINE_WINDOW,
                   help="Pause zwischen Szenarien bei --scenario both")
    p.add_argument("--keep", action="store_true", help="Testvideo nach dem Lauf NICHT loeschen (Debugging)")
    p.add_argument("--dry-run", action="store_true", help="nur Guards/Konfiguration pruefen, keine Requests")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    check_targets(args.base_url, args.prom_url, args.connect_ip)
    scenarios = ["standard", "plugins"] if args.scenario == "both" else [args.scenario]

    if args.dry_run:
        print(f"dry-run ok: base_url={args.base_url} prom_url={args.prom_url} connect_ip={args.connect_ip or '-'}")
        for s in scenarios:
            print(f"  {s}: " + " -> ".join(p["plugin"] for p in cfg.SCENARIOS[s]))
            video = video_for(s, args)
            print(f"    video: {video} ({'vorhanden' if os.path.isfile(video) else 'FEHLT'})")
        return 0

    for s in scenarios:
        video = video_for(s, args)
        if not os.path.isfile(video):
            raise SystemExit(
                f"Abbruch: Testvideo fehlt: {video} (auf sportvid01 unter /opt/e2e-data ablegen, "
                "siehe tests/e2e/README.md)"
            )
        # Schutz gegen abgebrochene Kopien oder Platzhalter (z.B. ein LFS-Pointer)
        if os.path.getsize(video) < 1024:
            raise SystemExit(f"Abbruch: {video} ist unvollstaendig (< 1 KB), kein echtes Video")
    user, password = os.environ.get("E2E_USER"), os.environ.get("E2E_PASSWORD")
    if not user or not password:
        raise SystemExit("Abbruch: E2E_USER/E2E_PASSWORD nicht gesetzt.")
    # nginx-Basic-Auth vor der dev-Domain (siehe SportvidClient)
    basic_user, basic_password = os.environ.get("E2E_BASIC_USER"), os.environ.get("E2E_BASIC_PASSWORD")
    if not basic_user or not basic_password:
        raise SystemExit("Abbruch: E2E_BASIC_USER/E2E_BASIC_PASSWORD nicht gesetzt (nginx-Basic-Auth der dev-Domain).")

    if args.connect_ip:
        pin_host(urlparse(args.base_url).hostname, args.connect_ip)
    client = SportvidClient(args.base_url, basic_auth=(basic_user, basic_password))
    prom = Prometheus(args.prom_url)
    try:
        client.login(user, password)
    except ApiError as e:
        res = ScenarioResult(scenario="login")
        res.fail(f"Login fehlgeschlagen: {e}")
        write_reports([res], args.out_dir)
        return EXIT_CODES[FAIL]

    results = []
    for i, s in enumerate(scenarios):
        if i > 0:
            # Sonst laege die Last des vorigen Szenarios im Baseline-Fenster
            # des naechsten und verfaelscht die GPU-/CPU-Vergleiche.
            print(f"Cooldown {args.cooldown:.0f}s vor Szenario {s}", flush=True)
            time.sleep(args.cooldown)
        results.append(run_scenario(s, client, prom, args))
        # neues Fenster je Szenario, damit die Checks nicht ueberlappen
        client.server_errors.clear()
    overall = write_reports(results, args.out_dir)
    print(f"\nGesamt: {overall} (Report: {args.out_dir}/report.md)")
    return EXIT_CODES[overall]


if __name__ == "__main__":
    sys.exit(main())
