package main

import (
    "context"
)

// TestingSuite exposes one public behavior-validation entrypoint.
type TestingSuite struct{}

func (m *TestingSuite) Validate(ctx context.Context) (string, error) {
    return dag.Container().
        From("python:3.12-slim").
        WithDirectory("/src", dag.CurrentModule().Source()).
        WithWorkdir("/src").
        WithExec([]string{"python", "-m", "unittest", "discover", "-s", "tests", "-v"}).
        Stdout(ctx)
}
