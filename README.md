<img width="512" height="512" alt="logo" src="https://github.com/user-attachments/assets/10a03183-279c-44c6-9bff-c0eaab6959f2" />

# ORVIBO Cloud

A custom Home Assistant integration for ORVIBO Cloud devices, including
curtains controlled through an Allone Pro.

## Install with HACS

Before inclusion in the default HACS catalog, add this repository as a custom
integration:

1. Open **HACS** in Home Assistant and select **Custom repositories** from the
   menu.
2. Add `https://github.com/Kosztyk/orvibo_cloud` and select **Integration**.
3. Install **ORVIBO Cloud** and restart Home Assistant.
4. Open **Settings > Devices & services > Add integration**, select **ORVIBO
   Cloud**, sign in and select your devices.

HACS manages subsequent downloads and version upgrades. After acceptance into
the default HACS catalog, the custom-repository step will no longer be needed.

## Manual installation and upgrades

1. Copy the `orvibo_cloud` folder from this archive into
   `/config/custom_components/`, replacing existing integration files.
2. Restart Home Assistant.
3. For a new setup, open **Settings > Devices & services > Add integration**
   and select **ORVIBO Cloud**. Existing installations can keep their integration
   entry, server, and device selections.
4. Sign in with the account used in the ORVIBO Home or HomeMate app, choose
   your home, select the devices to add, and assign their areas.

The integration folder must be `/config/custom_components/orvibo_cloud/`
and contain `manifest.json` directly inside it.

## Cloud server

Use the server that contains your app's devices. The available servers are
`homemate.orvibo.com`, `germany.orvibo.com`, `china.orvibo.com`, and
`usa.orvibo.com`. International accounts can try `homemate.orvibo.com` first.
The server can be changed in the integration's configuration options.

## Verified ORVIBO binary cloud TLS (v1.3.2)

The port-10002 connection validates the ORVIBO self-signed CA against a bundled, fingerprint-checked trust anchor and requires a matching DNS hostname. A legacy Basic Constraints extension necessitates relaxing only the `VERIFY_X509_STRICT` check; `CERT_REQUIRED`, certificate-chain validation and hostname checking remain active. This legacy CA has been corroborated in two public integrations and observed on the live ORVIBO server, but has not been verified independently with the manufacturer. No insecure TLS fallback is provided.

The version also fixes diagnostics account-email redaction, prevents cloud refreshes from overriding manually assigned device areas, synchronizes English translations, and backs off capture reconnections while stopping on rejected logins.

## Allone Pro RF blinds

This section applies to **device type 34** only. RF blinds associated with an
Allone Pro (type 67) or Allone hub (type 30) expose **Open**, **Close**, and
**Stop**. The integration detects their hub relationship from the discovered
device list, even if the hub itself is not selected for addition to Home
Assistant.

RF commands do not provide a measured position. These covers use assumed
state and do not expose a percentage slider. Directly controlled type 34
curtain motors, which do not share that hub UID, retain their existing
position support.

## Device type 127

Some Allone Pro accounts list named blinds as **device type 127** next to the
type 67 hub. Those rows are selected and shown in the device registry, and
this integration previously created no cover entity for them. That is still
the case.

Published command maps do not identify type 127:

- This integration sends `order` `rf control` with the type 34 button codes
  only when a type 34 device shares the hardware UID of a type 30 or 67 hub.
- The published PowerMate P2 / Allone Pro shade integration uses that same
  command for device types **34, 35, 39 and 42**. It does not list type 127.
- LAN catalogs document type 34, and type 35 with subtype `-2`, as position
  motors. Type 35 is therefore not enabled here, even when it shares a hub UID.

Type 127 is not relabelled as type 34. A shared hub UID is not treated as
proof that a row is a blind rather than another RF or infrared remote, and
this build does not invent a payload. Open, Close, Stop and percentage are
not added. A `value1` of 0 on these rows is not a position.

A 1.3.3 diagnostic download from one Allone Pro account showed 14 type 127
rows with company `A-OK Motor`, an empty subtype, a shared model, a hardware
UID shared with the type 67 hub, and no parent link. The rows were flat:
`irDeviceId` and `deviceModelType` were present as single fields, not button
lists. There was no `order`, no collection, and no value1–value3 other than
zero. value4 was outside 0–100 and outside the published button codes
380000, 380001 and 380002. Every row, including the hub, was reported
offline. That is enough to keep commands withheld. It is not a command
mapping. Company `A-OK Motor` is only a label; the published RF command is
selected by device type 34, 35, 39 or 42, and these rows are type 127.

### What the new diagnostics can show

Download **Settings > Devices & services > ORVIBO Cloud > Download diagnostics**.
For each device, `classification` reports:

