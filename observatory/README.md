# Atlas public-data observatory

A bounded collector and offline evidence replay tool, run from a source checkout.
This directory is separate from the installed Atlas Quant numerical runtime.
It makes no authenticated exchange calls, places no orders, and calls no language
models. The financial source is **historical**, while the NEA source is a current
hourly environmental observation.

```bash
python -m observatory sources
python -m observatory collect --output output/pilot-001 --days 7
python -m observatory verify output/pilot-001
```

`--sources nea` collects only the current Singapore PM2.5 observation.
`--sources binance` collects only historical BTCUSDT and ETHUSDT daily candles.
`--sources all` is the default. `--days` accepts 2–90; `--end-date YYYY-MM-DD`
selects a completed UTC day, defaulting to yesterday. An existing output directory
is rejected. Missing dates are never filled or silently removed.

Each source request has a 20-second timeout. The run checks a ten-minute total
budget before each request; the final request can overrun it by up to its timeout.
There are no automatic retry loops. Completed calendar months use monthly archives;
only dates from the requested window enter the export after the entire archive
is validated. The current month uses daily archives. Each archive and its
published checksum require separate requests. For 15 August–12 November 2026,
this reduces the 90-day request count from 360 to 60. At most two archive jobs
run concurrently. A failed financial request prevents new jobs, waits for any
in-flight job to finish, and suppresses the price export. Collecting NEA alone
needs one request.

The output contains exact response bytes under `raw/`, their source URLs and
request/receipt timestamps in `manifest.json`, source status in `report.json`,
and `ATTRIBUTION.md`. Manifest version 2 also records the archive plan, which
verification independently reconstructs from the date window. Version 1 daily
bundles remain verifiable. A complete financial collection also produces `prices.csv`:
two daily close series in the common quote currency **USDT**, not USD. The selected
assets are not a survivorship-free market universe. This short pilot cannot
establish predictive skill or an investment advantage.

Verification checks byte counts and SHA-256 digests, then reparses accepted raw
observations and regenerates the financial CSV without accessing the network.
Checksums demonstrate consistency, not a digital signature or factual truth.
Verification of a retained failed run can succeed while reporting
`collection_status: incomplete`; this confirms the failure evidence rather than
successful collection.

## Source permission boundaries

`SOURCE_REGISTRY` and `policy_check(source_id, use)` in `pilot.py` are the executable
source policy. Undefined uses fail closed. Binance, Kraken and Coinbase live
exchange adapters are disabled and have no implementation. Source access alone
never establishes permission for AI research, commercial use or publication.

- NEA data uses the Singapore Open Data Licence, with attribution and its stated
  exclusions. The software does not claim official endorsement.
- Binance Vision historical data is used only for non-commercial research and
  education under its dataset terms and CC BY-NC-SA 4.0. Redistributed derived
  data retains those conditions. Do not sell the dataset, derived signals or
  paid access to the resulting evidence. The repository's software licence does
  not replace the source-data licence.

The retained manifest records the exact registry used by this version. Replaying
an older run requires its corresponding code revision if policies or schemas
change. Recheck source terms before extending the permitted uses.

## Quality controls

The collector rejects future or timezone-free environmental timestamps, missing
regions, negative or non-finite values, inconsistent publication times and
duplicate observations. NEA observations older than three hours are labelled
`stale`, causing an incomplete collection status.

Historical archives must match their official checksum and contain exactly one
safe CSV member and one complete candle for each day of its daily or monthly
period, including leap days. Missing, duplicate, reordered and out-of-period
rows fail verification. Both millisecond and microsecond timestamp conventions
are checked. Prices,
OHLC relationships, volumes, trade counts, the common calendar, archive size and
expansion ratio are validated. No archive is extracted to the filesystem.

Exit status: `0` for successful collection or successful evidence verification;
`1` for a retained incomplete collection; `2` for invalid arguments, a refused
output overwrite or invalid evidence. Inspect the returned `collection_status`
when deciding whether a verified run contains usable observations.
