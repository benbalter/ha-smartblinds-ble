# SmartBlinds BLE — Home Assistant integration

Local, **hub-free and cloud-free** Home Assistant control of MySmartBlinds / Tilt
shade motors over Bluetooth LE. Works through HA's Bluetooth stack, including cheap
**ESP32 ESPHome Bluetooth Proxies** — so you can retire the discontinued hub.

> **Status: stub / pre-alpha.** Depends on the
> [`smartblinds-ble`](https://github.com/benbalter/smartblinds-ble) library, whose
> protocol is **not yet verified on current firmware** (Milestone 0). Do not expect
> this to work end-to-end until M0 passes.
>
> Not affiliated with, authorized by, or endorsed by MySmartBlinds or Tilt.

## What it does

- Exposes each shade as an **optimistic tilt `cover`** (`assumed_state`): the motor
  is open-loop, so HA tracks position and cannot see app/wand changes.
- **Bluetooth auto-discovery** of `SmartBlind_DFU` motors (via adapters or proxies).
- Config flow collects the **per-motor BLE key** (the main setup hurdle).

## Install (HACS custom repository)

1. HACS → Integrations → ⋮ → Custom repositories → add
   `https://github.com/benbalter/ha-smartblinds-ble` (type: Integration).
2. Install "SmartBlinds BLE", restart HA.
3. It should auto-discover nearby shades, or add one via
   Settings → Devices → Add Integration → SmartBlinds BLE.
4. When prompted, enter the motor's **key** — get it from
   [`smartblinds-find-key`](https://github.com/benbalter/smartblinds-ble) or by
   sniffing the app once.

## Requirements

- Home Assistant 2024.8+.
- A Bluetooth adapter **or** an ESPHome Bluetooth Proxy in range of each shade.
- The `smartblinds-ble` library (installed automatically via `manifest.json`
  `requirements` once it's published to PyPI).

## Layout

```
custom_components/smartblinds_ble/
├── __init__.py        # entry setup/teardown
├── manifest.json      # domain, bluetooth matcher, requirements, assumed_state
├── config_flow.py     # bluetooth-discovery + manual + key steps
├── cover.py           # optimistic tilt cover; maps 0..100% -> native 0..200
├── const.py
├── strings.json / translations/en.json
hacs.json
```

## Roadmap

Tracked in the library repo's
[`docs/ROADMAP.md`](https://github.com/benbalter/smartblinds-ble/blob/main/docs/ROADMAP.md).
M0 (validate protocol on real hardware) gates everything here.

## Credits & license

Templated on [`LennP/ha-motionblinds_ble`](https://github.com/LennP/ha-motionblinds_ble).
Protocol via [`dnschneid/pysmartblinds`](https://github.com/dnschneid/pysmartblinds).
[Apache-2.0](LICENSE).
