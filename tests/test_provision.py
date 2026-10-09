import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("provision", ROOT / "scripts" / "provision.py")
assert SPEC and SPEC.loader
provision = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(provision)


class ProvisionTest(unittest.TestCase):
    def test_creates_real_fixture_and_git_baseline(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "target"
            result = provision.provision(destination, initialize_git=True)
            self.assertEqual(result["result"], "PROVISIONED_LOCAL")
            self.assertEqual(len(result["base_sha"]), 40)
            self.assertTrue((destination / "dagger.json").is_file())
            self.assertTrue((destination / "flake.nix").is_file())
            cmd = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
                                 cwd=destination, text=True, capture_output=True)
            self.assertEqual(cmd.returncode, 0, cmd.stderr)

    def test_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "target"
            provision.provision(destination)
            with self.assertRaises(FileExistsError):
                provision.provision(destination)

    def test_remote_must_be_explicit_and_well_formed(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                provision.provision(Path(temp) / "target", remote_repository="owner/repo")
            with self.assertRaises(ValueError):
                provision.provision(Path(temp) / "target", True, "https://invalid.example")


if __name__ == "__main__":
    unittest.main()
