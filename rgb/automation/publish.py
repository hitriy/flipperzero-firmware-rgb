"""Upload to a draft release, then publish; never publish a partial build."""

import json
import os
from pathlib import Path
import subprocess
import urllib.error

from releases import api, rgb_tag


def run(*args):
    return subprocess.check_output(args, text=True).strip()


def main():
    repo = os.environ["GITHUB_REPOSITORY"]
    tag = rgb_tag(os.environ["UPSTREAM_TAG"])
    url = f"https://github.com/{repo}.git"
    sha = run("git", "-C", "source", "rev-parse", "HEAD")
    previous = run("git", "ls-remote", url, f"refs/tags/{tag}")
    if previous and previous.split()[0] != sha:
        raise RuntimeError("Existing RGB tag points at different source; bump PATCH_REVISION")
    run("gh", "auth", "setup-git")
    run("git", "-C", "source", "push", url, f"refs/tags/{tag}")
    try:
        release = api(f"repos/{repo}/releases/tags/{tag}")
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        release = None
    if release and not release["draft"]:
        raise RuntimeError("Refusing to overwrite an already published release")
    provenance = json.loads(Path("release/provenance.json").read_text())
    notes = (
        f"Official Flipper Zero **{os.environ['UPSTREAM_TAG']}** with quen0n's RGB backlight patch, "
        "ported for current firmware. For the three-LED SK6805 hardware mod on PA8.\n\n"
        "Select the colour in Settings → LCD and Notifications → LCD Color.\n\n"
        "Install the `update-*.tgz` package with qFlipper or copy/extract it to the SD card "
        "and run its update file. The full DFU image is also attached.\n\n"
        f"Upstream commit: `{provenance['upstream_commit']}`\n\n"
        f"Patched source commit: `{sha}`\n\n"
        "Build verified automatically; hardware behaviour has not been tested by this pipeline. "
        "Patch, provenance and SHA-256 checksums are attached.\n"
    )
    Path("release-notes.txt").write_text(notes, encoding="utf-8")
    if not release:
        run("gh", "release", "create", tag, "--repo", repo, "--verify-tag", "--draft",
            "--title", f"Flipper Zero {os.environ['UPSTREAM_TAG']} + RGB",
            "--notes-file", "release-notes.txt")
    run("gh", "release", "upload", tag, "--repo", repo, "--clobber",
        *map(str, sorted(Path("release").iterdir())))
    run("gh", "release", "edit", tag, "--repo", repo, "--draft=false",
        "--notes-file", "release-notes.txt")


if __name__ == "__main__":
    main()
