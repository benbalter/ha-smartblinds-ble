"""Constants for the SmartBlinds BLE (Tilt roller shade) integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "smartblinds_ble"

# Advertised BLE local-name prefix of Tilt roller shades (e.g. "RollerSh...").
LOCAL_NAME_PREFIX = "RollerSh"

# Config-entry keys.
CONF_ADDRESS = "address"
CONF_KEY = "key"  # 32-byte pairing key as 64 hex chars (rescued from the Tilt store)

MANUFACTURER = "SmarterHome / Tilt (unofficial)"
MODEL = "Tilt Roller Shade"

# Solar/battery motors that accept a single central: poll sparingly, connect on demand.
DEFAULT_POLL_INTERVAL = timedelta(minutes=30)

# Idle backoff. A shade that nobody touches reports the same status every poll, and
# each poll is a BLE session on a solar-charged motor — 48 a day per shade, almost
# all of them learning nothing. After IDLE_POLLS_BEFORE_BACKOFF identical reads the
# interval steps down this ladder; any change, command, or failure resets it to the
# head. Battery reporting stays hourly at worst, which is ample for a number that
# moves by single digits per week.
IDLE_POLL_INTERVALS = (
    timedelta(minutes=30),
    timedelta(hours=1),
    timedelta(hours=2),
)
IDLE_POLLS_BEFORE_BACKOFF = 3

# How long a shade needs to finish travelling. A position write returns as soon
# as the motor acknowledges and starts moving (tens of seconds before it
# arrives), so one delayed re-read converges the UI instead of showing a stale
# mid-travel position until the next 30-minute poll.
POSITION_TRAVEL_TIME = timedelta(seconds=30)
