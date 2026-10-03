# CLAUDE.md

Home Assistant custom integration for SmartBlinds shades over Bluetooth LE, installed through HACS. The protocol lives in the separate [smartblinds-ble](https://github.com/benbalter/smartblinds-ble) library; this repo is the Home Assistant wiring.

## Commands

Run these before pushing, in a Python 3.13 venv (see [README.md](README.md#development)):

```sh
pip install -r requirements_test.txt
ruff check custom_components tests
pytest -q
```

[ci.yml](.github/workflows/ci.yml) also runs hassfest and HACS validation. They only run as GitHub Actions, so open a pull request and wait for them to pass.

## Deploying

- HACS serves this integration straight from `main`, and the repo has no GitHub releases. Every push to `main` ships to every user on their next HACS update.
- That includes changing `requirements` in [manifest.json](custom_components/smartblinds_ble/manifest.json), which changes what Home Assistant installs.
- So run the checks above, work on a branch, and push or merge to `main` only when the owner says to.

## Public repo

Keep household specifics out of code, fixtures, tests and docs: no real device MACs, pairing keys, room or shade names, or LAN IPs. Use placeholders like the existing `AA:BB:CC:DD:EE:01`.
