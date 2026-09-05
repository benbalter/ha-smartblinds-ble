# SmartBlinds BLE — Home Assistant integration

Local, **hub-free and cloud-free** Home Assistant control of **Tilt / SmarterHome
roller shades** over Bluetooth LE. Works through HA's Bluetooth stack, including
cheap **ESP32 ESPHome Bluetooth Proxies** — so you can retire the discontinued
Tilt cloud bridge.

> **Status: alpha.** The encrypted Tilt protocol is implemented and validated
> against real shades (authenticated handshake + live position/battery reads) via
> the [`smartblinds-ble`](https://github.com/benbalter/smartblinds-ble) library.
> The HA layer here (config flow, coordinator, entities) is unit-tested but not yet
> field-tested through a proxy. See "Requirements" below — the library must be
> installable for the integration to load.
>
> Not affiliated with, authorized by, or endorsed by MySmartBlinds, Tilt, or
> SmarterHome.

## What it does

- Exposes each shade as a **position `cover`** with real state read back from the
  shade (0% = closed, 100% = open) — not optimistic/assumed-state.
- Exposes a **battery** sensor per shade.
- **Bluetooth auto-discovery** of `RollerSh…` shades (via a local adapter or an
  ESPHome proxy in range).
- Config flow collects the shade's **64-hex pairing key** and **validates it live**
  (authenticated read) before saving, so a wrong or stale key is rejected up front.
- Opens **brief, on-demand BLE sessions** and polls sparingly, to spare the solar
  battery and avoid locking the shade away from the Tilt app.

## How it works

The FireBeetle/ESP32 runs *stock* ESPHome Bluetooth-Proxy firmware. HA's
`habluetooth` transparently routes the BLE connection through whichever proxy is in
range; the integration drives the vendored, MIT-licensed Tilt codec in
`smartblinds-ble` (AES-128-CTR session, `HMAC-SHA256` pairing-key auth).

## Getting the pairing key

Each shade has a 32-byte (64-hex) pairing key. Rescue it from the Tilt cloud store
while the cloud is still up — see the
[`smartblinds-ble` docs](https://github.com/benbalter/smartblinds-ble). Confirm the
keys authenticate in range first with that repo's `contrib/gate_auth_mac.py`.

## Install (HACS custom repository)

1. HACS → Integrations → ⋮ → Custom repositories → add
   `https://github.com/benbalter/ha-smartblinds-ble` (type: Integration).
2. Install "SmartBlinds BLE", restart HA.
3. It auto-discovers nearby shades, or add one via
   Settings → Devices → Add Integration → SmartBlinds BLE.
4. Enter the shade's 64-hex **pairing key** when prompted.

## Requirements

- Home Assistant 2024.8+.
- A Bluetooth adapter **or** an ESPHome Bluetooth Proxy in range of each shade.
- The [`smartblinds-ble`](https://github.com/benbalter/smartblinds-ble) library.
  **It is not yet on PyPI**, so until it is published the `manifest.json`
  `requirements` pin (`smartblinds-ble==0.0.1`) will not resolve automatically —
  install the library into your HA environment manually (matching version `0.0.1`),
  or wait for the PyPI release. CI installs it from git `main`.

## Development

```bash
python3.13 -m venv .venv && . .venv/bin/activate
pip install -r requirements_test.txt      # or: pip install -e ../smartblinds-ble for a local lib
ruff check custom_components tests
pytest -q
```

The BLE protocol itself is exhaustively tested in the `smartblinds-ble` library
(against a fake shade peripheral); the tests here cover HA wiring — config flow,
coordinator, and entities — with a deterministic client double.

## Layout

```
custom_components/smartblinds_ble/
├── __init__.py        # entry setup/teardown (runtime_data coordinator)
├── manifest.json      # domain, RollerSh* bluetooth matcher, requirements
├── config_flow.py     # bluetooth-discovery + manual + validated key step
├── coordinator.py     # per-shade DataUpdateCoordinator over the Tilt library
├── cover.py           # position cover (0 closed .. 100 open)
├── sensor.py          # battery sensor
├── const.py
└── strings.json / translations/en.json
```

## Credits & license

Templated on [`LennP/ha-motionblinds_ble`](https://github.com/LennP/ha-motionblinds_ble).
Tilt protocol codec vendored (MIT) from
[`Sunrise-Labs-Dot-AI/tilt-local-bridge`](https://github.com/Sunrise-Labs-Dot-AI/tilt-local-bridge)
via the `smartblinds-ble` library. [Apache-2.0](LICENSE).
