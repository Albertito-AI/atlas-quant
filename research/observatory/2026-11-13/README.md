# First Atlas observatory execution

The first [hosted run](https://github.com/Albertito-AI/atlas-quant/actions/runs/43389389027) completed both jobs on 13 November 2026 using implementation commit `1a4d12fb82f538997ca547b47c8e3de53d50c3f5`, introduced by [PR #13](https://github.com/Albertito-AI/atlas-quant/pull/13).

- A current NEA PM2.5 observation was collected and independently replayed.
- Ninety closed UTC days, 15 August through 12 November 2026, yielded 180 BTCUSDT/ETHUSDT daily candles through 60 successful historical archive/checksum requests.
- The existing numerical engine completed its declared minimum-variance, equal-weight-baseline and doubled-cost historical calculations. A second environment recomputed the report from the downloaded input. Discrete fields agreed; 294 floating-point values agreed within relative/absolute tolerance `1e-10`. Maximum scaled difference was approximately `2.05e-14`. These results are numerically reproducible, not bitwise identical.
- Both original reports independently passed their own content-integrity checks. Two derived content hashes differ because some floating-point encodings differ. The comparison code excludes only these named hashes, not other discrete fields. A changed financial value and a changed metadata field were separately rejected.
- Local validation passed 248 tests and eight executable Opsbook policy tests. Hosted PR tests and dependency audit passed before merge. Software checks are not predictive-performance or learner-outcome evidence.

## Retained evidence

The two successful hosted ZIPs are preserved byte-for-byte. Their digests match the provider-returned artifact metadata. GitHub's temporary copies expire after fourteen days; these repository copies retain the initial evidence.

| File | Content |
|---|---|
| [receipt.json](receipt.json) | Exact versions, checks, schedules, artifact hashes and limitations |
| [atlas-environment-first-run.zip](atlas-environment-first-run.zip) | Original hosted environmental artifact |
| [atlas-market-first-run.zip](atlas-market-first-run.zip) | Original hosted historical inputs, source records, report and attribution |
| [retained-failed-attempts.zip](retained-failed-attempts.zip) | Two incomplete local attempts, original raw files and failure manifests |
| [local-successful-attempt.zip](local-successful-attempt.zip) | Complete fresh local retry and its original source evidence |
| [local-reproduction-report.json](local-reproduction-report.json) | Independently recomputed numerical result |
| [numerical-reproduction.json](numerical-reproduction.json) | Comparison scope and measured differences |
| [compare_reports.py](compare_reports.py) | Exact comparison implementation |

After extracting the hosted archives into separate directories, run the repository's `python -m observatory verify DIRECTORY` against the environmental root and the historical artifact's `market/` directory. Run `atlas-quant verify` on each financial `report.json`. Recompute with the command in [the operating guide](../../../docs/OBSERVATORY.md), then use `compare_reports.py HOSTED_REPORT LOCAL_REPORT`.

## Failures changed the implementation

The first daily-file collector exhausted its time budget after 606 seconds and forty verified candles. Completed-month batching reduced the requested archive plan from 360 to 60 HTTP calls. Its first local attempt subsequently hit a network timeout; it retained 162 verified candles but correctly withheld a complete price dataset. A fresh local attempt and the hosted run completed. This record does not erase the earlier failures or promise uninterrupted service.

Independent review also exposed a semantic verifier defect: an empty source set could previously pass after its report hash was changed. Required source and replay checks now reject it. The [actual Opsbook incident](../../../docs/opsbook/observed-verifier-repair.json) retains that repair. Its proposed second instruction remains unpromoted; the accepted source-permission procedure is revision 1. No measured agent learning gain is asserted.

## Data rights

The repository's MIT code licence does **not** apply to third-party datasets or override their terms. `compare_reports.py` is original MIT code. The Binance datasets and derived financial reports in this directory are supplied for non-commercial research and education under [Binance Vision Dataset Terms](https://github.com/binance/binance-public-data/blob/master/TERMS_AND_CONDITIONS.md) and [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). Preserve attribution and applicable share-alike conditions. Do not use this evidence in a paid signal product or proprietary live execution system.

NEA observations, accessed on 13 November 2026 through [data.gov.sg](https://api-open.data.gov.sg/v2/real-time/api/pm25), retain the [Singapore Open Data Licence](https://data.gov.sg/open-data-licence). Source-specific attribution also appears inside each evidence bundle. No source endorses Atlas.

These are historical research calculations on two selected instruments with a short evaluation window. They establish neither prospective forecasting performance, profitable trading, graduate readiness nor mathematical novelty. Live exchange adapters remain disabled.
