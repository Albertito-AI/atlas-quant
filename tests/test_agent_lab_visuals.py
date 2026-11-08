"""Integrity, labelling and data-projection checks for the five agent-lab figures."""
from copy import deepcopy
import csv
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_agent_lab", ROOT / "scripts/build_agent_lab.py")
visuals = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(visuals)


class AgentLabVisualTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = visuals.compute_evidence()
        cls.bundle = visuals.make_bundle(cls.evidence)

    def write_bundle(self, root):
        for name, value in self.bundle.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(value, encoding="utf-8", newline="\n")

    def test_five_accessible_offline_figures_and_five_data_exports(self):
        charts = {name: value for name, value in self.bundle.items() if name.endswith(".svg")}
        csvs = {name: value for name, value in self.bundle.items() if name.endswith(".csv")}
        self.assertEqual(len(charts), 5)
        self.assertEqual(len(csvs), 5)
        ns = {"s": "http://www.w3.org/2000/svg"}
        for name, value in charts.items():
            with self.subTest(chart=name):
                root = ET.fromstring(value)
                self.assertEqual(root.attrib["role"], "img")
                self.assertTrue(root.find("s:title", ns).text)
                self.assertTrue(root.find("s:desc", ns).text)
                self.assertTrue(any(label in value for label in ("SYNTHETIC DATA", "MODEL OUTPUT", "MODELLED SCENARIOS")))
                for node in root.iter():
                    self.assertNotIn(node.tag.split("}")[-1], ("script", "image", "foreignObject", "iframe"))
                    self.assertFalse(any(key.lower().startswith("on") or key.endswith("href") for key in node.attrib))

    def test_exports_preserve_observation_timing_and_scenario_inventory(self):
        belief = list(csv.DictReader(io.StringIO(self.bundle["data/regime-beliefs.csv"])))
        evidence = self.evidence
        self.assertEqual(len(belief), len(evidence["data"]["observed_index_log_returns"]))
        for i, row in enumerate(belief):
            self.assertEqual(float(row["prior_stress_probability"]), evidence["beliefs"]["prior_probabilities"][i][1])
            self.assertEqual(float(row["posterior_stress_probability"]), evidence["beliefs"]["posterior_probabilities"][i][1])
        rows = list(csv.DictReader(io.StringIO(self.bundle["data/scenarios.csv"])))
        for sample, sets in (("fitting", evidence["scenario_sets"]), ("held_out", evidence["heldout_scenario_sets"])):
            for name, draws in sets.items():
                subset = [row for row in rows if row["scenario"] == name and row["sample"] == sample]
                self.assertEqual(len(subset), len(draws))
                self.assertEqual([float(subset[0][s]) for s in evidence["data"]["symbols"]], draws[0])

    def test_policy_sweep_is_not_labelled_trade_approval(self):
        svg = self.bundle["governance-gates.svg"]
        self.assertIn(self.evidence["governance"]["outcome"], svg)
        self.assertIn("This sweep isolates one gate", svg)
        self.assertIn("cannot approve a trade", svg)
        rows = list(csv.DictReader(io.StringIO(self.bundle["data/governance.csv"])))
        self.assertEqual(len(rows), len(self.evidence["governance"]["risk_budget_sweep"]))
        for row, evidence in zip(rows, self.evidence["governance"]["risk_budget_sweep"]):
            self.assertEqual(float(row["worst_cvar"]), evidence["worst_cvar"])
            self.assertEqual(row["tail_gate_passed"], str(evidence["tail_gate_passed"]))

    def test_bundle_reproduces_and_modified_figure_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_bundle(root)
            visuals.verify_bundle(root, self.evidence)
            path = root / "regime-beliefs.svg"
            path.write_text(path.read_text().replace("Market state is a belief", "Market state is certain"))
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                visuals.verify_bundle(root, self.evidence)

    def test_changed_gate_and_numeric_evidence_cannot_hide_in_tolerance(self):
        changed = deepcopy(self.evidence)
        original = changed["governance"]["risk_budget_sweep"][0]["tail_gate_passed"]
        changed["governance"]["risk_budget_sweep"][0]["tail_gate_passed"] = not original
        with self.assertRaisesRegex(ValueError, "value changed"):
            visuals.compare_evidence(changed, self.evidence)
        changed = deepcopy(self.evidence)
        changed["allocations"]["robust"]["evaluation"]["worst_cvar"] += .001
        with self.assertRaisesRegex(ValueError, "numerical evidence changed"):
            visuals.compare_evidence(changed, self.evidence)

    def test_missing_manifest_entries_and_modified_evidence_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_bundle(root)
            path = root / "data/manifest.json"
            manifest = json.loads(path.read_text())
            manifest["sources"].pop("src/atlas_quant/beliefs.py")
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "inventory"):
                visuals.verify_bundle(root, self.evidence)
            self.write_bundle(root)
            changed = deepcopy(self.evidence)
            changed["data"]["observed_index_log_returns"][0] += .01
            (root / "data/evidence.json").write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError, "integrity digest"):
                visuals.verify_bundle(root, self.evidence)


if __name__ == "__main__":
    unittest.main()
