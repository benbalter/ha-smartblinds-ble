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
        set_error: Exception | None = None,
        travel_fraction: float = 1.0,
        **_kwargs,
    ) -> None:
        self._position = position
        self._battery = battery
        self._error = error
        # Raised by the write instead of moving (e.g. a stuck shade).
        self._set_error = set_error
        # Fraction of the requested move that has completed by the time the
        # write returns: 1.0 arrives instantly, 0.4 is a shade mid-travel. The
        # real motors take tens of seconds, so the library returns while the
        # shade is still moving.
        self._travel_fraction = travel_fraction
        self.set_position_calls = 0
        self.read_status_calls = 0

    async def read_status(self) -> ShadeStatus:
        self.read_status_calls += 1
        if self._error is not None:
            raise self._error
        return make_status(self._position, self._battery)

    async def set_position_and_read_status(
        self, position_percent: int, **_kwargs
    ) -> tuple[ShadeStatus, bool]:
        self.set_position_calls += 1
        if self._set_error is not None:
            raise self._set_error
        delta = position_percent - self._position
        self._position = round(self._position + delta * self._travel_fraction)
        self._target = position_percent
        return make_status(self._position, self._battery), True

    def finish_travel(self) -> None:
        """Pretend the motor has since reached its last target."""
        self._position = self._target
