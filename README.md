# test-suite-actions

Independent GitHub-native acceptance testing for disposable autonomous engineering workers.

This repository is a **verifier**, not the autonomous worker and not a second orchestration service. Its reusable composite Action reads GitHub's actual state and produces fail-closed evidence. It never writes the candidate, admission branch, or qualification.

## Pass 1 deliverables

- `action.yml`: reusable, read-only `inspect` and `admission` verification interface.
- `scripts/certify.py`: independent REST-based observation, exact-SHA run/job/ancestry checks, Sigstore signature verification, machine-readable evidence, and fail-closed reporting.
- `scripts/provision.py`: prepare an isolated local fixture and, optionally, attach an existing GitHub fixture remote. Remote target bootstrap is an explicit operator action, never implicit.
- `fixture/`: a real Python behavior contract with a Dagger validation module; deliberately **not** an always-green placeholder.
- `dagger/`, `flake.nix`, `tests/`: reproducible test entrypoint and dependency-free Python regression tests.
- `.github/workflows/validate.yml`: GitHub-hosted CI using Nix and Dagger.

## Validate locally

```sh
nix develop --command dagger call validate
python3 -m unittest discover -s tests -v
python3 scripts/provision.py --output /tmp/testing-fixture --init-git
```

Nix resolves an explicitly pinned nixpkgs revision. Commit a generated `flake.lock` as part of a later lock-refresh pass; avoid claiming bit-identical builds until the image digest and lock are frozen.

## Observe a deployed target

```sh
GH_TOKEN=... python3 scripts/certify.py \
  --scenario inspect \
  --repository OWNER/FIXTURE_REPO \
  --implementation-sha FULL_40_CHARACTER_SHA \
  --report certification.json
```

`inspect` yields `OBSERVED`, **not** `PASS`: inspection does not prove end-to-end execution.

## Verify a completed exact-SHA admission

```sh
GH_TOKEN=... python3 scripts/certify.py \
  --scenario admission --repository OWNER/FIXTURE_REPO \
  --implementation-sha FULL_40_CHARACTER_SHA \
  --base-sha BASE_SHA --candidate-sha CANDIDATE_SHA \
  --pr-number 12 --validation-run-id 123456 \
  --qualification-file qualification.json \
  --bundle-file qualification.sigstore.json \
  --report certification.json
```

The verifier invokes Cosign to verify the Sigstore bundle against the expected repository/workflow identity, independently inspects the exact GitHub validation run and jobs, verifies candidate ancestry, and requires canonical main to equal the qualified SHA.

A missing token, fixture repository, workflow, signature, or permission produces an explicit failure. No mocked test ever counts as live certification.

## Next milestones

Pass 2 runs a real disposable OpenCode worker against the isolated fixture and exercises full GitHub candidate validation, signing, and admission.
Pass 3 introduces safety/failure/lease/credential fault injection.
Pass 4 proves reconstruction and two sequential admitted improvements.
Pass 5 repeats on live GitHub and reports exact pinned implementation identities.

The fixture repository is intentionally **separate** from this test-controller repository; no additional paid service or persistent coordinator is required.
