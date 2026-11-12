"""Collect tested f7 output and record exactly which sources built it."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


def git(*args):
    return subprocess.check_output(["git", "-C", "source", *args], text=True).strip()


def main():
    tag = os.environ["RGB_TAG"]
    output = Path("release")
    output.mkdir(exist_ok=True)
    dist = Path("source/dist/f7-C")
    required = [f"flipper-z-f7-update-{tag}.tgz", f"flipper-z-f7-full-{tag}.dfu"]
    for name in required:
        if not (dist / name).is_file():
            raise RuntimeError(f"Required build output missing: {name}")
    for path in dist.iterdir():
        if path.is_file():
            shutil.copy2(path, output / path.name)
    patch = Path("automation/rgb/patches/0001-rgb-backlight.patch")
    shutil.copy2(patch, output / patch.name)
    provenance = {
        "upstream": "https://github.com/flipperdevices/flipperzero-firmware",
        "upstream_tag": os.environ["UPSTREAM_TAG"],
        "upstream_commit": Path("upstream-sha.txt").read_text().strip(),
        "rgb_tag": tag,
        "rgb_commit": git("rev-parse", "HEAD"),
        "automation_commit": subprocess.check_output(
            ["git", "-C", "automation", "rev-parse", "HEAD"], text=True).strip(),
        "patch_sha256": hashlib.sha256(patch.read_bytes()).hexdigest(),
        "patch_origin": "https://github.com/quen0n/flipperzero-firmware-rgb",
        "build_command": "./fbt TARGET_HW=7 DEBUG=0 COMPACT=1 updater_package fap_dist",
        "hardware_tested": False,
    }
    (output / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    checksums = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}"
                 for p in sorted(output.iterdir()) if p.name != "SHA256SUMS"]
    (output / "SHA256SUMS").write_text("\n".join(checksums) + "\n")


if __name__ == "__main__":
    main()
