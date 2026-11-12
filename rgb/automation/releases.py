"""Select official stable releases not yet published by this RGB fork."""

import json
import os
import re
import urllib.error
import urllib.request

UPSTREAM = "flipperdevices/flipperzero-firmware"
MIN_VERSION = (1, 5, 1)
PATCH_REVISION = 1


def version(tag):
    if not isinstance(tag, str) or not re.fullmatch(r"v?\d+\.\d+\.\d+", tag):
        raise ValueError(f"Not a stable firmware version: {tag!r}")
    return tuple(map(int, tag.removeprefix("v").split(".")))


def rgb_tag(tag):
    version(tag)
    return f"rgb-{tag}-r{PATCH_REVISION}"


def api(path):
    request = urllib.request.Request(
        f"https://api.github.com/{path}",
        headers={
            "Authorization": f"Bearer {os.environ['GH_TOKEN']}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "flipper-rgb-release-builder",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def select(releases, published, requested=""):
    if requested:
        version(requested)
    result = []
    for release in releases:
        if release["draft"] or release["prerelease"]:
            continue
        tag = release["tag_name"]
        try:
            parsed = version(tag)
        except ValueError:
            continue
        if parsed < MIN_VERSION or (requested and tag != requested):
            continue
        if rgb_tag(tag) not in published:
            result.append(tag)
    if requested and not any(
        r["tag_name"] == requested and not r["draft"] and not r["prerelease"]
        and version(requested) >= MIN_VERSION for r in releases
    ):
        raise ValueError("Requested tag is not a supported published official stable release")
    return sorted(set(result), key=version)


def all_releases(repo):
    result = []
    page = 1
    while True:
        batch = api(f"repos/{repo}/releases?per_page=100&page={page}")
        result.extend(batch)
        if len(batch) < 100:
            return result
        page += 1


def main():
    requested = os.environ.get("REQUESTED_TAG", "")
    published = {
        release["tag_name"] for release in all_releases(os.environ["GITHUB_REPOSITORY"])
        if not release["draft"]
    }
    tags = select(all_releases(UPSTREAM), published, requested)
    # GitHub matrices allow at most 256 jobs; subsequent checks catch up further.
    tags = tags[:20]
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write(f"matrix={json.dumps({'tag': tags})}\n")
        output.write(f"pending={'true' if tags else 'false'}\n")
    print(f"Pending stable releases: {tags}")


if __name__ == "__main__":
    main()
