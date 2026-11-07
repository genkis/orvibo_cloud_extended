"""Synthetic tests for Allone type 127 classification.

These tests do not contact ORVIBO, Home Assistant, or a blind motor.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path
import sys
import types
import unittest

COMPONENT = Path(__file__).resolve().parents[1] / "custom_components/orvibo_cloud"
PACKAGE = "_orvibo_type127_tests"
package = types.ModuleType(PACKAGE)
package.__path__ = [str(COMPONENT)]  # type: ignore[attr-defined]
sys.modules[PACKAGE] = package
protocol = importlib.import_module(f"{PACKAGE}.protocol")
control = importlib.import_module(f"{PACKAGE}.control")
classification = importlib.import_module(f"{PACKAGE}.classification")

SECRET_UID = "hardware-hub-SECRETUID"
SECRET_PARENT = "parent-SECRETUID"
SECRET_PAYLOAD = "LEARNED-RF-PAYLOAD-DO-NOT-ECHO"
SECRET_ORDER = "custom-order-SECRETORDER"
SECRET_EMAIL = "person@example.com"
SECRET_PROPERTY = "PROPERTY-SECRET-VALUE"
SECRETS = (
    SECRET_UID,
    SECRET_PARENT,
    SECRET_PAYLOAD,
    SECRET_ORDER,
    SECRET_EMAIL,
    SECRET_PROPERTY,
    "other-hardware-SECRETUID",
    "motor-SECRETUID",
)


def _readtable() -> dict:
    return {
        "status": 0,
        "data": {
            "room": [
                {"roomId": "room-1", "roomName": "Kitchen", "delFlag": 0}
            ],
            "device": [
                {
                    "deviceId": "device-hub",
                    "uid": SECRET_UID,
                    "deviceName": "Allone Pro",
                    "deviceType": 67,
                    "model": "VS20RB",
                    "roomId": "room-1",
                    "delFlag": 0,
                },
                {
                    "deviceId": "device-blind-127",
                    "uid": SECRET_UID,
                    "deviceName": "Kitchen blind",
                    "deviceType": "127",
                    "subDeviceType": 9,
                    "company": "A-OK",
                    "model": "AC128-01",
                    "parentUid": SECRET_PARENT,
                    "roomId": "room-1",
                    "delFlag": 0,
                    "email": SECRET_EMAIL,
                    "keyList": [
                        {
                            "order": "rf control",
                            "value1": 380000,
                            "code": SECRET_PAYLOAD,
                        },
                        {
                            "order": SECRET_ORDER,
                            "value1": 987654321,
                            "code": SECRET_PAYLOAD,
                        },
                    ],
                },
                {
                    "deviceId": "device-remote-127",
                    "uid": "other-hardware-SECRETUID",
                    "deviceName": "Spare remote",
                    "deviceType": 127,
                    "company": SECRET_EMAIL,
                    "delFlag": 0,
                },
                {
                    "deviceId": "device-curtain-rf",
                    "uid": SECRET_UID,
                    "deviceName": "Type 34 RF",
                    "deviceType": 34,
                    "model": "Curtain",
                    "delFlag": 0,
                },
                {
                    "deviceId": "device-curtain-pos",
                    "uid": "motor-SECRETUID",
                    "deviceName": "Type 34 motor",
                    "deviceType": 34,
                    "delFlag": 0,
                },
                {
                    "deviceId": "device-roller-35",
                    "uid": SECRET_UID,
                    "deviceName": "Type 35 roller",
                    "deviceType": 35,
                    "subDeviceType": -2,
                    "delFlag": 0,
                },
                {
                    "deviceId": "device-tv",
                    "uid": SECRET_UID,
                    "deviceName": "TV",
                    "deviceType": 6,
                    "delFlag": 0,
                },
                {
                    "deviceId": "device-deleted",
                    "uid": SECRET_UID,
                    "deviceName": "Deleted",
                    "deviceType": 127,
                    "delFlag": 1,
                },
            ],
            "deviceStatus": [
                {
                    "deviceId": "device-blind-127",
                    "online": 1,
                    "value1": 0,
                    "value2": 0,
                    "value3": 0,
                    "value4": 0,
                    "delFlag": 0,
                    "properties": {
                        "battery_power": 80,
                        "learned": SECRET_PROPERTY,
                    },
                },
                {
                    "deviceId": "device-curtain-rf",
                    "online": 1,
                    "value1": 0,
                    "delFlag": 0,
                },
                {
                    "deviceId": "device-curtain-pos",
                    "online": 1,
                    "value1": 40,
                    "delFlag": 0,
                },
                {
                    "deviceId": "device-hub",
                    "online": "online",
                    "delFlag": 0,
                },
            ],
        },
    }


class Type127ClassificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.devices = protocol.parse_readtable_devices(_readtable())
        cls.by_id = {device.uid: device for device in cls.devices}

    def test_discovery_keeps_supported_and_unmapped_rows(self) -> None:
        self.assertEqual(
            set(self.by_id),
            {
                "device-hub",
                "device-blind-127",
                "device-remote-127",
                "device-curtain-rf",
                "device-curtain-pos",
                "device-roller-35",
                "device-tv",
            },
        )
        blind = self.by_id["device-blind-127"]
        self.assertEqual(blind.device_type, "127")
        self.assertEqual(blind.sub_device_type, "9")
        self.assertEqual(blind.model, "AC128-01")
        self.assertEqual(blind.cloud_uid, SECRET_UID)
        self.assertEqual(blind.value1, 0)
        self.assertEqual(self.by_id["device-curtain-pos"].value1, 40)
        self.assertEqual(self.by_id["device-roller-35"].sub_device_type, "-2")

    def test_only_type_34_is_a_cover_and_only_shared_uid_is_rf(self) -> None:
        covers = [
            device.uid
            for device in self.devices
            if control.is_supported_curtain(device)
        ]
        rf = [
            device.uid
            for device in self.devices
            if control.is_rf_curtain(device, self.devices)
        ]
        self.assertEqual(covers, ["device-curtain-pos", "device-curtain-rf"])
        self.assertEqual(rf, ["device-curtain-rf"])
        self.assertFalse(
            control.is_supported_curtain(self.by_id["device-blind-127"])
        )
        self.assertFalse(control.is_rf_curtain(self.by_id["device-blind-127"], self.devices))
        self.assertFalse(control.is_rf_curtain(self.by_id["device-roller-35"], self.devices))
        self.assertTrue(control.is_allone_tv(self.by_id["device-tv"], self.devices))

    def test_existing_rf_command_is_unchanged_and_not_selected_for_127(self) -> None:
        self.assertEqual(
            control.rf_curtain_command("open"),
            control.OrviboControlCommand("rf control", 380000),
        )
        self.assertEqual(
            control.rf_curtain_command("close"),
            control.OrviboControlCommand("rf control", 380001),
        )
        self.assertEqual(
            control.rf_curtain_command("stop"),
            control.OrviboControlCommand("rf control", 380002),
        )
        with self.assertRaises(ValueError):
            control.rf_curtain_command("other")
        blind = classification.cover_classification(
            self.by_id["device-blind-127"], self.devices
        )
        self.assertEqual(blind["cover_command"], "withheld")
        self.assertEqual(
            blind["withheld_reason"],
            "type_127_has_no_published_command_mapping",
        )
        encoded_row = json.dumps(blind["row"])
        self.assertNotIn("380000", encoded_row)
        self.assertNotIn("987654321", encoded_row)
        self.assertIn("known_rf_open", encoded_row)

    def test_type_127_summary_reports_structure_without_payloads(self) -> None:
        blind = self.by_id["device-blind-127"]
        report = classification.cover_classification(blind, self.devices)
        row = report["row"]
        self.assertEqual(report["hub_association"], "allone_pro")
        self.assertTrue(report["parent_link_present"])
        self.assertFalse(report["matches_powermate_rf_type"])
        self.assertEqual(row["labels"], {"company": "A-OK"})
        self.assertEqual(row["type_fields"]["deviceType"], "127")
        self.assertEqual(row["type_fields"]["subDeviceType"], "9")
        self.assertEqual(row["value_shapes"]["value1"], "zero")
        self.assertEqual(row["allowlisted_orders"], ["rf control"])
        self.assertTrue(row["unlisted_order_present"])
        self.assertEqual(
            row["nested_value_shapes"]["keyList.value1"],
            "known_rf_open,other_number",
        )
        collections = {item["name"]: item for item in row["collections"]}
        self.assertEqual(collections["keyList"]["kind"], "list")
        self.assertEqual(collections["keyList"]["length"], 2)
        self.assertEqual(
            collections["keyList"]["child_keys"], ["code", "order", "value1"]
        )
        self.assertEqual(
            collections["properties"]["child_keys"], ["battery_power", "learned"]
        )
        encoded = json.dumps(report)
        for secret in SECRETS:
            self.assertNotIn(secret, encoded)

    def test_unshared_type_127_is_not_relabelled_as_a_blind_command(self) -> None:
        remote = classification.cover_classification(
            self.by_id["device-remote-127"], self.devices
        )
        self.assertEqual(remote["hub_association"], "none")
        self.assertEqual(remote["cover_command"], "withheld")
        self.assertEqual(remote["row"]["labels"], {})
        self.assertNotIn(SECRET_EMAIL, json.dumps(remote))

    def test_existing_cover_classes_stay_distinct(self) -> None:
        rf = classification.cover_classification(
            self.by_id["device-curtain-rf"], self.devices
        )
        position = classification.cover_classification(
            self.by_id["device-curtain-pos"], self.devices
        )
        roller = classification.cover_classification(
            self.by_id["device-roller-35"], self.devices
        )
        hub = classification.cover_classification(self.by_id["device-hub"], self.devices)
        self.assertEqual(rf["cover_command"], "rf_open_close_stop")
        self.assertIsNone(rf["withheld_reason"])
        self.assertEqual(rf["hub_association"], "allone_pro")
        self.assertEqual(position["cover_command"], "position")
        self.assertEqual(position["hub_association"], "none")
        self.assertEqual(position["row"]["value_shapes"]["value1"], "percent")
        self.assertEqual(roller["cover_command"], "withheld")
        self.assertEqual(
            roller["withheld_reason"],
            "powermate_rf_type_is_not_enabled_in_this_integration",
        )
        self.assertTrue(roller["matches_powermate_rf_type"])
        self.assertEqual(roller["row"]["type_fields"]["subDeviceType"], "-2")
        self.assertEqual(hub["hub_association"], "self_allone_pro")
        self.assertEqual(hub["cover_command"], "not_a_cover")

    def test_diagnostic_numbers_keep_position_and_published_buttons_only(self) -> None:
        self.assertEqual(classification.diagnostic_number(0), 0)
        self.assertEqual(classification.diagnostic_number(40), 40)
        self.assertEqual(classification.diagnostic_number(100), 100)
        self.assertEqual(classification.diagnostic_number(380000), 380000)
        self.assertEqual(classification.diagnostic_number(380002), 380002)
        self.assertEqual(classification.diagnostic_number(None), None)
        self.assertEqual(classification.diagnostic_number(-1), "**REDACTED**")
        self.assertEqual(
            classification.diagnostic_number(987654321), "**REDACTED**"
        )

    def test_binary_extract_does_not_gain_a_control_uid_or_echo_payloads(self) -> None:
        devices = protocol.extract_devices(
            [
                {
                    "tableName": "device",
                    "deviceId": "device-blind-127",
                    "uid": SECRET_UID,
                    "deviceType": 127,
                    "company": "Torro",
                    "keyList": [
                        {
                            "order": "rf control",
                            "value1": 380001,
                            "code": SECRET_PAYLOAD,
                        }
                    ],
                }
            ]
        )
        self.assertEqual(len(devices), 1)
        device = devices[0]
        self.assertEqual(device.cloud_uid, "")
        self.assertEqual(device.device_type, "127")
        report = classification.cover_classification(device, devices)
        self.assertEqual(report["hub_association"], "missing_control_uid")
        self.assertEqual(report["cover_command"], "withheld")
        self.assertEqual(report["row"]["labels"], {"company": "Torro"})
        self.assertEqual(
            report["row"]["nested_value_shapes"]["keyList.value1"], "known_rf_close"
        )
        encoded = json.dumps(report)
        self.assertNotIn(SECRET_UID, encoded)
        self.assertNotIn(SECRET_PAYLOAD, encoded)

    def test_observed_aok_type127_shape_stays_withheld(self) -> None:
        """Lock the sanitized 1.3.3 account shape. Stand-in numbers are not the account's hidden values."""

        hub_uid = "observed-hub-uid"
        sentinel_values = (
            "IRID-SENTINEL",
            "DMT-SENTINEL",
            "EXT-SENTINEL",
            "GDID-SENTINEL",
            "PROFILE-SENTINEL",
            "APP-SENTINEL",
            "ZONE-SENTINEL",
            "STATUS-SENTINEL",
        )
        blind = {
            "deviceId": "observed-blind",
            "uid": hub_uid,
            "deviceName": "Kitchen blind",
            "deviceType": 127,
            "company": "A-OK Motor",
            "model": "model_A",
            "irDeviceId": sentinel_values[0],
            "deviceModelType": sentinel_values[1],
            "endpoint": 1,
            "extAddr": sentinel_values[2],
            "gdid": sentinel_values[3],
            "profileID": sentinel_values[4],
            "appDeviceId": sentinel_values[5],
            "zoneId": sentinel_values[6],
            "statusId": sentinel_values[7],
            "alarmType": 0,
            "authority": 0,
            "version": "1",
            "roomId": "room-1",
            "createTimeSec": 1,
            "updateTimeSec": 1,
            "delFlag": 0,
            "online": 0,
            "value1": 0,
            "value2": 0,
            "value3": 0,
            "value4": 250,
        }
        payload = {
            "status": 0,
            "data": {
                "device": [
                    {
                        "deviceId": "observed-hub",
                        "uid": hub_uid,
                        "deviceName": "Allone Pro",
                        "deviceType": 67,
                        "model": "hub-model",
                        "delFlag": 0,
                        "online": 0,
                    },
                    blind,
                ],
                "deviceStatus": [
                    {
                        "deviceId": "observed-blind",
                        "online": 0,
                        "value1": 0,
                        "value2": 0,
                        "value3": 0,
                        "value4": 250,
                        "delFlag": 0,
                    }
                ],
            },
        }
        devices = protocol.parse_readtable_devices(payload)
        found = {device.uid: device for device in devices}
        device = found["observed-blind"]
        self.assertEqual(device.device_type, "127")
        self.assertEqual(device.sub_device_type, "")
        self.assertEqual(device.model, "model_A")
        self.assertFalse(device.online)
        self.assertFalse(device.parent_uid)
        self.assertFalse(control.is_supported_curtain(device))
        self.assertFalse(control.is_rf_curtain(device, devices))
        report = classification.cover_classification(device, devices)
        self.assertEqual(report["hub_association"], "allone_pro")
        self.assertFalse(report["parent_link_present"])
        self.assertEqual(report["cover_command"], "withheld")
        self.assertEqual(
            report["withheld_reason"],
            "type_127_has_no_published_command_mapping",
        )
        self.assertFalse(report["matches_powermate_rf_type"])
        row = report["row"]
        self.assertEqual(row["labels"], {"company": "A-OK Motor"})
        self.assertEqual(row["type_fields"], {"deviceType": "127"})
        self.assertEqual(
            row["value_shapes"],
            {
                "value1": "zero",
                "value2": "zero",
                "value3": "zero",
                "value4": "other_number",
            },
        )
        self.assertEqual(row["collections"], [])
        self.assertEqual(row["allowlisted_orders"], [])
        self.assertFalse(row["unlisted_order_present"])
        self.assertIn("irDeviceId", row["field_names"])
        self.assertIn("deviceModelType", row["field_names"])
        encoded = json.dumps(report)
        for secret in (*sentinel_values, hub_uid):
            self.assertNotIn(secret, encoded)
        self.assertNotIn("380000", encoded)
        self.assertNotIn("250", encoded)
        self.assertEqual(classification.diagnostic_number(250), "**REDACTED**")

    def test_cover_platform_uses_the_type_34_gate(self) -> None:
        source = (COMPONENT / "cover.py").read_text(encoding="utf-8")
        self.assertIn("is_supported_curtain(device)", source)
        self.assertNotIn('"127"', source)
        diagnostics = (COMPONENT / "diagnostics.py").read_text(encoding="utf-8")
        self.assertIn("cover_classification(", diagnostics)
        self.assertIn("diagnostic_number(", diagnostics)


if __name__ == "__main__":
    unittest.main()
