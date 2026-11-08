"""Independent identities and integrity checks for the published visual evidence."""
from copy import deepcopy
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_visuals", ROOT / "scripts/build_visuals.py")
visuals = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(visuals)


class VisualEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = visuals.compute_evidence()
        cls.bundle = visuals.make_bundle(cls.evidence)

    def _write_bundle(self, root):
        for name, content in self.bundle.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")

    def test_cash_entry_and_drawdown_reconcile_to_wealth(self):
        p = self.evidence["performance"]
        self.assertEqual(len(p["net_returns"]), 443)
        self.assertEqual(len(p["dates"]), 444)
        for prefix in ("selected", "baseline"):
            wealth = p[prefix + "_equity"]
            self.assertEqual(wealth[0], 100000)
            # First investment is entirely from cash, so the independent
            # self-financing identity is V+ = V- / (1 + per-side cost).
            self.assertAlmostEqual(wealth[1], 100000 / 1.001, places=7)
            peak = wealth[0]
            for value, dd in zip(wealth, p[prefix + "_drawdown"]):
                peak = max(peak, value)
                self.assertAlmostEqual(dd, value / peak - 1, places=12)
        for previous, current, net in zip(p["selected_equity"], p["selected_equity"][1:], p["net_returns"]):
            self.assertAlmostEqual(current / previous - 1, net, places=12)

    def test_first_signal_is_temporally_separate_and_weights_feasible(self):
        a = self.evidence["allocation"]
        dates = self.evidence["provenance"]["dates"]
        self.assertEqual(a["training_return_count"], 60)
        self.assertEqual(a["signal_date"], dates[60])
        self.assertEqual(a["execution_date"], dates[61])
        for weights in a["weights"].values():
            self.assertAlmostEqual(sum(weights), 1, places=10)
            self.assertTrue(all(0 <= w <= .5 + 1e-10 for w in weights))
        # Check that no future observations enter the displayed correlation.
        prices = self.evidence["provenance"]["prices"]
        returns = [[prices[t][i] / prices[t - 1][i] - 1 for i in range(4)] for t in range(1, 61)]
        averages = [sum(r[i] for r in returns) / 60 for i in range(4)]
        for i in range(4):
            for j in range(4):
                cross = sum((r[i] - averages[i]) * (r[j] - averages[j]) for r in returns)
                vari = sum((r[i] - averages[i]) ** 2 for r in returns)
                varj = sum((r[j] - averages[j]) ** 2 for r in returns)
                self.assertAlmostEqual(a["correlation"][i][j], cross / math.sqrt(vari * varj), places=12)

    def test_option_curve_satisfies_put_call_and_delta_parity(self):
        o = self.evidence["options"]
        model = o["inputs"]
        for point in o["curve"]:
            discounted_spot = point["spot"] * math.exp(-model["dividend"] * model["maturity"])
            discounted_strike = model["strike"] * math.exp(-model["rate"] * model["maturity"])
            self.assertAlmostEqual(point["call"] - point["put"], discounted_spot - discounted_strike, places=11)
            self.assertAlmostEqual(point["call_delta"] - point["put_delta"], 1.0, places=12)
        self.assertAlmostEqual(o["analytical"], 10.450583572185565, places=10)

    def test_monte_carlo_intervals_count_pairs(self):
        for point in self.evidence["options"]["monte_carlo"]:
            self.assertEqual(point["independent_pairs"], point["paths"] // 2)
            self.assertAlmostEqual((point["ci_high"] + point["ci_low"]) / 2, point["price"], places=12)
            self.assertAlmostEqual((point["ci_high"] - point["price"]) / point["standard_error"], 1.959963984540054, places=10)

    def test_tail_counts_and_fractional_mass(self):
        p, tail = self.evidence["performance"], self.evidence["tail_risk"]
        losses = sorted((-r for r in p["net_returns"]), reverse=True)
        self.assertEqual(sum(tail["counts"]), len(losses))
        mass = len(losses) * .05
        whole = math.floor(mass)
        expected = (sum(losses[:whole]) + (mass - whole) * losses[whole]) / mass
        self.assertAlmostEqual(expected, tail["risk"]["expected_shortfall"], places=12)
        var_index = math.ceil(.95 * len(losses)) - 1
        self.assertEqual(sorted(losses)[var_index], tail["risk"]["var"])

    def test_svg_labels_and_offline_content(self):
        svg_files = {name: text for name, text in self.bundle.items() if name.endswith(".svg")}
        self.assertEqual(len(svg_files), 6)
        ns = {"s": "http://www.w3.org/2000/svg"}
        for name, text in svg_files.items():
            with self.subTest(asset=name):
                root = ET.fromstring(text)
                self.assertEqual(root.attrib["role"], "img")
                self.assertTrue(root.find("s:title", ns).text)
                self.assertTrue(root.find("s:desc", ns).text)
                self.assertTrue("SYNTHETIC DATA" in text or "MODEL OUTPUT" in text)
                for node in root.iter():
                    self.assertNotIn(node.tag.split("}")[-1], ("script", "image", "foreignObject", "iframe"))
                    self.assertFalse(any(attr.lower().startswith("on") for attr in node.attrib))
                    self.assertFalse(any(attr.endswith("href") for attr in node.attrib))

    def test_bundle_verifies_and_catches_changed_chart(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_bundle(root)
            visuals.verify_bundle(root, self.evidence)
            chart = root / "cost-sensitivity.svg"
            chart.write_text(chart.read_text(encoding="utf-8").replace("Costs change the result", "Altered result"), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                visuals.verify_bundle(root, self.evidence)

    def test_missing_or_altered_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_bundle(root)
            path = root / "data/manifest.json"
            manifest = json.loads(path.read_text(encoding="utf-8"))
            manifest["files"].pop("tail-risk.svg")
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "inventory"):
                visuals.verify_bundle(root, self.evidence)
            path.unlink()
            with self.assertRaises(FileNotFoundError):
                visuals.verify_bundle(root, self.evidence)

    def test_numerical_evidence_and_saved_price_hash_are_checked(self):
        changed = deepcopy(self.evidence)
        changed["cost_scenarios"][0]["final_equity"] *= 1.01
        with self.assertRaisesRegex(ValueError, "numerical evidence changed"):
            visuals.compare_evidence(changed, self.evidence)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_bundle(root)
            changed = deepcopy(self.evidence)
            changed["provenance"]["prices"][0][0] += 1
            (root / "data/visual-evidence.json").write_text(json.dumps(changed), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "dataset hash"):
                visuals.verify_bundle(root, self.evidence)


if __name__ == "__main__":
    unittest.main()
