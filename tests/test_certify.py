import base64
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("certify", ROOT / "scripts" / "certify.py")
assert SPEC and SPEC.loader
certify = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(certify)

REPO = "example/fixture"
BASE = "a" * 40
CANDIDATE = "b" * 40
IMPLEMENTATION = "c" * 40
RUN = 456
PR = 12


def fake_responses():
    records = {
        "": {"full_name": REPO, "default_branch": "main"},
        "/git/ref/heads/main": {"object": {"sha": CANDIDATE}},
        "/pulls/12": {"base": {"ref": "main"}, "head": {"sha": CANDIDATE}, "state": "closed"},
        "/compare/" + BASE + "..." + CANDIDATE: {"status": "ahead", "ahead_by": 1},
        "/actions/runs/456": {
            "head_sha": CANDIDATE,
            "path": certify.WORKFLOW,
            "event": "pull_request",
            "status": "completed",
            "conclusion": "success",
            "pull_requests": [{"number": PR}],
        },
        "/actions/runs/456/jobs?per_page=100": {
            "total_count": 2,
            "jobs": [
                {"name": "deterministic", "status": "completed", "conclusion": "success"},
                {"name": "security", "status": "completed", "conclusion": "success"},
            ],
        },
    }
    for path in certify.EXPECTED_WORKFLOWS:
        value = "uses: Samwise-x/opencode-actions@" + IMPLEMENTATION + "\n"
        records["/contents/" + path + "?ref=main"] = {
            "encoding": "base64",
            "content": base64.b64encode(value.encode()).decode(),
        }
    return records


def manifest():
    return {
        "schema": 1,
        "kind": "qualified-candidate",
        "repository": REPO,
        "base_sha": BASE,
        "candidate_sha": CANDIDATE,
        "pr_number": PR,
        "validation_run_id": str(RUN),
        "validation_workflow_ref": REPO + "/" + certify.WORKFLOW + "@refs/pull/12/merge",
        "required_checks": ["deterministic", "security"],
    }


class CertificationTest(unittest.TestCase):
    def setUp(self):
        self.records = fake_responses()
        self.queries = []
        self.signatures = 0

    def get(self, repo, path):
        self.assertEqual(repo, REPO)
        self.queries.append(path)
        return self.records[path]

    def signature(self, qualification, bundle, repo, workflow):
        self.assertTrue(qualification.is_file() and bundle.is_file())
        self.assertEqual(repo, REPO)
        self.assertEqual(workflow, certify.WORKFLOW)
        self.signatures += 1

    def verification(self, doc=None):
        with tempfile.TemporaryDirectory() as temp:
            q = Path(temp) / "qualification.json"
            b = Path(temp) / "bundle.json"
            q.write_text(json.dumps(manifest() if doc is None else doc))
            b.write_text("{}")
            return certify.verify_admission(
                REPO, IMPLEMENTATION, BASE, CANDIDATE, PR, RUN, q, b, self.get, self.signature
            )

    def test_inspection_observes_pinned_workflows_without_claiming_certification(self):
        result = certify.inspect(REPO, IMPLEMENTATION, self.get)
        self.assertEqual(result["result"], "OBSERVED")
        self.assertIs(result["certifies_live_worker"], False)

    def test_inspection_rejects_mismatched_release_pin(self):
        path = "/contents/" + certify.EXPECTED_WORKFLOWS[0] + "?ref=main"
        self.records[path]["content"] = base64.b64encode(("uses: Samwise-x/opencode-actions@" + BASE).encode()).decode()
        with self.assertRaisesRegex(certify.EvidenceError, "pin"):
            certify.inspect(REPO, IMPLEMENTATION, self.get)

    def test_exact_verified_admission(self):
        result = self.verification()
        self.assertEqual(result["result"], "ADMISSION_VERIFIED")
        self.assertEqual(self.signatures, 1)
        self.assertIn("/actions/runs/456/jobs?per_page=100", self.queries)

    def test_rejects_moved_canonical(self):
        self.records["/git/ref/heads/main"]["object"]["sha"] = BASE
        with self.assertRaisesRegex(certify.EvidenceError, "canonical"):
            self.verification()

    def test_rejects_wrong_workflow_and_failed_checks(self):
        self.records["/actions/runs/456"]["path"] = "unsafe.yml"
        with self.assertRaisesRegex(certify.EvidenceError, "workflow"):
            self.verification()
        self.records["/actions/runs/456"]["path"] = certify.WORKFLOW
        self.records["/actions/runs/456/jobs?per_page=100"]["jobs"][1]["conclusion"] = "failure"
        with self.assertRaisesRegex(certify.EvidenceError, "security"):
            self.verification()

    def test_rejects_speculative_signature_or_manifest(self):
        with self.assertRaisesRegex(certify.EvidenceError, "qualification"):
            self.verification({**manifest(), "candidate_sha": BASE})
        with tempfile.TemporaryDirectory() as temp:
            q = Path(temp) / "q.json"
            b = Path(temp) / "b.json"
            q.write_text(json.dumps(manifest()))
            b.write_text("{}")
            def reject(*args):
                raise certify.EvidenceError("invalid signature")
            with self.assertRaisesRegex(certify.EvidenceError, "signature"):
                certify.verify_admission(REPO, IMPLEMENTATION, BASE, CANDIDATE, PR, RUN, q, b, self.get, reject)

    def test_rejects_missing_jobs_and_non_descendant_candidate(self):
        self.records["/actions/runs/456/jobs?per_page=100"]["jobs"].pop()
        with self.assertRaisesRegex(certify.EvidenceError, "security"):
            self.verification()
        self.records = fake_responses()
        self.records["/compare/" + BASE + "..." + CANDIDATE] = {"status": "diverged", "ahead_by": 1}
        with self.assertRaisesRegex(certify.EvidenceError, "descend"):
            self.verification()


if __name__ == "__main__":
    unittest.main()
