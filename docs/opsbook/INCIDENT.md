# Public access did not establish research permission

Observed during the Atlas live-research design review on 13 November 2026.
This was a **design near miss**, not an unauthorised collection incident. No
Coinbase feed was ingested into the pilot.

The initial technical question was whether public exchange feeds could support
agent research. An unauthenticated endpoint established technical availability,
but the primary terms revealed a different permission boundary. Coinbase's
[Market Data Terms of Use, section 3(5)](https://www.coinbase.com/legal/market_data)
restrict the proposed AI development, validation and benchmarking without prior
written consent. The pilot therefore excludes that feed. Binance and Kraken
live feeds also remain disabled while the intended use is unresolved.

A permitted alternative has a different scope. The
[Binance Vision Dataset Terms](https://github.com/binance/binance-public-data/blob/master/TERMS_AND_CONDITIONS.md)
cover specified non-commercial historical research and educational uses, with
attribution and share-alike conditions. They do not establish permission for
unrestricted live exchange use or commercial signals. Singapore's
[Open Data Licence](https://data.gov.sg/open-data-licence) supplies the recorded
basis for attributed environmental observations.

The operational correction is to check the **source and intended use** at
activation, including a later change of purpose. A successful connection, a
public URL, a code repository's MIT licence, or an accepted Opsbook rule does
not create data rights.

The nearby counterexample is read-only inspection of documentation. Such an
inspection does not activate a feed. A rule requiring the acquisition gate for
every operation mentioning a public source would obstruct that unaffected work.

## Evidence boundaries

- `practice-cases.json` retains the observed near miss and three explicitly
  labelled routing scenarios.
- `exam-cases.json` was labelled by a separate reviewer before that reviewer saw
  a candidate rule. Boolean concepts were represented as categorical strings
  for Opsbook's existing schema. These are now visible regression fixtures,
  not secret examinations or observations of learner performance.
- `overbroad-rule.json` requires a check for every public-source operation.
  Actual replay introduces errors on inspection and documentation controls;
  actual promotion is refused with exit code 2.
- `accepted-rule.json` was produced by Opsbook's `learn` command from practice
  cases. It applies when `task = activate-source`, including a purpose change
  represented as a fresh activation decision.
- `evidence.json` records the actual CLI results: an empty initial manual,
  rejected broad draft, narrower replay, promotion and readback. Local root
  paths in the recorded command display are normalised to repository-relative
  paths; the executable arguments were absolute paths to these same files.
- `verification.json` records the actual trusted executable gate result for
  `pilot-plan.json`. This is a check of the recorded source policy, not an
  independent legal opinion or a new licence.

These tests demonstrate scoped procedure selection and enforcement. They do
not demonstrate model learning, better financial predictions, successful live
collection, a graduated learner, or general intelligence.
