# Modeling question bank — Phase 2
#
# YAML by content; .md extension per SUITE-DESIGN §5 convention. One
# entry per gate-check id; build-time coverage enforces this.

- id: MODEL-ENTITY-NAME-UNIQUE
  binds_to_check: MODEL-ENTITY-NAME-UNIQUE

  lead_in: |
    The entity '{{entity_name}}' appears more than once in
    domain-model.md. Each entity must have exactly one definition —
    which of the duplicates is the real one, or should they be merged
    into a new one?

  probes:
    - trigger: "answer reveals two genuinely-different concepts sharing a name"
      ask: |
        Then they need distinct names. What does each one mean in
        business terms? Rename the less-obvious one.
    - trigger: "answer says 'merge them'"
      ask: |
        Sketch the merged shape: attributes from both, business rules
        from both, any conflict resolved how?

  good_example: |
    "The two Account definitions are stale from an earlier draft —
     drop the second and keep the first."

  bad_example:
    answer: "Doesn't matter, just pick one."
    rebuttal: |
      It matters — the duplicate means a downstream contract or flow
      could end up referencing the wrong one. Pick the canonical
      definition and remove the other.

  reflect_template: |
    Resolving '{{entity_name}}' duplication by {{action}}. Sound right?

- id: ENTITY-IN-GLOSSARY
  binds_to_check: ENTITY-IN-GLOSSARY

  lead_in: |
    Entity '{{entity_name}}' is in domain-model.md but isn't in
    glossary.md. Glossary is the ubiquitous-language source of truth
    — every entity name has to appear there. Want me to add the
    skeleton?

  probes:
    - trigger: "answer says 'it's not really a domain concept'"
      ask: |
        If it's not a domain concept, why is it in domain-model.md?
        Either it belongs there (add to glossary) or it should be
        removed from the model (refactor).

  good_example: |
    "Add it — short paragraph: 'Notification — a transient outbound
     message produced when a watched resource changes.'"

  bad_example:
    answer: "It's obvious from the name."
    rebuttal: |
      Glossary entries exist for the cases where it's not obvious —
      and for downstream contract reviewers who don't know the
      domain. Add the entry; one sentence is enough.

  reflect_template: |
    Adding glossary entry for '{{entity_name}}': {{summary}}. Sound right?

- id: GLOSSARY-COVERS-ATTRIBUTES
  binds_to_check: GLOSSARY-COVERS-ATTRIBUTES

  lead_in: |
    Attribute '{{attribute_name}}' on entity '{{entity_name}}' is in
    domain-model.md but not in glossary.md. What's the one-sentence
    business meaning of this attribute?

  probes:
    - trigger: "answer restates the attribute name without defining it"
      ask: |
        A glossary entry has to add information beyond the name.
        What constraint, default, or business meaning applies that a
        reader couldn't guess from the name alone?

  good_example: |
    "`status`: enum, one of `active` / `archived`. Defaults to
     `active` on creation; the contributor toggles it."

  bad_example:
    answer: "status is the status of the item."
    rebuttal: |
      That doesn't say anything. What values can it take, what
      defaults, what triggers a change?

  reflect_template: |
    Adding glossary entry for '{{entity_name}}.{{attribute_name}}':
    {{summary}}. Sound right?

- id: MODEL-ENTITY-HAS-ID-TIMESTAMPS
  binds_to_check: MODEL-ENTITY-HAS-ID-TIMESTAMPS

  lead_in: |
    Entity '{{entity_name}}' is missing one or more of the baseline
    fields ({{missing_fields}}). Most entities need these — but some
    legitimately don't. What's the story for this one: are the fields
    just missing (resolve by adding) or genuinely not applicable
    (mark n-a with a reason)?

  probes:
    - trigger: "answer says the entity is immutable / append-only"
      ask: |
        Append-only is a fine reason to skip `updatedAt`. Capture
        that as the n-a reason: 'append-only, no updates supported'.
    - trigger: "answer says the entity has no identity"
      ask: |
        Then this might be a value object rather than an entity. Move
        it out of the Entities section and into a Value Objects
        section, or document the reason it stays.

  good_example: |
    "User has no updateable fields in v1 — registration is one-shot
     and role is immutable. Mark `updatedAt` as n-a, reason: 'no
     update flows in v1'."

  bad_example:
    answer: "Doesn't need them."
    rebuttal: |
      Why doesn't it need them? Specifically — name the design
      decision that makes them inapplicable. That decision is what
      goes in the n-a reason.

  reflect_template: |
    Marking '{{entity_name}}.{{field}}' as {{response}}: {{reason}}.
    Sound right?

