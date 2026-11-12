# E2E-Test sportvid (dev)

Funktionaler End-to-End-Test: Ein Testvideo wird hochgeladen und analysiert.
Danach prüft der Test über die Prometheus-HTTP-API, ob die erwarteten
Monitoring-Signale im Zeitfenster des Laufs aufgetreten sind.

Hintergrund, Entscheidungen und offene Punkte stehen im Servermonitoring-Repo
unter `docs/e2e-tests.md`.

## Szenarien

| Szenario | Ablauf |
|---|---|
| `standard` | Upload (HLS-Konvertierung) → `object_tracker` (Spieler-Tracking, GPU) |
| `plugins` | Upload → `object_tracker` → `team_clustering` (auf den Tracklets des Trackers) |
| `both` | `standard`, dann 5 min Cooldown, dann `plugins` |

Die automatische Analyse beim Upload ist im Backend derzeit auskommentiert
(`views/video.py`, `tasks/convert_video.py`). Deshalb startet der Test jedes
Plugin explizit über `POST /api/plugin/run/new`. Parameter und Begründungen
stehen in `config.py`.

Es kommen nur Plugins infrage, deren Ray-Plugins auf dev deployt sind
(`inference_ray/deploy.dev.yml`). Alle anderen lehnt das Backend mit HTTP 400
`plugin_unavailable` ab. Deshalb fragt der Test vorab `GET /api/plugin/available` ab.
Fehlt ein Szenario-Plugin, endet er als INCONCLUSIVE, bevor ein Video hochgeladen wird.
Die ursprünglich geplanten `shotdetection`, `shot_type_classification` und
`face_clustering` sind seit dem Infra-Umbau vom 2026-10-27 nicht mehr deployt.

## Ergebnis

- **PASS** (Exit 0): Video und alle Plugin-Runs sind `DONE`, kein HTTP-5xx und alle harten PromQL-Checks sind erfüllt.
- **FAIL** (Exit 1): Ein funktionaler Fehler oder ein harter Check ist fehlgeschlagen.
- **INCONCLUSIVE** (Exit 2): Prometheus ist nicht erreichbar, Targets sind nicht UP oder ein Szenario-Plugin ist auf dev nicht deployt. Der Test wird dann gar nicht erst gestartet.

Der zentrale Nachweis ist je Plugin der Check „Ray Serve Requests `<application>`“.
Er zählt nur Requests auf die Ray-Serve-Application des Plugins (`ray_apps` in
`config.py`). Der allgemeine Request-Zähler ist nur weich, weil schon der Upload
den `thumbnail_generator` aufruft.

Weiche Checks (`hard=False`) erzeugen nur WARN. Das betrifft die GPU, weil sie
wahrscheinlich mit prod geteilt wird, und den allgemeinen Ray-Request-Zähler.
Alle Checks stehen in `promql_checks.py`.

Das Testvideo wird am Ende immer gelöscht, außer mit `--keep`. Die
PluginRuns und Timelines verschwinden per FK-CASCADE mit.

## Ausführen

Nur manuell über GitHub → Actions → **e2e_dev** → *Run workflow*. Der
Workflow läuft auf dem Self-Hosted-Runner auf sportvid01, weil Prometheus dort
nur auf `127.0.0.1:9090` erreichbar ist. Der Report (`report.md`/`report.json`)
landet als Artifact und in der Job-Summary.

> `workflow_dispatch` erscheint in der GitHub-Oberfläche erst, wenn
> `e2e-dev.yml` auf dem Default-Branch liegt (`develop`). Danach lässt er sich
> per *Use workflow from* auf jedem Branch starten.
>
> **Temporär (vor dem PR entfernen):** Bis dahin startet jeder Push auf
> `feature/e2e-tests-develop`, der `tests/e2e/**` oder die Workflow-Datei ändert,
> einen Lauf (Szenario `standard`, Video wird behalten).

Lokal geht nur der Offline-Teil (es gibt keinen Zugriff auf das Prometheus von sportvid01):

```sh
pip install -r tests/e2e/requirements.txt
python -m unittest discover -s tests/e2e -v     # Offline-Tests mit Fakes
python tests/e2e/run_e2e.py --dry-run --scenario both
```

