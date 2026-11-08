# Security and delivery review: twenty work rounds

Date: 8 November 2026. Reviewer: the security agent in the six-agent build. These are twenty bounded study, implementation and review passes performed by one agent. They are not twenty independent penetration tests or a certification. Source inspection used AI-Investment-Advisor commit `990a16c12436e83d0e977f48d6a81485deb6f251`. No upstream code was copied into this project.

| Round | Work and evidence | Decision or result |
|---|---|---|
| 01 | Inventoried upstream `SECURITY.md`, `AGENTS.md`, environment configuration and security-related Python paths. | Defined Atlas's smaller offline attack surface and excluded broker credentials, server deployment and generated code execution. |
| 02 | Read upstream `src/utils/boot_validation.py` and `src/services/llm_credential_cipher.py`, including their documented fallback and production-key checks. | Avoided creating a credential store; documented that checks must correspond to real capabilities and must not imply stronger protection than they provide. |
| 03 | Read upstream `src/api/middleware/local_auth.py`, including `assert_safe_bind`, exemptions and Docker caveats. | Kept runtime server hosting outside this release. A future hosted version requires a separate authentication and isolation design. |
| 04 | Read upstream `src/tools/mcp_sse_router.py` and located skill execution references. | Recorded its explicit zero-tool bridge status; avoided advertising unimplemented bridges or delegating executable authority to narrative. |
| 05 | Checked GitHub's primary secure-use guidance. | Selected read-only tokens, ordinary pull-request triggers and full action commit pins; avoided privileged PR execution. |
| 06 | Resolved official `actions/checkout` v4, `actions/setup-python` v5 and `actions/upload-artifact` v4 refs through `git ls-remote`. | Pinned the two actions actually needed; omitted unnecessary artifact publishing. Resolved refs are recorded below. |
| 07 | Implemented AST checks for selected dynamic code execution, including imported aliases; exercised `eval`, `exec`, aliased `os.system` and imported `builtins.eval` fixtures. | `test_blocks_dynamic_execution` passes. Static analysis limitations are explicit. |
| 08 | Added selected unsafe deserialisation and network-import checks; tested `pickle`, `subprocess`, `socket` and `urllib.request`. | `test_blocks_network_and_unsafe_deserialisation` and safe NumPy/SciPy counterexample pass. |
| 09 | Added common credential-pattern checks and synthetic fixture tests. | GitHub-token and private-key markers are detected; matched contents never appear in findings. This is not exhaustive secret detection. |
| 10 | Added file handling limits, symlink rejection, unreadable-text handling and environment-file rejection. | Oversized text, environment files, broken symlinks and invalid Python are rejected by tests without executing scanned content. |
| 11 | Implemented CI matrix for Python 3.11, 3.12 and 3.13 with bounded runtime, no persisted checkout credential, tests, repository policy and dependency consistency. | Configuration exists; GitHub execution must be checked separately after publication. |
| 12 | Added source/wheel build and isolated-wheel smoke job outside the checkout. | CI checks an independent Black–Scholes reference value and installed CLI entry point. This round validates the configuration, not a completed remote job. |
| 13 | Verified PyPI versions for `build` 1.6.1 and `pip-audit` 2.10.1; created dependency audit and Dependabot configurations. | Audit uses resolved pinned runtime requirements and fails on an incomplete audit. Corrected the local-package exclusion to actual distribution name `atlas-quant-research`. |
| 14 | Independently parsed both workflow YAML files and asserted trigger set, read-only permissions, timeout and checkout credential settings. | Both passed the structural check; scanner tests reject unpinned and privileged examples. |
| 15 | Wrote `SECURITY.md` and `CONTRIBUTING.md` with boundaries, reporting, numerical evidence requirements and residual risks. | Distinguished source-controlled checks from unverified GitHub platform settings and hashes from authenticated signatures. |
| 16 | Reviewed `data.py` bounded CSV ingestion and array ownership; identified copy-before-shape validation for direct array construction. | Data agent changed validation to inspect shape before the float copy. Source-label length mismatch was passed to integration. |
| 17 | Reviewed numerical work limits and fail-closed paths in `quant.py`: tree step cap, Monte Carlo path cap, finite scalars, covariance size and solver feasibility. | No executable/network authority found. Bounds reduce accidental workload; they are not a public-service sandbox. |
| 18 | Reviewed report escaping, fixed SVG contexts and hash-based style policy; identified finite-extreme chart and percentage overflow. | Report agent added explicit out-of-range chart handling and percentage checks with regression tests. No active scripts or external resources are required. |
| 19 | Reviewed external critique ingestion: byte limit, duplicate keys, role binding, allowlisted findings and evidence links; challenged malformed self-hashed report input. | Research agent added evidence-shape validation and adversarial regression coverage. Checksums remain integrity-only. |
| 20 | Ran the available integrated suite and repeated the owned policy tests after workflow/package-name changes. | Integration snapshot passed 99 tests; later modules add tests. Owned scanner suite passed 13 tests and repository policy reported zero findings. Rerun commands below for current results. |

## Verification commands

```bash
python scripts/security_check.py
PYTHONPATH=src python -m unittest discover -s tests -p test_security.py -v
PYTHONPATH=src python -m unittest discover -s tests -v
```

The 99-test figure records the specific intermediate integration run observed by this agent, not a permanent project test count. The final integrated run is recorded by the coordinating agent. No GitHub Actions success is asserted here.

## Resolved official action refs

| Repository and tag | Commit resolved on 8 November 2026 | Used |
|---|---|---|
| `actions/checkout` v4 | `11d5960a326750d5838078e36cf38b85af677262` | Yes |
| `actions/setup-python` v5 | `a26af69be951a213d495a4c3e4e4022e16d87065` | Yes |
| `actions/upload-artifact` v4 | `ea165f8d65b6e75b540449e92b4886f43607fa02` | No |

Resolving a ref verifies which object the official repository advertises at that moment. It does not constitute a full audit of that action's implementation or its runtime.

Primary references: [GitHub secure use](https://docs.github.com/en/actions/reference/security/secure-use), [pip-audit](https://pypi.org/project/pip-audit/), [Python build](https://pypi.org/project/build/), and [upstream source snapshot](https://github.com/neohsiung/AI-Investment-Advisor/tree/990a16c12436e83d0e977f48d6a81485deb6f251).

## Local dependency advisory check

A separate disposable environment installed `pip-audit==2.10.1` and queried the published advisory database for the exact runtime versions used locally, `numpy==2.3.5` and `scipy==1.17.0`, on 8 November 2026. Command: `python -m pip_audit --no-deps --disable-pip -r runtime-audit-requirements.txt --progress-spinner off`. Result: exit code 0, **No known vulnerabilities found**. The two-line requirements input contained only those version pins. The tool warned that hashed requirements offer stronger distribution integrity. This result covers those two package/version advisories; it does not audit native binaries, build dependencies, the auditor's own environment or future versions.
