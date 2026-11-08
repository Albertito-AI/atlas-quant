"""Exercise visual provenance through Git and Windows text newline conversion."""
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load_generator(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FINANCIAL = load_generator("build_visuals")
AGENT_LAB = load_generator("build_agent_lab")
GALLERIES = (
    (FINANCIAL, Path("docs/assets"), "data/visual-evidence.json"),
    (AGENT_LAB, Path("docs/assets/agent-lab"), "data/evidence.json"),
)


class VisualNewlineTests(unittest.TestCase):
    def test_generators_round_trip_with_windows_text_newlines(self):
        # Emulate Windows' default text write translation on any test platform.
        # Explicit newline arguments retain their real Python behaviour.
        original_open = Path.open

        def windows_text_open(path, mode="r", buffering=-1, encoding=None,
                              errors=None, newline=None):
            if "w" in mode and "b" not in mode and newline is None:
                newline = "\r\n"
            return original_open(path, mode, buffering, encoding, errors, newline)

        for generator, asset_path, evidence_name in GALLERIES:
            with self.subTest(gallery=str(asset_path)), tempfile.TemporaryDirectory() as tmp:
                evidence = json.loads((ROOT / asset_path / evidence_name).read_text(encoding="utf-8"))
                output = Path(tmp)
                # The financial identities are exercised separately. Reuse the
                # committed evidence here to isolate the real CLI's file I/O.
                with patch.object(Path, "open", windows_text_open), \
                        patch.object(generator, "compute_evidence", return_value=evidence), \
                        patch("sys.argv", [generator.__name__, "--output", str(output)]), \
                        redirect_stdout(io.StringIO()):
                    self.assertEqual(generator.main(), 0)
                generator.verify_bundle(output, evidence)
                for path in output.rglob("*"):
                    if path.is_file():
                        self.assertNotIn(b"\r\n", path.read_bytes(), str(path.relative_to(output)))

    @unittest.skipUnless(shutil.which("git"), "Git is needed to exercise checkout conversion")
    def test_autocrlf_checkout_preserves_source_and_asset_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            repository = Path(tmp) / "repository"
            checkout = Path(tmp) / "checkout"
            repository.mkdir()
            checkout.mkdir()
            paths = set()
            for _, asset_path, _ in GALLERIES:
                manifest = json.loads((ROOT / asset_path / "data/manifest.json").read_text(encoding="utf-8"))
                paths.update(Path(name) for name in manifest["sources"])
                paths.update(asset_path / name for name in manifest["files"])
                paths.add(asset_path / "data/manifest.json")
            attributes = ROOT / ".gitattributes"
            if attributes.is_file():
                paths.add(Path(".gitattributes"))
            for relative in paths:
                target = repository / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / relative).read_bytes())

            def git(*arguments):
                return subprocess.run(["git", *arguments], cwd=repository, check=True,
                                      capture_output=True, text=True)

            git("init", "--quiet")
            git("-c", "core.autocrlf=false", "add", "--all")
            # No commits, remote access or account identity are required.
            git("-c", "core.autocrlf=true", "-c", "core.eol=crlf", "checkout-index",
                "--all", "--force", f"--prefix={checkout.as_posix()}/")
            for generator, asset_path, evidence_name in GALLERIES:
                with self.subTest(gallery=str(asset_path)):
                    evidence = json.loads((checkout / asset_path / evidence_name).read_text(encoding="utf-8"))
                    with patch.object(generator, "ROOT", checkout):
                        generator.verify_bundle(checkout / asset_path, evidence)


if __name__ == "__main__":
    unittest.main()
