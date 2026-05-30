---
description: "Use when mapping these specs/contracts into a real implementation repository. Keeps implementations consistent without prescribing a language, framework, or runtime."
applyTo: "**"
---

# API Implementation — Contract Conformance Guide

This template repository does not contain runnable implementation code.  
When this template is instantiated, this guidance applies to that repository and helps implement these contracts consistently.

## Required conformance checks

| Implementation concern | Authoritative source in the repository using this template |
|------------------------|-----------------------------------|
| Route paths, HTTP methods, request/response shapes, status codes | `docs/specifications/contracts/openapi.yaml` |
| Roles, auth rules, and operation permissions | `docs/specifications/auth-matrix.md` |
| Entity names, attributes, relationships, and invariants | `docs/specifications/domain-model.md` |
| Flow order, preconditions, and side effects | `docs/specifications/sequence-diagrams.md` |
| Domain event channels and message schemas | `docs/specifications/contracts/asyncapi.yaml` |
| Historical event payload schema and constraints | `docs/specifications/contracts/datacontract.yaml` |

## Principles for implementation repositories

1. **Specs are the source of truth.** If implementation and spec diverge, fix implementation first.
2. **Do not add undocumented behavior.** Any new endpoint, event, or payload field requires an intentional spec update.
3. **Keep names exact.** Reuse entity and field names from the domain model and contracts; avoid synonyms.
4. **Keep access control exact.** Permission checks in code must match the auth matrix.
5. **Be implementation-agnostic in this repo.** Store requirements and guidance here; keep runtime/framework-specific code elsewhere.
