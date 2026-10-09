# Disposable engineering fixture

This fixture supplies a genuine, intentionally small behavior-validation graph.
The function in app.py must satisfy tests/test_app.py. Changing the function to return
a wrong value makes `dagger call validate` fail.

Provision a fresh local copy with:
`python3 scripts/provision.py --output /tmp/testing-fixture --init-git`

For a live GitHub target, the fixture must be placed in an **existing isolated** repository,
then bootstrapped using the pinned opencode-actions distribution's `make TARGET=...`
under separately authorized credentials. The test-suite verifier never provisions
that remote state implicitly.

No model or paid service is needed to run these fixture behavior tests.
