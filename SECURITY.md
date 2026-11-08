# Security policy

Atlas Quant is an offline research toolkit. It reads local price files and produces local analytical reports. It has no brokerage connection, no order execution, no credential store, no generated-code execution and no runtime HTTP server. Installing dependencies and running CI require network access. The software has not undergone an independent professional security audit.

## Reporting

Use the repository's **Security → Report a vulnerability** function if private vulnerability reporting is enabled. If that function is unavailable, open an issue requesting a private reporting channel without including exploit details, credentials or sensitive data. Include a minimal reproducer and the affected commit through that private channel. No response-time or support guarantee is offered. Security fixes target the current `main` branch; users should review changes before updating.

## Trust boundaries

| Boundary | Control | Residual limitation |
|---|---|---|
| Local CSV to numerical engine | Input size, dimensions, date, identifier and finite-price validation; no automatic missing-value repair | Validation cannot establish market-data accuracy, adjustment quality, currency consistency or data rights |
| Research text to calculations | Structured evidence and role validation; narrative has no tools or trade authority | Narrative may still be persuasive or misleading; schema validity is not truth |
| Evidence to trace | Canonical hashes identify changed records | Hashes are not digital signatures and do not authenticate a provider or prevent an attacker replacing both data and hash |
| Report data to HTML | Text escaping and restrictive content policy in the report renderer | An altered renderer or malicious dependency is outside this boundary; independently inspect published HTML |
| Source to CI | Read-only job tokens, pinned external action commits, no persisted checkout credential, bounded job duration | GitHub settings, runner images, dependency distributions and transitive build tools are additional trust dependencies |
| Dependency selection | Dependency audit workflow and Dependabot update proposals | Advisory coverage is incomplete; a clean scan does not prove absence of vulnerabilities or malicious packages |

The CLI intentionally operates with the invoking user's filesystem permissions. Run it as an ordinary user in a disposable virtual environment; do not supply sensitive output destinations to untrusted wrappers. File-size and numerical resource limits reduce accidental exhaustion. They are not an operating-system sandbox and do not protect a shared public service against denial of service. A future hosted or multi-user service requires a separate threat model, authentication, isolation and abuse controls.

## Checks

```bash
python scripts/security_check.py
python -m unittest discover -s tests -v
```

The repository policy script checks common credential patterns, Python syntax, selected network/unsafe-deserialisation imports, dynamic-execution calls and narrow workflow conventions. It reports rule identifiers and line numbers without printing a matched secret. It does not perform complete data-flow analysis, inspect native dependencies, detect every secret format or certify correctness. Obfuscated imports and deliberately modified policy code require review.

The dependency audit resolves the current supported runtime, queries published package advisories and fails if the check cannot complete. Its result applies to the resolved package versions at that run. It is separate from the offline runtime policy.

## Repository settings

Source-controlled configuration does not enable platform protections by itself. The repository owner should verify branch protection or rulesets, require passing checks before merges, restrict token permissions, enable private vulnerability reporting, and enable GitHub secret scanning where available. Do not state that these settings are active until verified in GitHub.

Changes that introduce network providers, broker credentials, dynamic execution, a web server or personal portfolio storage require an explicit design review and updated tests. Keep such changes out of routine numerical refactoring.

See GitHub's [secure use reference](https://docs.github.com/en/actions/reference/security/secure-use) and the [pip-audit security model](https://github.com/pypa/pip-audit#security-model) for the limits of these supply-chain controls.
