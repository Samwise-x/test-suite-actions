# Domain language

**system under test**: a separately deployed GitHub Action implementation, pinned to an exact Git commit.

**fixture repository**: an isolated GitHub repository used to exercise real execution without risking the implementation repository.

**observation**: independent retrieval of authoritative GitHub state; observation alone is not certification.

**certification**: verified satisfaction of the claimed lifecycle contract using live evidence, not the tested Action's own claimed success.

**baseline SHA**: the exact canonical commit at the start of an execution.

**candidate SHA**: the exact commit proposed for admission.

**validation run**: the specific GitHub Actions workflow run that evaluated the candidate SHA.

**qualification**: signed evidence binding the candidate to its validation run and required checks.

**admission**: a canonical-ref transition that advances main to the exact qualified candidate.

**test controller**: bounded GitHub Action collecting independent evidence, not a production execution authority.