Das Script lehnt alles außer `https://dev.sportvid.dshs-koeln.de` und
lokales Prometheus hart ab. Ein Override-Flag gibt es bewusst nicht.

## Vorbedingungen (einmalig)

1. Test-User auf dev anlegen. Die Zugangsdaten kommen als Repo-Secrets
   `E2E_DEV_USER` und `E2E_DEV_PASSWORD` ins sportvid-Repo. Dazu die
   nginx-Basic-Auth der dev-Domain (`.htpasswd`, derselbe Login wie im Browser-Popup)
   als `E2E_DEV_BASIC_USER` und `E2E_DEV_BASIC_PASSWORD`.
2. Die Testvideos auf sportvid01 unter `/opt/e2e-data/` ablegen, lesbar für den
   User `github-runner` (siehe Abschnitt „Testvideo“). Sie liegen bewusst **nicht**
   im Repo.
3. Runner-Host (als `github-runner`): `python3 -m venv` funktioniert
   (seit 2026-11-04 installiert). Die dev-Domain ist vom Host selbst aus **nicht**
   erreichbar (Hairpin), deshalb verbindet sich das Script per `--connect-ip 127.0.0.1`
   direkt mit dem lokalen Proxy. Verifiziert per `curl --resolve`.

## Testvideo

**Ablage:** auf sportvid01 unter `/opt/e2e-data/`. Der Workflow setzt
`E2E_VIDEO_DIR=/opt/e2e-data`. Lokal greift der Fallback `tests/e2e/data/`, der
per `.gitignore` (`**/data/`) ausgeschlossen ist.

Warum nicht im Repo: `Sportvid/sportvid` ist ein **öffentlicher Fork**. GitHub
lehnt dort neue LFS-Objekte ab („can not upload new objects to public fork“, 2026-11-05).
Als normale Git-Dateien wären sie öffentlich und dauerhaft in der Historie.

Einrichtung (einmalig, als User mit sudo auf sportvid01; die Dateien vorher per `scp`
nach `/tmp/` kopieren):

    sudo install -d -m 755 /opt/e2e-data
    sudo install -m 644 /tmp/e2e_clip.mp4 /tmp/e2e_clip_faces.mp4 /opt/e2e-data/
    sudo -u github-runner ls -la /opt/e2e-data

Zwei Videos, Zuordnung zu den Szenarien in `config.SCENARIO_VIDEOS`:

| Datei | Szenario | Inhalt |
|---|---|---|
| `e2e_clip.mp4` | `standard` | feste Weitwinkelkamera, Fußballplatz bei Tag, Spieler sehr klein |
| `e2e_clip_faces.mp4` | `plugins` | Training bei Flutlicht, Kamera nah am Spiel, Trikots gut erkennbar (für `team_clustering`). Der Name stammt aus der ursprünglichen Auswahl für `face_clustering`. |

`e2e_clip_faces.mp4`: 30 s (Sekunde 36-66 einer 181-s-Aufnahme), H.264
1920x1080 (Auflösung bewusst behalten, damit die Detektion genug Pixel hat), AAC, ca. 38 MB:

    ffmpeg -ss 36 -i original2.mp4 -t 30 -map 0:v:0 -map 0:a:0? \
      -c:v libx264 -preset medium -crf 23 -pix_fmt yuv420p \
      -c:a aac -b:a 128k -movflags +faststart e2e_clip_faces.mp4

`e2e_clip.mp4`: 60 s, H.264 1280x720, AAC, ca. 4 MB.
Erzeugt am 2026-11-05 aus einer 87-s-Aufnahme (HEVC 1080p, 492 MB):

    ffmpeg -i original.mp4 -t 60 -map 0:v:0 -map 0:a:0? -vf scale=-2:720 \
      -c:v libx264 -preset medium -crf 26 -pix_fmt yuv420p \
      -c:a aac -b:a 128k -movflags +faststart e2e_clip.mp4

Neu kodiert, weil das Original selbst gekürzt noch 339 MB hatte. Jeder Lauf
lädt das Video über den Proxy hoch.

Achtung: Die sportvid-`.gitignore` ignoriert `README.md`. Diese Datei braucht
deshalb `git add -f`.

**Herkunft:** Beide Aufnahmen wurden eigens für diesen Test aufgenommen und
für die Verwendung hier freigegeben (Bestätigung durch H. Möller, 2026-11-05).
