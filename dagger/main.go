package main

import (
    "context"
    "dagger/testing-suite/internal/dagger"
)

// TestingSuite exposes one public behavior-validation entrypoint.
type TestingSuite struct{}

func (m *TestingSuite) Validate(
    ctx context.Context,
    // +defaultPath="/"
    source *dagger.Directory,
) (string, error) {
    return dag.Container().
        From("ghcr.io/astral-sh/uv:0.9.11-python3.12-bookworm-slim@sha256:ef305979f94d4729707a0fc98444ebf1bc0e63a2d2919a62d28fcc3e42957508").
        WithExec([]string{"sh", "-ec", "apt-get update -qq && apt-get install -y -qq --no-install-recommends git ca-certificates && rm -rf /var/lib/apt/lists/*"}).
        WithDirectory("/src", source).
        WithWorkdir("/src").
        WithExec([]string{"python", "-m", "unittest", "discover", "-s", "tests", "-v"}).
        Stdout(ctx)
}
