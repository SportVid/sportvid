"""Zentrale Konfiguration fuer den E2E-Test gegen sportvid **dev**.

Alles, was umgebungs- oder versionsabhaengig ist (Hostnamen, Metrik-/Container-
Namen, Plugin-Parameter, Schwellwerte), steht hier gebuendelt. Werte mit
"UNVERIFIED" waeren aus Code/Dashboards abgeleitet, aber noch nicht gegen die
echte Prometheus-Instanz auf sportvid01 geprueft.
"""

# --- Ziel-Guard -------------------------------------------------------------
# Der Test darf ausschliesslich gegen dev laufen (geteilter Host/GPU mit prod,
# siehe Servermonitoring docs/e2e-tests.md). run_e2e.py bricht hart ab, wenn
# --base-url auf einen anderen Host zeigt.
ALLOWED_APP_HOSTS = {"dev.sportvid.dshs-koeln.de"}
DEFAULT_BASE_URL = "https://dev.sportvid.dshs-koeln.de"

# Prometheus ist auf sportvid01 nur an 127.0.0.1:9090 gebunden - der Test
# laeuft deshalb auf dem Self-Hosted-Runner und fragt lokal ab.
ALLOWED_PROM_HOSTS = {"localhost", "127.0.0.1"}
DEFAULT_PROM_URL = "http://localhost:9090"

# Grafana ist nicht oeffentlich; Links im Report setzen einen SSH-Tunnel
# (localhost:3000) voraus.
DEFAULT_GRAFANA_URL = "http://localhost:3000"
GRAFANA_DASHBOARDS = {
    "Ray Serve": "rayServeDashboard",
    "Ray Default": "rayDefaultDashboard",
    "cAdvisor Container": "cadvisorContainerResources",
    "SportVid App-Metriken": "sportvidAppMetrics",
}

# --- Testlaeufe -------------------------------------------------------------
# Nur Plugins, deren Ray-Plugins auf dev deployt sind (inference_ray/deploy.dev.yml).
# Das Backend lehnt alle anderen mit HTTP 400 "plugin_unavailable" ab (plugin_catalogue.py).
# shotdetection, shot_type_classification und face_clustering sind seit dem
# Infra-Umbau vom 2026-10-27 weder auf dev noch auf prod deployt. Der erste echte
# Lauf am 2026-11-12 scheiterte genau daran.
#
# Felder je Plugin:
#   plugin      Backend-Plugin-Name fuer POST /api/plugin/run/new
#   parameters  werden 1:1 geschickt
#   ray_apps    Ray-Serve-Applications, die das Plugin aufruft (= Task.ray_plugins
#               im Backend, = "name" in deploy.dev.yml). Fuer den PromQL-Nachweis, dass
#               genau dieses Plugin gelaufen ist (Label application=...).
#   needs       {parameter: plugin}: setzt die PluginRun-ID eines frueheren Plugins
#               im selben Szenario als Parameter ein.
OBJECT_TRACKER = {
    "plugin": "object_tracker",
    # detector/tracker wie Frontend-Default (usePluginParams.js DEFAULT_PLAYER_DETECTOR,
    # ModalPlugin.vue tracker "bytetrack"). Den Rest (detector_params etc.) fuellt der
    # Serializer (serializers/object_tracker.py). Abweichung: fps 10 (Server-Default)
    # statt Video-fps (Frontend, meist 30), um Laufzeit und GPU-Last zu dritteln.
    "parameters": {"fps": 10, "detector": "yolox_sportsmot", "tracker": "bytetrack"},
    "ray_apps": ["object_tracker"],
}
TEAM_CLUSTERING = {
    "plugin": "team_clustering",
    # Server-Defaults (KMEANS, K=3, 2 Teams), siehe serializers/team_clustering.py.
    # Braucht die Tracklets (TYPE_BBOXES) eines object_tracker-Runs.
    "parameters": {},
    "ray_apps": ["team_clustering"],
    "needs": {"object_tracker_id": "object_tracker"},
}

SCENARIOS = {
    # Lauf A: Upload (HLS) + Spieler-Tracking (GPU)
    "standard": [OBJECT_TRACKER],
    # Lauf B: Tracking, danach Team-Zuordnung auf dessen Ergebnis (nacheinander)
    "plugins": [OBJECT_TRACKER, TEAM_CLUSTERING],
}

