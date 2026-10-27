import io
import json
import logging
import os
import tarfile
from collections import Counter, defaultdict
from typing import Iterator, Tuple

import requests
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from backend.models import LensProfile
from backend.utils.lens import parse_eis, unsupported_reason


logger = logging.getLogger(__name__)

# Gyroflow lens profile database (CC0-1.0), pinned so imports are reproducible
REPOSITORY_TARBALL = "https://codeload.github.com/gyroflow/lens_profiles/tar.gz/{commit}"
DEFAULT_COMMIT = "886fc616c9c2c788856f54c21d451b9cb7fc4f44"
# top-level directories of the repository, i.e. the camera groups people record training footage with
DEFAULT_GROUPS = ["GoPro", "DJI", "Mobile phones"]


def _iter_tarball(commit: str) -> Iterator[Tuple[str, bytes]]:
    response = requests.get(REPOSITORY_TARBALL.format(commit=commit), timeout=300)
    response.raise_for_status()
    with tarfile.open(fileobj=io.BytesIO(response.content), mode="r:gz") as tar:
        for member in tar:
            if member.isfile() and member.name.endswith(".json"):
                # strip the "lens_profiles-<commit>/" prefix
                yield member.name.split("/", 1)[1], tar.extractfile(member).read()


def _iter_directory(path: str) -> Iterator[Tuple[str, bytes]]:
    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith(".json"):
                full_path = os.path.join(root, file)
                with open(full_path, "rb") as f:
                    yield os.path.relpath(full_path, path).replace(os.sep, "/"), f.read()


class Command(BaseCommand):
    help = "Import lens profiles from Gyroflow's lens profile database (https://github.com/gyroflow/lens_profiles)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path", type=str, help="local checkout of the lens_profiles repository (skips the download)"
        )
        parser.add_argument("--commit", type=str, default=DEFAULT_COMMIT, help="repository commit to download")
        parser.add_argument("--groups", nargs="+", default=DEFAULT_GROUPS, help="top-level directories to import")

    def handle(self, *args, **options):
        groups = set(options["groups"])
        if options["path"]:
            if not os.path.isdir(options["path"]):
                raise CommandError(f"Not a directory: {options['path']}")
            files = _iter_directory(options["path"])
            source_commit = options["commit"] if options["commit"] != DEFAULT_COMMIT else "local"
        else:
            self.stdout.write(f"Downloading lens profiles @ {options['commit']}")
            files = _iter_tarball(options["commit"])
            source_commit = options["commit"]

        profiles = []
        skipped = Counter()
        for key, content in files:
            group = key.split("/", 1)[0]
            if group not in groups:
                continue
            try:
                raw = json.loads(content.decode("utf-8-sig"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                skipped["unparsable"] += 1
                continue

            params = raw.get("fisheye_params") or {}
            calib = raw.get("calib_dimension") or {}
            if not calib.get("w") or not calib.get("h") or not params.get("camera_matrix"):
                skipped["missing calibration"] += 1
                continue
            profiles.append((key, group, raw))

        # the same brand is sometimes spelled differently ("DJI" / "Dji"), use the most common spelling
        spellings = defaultdict(Counter)
        for _, _, raw in profiles:
            brand = (raw.get("camera_brand") or "").strip()
            spellings[brand.lower()][brand] += 1
        canonical_brand = {k: v.most_common(1)[0][0] for k, v in spellings.items()}

        created = updated = 0
        with transaction.atomic():
            for key, group, raw in profiles:
                params = raw["fisheye_params"]
                brand = canonical_brand[(raw.get("camera_brand") or "").strip().lower()]
                _, was_created = LensProfile.objects.update_or_create(
                    key=key,
                    defaults={
                        "name": raw.get("name") or os.path.splitext(os.path.basename(key))[0],
                        "group": group,
                        "brand": brand or group,
                        "model": (raw.get("camera_model") or "").strip(),
                        "lens_model": (raw.get("lens_model") or "").strip(),
                        "camera_setting": (raw.get("camera_setting") or "").strip(),
                        "note": (raw.get("note") or "").strip(),
                        "calib_width": int(raw["calib_dimension"]["w"]),
                        "calib_height": int(raw["calib_dimension"]["h"]),
                        "fps": raw.get("fps") or None,
                        "camera_matrix": params["camera_matrix"],
                        "distortion_coeffs": params.get("distortion_coeffs") or [],
                        "rms_error": params.get("RMS_error"),
                        "official": bool(raw.get("official")),
                        "eis": parse_eis(
                            raw.get("name"), raw.get("note"), raw.get("lens_model"), raw.get("camera_setting")
                        ),
                        "unsupported_reason": unsupported_reason(raw),
                        "source_commit": source_commit,
                        "raw": raw,
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {created + updated} lens profiles ({created} new, {updated} updated) "
                f"from {', '.join(sorted(groups))}; skipped: {dict(skipped) or 'none'}"
            )
        )
