# Pass 1 architecture and test boundary

The external testing Action has one responsibility: **verify externally observable behavior**.

- `opencode-actions` owns worker execution, leases, candidate production, and trusted admission.
- `test-suite-actions` owns fixture definitions, independent observation, acceptance assertions, and evidence reports.
- GitHub owns durable refs, PRs, Issues, workflow runs, and artifacts.
- Nix supplies a declared CLI/toolchain environment.
- Dagger supplies the portable behavior-validation entrypoint.

There is no new persistent service, database, agent memory, or shared mutable testing state.

## Public seams

1. `python3 scripts/provision.py --output PATH [--init-git] [--remote-repository OWNER/REPO]` creates an isolated local fixture. It refuses to overwrite existing directories.
2. `dagger call validate` runs the repository's behavior tests in a disposable container.
3. `python3 scripts/certify.py --scenario inspect|admission ...` reads real GitHub state and writes JSON evidence.
4. Composite `action.yml` exposes the verification seam to any authorized GitHub workflow.

The suite never mints admission authority. It fails closed when an expected source is missing, incomplete, or inconsistent. Tests exercise these public entrypoints rather than test-only production hooks.

## Meaning of results

- `OBSERVED`: target metadata, deployed control-plane files, and expected immutable implementation references were observed. This is NOT end-to-end certification.
- `ADMISSION_VERIFIED`: the supplied signed qualification and GitHub's exact run, jobs, candidate ancestry, and canonical SHA are consistent. This is only the completed admission seam, not recovery or compounding certification.
- `FAIL`: missing/contradictory evidence, validation error, permission denial, or rejected signature.

The live end-to-end certification outcome remains unavailable until the later acceptance scenarios execute.

## Trust boundary

The reusable Action requests no write permissions. GitHub controller credentials must be read-scoped for independent verification. The prospective fixture operator may separately provision a test target using narrowly scoped GitHub App credentials. Never expose fixture administration or admission tokens to tested OpenCode workers.

## Out of scope for Pass 1

No live worker execution without configured fixture infrastructure and authentication. No simulated success substituted for missing remote state. No silent repair of the tested repository.
