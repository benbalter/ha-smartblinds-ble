# SmartBlinds BLE — Home Assistant integration

Local, **hub-free and cloud-free** Home Assistant control of **Tilt / SmarterHome
roller shades** over Bluetooth LE. Works through HA's Bluetooth stack, including
cheap **ESP32 ESPHome Bluetooth Proxies** — so you can retire the discontinued
Tilt cloud bridge.

> **Status: working.** Verified end-to-end on 2026-09-11 against four Tilt roller
> shades, routed through an ESP32 ESPHome Bluetooth Proxy: all four paired, report
> live position and battery, and physically move on a `cover.set_position` from
> Home Assistant. No cloud, no hub, no phone app in the path.
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
- Handles the fact that **a shade keeps moving after the command returns**: the
  write finishes as soon as the motor accepts it, tens of seconds before it
  arrives, so the integration schedules a single re-read to converge rather than
  re-sending the command. A shade that never moves at all fails the action with a
  message naming it.

## How it works

The FireBeetle/ESP32 runs *stock* ESPHome Bluetooth-Proxy firmware. HA's
`habluetooth` transparently routes the BLE connection through whichever proxy is in
range; the integration drives the vendored, MIT-licensed Tilt codec in
`smartblinds-ble` (AES-128-CTR session, `HMAC-SHA256` pairing-key auth).

## Getting the pairing key

Each shade has a 32-byte (64-hex) pairing key. Rescue it from the Tilt cloud store
**while the cloud is still up** — see the
[`smartblinds-ble` docs](https://github.com/benbalter/smartblinds-ble/blob/main/docs/PROTOCOL.md).
Confirm the keys authenticate in range first with that repo's
`contrib/gate_auth_mac.py`.

These keys cannot be brute-forced (32 bytes) or recovered from packet captures,
and the vendor cloud is winding down, so **an exported key is irreplaceable** —
back it up outside Home Assistant.

## Install (HACS custom repository)

1. HACS → Integrations → ⋮ → Custom repositories → add
   `https://github.com/benbalter/ha-smartblinds-ble` (type: Integration).
2. Install "SmartBlinds BLE", restart HA.
3. It auto-discovers nearby shades, or add one via
   Settings → Devices → Add Integration → SmartBlinds BLE.
4. Enter the shade's 64-hex **pairing key** when prompted.

> Every shade advertises the same local name (`RollerSh`), and the config flow does
> not yet show the MAC, so discovery cards are indistinguishable. Trial and error
> is safe: the key is validated against the live shade and nothing is saved unless
> it authenticates. *"That key did not authenticate this shade"* means right shade,
> wrong key — try the next one. *"Could not reach the shade"* means range, or a
> phone holding the connection.

## Requirements

- Home Assistant 2024.8+.
- A Bluetooth adapter **or** an ESPHome Bluetooth Proxy in range of each shade.
  One proxy per room beats one central proxy: authentication held up at −85 dBm in
  testing, but that is not a level to depend on for regular polling.
- The [`smartblinds-ble`](https://pypi.org/project/smartblinds-ble/) library,
  pulled automatically from PyPI by `manifest.json`
  (`smartblinds-ble==0.1.1`) — no manual install. If setup fails, check the HA log
  for a pip error from `homeassistant.util.package`.

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
