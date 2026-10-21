# ADR 0004: Strict Core-Plugin Architectural Isolation

## Context
Circular dependencies between core business logic and specific vendor plugins create tight coupling, making testing and refactoring fragile.

## Decision
Enforce a unidirectional dependency boundary:
- `core/` contains interfaces and registries; it never imports `plugins/`.
- `plugins/` import only `core/` (and their respective external libraries).
- `tools/check_architecture.py` statically enforces this rule via AST analysis.

## Consequences
- Core can be tested independently of any third-party AI APIs.
- Plugins can be developed, mocked, or swapped without risking core regression.
