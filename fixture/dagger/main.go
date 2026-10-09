package main

import (
    "context"
    "dagger/validation/internal/dagger"
)

type Validation struct{}

// Real validation: the fixture breaks when application behavior breaks.
func (m *Validation) Validate(
    ctx context.Context,
    // +defaultPath="/"
    source *dagger.Directory,
) (string, error) {
    return dag.Container().
        From("ghcr.io/astral-sh/uv:0.9.11-python3.12-bookworm-slim@sha256:ef305979f94d4729707a0fc98444ebf1bc0e63a2d2919a62d28fcc3e42957508").
        WithDirectory("/src", source).
        WithWorkdir("/src").
        WithExec([]string{"python", "-m", "unittest", "discover", "-s", "tests", "-v"}).
        Stdout(ctx)
}