- id: MODEL-ENTITY-BUSINESS-RULE
  binds_to_check: MODEL-ENTITY-BUSINESS-RULE

  lead_in: |
    Entity '{{entity_name}}' has no business rules listed. Most
    entities have at least one (uniqueness, immutability, defaults).
    What's the first business rule that applies — or is this entity a
    pure data carrier with no rules?

  probes:
    - trigger: "answer is 'no rules'"
      ask: |
        A pure data carrier is a legitimate case — but capture WHY
        explicitly. What makes this entity rule-free that a reviewer
        wouldn't otherwise guess?
    - trigger: "answer describes a constraint that's really an attribute type"
      ask: |
        That sounds like an attribute-level constraint (e.g. type,
        nullability). Business rules are usually about
        relationships, defaults, or invariants across attributes —
        is there one of those?

  good_example: |
    "Email must be unique across all users. Role is set at
     registration and cannot be changed via the API."

  bad_example:
    answer: "id must be a UUID."
    rebuttal: |
      That's an attribute type, not a business rule. Is there an
      invariant that spans the whole entity?

  reflect_template: |
    Adding business rules to '{{entity_name}}':
    {{summary}}
    Sound right?

- id: MODEL-LIFECYCLE-DEFINED
  binds_to_check: MODEL-LIFECYCLE-DEFINED

  lead_in: |
    Entity '{{entity_name}}' has a `status` attribute but no
    documented lifecycle. Is status a real state machine here (define
    the transitions) or just a flag with two unrelated values (mark
    n-a)?

  probes:
    - trigger: "answer says 'state machine'"
      ask: |
        Walk me through the transitions. What states exist, and what
        action moves between them?
    - trigger: "answer says 'just a flag'"
      ask: |
        OK to mark n-a — but capture the reason: 'status is a flag,
        not a state machine; values are independent and either may
        appear at creation'.

  good_example: |
    "Item: active ⟷ archived. PATCH /v1/items/{id} with status flips
     between them in either direction. No third state."

  bad_example:
    answer: "It's complicated."
    rebuttal: |
      Lifecycles are how we keep state changes auditable downstream
      (every transition becomes an event). Even a complicated one is
      worth drawing.

  reflect_template: |
    Adding lifecycle for '{{entity_name}}': {{summary}}. Sound right?

- id: MODEL-RELATIONSHIP-BIDIRECTIONAL
  binds_to_check: MODEL-RELATIONSHIP-BIDIRECTIONAL

  lead_in: |
    The relationship '{{lhs}} → {{rhs}}' has no reverse statement
    '{{rhs}} → {{lhs}}'. Is this genuinely one-way (e.g. an audit log
    referencing a thing without the thing knowing about its log
    entries) or just missing?

  probes:
    - trigger: "answer says 'add the reverse'"
      ask: |
        What's the reverse relationship's nature — 'belongs to',
        'is owned by', 'aggregates'? I'll capture that phrasing.
    - trigger: "answer says 'one-way is intentional'"
      ask: |
        Mark n-a with the reason: '{{rhs}} doesn't need to know about
        {{lhs}} because <X>'. Capture X.

  good_example: |
    "Item belongs to User (contributorId)."

  bad_example:
    answer: "It's implied."
    rebuttal: |
      Implied relationships drift. Make it explicit so downstream
      contracts can rely on the bidirectional shape.

  reflect_template: |
    Adding reverse relationship: '{{rhs}} → {{lhs}}' ({{kind}}).
    Sound right?
