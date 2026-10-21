# ADR 0003: Self-Updating Documentation via File Headers

## Context
Codebases developed or modified by AI agents and humans suffer from documentation rot. Agents waste context window tokens reading entire files merely to understand module purposes and dependencies.

## Decision
Mandate a standardized <=10 line file header docstring on all source files (`Purpose`, `Inputs`, `Outputs`, `Depends on`, `Used by`, `Config keys`, `Tests`). Provide `tools/update_docs.py` to automatically scan headers and generate `docs/CODEMAP.md`.

## Consequences
- Agents can read `docs/CODEMAP.md` cheaply without reading every file.
- Header validity and `Used by` accuracy are enforced via unit tests and pre-commit hooks.
