# ADR-003 – Coding Standards & Command Contract

Status: Accepted

Date: 2026-07-11

---

# Context

As SBA AI Studio grows, consistency becomes more important than individual coding style.

This ADR defines the coding standards and command contract used throughout the project.

---

# Command Contract

Every command performs exactly one Resolve operation.

Examples

- create_project()
- sync_bins()
- import_media()
- verify_media()

Commands never call other commands.

Commands operate only on ResolveContext.

---

# Manager Contract

Managers orchestrate commands.

Managers never communicate directly with the Resolve API.

Managers contain workflow logic.

---

# Service Contract

Services contain business logic.

Services may coordinate multiple commands.

Services are independent of the user interface.

---

# Context Contract

ResolveContext contains runtime state.

It is the only object shared between commands.

Business data belongs in domain models.

---

# Naming Standards

Functions use:

Verb + Object

Examples

- create_project()
- sync_bins()
- import_media()
- verify_media()
- create_timeline()

Avoid generic names such as:

- process()
- execute()
- handle()
- cleanup()

---

# File Standards

Each file has one responsibility.

Every public class and function includes a docstring.

Type hints should be used where practical.

Imports are grouped as:

1. Standard library
2. Third-party packages
3. SBA AI Studio modules

---

# Error Handling

Commands raise exceptions only for unrecoverable errors.

Recoverable issues are recorded in ResolveReport.

Managers decide whether execution should continue.

---

# Logging

Commands report meaningful progress.

Debug output should never replace structured reporting.

---

# Testing

Every new feature must pass:

- Python compilation
- Project Doctor
- Resolve validation

No feature is complete until all three pass.

---

# Consequences

The project maintains a consistent coding style regardless of how many modules or contributors are involved.

Architecture remains predictable and maintainable.