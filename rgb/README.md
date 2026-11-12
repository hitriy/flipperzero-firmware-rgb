# Official Flipper Zero firmware with RGB backlight

This fork builds official stable firmware with Victor Nikitchuk / quen0n's
three-LED SK6805 RGB backlight modification on PA8. Firmware target: **f7**.
The initial supported official release is **1.5.1**. Other firmware functionality
is inherited from the official release. Hardware validation is still required.

## Releases and installation

The RGB stable firmware workflow checks official releases every five minutes.
It ignores drafts and prereleases, catches up on missing stable versions since
1.5.1, and publishes a release only after building firmware, the updater and apps.
GitHub may delay scheduled runs; this is not a guaranteed five-minute SLA.

Download the `flipper-z-f7-update-rgb-<version>-r1.tgz` from this fork's Releases.
Extract it onto the SD card and launch its update file from Flipper's file browser.
A full DFU image is supplied for qFlipper installation/recovery. Select the
backlight colour under **Settings → LCD and Notifications → LCD Color**.
These images require the RGB backlight hardware modification.

Each release includes SHA256SUMS, the applied patch, provenance.json, and a Git
tag pointing to the exact patched sources. The official upstream tag stays
unchanged. RGB releases use `rgb-<official-tag>-r1`. Uploads happen to a draft;
publication happens only after all files have uploaded successfully. Failed
builds stay unpublished and are retried by subsequent checks. If upstream changes
conflict with the patch, the workflow fails rather than building unpatched firmware.

## Dispatch hook

GitHub releases in another repository do not trigger this fork's `release` event.
Creating an actual release webhook on the official repository requires its
administrators' access. This fork provides an authenticated dispatch endpoint
for an upstream webhook relay or external release watcher:

```sh
gh api --method POST repos/OWNER/REPO/dispatches \
  -f event_type=upstream-release \
  -f 'client_payload[tag]=1.5.1'
```

The caller needs repository Contents: write permission. Tags are verified against
published official stable releases, so the hook cannot build arbitrary branches
or refs. The normal scheduled path needs only the automatic GITHUB_TOKEN, with no
personal token stored in the repository. Manual runs are also available in Actions.

Keep the workflow on the default branch and enable Actions in the fork. A small
heartbeat commit after 30 days without commits keeps the repository active ahead
of GitHub's 60-day inactivity cutoff for scheduled workflows. Branch protection
must allow this bot push; check Actions if automatic release checks stop. The dispatch
hook is available for a separately managed release watcher, but no external relay
is provisioned by this repository.

## Patch origin and changes

Source: https://github.com/quen0n/flipperzero-firmware-rgb

- Snapshot: `681d33c15ab8f1b54c8f3e061dd6ff447cbc757a`.
- Upstream merge base: `ef0300d239026da47b2315dd3278ec99826600e1`.
- Extracted only the seven RGB-related firmware files; excluded README/workflow
  deletions and unrelated protobuf submodule changes from the old fork.
- Preserved original author and GPL notices.
- Ported notification hooks and HAL integration to official 1.5.1.
- Validate persisted colour indices and palette lookups.
- Load settings in the notification service, including SD card mount, rather
  than accessing storage from HAL calls during early boot.
- Preserve notification LED updates when the light bitmask also includes backlight.
- SK6805 signalling timings and the original three-LED/PA8 mapping are retained.

`patches/0001-rgb-backlight.patch` applies to a clean official 1.5.1 checkout.
The release workflow starts from each official tag and applies this patch; it does
not build the aging default-branch snapshot for future releases.

## Maintenance and local verification

```sh
python3 -m unittest discover -s rgb/automation -v
./fbt TARGET_HW=7 DEBUG=0 COMPACT=1 updater_package fap_dist
```

When changing the patch for an already published upstream version, increment
PATCH_REVISION in `automation/releases.py` and the matching RGB_TAG suffix in
`.github/workflows/rgb-release.yml`. Existing published releases are immutable.
Regenerate the patch from firmware changes only, excluding automation files.
Hardware checks: boot and DFU/recovery entry, colour selection, brightness/off,
save/reboot, SD insertion, and normal RGB notification LED operation.
