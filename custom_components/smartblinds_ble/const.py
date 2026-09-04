"""Constants for the SmartBlinds BLE integration."""

from __future__ import annotations

DOMAIN = "smartblinds_ble"

# The BLE name shade motors advertise with (see smartblinds_ble library).
LOCAL_NAME = "SmartBlind_DFU"

# Config-entry keys.
CONF_ADDRESS = "address"
CONF_KEY = "key"  # per-motor BLE key (hex string), discovered via smartblinds-find-key

ENTITY_NAME = "SmartBlind {address}"
MANUFACTURER = "MySmartBlinds / Tilt (unofficial)"
