"""Deterministic test doubles for the HA layer.

The full encrypted BLE protocol is exercised end-to-end in the ``smartblinds-ble``
library's own test suite (against a fake shade peripheral). These integration
tests only need to verify Home Assistant wiring -- config flow, coordinator, and
entities -- so they stub ``TiltShadeClient`` with a deterministic double.
"""

from __future__ import annotations

from smartblinds_ble.tilt import ShadeStatus


def make_status(position: int = 30, battery: int = 66) -> ShadeStatus:
    return ShadeStatus(
        raw_position=position * 10,
        battery_percent=battery,
        charge_status=0,
        calibrated=True,
    )


class FakeTiltClient:
    """Stand-in for TiltShadeClient with canned reads and a recorded write."""

    def __init__(
        self,
        *_args,
        position: int = 30,
        battery: int = 66,
        error: Exception | None = None,
        **_kwargs,
    ) -> None:
        self._position = position
        self._battery = battery
        self._error = error
        self.set_position_calls = 0

    async def read_status(self) -> ShadeStatus:
        if self._error is not None:
            raise self._error
        return make_status(self._position, self._battery)

    async def set_position_and_read_status(
        self, position_percent: int, **_kwargs
    ) -> tuple[ShadeStatus, bool]:
        self._position = position_percent
        self.set_position_calls += 1
        return make_status(self._position, self._battery), True
