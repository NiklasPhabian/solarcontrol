"""Shelly Plug M Gen3 control and metering helper.

This module wraps the Shelly Gen3 RPC endpoints needed for relay control
and retrieving live power/energy measurements.
"""

from __future__ import annotations

from typing import Any, Dict

import requests


class ShellyPlugMGen3:
    """Control a Shelly Plug M Gen3 and read its meter values.

    Parameters
    ----------
    host:
        Device hostname or IP address.
    switch_id:
        Switch channel ID for RPC calls. Usually 0 for Shelly Plug devices.
    timeout_seconds:
        HTTP timeout for device requests.
    """

    def __init__(self, host: str, switch_id: int = 0, timeout_seconds: float = 5.0):
        if not host:
            raise ValueError("host must not be empty")
        self.host = host
        self.switch_id = int(switch_id)
        self.timeout_seconds = float(timeout_seconds)

    def _rpc(self, method: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
        payload = params or {}
        endpoint = f"http://{self.host}/rpc/{method}"
        response = requests.get(endpoint, params=payload, timeout=self.timeout_seconds)
        response.raise_for_status()
        return response.json()

    def turn_on(self) -> None:
        """Turn the plug output on."""
        self._rpc("Switch.Set", {"id": self.switch_id, "on": True})

    def turn_off(self) -> None:
        """Turn the plug output off."""
        self._rpc("Switch.Set", {"id": self.switch_id, "on": False})

    def get_meter_status(self) -> Dict[str, Any]:
        """Return the full Shelly switch status payload."""
        return self._rpc("Switch.GetStatus", {"id": self.switch_id})

    def read_power_watts(self) -> float:
        """Read current active power in watts."""
        status = self.get_meter_status()
        return float(status.get("apower", 0.0))

    def read_energy_wh(self) -> float:
        """Read accumulated active energy in Wh."""
        status = self.get_meter_status()
        aenergy = status.get("aenergy", {})
        if isinstance(aenergy, dict):
            return float(aenergy.get("total", 0.0))
        return 0.0


__all__ = ["ShellyPlugMGen3"]
