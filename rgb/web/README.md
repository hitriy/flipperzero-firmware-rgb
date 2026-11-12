# GitHub Pages web updater

Live: https://hitriy.github.io/flipperzero-firmware-rgb/

This builds a pinned version of the official Flipper Lab frontend with a small
RGB-specific overlay. It retains the upstream Web Serial and firmware-update
implementation. The supported desktop browsers are Chrome and Edge. The device
must boot normally and have a microSD card; DFU recovery still uses qFlipper.

`prepare.py` validates every published RGB release's update bundle against both SHA256SUMS
and GitHub's asset digest. It copies that exact bundle into the static site and
generates `channels.json`. Serving the bundle from the same origin avoids GitHub
release-download CORS restrictions. The updater only offers the RGB channel.
The version selector appears before connection and in the connected firmware
update panel. It defaults to the newest version (numeric firmware version and
patch revision ordering), remembers the visitor's choice for the current browser
session, and selects the matching release notes, download and USB update bundle.
The selector is disabled while an update is running. Drafts and prereleases are
excluded. New published versions appear automatically after the next deployment.
No API key, GitHub token or backend is needed by visitors. The upstream regional
configuration request remains unchanged.

The Pages workflow runs after successful firmware workflows, checks whether the
published RGB version list differs from the live site, and rebuilds only when necessary.
It also runs when its source/configuration changes or when started manually.
Using `workflow_run` is intentional: releases published with GITHUB_TOKEN do not
trigger a separate `release` workflow. Hash routing and the project base path
make direct navigation and worker/assets loading compatible with GitHub Pages.

The build replaces upstream's client environment-variable spreading with an
explicit allowlist, so CI secrets cannot be embedded in JavaScript. Upstream
source, license notice and attribution are included through the pinned checkout
and `NOTICE.txt`. `prepare.py` fails if expected source text changes.

Local verification used the production Quasar build. Browser UI and release
download checks can be performed without a connected Flipper; actual USB
transfer, firmware installation and RGB behaviour require the modified device.
