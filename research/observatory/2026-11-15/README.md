# Retained environmental observation

Preserved on **15 November 2026 Singapore time (14 November UTC)**. The observation and original archive timestamps remain unchanged.

This directory preserves the original environmental ZIP from [Observatory run 43590826729](https://github.com/Albertito-AI/atlas-quant/actions/runs/43590826729), collected on 14 November 2026 at source revision `8f0771a13ec02da4fd0e1987417be715c1972b7b`. It retains one already collected observation for reproducible inspection before the provider's temporary copy expires. No collection, market calculation or source activation was performed for this preservation step.

## Original bytes and provenance

- File: [environment-43590826729-1.zip](environment-43590826729-1.zip)
- GitHub artifact: `14111563799`; original compressed size: **2,616 bytes**.
- SHA-256: `ab532605dc91b48959c0f950411b41e0b289a9a1eee2b0078ff40e2ba61be3fe`.
- Temporary artifact expiry: **28 November 2026, 11:36:28 UTC**, equivalent to **19:36:28 Singapore time**.
- The downloaded ZIP digest and size matched GitHub's artifact metadata. The ZIP was retained without recompression. CRC and safe-member checks passed.

The archive contains four regular files: `manifest.json`, `raw/nea-pm25.json`, `report.json` and `ATTRIBUTION.md`. The manifest describes the latter three files; the native verifier's `files_checked: 3` therefore does not mean that the ZIP contains only three members.

## Offline verification and its limits

After checking the ZIP digest, extract it into a new directory. From a checkout of the source revision above, run:

```sh
python -m observatory verify DIRECTORY
```

The exact original verifier returned `status: verified`, `collection_status: ok`, `files_checked: 3` and `network_requests: 0` under Python 3.12.14. Its three module files were checked against their Git object identities. A separate automated review also ran verification with network access blocked and observed zero network attempts.

This verification checks member sizes and hashes, required source records, attribution, source-policy identity and acquisition chronology. It then re-parses the retained NEA response using the recorded receipt time and requires equality with the stored report, including calculated freshness. It does not reproduce a financial calculation or establish scientific truth. The observation's freshness is evaluated at its original receipt time, not at the time a reader opens this archive.

The automated reviewer rejected four separately altered copies: changed raw bytes; a changed reported value with a recomputed manifest hash; a removed required source with a recomputed hash; and an impossible acquisition chronology. The unchanged original passed. These are bounded software and provenance checks, not proof of source authenticity, predictive skill, agent learning or investment performance.

## Source attribution and rights

Contains information from **NEA PM2.5 via data.gov.sg**, requested on **14 November 2026 at 11:36:28.474254 UTC** and received at **11:36:28.759262 UTC**, from <https://api-open.data.gov.sg/v2/real-time/api/pm25>, made available under the [Singapore Open Data Licence 1.0](https://data.gov.sg/open-data-licence). The original `ATTRIBUTION.md` is preserved inside the ZIP. No official endorsement is implied. The repository's software licence does not replace the source-data licence.

The retained event time is **11:00 UTC** and source publication time **11:30:44 UTC** on 14 November. Regional observations are north 6, south 4, east 5, west 4 and central 5, in **micrograms per cubic metre**. These are one-hour PM2.5 observations from that dated source response, not current readings, a forecast or evidence of a causal relationship with financial markets.

This is the existing environmental research use. No data-source rights were expanded or renewed; the existing source-policy review expiry remains 13 December 2026. No live exchange connection, order, paid call or new experiment is represented by this archive.
