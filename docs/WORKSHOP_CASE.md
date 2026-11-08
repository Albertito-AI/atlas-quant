# A reproducible workshop: can trading costs change the conclusion?

This short case is designed for teaching a research-review process. It uses
**synthetic data only**. It is not a historical market result, an investment
recommendation, a proven strategy, or an independently certified audit.

## Learning outcomes

Participants should be able to identify the dataset, explain the difference
between a decision and an execution date, compare the effect of costs, and
point to assumptions that remain outside the experiment.

## Generate the case

From an installed source checkout, with the tested dependencies installed:

```bash
python examples/workshop_case.py --output output/workshop
```

Choose a new directory. The command never replaces an existing directory.
It generates three HTML reports, three machine-readable JSON records and a
`summary.json`. The three cases are 0, 10 and 50 basis points per side. These are
illustrative scenarios, not estimates of typical real transaction costs.

Open `output/workshop/cost-10bps.html`, then open the zero- and 50-basis-point
reports. All three cases use the same generated prices, seed, strategy,
lookback, rebalance schedule and initial capital. Only the per-side fee changes.
The generated summary gives the exact calculated numbers, so no fixed
performance figure has to be trusted as a marketing claim.

## Discussion and checks

1. **Provenance.** Each report is labelled synthetic and identifies the same
   dataset hash. Why does the dataset hash not prove market data quality? The
   example was generated, and a hash is not proof of authenticity.
2. **Timing.** Inspect the trade ledger in each JSON record. Compare
   `decision_date` and `date`. A decision at a close executes at the next close;
   the allocation purchased at that next close does not capture the preceding
   interval's price move.
3. **Costs.** Compare final equity, total return and total transaction cost in
   `summary.json`. Costs are charged on each absolute buy or sell notional.
   Why can small costs accumulate with repeated rebalancing?
4. **Benchmark.** Each report also runs an equal-weight comparison with the
   same lag and cost assumptions. A difference in returns is not proof of
   risk-adjusted alpha or evidence that either strategy will work in future.
5. **Remaining uncertainty.** The case assumes fractional shares, complete
   liquidity, one currency and closing-price fills. Tax, market impact,
   financing and terminal liquidation are omitted. Synthetic data cannot
   establish that results generalise to historical or future markets.

Verify each machine-readable report, for example:

```bash
atlas-quant verify output/workshop/cost-10bps.json
```

A passing check establishes that the recorded content and its internal
cross-references remain consistent. It is not a digital signature or an
independent verification of the prices, calculations or suitability.

## Facilitator's exercise

Ask a participant to change a number in a copy of the JSON and run the verify
command. It should reject the modified copy. Ask a second participant to
explain why an attacker able to replace the data and recompute hashes could
still create a self-consistent file. End by listing what evidence would be
required before reaching any conclusion about a real investment proposition.