# Testvideo je Szenario. Die Dateien liegen NICHT im Repo, sondern im Verzeichnis
# E2E_VIDEO_DIR (Workflow: /opt/e2e-data auf sportvid01, lokal tests/e2e/data/). Grund:
# oeffentlicher Fork, keine LFS-Uploads moeglich. Herkunft siehe README.
# Lauf A: feste Weitwinkelkamera, Spieler klein, reicht fuer Tracking. Lauf B: Kamera
# naeher am Spiel, Trikotfarben besser erkennbar fuer team_clustering. (Der Clip wurde
# urspruenglich fuer face_clustering ausgewaehlt, daher der Dateiname.)
SCENARIO_VIDEOS = {
    "standard": "e2e_clip.mp4",
    "plugins": "e2e_clip_faces.mp4",
}

UPLOAD_FIELDS = {"sport": "soccer"}

# --- Timeouts / Timing (Sekunden) --------------------------------------------
VIDEO_TIMEOUT = 10 * 60
PLUGIN_TIMEOUT = 20 * 60
POLL_INTERVAL = 10
# Scrape-Intervall ist 15s - nach Abschluss warten, bis Prometheus die letzten
# Werte sicher eingesammelt hat.
SCRAPE_SETTLE = 60
BASELINE_WINDOW = 5 * 60

# --- Prometheus-Labels/Namen --------------------------------------------------
ENV_LABEL = 'environment="dev"'
# Container-Namen der dev-Umgebung in cAdvisor. Verifiziert 2026-11-04 per
# count by (name) (container_last_seen{name=~".*dev.*"}). PromQL-Regex sind voll
# verankert, die Namen muessen also exakt passen.
DEV_CONTAINER_REGEX = "analyser_dev|inference_ray_dev|celery-gpu_dev"
# OOM-Kills der dev-Container laut cAdvisor. Ersetzt den frueheren Ray-Counter
# (ray_memory_manager_worker_eviction_total): Eine Suche nach ray_.*(evict|oom|kill).*
# lieferte am 2026-11-04 keine Daten, diese Ray-Version exportiert ihn also nicht.
# Verifiziert 2026-11-12: Im ersten echten Lauf lieferte die Query einen Wert (0)
# statt "ohne Daten", die Serien existieren also.
OOM_METRIC = "container_oom_events_total"

# Vorcheck: jedes Target muss UP sein (min(up) == 1), sonst INCONCLUSIVE.
# Ray: Die Service-Discovery-Datei, die Ray selbst schreibt, setzt
# das Label job="ray" und ueberschreibt damit den job_name
# "inference_ray_dev" aus prometheus.yml. Am 2026-11-04 lieferte
# up{job="inference_ray_dev"} nichts, obwohl Ray-Metriken mit
# environment="dev" ankamen. Deshalb wird ueber das environment-Label
# gefiltert und beide Job-Namen werden akzeptiert.
# Verifiziert 2026-11-04: count by (job) (up{environment="dev"}) liefert job="ray" (3 Targets).
PRECHECK_TARGETS = {
    "inference_ray_dev": 'up{environment="dev",job=~"ray|inference_ray_dev"}',
    "sportvid_backend_dev": 'up{job="sportvid_backend_dev"}',
    "sportvid_celery_dev": 'up{job="sportvid_celery_dev"}',
    "cadvisor": 'up{job="cadvisor"}',
}

# --- Hairpin-Workaround --------------------------------------------------------
# sportvid01 erreicht seine eigene oeffentliche dev-Domain nicht (curl am
# 2026-11-04: Timeout nach 135 s). Deshalb kann die TCP-Verbindung direkt auf
# eine lokale IP gelenkt werden, wie bei curl --resolve. Hostname, SNI und
# Zertifikatspruefung bleiben dev.sportvid.dshs-koeln.de, also routet der
# Proxy weiterhin auf dev, und der Hard-Guard greift unveraendert.
# Verifiziert 2026-11-05: curl --resolve ...:443:127.0.0.1 erreicht den dev-vhost des
# lokalen Proxys (Antwort 401 = nginx-Basic-Auth, siehe sportvid_client.py).
DEFAULT_CONNECT_IP = "127.0.0.1"
ALLOWED_CONNECT_IPS = {"127.0.0.1", "172.20.5.25"}

# Mindestanstieg gegenueber Baseline, damit "Last sichtbar" als erfuellt gilt.
GPU_UTIL_MIN_DELTA = 20.0  # Prozentpunkte
GPU_BASELINE_SATURATED = 80.0  # darueber ist der Vergleich nicht aussagekraeftig
CPU_MIN_DELTA_CORES = 0.2
