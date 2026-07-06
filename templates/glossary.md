# Glossary — [Domain]

> The ubiquitous language for the [Domain] domain — a lexicon, not a
> reference manual. Every entity, role, domain event, enumeration,
> and key term used in the spec set has a one- or two-sentence entry
> here under the exact name the other documents use. Attribute-level
> detail lives in `domain-model.md`'s entity tables (the single
> attribute authority), not here. Code, docs, and conversation must
> use these terms.

---

## Entities

### [Resource1]

[One- or two-sentence description of what a [Resource1] is in this
domain. Reference its lifecycle and ownership relationships in plain
language — don't enumerate attributes; the domain model owns those.]

---

## Roles

### [role1]

[Describe what this role can do, and how it maps to a PRD persona.]

---

## Domain events

### [Resource1]Created

Published on `[domain].[resource1].created` whenever a new
[Resource1] is added. Payload is the full record.

### [Resource1]Updated

Published on `[domain].[resource1].updated` whenever a [Resource1]
changes. Payload is the full record post-change.

---

## Enumerations

### [EnumName]

[One sentence: what this enumeration classifies, whether it is open
or closed, and where the authoritative value list lives (the domain
model's `## Enumerations` section; the openapi schema for open
enums).]

---

## Other terms

### [domain-specific concept]

[Define every other term that appears in code or specs and would not
be obvious from name alone. Keep entries short.]
