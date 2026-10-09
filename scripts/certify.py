#!/usr/bin/env python3
"""External, read-only GitHub verification; no simulated success path."""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable, Any

REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SHA = re.compile(r"^[0-9a-f]{40}$")
WORKFLOW = ".github/workflows/opencode-candidate-validation.yml"
EXPECTED_WORKFLOWS = (
    ".github/workflows/opencode-frontier.yml",
    ".github/workflows/opencode-candidate-validation.yml",
    ".github/workflows/opencode-admit.yml",
)
REQUIRED_JOBS = ("deterministic", "security")
OIDC_ISSUER = "https://token.actions.githubusercontent.com"


class EvidenceError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise EvidenceError(message)


def fetch_json(repository: str, path: str) -> dict:
    token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    require(bool(token), "GitHub read token is required")
    request = urllib.request.Request(
        "https://api.github.com/repos/" + repository + path,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + str(token),
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "test-suite-actions/1",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise EvidenceError("GitHub GET " + path + " failed: HTTP " + str(exc.code)) from exc
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        raise EvidenceError("GitHub GET " + path + " failed: " + str(exc)) from exc


def current_main(repository: str, get: Callable[[str, str], dict]) -> str:
    data = get(repository, "/git/ref/heads/main")
    sha = str(data.get("object", {}).get("sha", ""))
    require(bool(SHA.fullmatch(sha)), "canonical main SHA is missing or malformed")
    return sha


def inspect(repository: str, implementation_sha: str, get: Callable[[str, str], dict]) -> dict:
    info = get(repository, "")
    require(info.get("full_name") == repository, "fixture repository identity mismatch")
    require(info.get("default_branch") == "main", "fixture canonical branch is not main")
    main_sha = current_main(repository, get)
    observed = []
    for filename in EXPECTED_WORKFLOWS:
        body = get(repository, "/contents/" + filename + "?ref=main")
        require(body.get("encoding") == "base64", "workflow source was not returned as base64: " + filename)
        try:
            contents = base64.b64decode(body["content"], validate=False).decode("utf-8")
        except (KeyError, UnicodeDecodeError, ValueError) as exc:
            raise EvidenceError("workflow source could not be decoded: " + filename) from exc
        references = re.findall(r"uses:\s*Samwise-x/opencode-actions(?:/[\w-]+)?@([^\s#]+)", contents)
        require(bool(references), "workflow missing pinned self-action: " + filename)
        require(all(ref == implementation_sha for ref in references), "incorrect or unresolved self-action pin: " + filename)
        observed.append(filename)
    return {
        "result": "OBSERVED",
        "repository": repository,
        "implementation_sha": implementation_sha,
        "canonical_sha": main_sha,
        "observed_workflows": observed,
        "certifies_live_worker": False,
    }


def verify_sigstore(qualification: Path, bundle: Path, repository: str, workflow: str) -> None:
    require(qualification.is_file() and bundle.is_file(), "qualification or Sigstore bundle missing")
    identity = r"^https://github\.com/" + re.escape(repository + "/" + workflow) + r"@refs/.*$"
    argv = [
        "cosign", "verify-blob",
        "--bundle", str(bundle),
        "--certificate-identity-regexp", identity,
        "--certificate-oidc-issuer", OIDC_ISSUER,
        str(qualification),
    ]
    if not shutil.which("cosign"):
        require(bool(shutil.which("nix")), "Cosign and Nix are both unavailable")
        argv = ["nix", "shell", "github:NixOS/nixpkgs/2833a4f2f08058f980a143c9fb447953ef15f1cb#cosign", "--command", *argv]
    try:
        result = subprocess.run(argv, capture_output=True, text=True, check=False, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise EvidenceError("Cosign verification unavailable: " + str(exc)) from exc
    require(result.returncode == 0, "invalid Sigstore qualification signature or workflow identity")


def verify_admission(
    repository: str,
    implementation_sha: str,
    base_sha: str,
    candidate_sha: str,
    pr_number: int,
    run_id: int,
    qualification: Path,
    bundle: Path,
    get: Callable[[str, str], dict],
    signature: Callable[[Path, Path, str, str], None],
) -> dict:
    for name, sha in (("base", base_sha), ("candidate", candidate_sha)):
        require(bool(SHA.fullmatch(sha)), name + " SHA is invalid")
    require(base_sha != candidate_sha, "candidate did not advance canonical baseline")
    require(pr_number > 0 and run_id > 0, "PR number and validation run ID are required")
    require(qualification.is_file() and bundle.is_file(), "qualification and Sigstore bundle required")

    try:
        manifest = json.loads(qualification.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceError("qualification JSON cannot be read") from exc
    require(manifest.get("schema") == 1 and manifest.get("kind") == "qualified-candidate",
            "unsupported qualification schema or kind")
    expected = {
        "repository": repository,
        "base_sha": base_sha,
        "candidate_sha": candidate_sha,
        "pr_number": pr_number,
        "validation_run_id": str(run_id),
    }
    for name, value in expected.items():
        require(str(manifest.get(name, "")) == str(value), "qualification " + name + " differs from expected identity")
    workflow_ref = str(manifest.get("validation_workflow_ref", ""))
    require(workflow_ref.startswith(repository + "/" + WORKFLOW + "@"),
            "qualification workflow identity does not match canonical validation")
    require(set(manifest.get("required_checks", [])) == set(REQUIRED_JOBS),
            "qualified required-job set differs from policy")

    # Crypto first; no unsigned qualification can be interpreted as evidence.
    signature(qualification, bundle, repository, WORKFLOW)

    observed = inspect(repository, implementation_sha, get)
    require(observed["canonical_sha"] == candidate_sha, "inspected main does not match admitted SHA")
    current = current_main(repository, get)
    require(current == candidate_sha, "canonical main does not equal the admitted candidate")

    pr = get(repository, "/pulls/" + str(pr_number))
    require(pr.get("base", {}).get("ref") == "main", "candidate PR base is not canonical main")
    require(pr.get("head", {}).get("sha") == candidate_sha, "candidate PR head moved")
    require(pr.get("state") in ("open", "closed"), "PR state is unavailable")

    comparison = get(repository, "/compare/" + base_sha + "..." + candidate_sha)
    require(comparison.get("status") == "ahead" and comparison.get("ahead_by", 0) > 0,
            "candidate does not descend from baseline")

    run = get(repository, "/actions/runs/" + str(run_id))
    require(run.get("head_sha") == candidate_sha, "validation run evaluated another commit")
    require(run.get("path") == WORKFLOW, "validation run workflow path mismatch")
    require(run.get("event") == "pull_request", "validation event is not pull_request")
    require(run.get("status") == "completed" and run.get("conclusion") == "success",
            "validation run did not complete successfully")
    associated_prs = {int(p["number"]) for p in run.get("pull_requests", []) if "number" in p}
    require(not associated_prs or pr_number in associated_prs, "validation run belongs to a different PR")

    jobs = get(repository, "/actions/runs/" + str(run_id) + "/jobs?per_page=100")
    rows = jobs.get("jobs", [])
    require(jobs.get("total_count", len(rows)) == len(rows), "validation jobs response was truncated")
    for name in REQUIRED_JOBS:
        matching = [j for j in rows if j.get("name") == name]
        require(bool(matching), "required validation job missing: " + name)
        require(all(j.get("status") == "completed" and j.get("conclusion") == "success" for j in matching),
                "required validation job failed: " + name)
    return {
        "result": "ADMISSION_VERIFIED",
        "repository": repository,
        "implementation_sha": implementation_sha,
        "baseline_sha": base_sha,
        "candidate_sha": candidate_sha,
        "pr_number": pr_number,
        "validation_run_id": run_id,
        "required_jobs": list(REQUIRED_JOBS),
        "signed_qualification_verified": True,
        "certifies_recovery_or_compounding": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=("inspect", "admission"), required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--implementation-sha", required=True)
    parser.add_argument("--base-sha", default="")
    parser.add_argument("--candidate-sha", default="")
    parser.add_argument("--pr-number", default="")
    parser.add_argument("--validation-run-id", default="")
    parser.add_argument("--qualification-file", default="")
    parser.add_argument("--bundle-file", default="")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report: dict[str, Any]
    try:
        require(bool(REPOSITORY.fullmatch(args.repository)), "repository must be OWNER/REPO")
        require(bool(SHA.fullmatch(args.implementation_sha)), "implementation SHA must be a full immutable commit")
        if args.scenario == "inspect":
            report = inspect(args.repository, args.implementation_sha, fetch_json)
        else:
            require(args.pr_number.isdigit() and args.validation_run_id.isdigit(), "numeric PR and validation-run IDs required")
            require(bool(args.qualification_file and args.bundle_file), "signed qualification paths required")
            report = verify_admission(
                args.repository, args.implementation_sha, args.base_sha, args.candidate_sha,
                int(args.pr_number), int(args.validation_run_id),
                Path(args.qualification_file), Path(args.bundle_file),
                fetch_json, verify_sigstore,
            )
        status = 0
    except (EvidenceError, OSError, ValueError, TypeError) as exc:
        report = {"result": "FAIL", "repository": args.repository, "scenario": args.scenario,
                  "reason": str(exc)}
        status = 1
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
