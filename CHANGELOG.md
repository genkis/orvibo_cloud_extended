# Changelog

## 1.3.3 — Allone type 127 diagnostics, no new blind commands

Device type 127 is discovered and can appear in the device registry, but it is
not a cover. Published Allone RF open/close/stop commands apply to type 34 in
this integration (and to types 34, 35, 39 and 42 in the separate PowerMate P2
integration). Type 127 is in neither command map. This release does not send
commands for it and does not treat it as type 34.

Diagnostics now include a redacted classification for every device: hub
association without the hardware UID, cover support, and a structural summary
of the device row (field names, short product labels, numeric type codes,
collection names and lengths, allowlisted order tokens, and value shapes).
Unrecognized numbers outside 0–100 and outside the three published RF button
codes are redacted. Learned payloads, account identifiers and email addresses
are not copied into that summary.

Type 34 curtains are unchanged: shared Allone UID still means open/close/stop
with no percentage; other type 34 devices still use position. No config-entry
schema change.

A later check of one sanitized 1.3.3 download (14 type 127 rows, company
`A-OK Motor`, Allone Pro association, no button list, no published RF code)
did not reveal a command. No further diagnostic fields were added. A
regression test locks that shape so it stays withheld.

## 1.3.2 — HACS reviewer fixes

1. **Authenticated TLS:** port 10002 uses hostname checks and `ssl.CERT_REQUIRED` with the ORVIBO private CA bundled and fingerprint checked before loading it. The server trust anchor was corroborated against two public ORVIBO integration repositories and a certificate chain observed on the user's server. The CA is self-signed and its authenticity has not been confirmed by ORVIBO directly. `VERIFY_X509_STRICT` alone is relaxed because this 2018 CA has non-critical Basic Constraints; ordinary certificate-chain, validity and DNS hostname verification remain enabled. There is no `CERT_NONE` fallback.
2. **Account privacy:** diagnostic export redacts `CONF_EMAIL` in addition to password hash and user ID.
3. **Area persistence:** initial device registration applies configured areas; polling no longer overwrites manual Home Assistant area assignments. An explicit options-flow change still updates the area.
4. **English translations:** `translations/en.json` now matches `strings.json`.
5. **Capture reconnects:** rejected binary login ends the capture listener; transient network errors back off exponentially from five seconds to five minutes.

The tested integration's protocol, device controls and remembered blind-state logic are otherwise unchanged. Live device operation was confirmed by the integration maintainer on the local test build; CI cannot reproduce a real ORVIBO device connection.

## 1.3.1 — HACS publication preparation

- Add HACS and Hassfest GitHub Actions validation with no skipped HACS checks.
- Add offline packaging checks and Python syntax validation.
- Add GitHub Actions publishing workflow for the 1.3.1 release, guarded by
  successful validation on the main branch.
- Align root and integration README documentation, including HACS installation
  and the optional per-blind remembered-state feature.
- Clarify that earlier claimed hardware/runtime tests are not bundled.
- Make the HACS display name human-readable and add the integration type.

**No runtime device control, login, network protocol, TLS or blind logic changed.**
