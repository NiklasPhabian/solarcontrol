import unittest
from unittest.mock import Mock, patch

from shelly_plug_m_gen3 import ShellyPlugMGen3


def _mock_response(payload):
    response = Mock()
    response.raise_for_status = Mock()
    response.json.return_value = payload
    return response


class TestShellyPlugMGen3(unittest.TestCase):
    def test_requires_host(self):
        with self.assertRaises(ValueError):
            ShellyPlugMGen3(host="")


    @patch("shelly_plug_m_gen3.requests.get")
    def test_turn_on_uses_switch_set(self, mock_get):
        mock_get.return_value = _mock_response({"was_on": False, "on": True})
        plug = ShellyPlugMGen3(host="192.168.1.120")
        plug.turn_on()

        mock_get.assert_called_once_with(
            "http://192.168.1.120/rpc/Switch.Set",
            params={"id": 0, "on": True},
            timeout=5.0,
        )


    @patch("shelly_plug_m_gen3.requests.get")
    def test_turn_off_uses_switch_set(self, mock_get):
        mock_get.return_value = _mock_response({"was_on": True, "on": False})
        plug = ShellyPlugMGen3(host="shellyplug.local", switch_id=1, timeout_seconds=2)
        plug.turn_off()

        mock_get.assert_called_once_with(
            "http://shellyplug.local/rpc/Switch.Set",
            params={"id": 1, "on": False},
            timeout=2.0,
        )


    @patch("shelly_plug_m_gen3.requests.get")
    def test_read_power_and_energy(self, mock_get):
        mock_get.return_value = _mock_response(
            {"apower": 123.4, "aenergy": {"total": 5678.9}}
        )
        plug = ShellyPlugMGen3(host="192.168.1.120")

        self.assertEqual(plug.read_power_watts(), 123.4)
        self.assertEqual(plug.read_energy_wh(), 5678.9)
