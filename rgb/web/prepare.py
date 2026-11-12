"""Adapt a pinned Flipper Lab checkout to a static, same-origin RGB updater."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

LAB_COMMIT = "9902d4d8103fa5df1e478cbd5d35a3a6f4f566fc"
REPO = "hitriy/flipperzero-firmware-rgb"


def release_key(release):
    match = re.fullmatch(r"rgb-v?(\d+)\.(\d+)\.(\d+)-r(\d+)", release["tag_name"])
    if not match:
        raise ValueError("Expected an RGB release tag")
    return tuple(map(int, match.groups()))


def published_releases(data):
    releases = data if isinstance(data, list) else [data]
    return sorted((r for r in releases if not r["draft"] and not r["prerelease"]
                   and re.fullmatch(r"rgb-v?\d+\.\d+\.\d+-r\d+", r["tag_name"])),
                  key=release_key, reverse=True)


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
    releases = published_releases(json.loads(args.release.read_text(encoding="utf-8-sig")))
    if not releases:
        raise ValueError("No published RGB stable releases")
    frontend = args.lab / "frontend"
    public = frontend / "public"
    (public / "firmware").mkdir(exist_ok=True)
    channels = {"rgb_tag": releases[0]["tag_name"], "release_url": releases[0]["html_url"],
                "releases": [], "channels": [
        {"id": "release", "title": "Official + RGB", "versions": []},
        {"id": "custom", "title": "Official + RGB", "versions": []},
    ]}
    for release in releases:
        tag = release["tag_name"]
        name = f"flipper-z-f7-update-{tag}.tgz"
        asset = next(a for a in release["assets"] if a["name"] == name)
        directory = args.downloads / tag
        # Single-release input remains supported for local builds.
        if not directory.exists():
            directory = args.downloads
        bundle = directory / name
        digest = hashlib.sha256(bundle.read_bytes()).hexdigest()
        checksums = dict(line.split(maxsplit=1)[::-1] for line in
                         (directory / "SHA256SUMS").read_text().splitlines())
        if checksums.get(name) != digest or asset.get("digest") != f"sha256:{digest}":
            raise ValueError(f"Firmware checksum mismatch: {tag}")
        shutil.copy2(bundle, public / "firmware" / name)
        shutil.copy2(directory / "SHA256SUMS", public / "firmware" / f"{tag}-SHA256SUMS")
        version = '.'.join(map(str, release_key(release)[:3]))
        file = {"url": f"{args.base}firmware/{name}", "type": "update_tgz", "target": "f7", "sha256": digest}
        channels["releases"].append({"tag": tag, "release_url": release["html_url"], "bundle_url": file["url"]})
        for channel, label in zip(channels["channels"], [version, tag]):
            channel["versions"].append({"version": label, "files": [file], "changelog": release.get("body", "")})
    (public / "channels.json").write_text(json.dumps(channels, indent=2) + "\n")
    (public / ".nojekyll").touch()
    shutil.copy2(Path(__file__).with_name("NOTICE.txt"), public / "NOTICE.txt")

    api = frontend / "src/entities/Flipper/api/index.ts"
    text = api.read_text()
    shutil.copy2(Path(__file__).with_name("firmwareDownload.ts"), frontend / "src/shared/components/firmwareDownload.ts")
    text = "import { downloadFirmware } from 'shared/components/firmwareDownload'\n" + text
    start = text.index("async function fetchChannels(")
    end = text.index("async function fetchRegions()")
    text = text[:start] + f'''async function fetchChannels() {{
  const response = await fetch('{args.base}channels.json', {{ cache: 'no-cache' }})
  if (!response.ok) throw new Error('Unable to load RGB release metadata')
  const data = await response.json()
  return data.channels
}}

''' + text[end:]
    start = text.index("async function fetchFirmware(url: string)")
    end = text.index("export const api =", start)
    text = text[:start] + '''async function fetchFirmware(url: string) {
  return unpack(await downloadFirmware(url))
}

async function fetchFirmwareTar(url: string) {
  return ungzip(await downloadFirmware(url))
}

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
    shutil.copy2(Path(__file__).with_name("ReleasePicker.vue"), frontend / "src/shared/components/RgbReleasePicker.vue")
    replace(update, "import { ref, computed, onMounted } from 'vue'",
            "import { ref, computed, onMounted } from 'vue'\nimport RgbReleasePicker from 'shared/components/RgbReleasePicker.vue'")
    replace(update, "const getChannel = (channelId: string) => {", '''const selectedRgbVersion = ref(sessionStorage.getItem('rgb-version') || '')
const selectRgbVersion = (tag: string) => {
  selectedRgbVersion.value = tag
  if (fwOptions.value.custom) {
    fwOptions.value.custom.version = tag
    fwModel.value = fwOptions.value.custom
    compareVersions()
  }
}
const getChannel = (channelId: string) => {''')
    replace(update, "return channels.value.find((channel) => channel.id === channelId)", '''const channel = channels.value.find((channel) => channel.id === channelId)
    if (!channel) return undefined
    const versions = channels.value.find((item) => item.id === 'custom')?.versions || []
    const index = Math.max(0, versions.findIndex((item) => item.version === selectedRgbVersion.value))
    return { ...channel, versions: [channel.versions[index] || channel.versions[0]!] }''')
    replace(update, '    <template v-if="ableToUpdate && flipperStore.info?.storage.sdcard?.status">',
            '''    <RgbReleasePicker :disabled="flipperStore.flags.updateInProgress" @selected="selectRgbVersion" />
    <template v-if="ableToUpdate && flipperStore.info?.storage.sdcard?.status">''')
    replace(update, "const compareVersions = () => {", "const compareVersions = () => {\n  aheadOfRelease.value = false")
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
    replace(layout, '<script setup lang="ts">', '<script setup lang="ts">\nimport RgbReleasePicker from \'shared/components/RgbReleasePicker.vue\'')
    replace(layout, '''<q-page class="flex flex-center fit" padding>
          <FlipperConnectWebBtn />''', f'''<q-page class="flex flex-center column fit" padding>
          <div style="max-width: 620px; text-align: center; margin: 28px 16px">
            <h1 style="font-size: 36px; line-height: 1.2; font-weight: 700">Official firmware.<br>RGB backlight.</h1>
            <p style="font-size: 18px">Choose a release and install directly over USB.</p>
            <p>For the three-LED SK6805 backlight mod. Use Chrome or Edge on desktop, close qFlipper, and connect your Flipper with a USB data cable. A microSD card must be installed.</p>
            <RgbReleasePicker />
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
    print(f"Prepared {len(releases)} verified releases; newest {releases[0]['tag_name']}; Pages base {args.base}")


if __name__ == "__main__":
    main()