- `hub_association`: `allone_pro`, `allone`, `self_allone_pro`, `self_allone`,
  `none`, or `missing_control_uid`. The hardware UID stays redacted.
- `parent_link_present`: whether a parent or gateway id was present, not the id.
- `cover_command`: `rf_open_close_stop`, `position`, `withheld`, or `not_a_cover`.
- `withheld_reason`: why no cover command was selected.
- `matches_powermate_rf_type`: true only for types 34, 35, 39 and 42.
- `row`: field names, safe product labels such as `company`, short numeric
  type codes, value shapes (`zero`, `percent`, `known_rf_open`,
  `known_rf_close`, `known_rf_stop`, `other_number`, `text`), collection names,
  lengths and child key names, and allowlisted order tokens such as
  `rf control`.

Learned code strings, unlisted order text, email addresses and identifiers are
omitted. `value1` through `value4` in the device list remain visible when they
are 0–100 or one of the three published button codes. Any other number is
replaced with `**REDACTED**`.

If a type 127 row has an empty `labels` object, no collection, and only
`zero` or `empty` value shapes, the cloud row still does not identify a
command. Do not replay type 34 button codes against it. A shape of
`other_number` or `text` is also not the published type 34 command.

### Install and rollback

This build does not change the config-entry schema, device selections, or
remembered-state options. It does not move blinds.

Install over 1.3.2:

1. Replace `/config/custom_components/orvibo_cloud/` with this version's
   `custom_components/orvibo_cloud` folder. `manifest.json` must sit directly
   inside that folder and report version `1.3.3`.
2. Restart Home Assistant. Keep the existing integration entry.
3. Download diagnostics and inspect type 127 `classification` objects.

Roll back to 1.3.2:

1. Replace the integration folder with the 1.3.2 files.
2. Restart Home Assistant.
3. Leave the integration entry in place. Rolling back does not require
   deleting devices or options, because 1.3.3 does not write a new command
   and does not migrate options.

### Optional remembered open/closed state

Open **Settings > Devices & services > ORVIBO Cloud > Configure**. Keep the
desired devices selected, then use each RF blind's **Device settings** step:

- **Remember assumed open/closed state**: disabled by default, independently
  for each blind. A successful Open command assumes open, a successful Close
  command assumes closed, and a successful Stop command returns to unknown.
- **Restore assumed state after restart**: disabled by default. When remembering
  is enabled, restore the last successful command and its original timestamp
  after a Home Assistant restart or integration reload.
- **Assumed state expiry**: whole minutes, with `0` meaning no expiry. An expired
  assumption returns to unknown automatically. Restarting does not extend its
  lifetime. Expired history remains available for diagnostics.

Finish every device step to save the settings. The same options are available
during initial setup. Existing installations keep the unknown RF state until
remembering is explicitly enabled.

| Successful Home Assistant command | Assumed state | Percentage |
| --- | --- | --- |
| Open | Open | Unknown |
| Close | Closed | Unknown |
| Stop | Unknown | Unknown |

Remembered states remain marked `assumed_state: true`. Enabled blinds expose
`last_action`, `last_action_time` (UTC), `state_source: last_successful_command`,
and `assumption_expired`. Failed commands leave the prior history intact, and
ordinary cloud refreshes do not overwrite it with placeholder position values.

This records an accepted command, not confirmation that the motor reached an
endpoint. Movements made in the HomeMate app or with a physical remote are not
detected, so the assumption can become stale. Restoration uses Home Assistant's
standard restore-state storage; an abrupt power loss can lose recent history.

## Diagnostics

Redacted raw event capture can be enabled in the integration options while
troubleshooting. Disable it when finished. It records unsolicited cloud
events; it does not intercept commands sent by the phone app. The type 127
classification above is separate: it summarizes the device table already
returned to the integration and does not open a capture session.

## Credits and license

Maintained by **Kosztyk**. Based on the original `maycode0-0/orvibo-cloud`
integration. The original MIT license notice is retained in
`LICENSE`.

The remembered RF state feature builds on the idea proposed by **craiglemon**
in [pull request #2](https://github.com/Kosztyk/orvibo_cloud/pull/2).

## Validation

The CI checks verify packaging, metadata and Python syntax. Version 1.3.2 adds
local TLS handshake tests for legacy-CA compatibility, hostname and trust-chain
rejection, plus rejected-login and bounded reconnect-backoff tests.
Version 1.3.3 adds synthetic device-table tests for type 127 classification.
Those tests do not operate a blind. The previous 51-check runtime test suite
is not included in the public repository, so those earlier results are
historical and not reproduced here. See [VALIDATION.md](VALIDATION.md) in the
repository root for the scope and limits of the published checks.
