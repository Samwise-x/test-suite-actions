package main

import "context"

type Validation struct{}

// Real validation: the fixture breaks when application behavior breaks.
func (m *Validation) Validate(ctx context.Context) (string, error) {
    return dag.Container().
        From("python:3.12-slim").
        WithDirectory("/src", dag.CurrentModule().Source()).
        WithWorkdir("/src").
        WithExec([]string{"python", "-m", "unittest", "discover", "-s", "tests", "-v"}).
        Stdout(ctx)
}
