# Atlas public-data observatory

A bounded research pilot connects current environmental observations and real historical market data to reproducible analysis. The financial engine stays offline. There is no broker adapter, order submission, paid model call or unattended trading.

## What runs

| Lane | Input | Current purpose |
|---|---|---|
| Environmental observation | Current NEA regional PM2.5 readings through data.gov.sg | Record observation, publication and receipt times; reject invalid observations and flag stale data. |
| Historical market research | Binance Vision BTCUSDT and ETHUSDT daily candle archives | Verify archive checksums, replay original files, export a complete common calendar and exercise the existing backtest. |
| Live exchange research | Disabled | Binance live, Kraken and Coinbase have no enabled connection. Intended AI/public-output permissions remain unresolved or require consent. |

Historical candles are not a live exchange feed. An hourly workflow is a scheduled snapshot attempt, not a continuously connected service. A successful collection is not evidence of predictive accuracy, agent learning or investment profitability.

## Reproduce a bounded run

Use Python 3.11 or later from the repository root. The collector uses the standard library and is separate from the installed `atlas-quant` package.

```sh
python -m observatory sources
python docs/opsbook/bootstrap.py
python .opsbook/bin/opsbook.py verify '{"task":"activate-source","source_kind":"public"}' --checks docs/opsbook/checks.json
python -m observatory collect --sources nea --output output/nea-observation
python -m observatory verify output/nea-observation
python -m observatory collect --sources binance --days 90 --output output/market-observation
python -m observatory verify output/market-observation
```

Each output directory must be new. The manifest retains source URLs, declared permissions, retrieval times and hashes. Exact source responses are retained for replay. The verifier re-reads saved evidence rather than trusting a success label. Hashes detect changed content; they are not digital signatures or proof that a remote source was truthful.

The historical collector is limited to two named instruments, at most 90 closed UTC days, fixed public hosts, bounded response sizes, 20-second request timeouts and a ten-minute collection budget. It validates complete monthly archives for closed months and selects the requested dates; the current month uses daily archives. At most two archive workers operate concurrently. A request already in flight can extend beyond the overall deadline by its request timeout. Missing files, invalid checksums, duplicate candles and incomplete calendars fail closed; values are never filled with invented zeroes. A failed collection retains available evidence and does not create an apparently complete financial dataset.

## Fixed first financial experiment

After installing the numerical package with `python -m pip install -c requirements-tested.txt .`:

```sh
atlas-quant backtest output/market-observation/prices.csv \
  --strategy minimum_variance --lookback 60 --rebalance-every 7 \
  --cost-bps 10 --max-weight 0.8 --periods-per-year 365 \
  --output output/market-research
atlas-quant verify output/market-research/report.json
```

This is a rolling historical experiment on 90 days, with 60 past observations per estimate, seven-observation rebalancing, an 80% target weight cap, a 365-observation annualisation convention and a fixed assumed cost of 10 basis points on each buy or sell notional. The existing engine supplies next-close execution, self-financing accounting, a matched equal-weight baseline and a doubled-cost comparison. Both prices are quoted in **USDT**, not USD. The assumed cost is not a measured fee, spread or realised fill; the model does not reproduce order-book queues or market impact.

The two instruments were selected for a small operational pilot, not a representative or survivorship-free universe. The evaluation period is short, successive rolling windows overlap, and historical results do not demonstrate prospective forecasting. Keep every configuration and failed attempt. Do not select and advertise the most favourable run. The initial seven-day collection canary, if used, validates plumbing only and does not support this 60-observation experiment.

## Source rights and attribution

- **NEA PM2.5:** [API](https://api-open.data.gov.sg/v2/real-time/api/pm25), [documentation](https://guide.data.gov.sg/developer-guide/real-time-apis), [Singapore Open Data Licence](https://data.gov.sg/open-data-licence). Include the dataset name, access date, source and licence link with derived output. No official endorsement is implied.
- **Binance Vision:** [archives](https://data.binance.vision/), [dataset terms](https://github.com/binance/binance-public-data/blob/master/TERMS_AND_CONDITIONS.md), reviewed 13 November 2026. These datasets and derived outputs are used only for the expressly permitted non-commercial research and education scope, with attribution and CC BY-NC-SA 4.0 obligations. They are not included in a paid service, trading execution system or commercial signal product. The repository's MIT code licence does not relicense these data.
- **Live exchange candidates:** a technically public endpoint does not establish permission for this research or publication use. [Coinbase's terms](https://www.coinbase.com/legal/market_data) expressly restrict the proposed AI uses without written consent. [Kraken's notice](https://docs-legacy.kraken.com/api/docs/guides/global-intro/) requires permission for non-personal commercial use. The live Binance endpoint documentation does not by itself resolve all intended rights. Their disabled state must not be removed merely to make an experiment run.

Review permissions again before adding a source, changing purpose, distributing new derived material or enabling commercial use. The source registry is a dated operational decision, not a legal warranty. Keep source-specific conditions with every experiment and do not transfer restrictive data into unrelated public or paid products.

## Scheduled execution and review

[The public GitHub workflow](https://github.com/Albertito-AI/atlas-quant/actions/workflows/observatory.yml) attempts an environmental observation hourly at minute 17. It attempts the 90-day historical experiment daily at 02:27 UTC, which is 10:27 Singapore time. A relevant main-branch push or manual dispatch runs both lanes. GitHub may delay or skip schedules; configured timing is not an uptime promise.

The jobs use standard public runners, read-only repository permissions, pinned actions and no credentials for the sources. The dated source-permission check runs before acquisition and stops scheduled collection when its review expires on 13 December 2026, unless a genuine new review is recorded. Artifacts retain observations, reports and failure records for 14 days. They are temporary workflow evidence, not a permanent research archive. The existing Atlas Flexible Workflow review must inspect actual job outcomes and retain selected reproducible records before expiry. It must not turn a missing artifact into a passed check.

Academic GitHub Development owns bounded improvements; Atlas Flexible Zero Fail owns operational failure review; Atlas School Review owns assessment readiness. Existing task identities and cadence are retained. No new paid infrastructure, private CI or model API allowance is created.

## Applying Opsbook and the mathematics programme

Read the [project Opsbook](opsbook/README.md) before a task. Its initial accepted source-review procedure and contrary cases are retained with executable verification records. Retain an observed incident or near miss, draft a scoped instruction, test it against separately labelled cases including a contrary case, and record whether the rule was accepted or rejected. A subsequent agent must read the accepted instruction and demonstrate its application before a transfer claim is made. Rules confer no new authority. Passing implementation tests is not a measured learning gain.

The first research work packets concern data corruption, forecast calibration, exact allocation, observation efficiency and transfer of a tested procedure. Atlas Open Mathematics provides a separate [bounded integer-certificate laboratory](https://github.com/Albertito-AI/atlas-open-mathematics/blob/main/docs/AGENT_CHALLENGES.md). Connecting that checker to market constraints remains a further experiment; this release does not claim it already verifies financial allocations.

The private School's [Bridgewater packet](https://github.com/Albertito-AI/atlas-agent-school/blob/main/postgraduate/OBSERVATORY_PILOT.md), introduced in [PR #35](https://github.com/Albertito-AI/atlas-agent-school/pull/35), maps this pilot to its existing missions. It does not create real graduates, open enrolment or award placements. A claim of novelty requires prior-art review and new evidence. Publication in The Human Question remains an independent editorial decision.

The next improvement is chosen from a recorded failure or a predeclared research question. Compare with a simple baseline, preserve negative results, obtain independent review and retain a reversal path. Expand the source set only when that addition answers a useful question within the existing resource budget.
