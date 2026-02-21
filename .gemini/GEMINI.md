# Python Development Guidelines

## 0) Scope

- These rules apply **only when working with Python code** in this repository.
- They **complement** the root-level `GEMINI.md`.
- They **must not override** global constraints from `GEMINI.md` unless explicitly stated.

---

## 1) Language & Version

- Target **Python 3.11+** unless existing repository configuration specifies otherwise.
- Write idiomatic, standard Python.

---

## 2) Project Structure (Python)

- Put Python packages under `src/`.
- Do **not** import from the project root; use proper package imports.
- Keep `__init__.py` **minimal** and **free of side effects**.

---

## 3) Type Safety

- Every function and method must include **type hints** for all parameters and the return type.
- Code must comply with **`mypy --strict`**.
- Avoid `Any` unless it is strictly unavoidable and clearly justified.
- Prefer:
  - `dataclasses`
  - `TypedDict`
  - `Protocol`
  - precise union types

---

## 4) Style & Readability

- Prefer comprehensions over verbose loops **when clarity is preserved**.
- Prefer the standard library over external dependencies when reasonable.
- Avoid unnecessary abstractions and boilerplate.
- Keep functions small and focused.

---

## 5) Functional Design

- Prefer pure functions where possible.
- Separate business logic from I/O, framework, or environment-specific code.
- Core logic must be testable without external dependencies.

---

## 6) Testing (Python)

- Use `pytest`-style unit tests.
- Unit tests must **not** depend on real external systems.
- Mock network, filesystem, APIs, and time where appropriate.
- Write tests incrementally alongside implementation.

---

## 7) Tooling (Python)

- **All Python execution must go through `uv`.**
  - Use `uv run` to run modules, scripts, and tests.
  - Do **not** invoke `python`, `pip`, `venv`, or `poetry` directly.

- Dependency management is handled with `uv`.
- Linting and formatting are enforced with `ruff`.
- Type checking is enforced with `mypy`.
- Prefer explicit exception handling over silent failures.

### Common commands (examples)

- Tests: `uv run pytest`
- Lint: `ruff check`
- Format: `ruff format`
- Type check: `mypy`

---

## 8) Logging & Errors (Python)

- Use logging for diagnostics, **not** for control flow.
- Do not mix logging output with return values.
- Do not swallow exceptions.
- Catch exceptions only when meaningful recovery or translation is possible.
- Preserve original exception context when re-raising.

---

## 9) Non-Code Artifacts

- Do not embed large SQL queries, templates, or other non-Python artifacts as inline strings.
- Store them as separate files and load them explicitly.
- Keep loading logic explicit and testable.

---

## 10) Comments & Docstrings

- Add comments sparingly.
- Explain **why** something is done, not **what** is done.
- Avoid long or line-by-line comments.
- Docstrings should describe behavior and constraints, not implementation details.

---

## 11) Additional Rules for Gemini (Compliance Helpers)

- When you modify or add Python code, **also update or add unit tests** in the same change whenever behavior changes.
- Do **not** introduce new third-party dependencies unless explicitly required. Prefer the standard library.
- Keep core logic decoupled from I/O so it can be tested without external systems.
- Ensure changes pass the repository tooling: `uv run pytest`, `ruff check`, and `mypy`.
- Do not broaden types to "make mypy happy"; prefer precise types and small refactors.
- Avoid hidden behavior:
  - no side effects at import time
  - no implicit global state changes

- Prefer small, reviewable diffs: minimal changes that meet requirements.
