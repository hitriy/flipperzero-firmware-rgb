"""Adapt a pinned Flipper Lab checkout to a static, same-origin RGB updater."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

LAB_COMMIT = "9902d4d8103fa5df1e478cbd5d35a3a6f4f566fc"
REPO = "hitriy/flipperzero-firmware-rgb"


def replace(path, before, after):
    text = path.read_text(encoding="utf-8")
    if before not in text:
        raise RuntimeError(f"Pinned upstream source changed: {path}: {before[:60]}")
    path.write_text(text.replace(before, after), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lab", type=Path, required=True)
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--downloads", type=Path, required=True)
    parser.add_argument("--base", default="/flipperzero-firmware-rgb/")
    args = parser.parse_args()
    if not re.fullmatch(r"/[a-zA-Z0-9_-]+/", args.base):
        raise ValueError("Expected a GitHub Pages project base path")
    release = json.loads(args.release.read_text(encoding="utf-8-sig"))
    tag = release["tag_name"]
    match = re.fullmatch(r"rgb-(v?\d+\.\d+\.\d+)-r\d+", tag)
    if not match or release["draft"] or release["prerelease"]:
        raise ValueError("Expected a published RGB stable release")
    name = f"flipper-z-f7-update-{tag}.tgz"
    asset = next(a for a in release["assets"] if a["name"] == name)
    bundle = args.downloads / name
    digest = hashlib.sha256(bundle.read_bytes()).hexdigest()
    checksums = dict(line.split(maxsplit=1)[::-1] for line in
                     (args.downloads / "SHA256SUMS").read_text().splitlines())
    if checksums.get(name) != digest or asset.get("digest") != f"sha256:{digest}":
        raise ValueError("Firmware checksum mismatch")
    frontend = args.lab / "frontend"
    public = frontend / "public"
    (public / "firmware").mkdir(exist_ok=True)
    shutil.copy2(bundle, public / "firmware" / name)
    shutil.copy2(args.downloads / "SHA256SUMS", public / "firmware/SHA256SUMS")
    version = match[1].removeprefix("v")
    file = {"url": f"{args.base}firmware/{name}", "type": "update_tgz", "target": "f7", "sha256": digest}
    channels = {"rgb_tag": tag, "release_url": release["html_url"], "channels": [
        {"id": "release", "title": "Official + RGB", "versions": [{"version": version, "files": [file]}]},
        {"id": "custom", "title": "Official + RGB", "versions": [{"version": tag, "files": [file]}]},
    ]}
    (public / "channels.json").write_text(json.dumps(channels, indent=2) + "\n")
    (public / ".nojekyll").touch()
    shutil.copy2(Path(__file__).with_name("NOTICE.txt"), public / "NOTICE.txt")

    api = frontend / "src/entities/Flipper/api/index.ts"
    text = api.read_text()
    start = text.index("async function fetchChannels(")
    end = text.index("async function fetchRegions()")
    text = text[:start] + f'''async function fetchChannels() {{
  const response = await fetch('{args.base}channels.json', {{ cache: 'no-cache' }})
  if (!response.ok) throw new Error('Unable to load RGB release metadata')
  const data = await response.json()
  return data.channels
}}

''' + text[end:]
    api.write_text(text, encoding="utf-8")
    config = frontend / "quasar.config.ts"
    replace(config, "vueRouterMode: 'history'", "vueRouterMode: 'hash'")
    replace(config, "// publicPath: '/',", f"publicPath: '{args.base}',")
    # Upstream spreads process.env into the client bundle. Never embed runner secrets.
    replace(config, "...process.env", f"RGB_PUBLIC_PATH: '{args.base}'")
    replace(frontend / "src/app/App.vue", "Platform.is.electron ? '' : '/'",
            "Platform.is.electron ? '' : process.env.RGB_PUBLIC_PATH")
    update = frontend / "src/features/Flipper/ui/Update.vue"
    replace(update, ':options="Object.values(fwOptions)"',
            ':options="Object.values(fwOptions).filter(option => option.value === \'custom\')"')
    replace(update, 'v-if="fwModel"', 'v-if="fwModel && channels.length"')
    replace(update, "Firmware Update</p>", "RGB Firmware Update</p>")
    replace(update, "Your firmware is up to date.", "Official base version matches. Install below to apply the RGB build.")

    header = frontend / "src/app/layouts/Main/components/Header.vue"
    text = header.read_text()
    text = re.sub(r"      <img\s.*?/>",
                  '      <div class="text-h6 text-weight-bold">Flipper RGB</div>', text, count=1, flags=re.S)
    start = text.index("const extLinks = [")
    end = text.index("\nconst linksMenu", start)
    text = text[:start] + f'''const extLinks = [
  {{ title: 'Releases', icon: 'download', link: 'https://github.com/{REPO}/releases', blank: true, router: false }},
  {{ title: 'Source', icon: 'code', link: 'https://github.com/{REPO}', blank: true, router: false }},
  {{ title: 'Flipper Lab', icon: 'open_in_new', link: 'https://github.com/flipperdevices/lab.flipper.net', blank: true, router: false }}
]
''' + text[end:]
    header.write_text(text)
    layout = frontend / "src/app/layouts/Main/MainLayout.vue"
    replace(layout, '''<q-page class="flex flex-center fit" padding>
          <FlipperConnectWebBtn />''', f'''<q-page class="flex flex-center column fit" padding>
          <div style="max-width: 620px; text-align: center; margin: 28px 16px">
            <h1 style="font-size: 36px; line-height: 1.2; font-weight: 700">Official firmware.<br>RGB backlight.</h1>
            <p style="font-size: 18px">Install <strong>{tag}</strong> directly over USB.</p>
            <p>For the three-LED SK6805 backlight mod. Use Chrome or Edge on desktop, close qFlipper, and connect your Flipper with a USB data cable. A microSD card must be installed.</p>
            <p><a href="{release['html_url']}" target="_blank" rel="noopener">Release notes and downloads</a> · <a href="{args.base}firmware/{name}">Download update bundle</a></p>
          </div>
          <FlipperConnectWebBtn />
          <p style="max-width: 620px; text-align: center; margin: 28px 16px; color: #666">Unofficial RGB build by hitriy, based on quen0n’s patch. Powered by Flipper Lab. Browser updating requires a normally booting device; use qFlipper for DFU recovery. Firmware has been build-tested; hardware testing is still required.</p>''')
    package = frontend / "package.json"
    data = json.loads(package.read_text())
    data["productName"] = "Flipper RGB — Web Updater"
    data["description"] = "Official Flipper Zero firmware with RGB backlight. Install hitriy’s builds over USB."
    package.write_text(json.dumps(data, indent=2) + "\n")
    replace(frontend / "index.html", 'user-scalable=no, initial-scale=1, maximum-scale=1, minimum-scale=1, width=device-width',
            'initial-scale=1, width=device-width')
    print(f"Prepared {tag}; SHA256 {digest}; Pages base {args.base}")


if __name__ == "__main__":
    main()
