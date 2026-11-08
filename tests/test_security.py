"""Adversarial behaviour checks for the repository policy scanner."""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location('security_check', Path(__file__).resolve().parents[1] / 'scripts' / 'security_check.py')
scanner = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(scanner)


class SecurityPolicyTests(unittest.TestCase):
    def test_blocks_dynamic_execution(self):
        for source in ('eval(data)', 'exec(data)', 'import os as operating\noperating.system(data)', 'from builtins import eval as run\nrun(data)'):
            with self.subTest(source=source):
                self.assertTrue(scanner.inspect_python(source))

    def test_blocks_network_and_unsafe_deserialisation(self):
        for source in ('import socket', 'from urllib import request', 'import pickle as p', 'from subprocess import run'):
            with self.subTest(source=source):
                self.assertTrue(scanner.inspect_python(source))

    def test_safe_scientific_code_passes(self):
        self.assertEqual(scanner.inspect_python('import numpy as np\nfrom scipy.stats import norm\nx = np.array([1.0])\n'), [])

    def test_parse_errors_fail(self):
        self.assertEqual(scanner.inspect_python('def broken(')[0][1], 'invalid-python')

    def test_secret_redaction(self):
        fake = 'gh' + 'p_' + 'A' * 36
        findings = scanner.inspect_text(fake)
        self.assertEqual(findings, [(1, 'github-token')])
        self.assertNotIn(fake, repr(findings))

    def test_private_keys_are_detected(self):
        marker = '-----BEGIN ' + 'PRIVATE KEY-----'
        self.assertEqual(scanner.inspect_text(marker), [(1, 'private-key')])

    def test_unpinned_actions_rejected(self):
        self.assertIn((3, 'unpinned-action'), scanner.inspect_workflow('permissions:\n  contents: read\n- uses: actions/checkout@v4'))

    def test_pinned_action_and_read_permission_pass(self):
        workflow = 'permissions:\n  contents: read\n- uses: actions/checkout@' + 'a' * 40
        self.assertEqual(scanner.inspect_workflow(workflow), [])


    def test_exact_pinned_atlas_caller_has_narrow_write_exception(self):
        caller = scanner.APPROVED_ATLAS_CALLER
        path = scanner.APPROVED_ATLAS_PATH
        self.assertEqual(scanner.inspect_workflow(caller, path), [])
        self.assertTrue(any(rule == 'write-token-permission' for _, rule in scanner.inspect_workflow(caller)))
        self.assertTrue(any(rule == 'write-token-permission' for _, rule in scanner.inspect_workflow(caller, Path('.github/workflows/other.yml'))))
        for mutation in (
            caller.replace('actions: write', 'contents: write'),
            caller.replace('2e849a36fd6a2b93d1a968efd4fcccdb7523132b', '0' * 40),
            caller + '  extra-job: {}\n',
        ):
            with self.subTest(mutation=mutation[-50:]):
                self.assertTrue(scanner.inspect_workflow(mutation, path), 'Modified caller must lose exception')

    def test_privileged_workflow_rejected(self):
        result = scanner.inspect_workflow('on: pull_request_target\npermissions: write-all\nruns-on: self-hosted\n')
        self.assertTrue(any(rule == 'privileged-workflow-trigger' for _, rule in result))
        self.assertTrue(any(rule == 'privileged-workflow-setting' for _, rule in result))

    def test_missing_readonly_permission_rejected(self):
        self.assertIn((1, 'explicit-readonly-permissions-required'), scanner.inspect_workflow('on: push'))

    def test_env_and_symlink_rejected_without_reading_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / '.env').write_text('local value', encoding='utf-8')
            (root / 'link.py').symlink_to(root / 'missing')
            findings = scanner.scan(root)
            self.assertTrue(any('environment-file' in finding for finding in findings))
            self.assertTrue(any('symlink-requires-review' in finding for finding in findings))

    def test_oversized_text_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'large.txt').write_text('x' * (scanner.MAX_FILE_BYTES + 1), encoding='utf-8')
            self.assertTrue(any('text-file-too-large' in item for item in scanner.scan(root)))

    def test_repository_policy(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(scanner.scan(root), [])


if __name__ == '__main__':
    unittest.main()
