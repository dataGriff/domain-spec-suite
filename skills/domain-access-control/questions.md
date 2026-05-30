# Access Control question bank — Phase 3
#
# YAML by content; .md extension per SUITE-DESIGN §5 convention.

- id: AUTH-ROLE-HAS-DESCRIPTION
  binds_to_check: AUTH-ROLE-HAS-DESCRIPTION

  lead_in: |
    Role `{{role}}` has no description in the auth-matrix Roles table.
    What does this role mean — who is it for, what can they do, what
    can't they do?

  probes:
    - trigger: "answer just restates the role name"
      ask: |
        That's the name, not the meaning. What's the *purpose* of
        this role — what set of operations does it gate access to,
        and what's the user persona behind it?

  good_example: |
    "`contributor`: Can add items and edit/remove their own items."

  bad_example:
    answer: "A contributor."
    rebuttal: |
      A reviewer landing on this row needs to know what a contributor
      can DO. One concrete sentence on capabilities.

  reflect_template: |
    Setting role `{{role}}` description to: {{summary}}. Sound right?

- id: AUTH-MATRIX-COMPLETE
  binds_to_check: AUTH-MATRIX-COMPLETE

  lead_in: |
    Operation '{{operation}}' has no permission decision recorded for
    role '{{role}}' (empty cell). What's the decision — Public,
    Allowed, Allowed-if-owner, or Forbidden?

  probes:
    - trigger: "answer is 'I'm not sure'"
      ask: |
        Default to Forbidden if there's no clear reason to allow.
        Access control regressions ship most often when undecided
        cells default to 'allow' in the implementation.
    - trigger: "answer is conditional ('depends on...')"
      ask: |
        That sounds like 'Allowed-if-owner' or a special case
        capture in the Ownership Rule section. Which is it?

  good_example: |
    "Edit item × contributor: Allowed-if-owner (🔒 own). A
     contributor can only edit items where item.contributorId matches
     their user id."

  bad_example:
    answer: "Probably allowed."
    rebuttal: |
      'Probably' isn't a permission. Pick: Public / Allowed /
      Allowed-if-owner / Forbidden. If genuinely unclear, default to
      Forbidden and revisit when the use case sharpens.

  reflect_template: |
    Setting '{{operation}}' × '{{role}}' to {{decision}}. Sound right?

- id: ERROR-CATALOGUE-COMPLETE
  binds_to_check: ERROR-CATALOGUE-COMPLETE

  lead_in: |
    Error `{{code}}` is missing {{missing_fields}} in
    error-catalogue.md. Walk me through:
    — HTTP status this returns
    — One-sentence Meaning (what failed)
    — Triggered by (the conditions a caller hits to receive it)

  probes:
    - trigger: "answer mixes Meaning and Triggered-by"
      ask: |
        Keep them separate: Meaning is 'what's wrong from the
        caller's perspective'; Triggered-by is 'what they did or
        didn't do that hit this'.

  good_example: |
    "`INVALID_CREDENTIALS`. HTTP 401. Meaning: the email or password
     didn't match a known user. Triggered by: POST /v1/auth/login
     with a non-existent email, or a known email with the wrong
     password. (Indistinguishable, deliberately, to avoid
     enumeration.)"

  bad_example:
    answer: "It means bad creds."
    rebuttal: |
      Catalogue entries need full HTTP / Meaning / Triggered-by for
      contract reviewers and API consumers. Flesh out each.

  reflect_template: |
    Completing `{{code}}`:
    {{summary}}
    Sound right?

- id: ERROR-CODE-IN-CATALOGUE
  binds_to_check: ERROR-CODE-IN-CATALOGUE

  lead_in: |
    Error code `{{code}}` is referenced in {{source_file}} but doesn't
    appear in error-catalogue.md. Either add a catalogue entry for it,
    or rename the reference to an existing code. Which?

  probes:
    - trigger: "answer says 'add it'"
      ask: |
        Give me HTTP status / Meaning / Triggered-by so I can write
        the entry.

  good_example: |
    "Add it. `WALK_NOT_CANCELLABLE`. HTTP 409. Meaning: the walk is
     already in a terminal state (completed, declined, cancelled).
     Triggered by: POST /v1/walks/{id}/cancel on a non-cancellable
     walk."

  bad_example:
    answer: "It's the same as FORBIDDEN."
    rebuttal: |
      Then use FORBIDDEN in the reference, not a new code. Catalogue
      avoids duplication.

  reflect_template: |
    Adding `{{code}}` to error-catalogue.md: {{summary}}. Sound right?

- id: AUTH-ROLE-TRACES-TO-PERSONA
  binds_to_check: AUTH-ROLE-TRACES-TO-PERSONA

  lead_in: |
    Role `{{role}}` doesn't trace to a PRD persona and isn't marked
    as a system role. Which persona does this role serve — or is it a
    system role (e.g. scheduler, webhook receiver)?

  probes:
    - trigger: "answer is 'multiple personas'"
      ask: |
        Pick the primary one — the persona who motivated the role
        existing. Other personas with the same role can be noted in
        the Description.
    - trigger: "answer is 'it's a system role'"
      ask: |
        Add the word `system` to the 'Traces to persona' column
        (e.g. `system (webhook receiver)`). That's the canonical
        marker for a non-user role.

  good_example: |
    "`contributor` traces to Stockroom Lead (PRD §Target Users)."

  bad_example:
    answer: "Whoever needs it."
    rebuttal: |
      Roles exist BECAUSE a persona needs them. Which persona is the
      reason this role exists?

  reflect_template: |
    Setting '{{role}}' trace to: {{trace}}. Sound right?

- id: AUTH-MATRIX-OPENAPI-MATCH
  binds_to_check: AUTH-MATRIX-OPENAPI-MATCH

  lead_in: |
    This check fires only when contracts/openapi.yaml exists (Phase
    6+) and one of the auth-matrix operations doesn't have a matching
    OpenAPI path+method. At this phase (Access Control) it's
    typically skipped — but if you're here because of it, the
    operation '{{operation}}' has no matching contract entry. Is the
    operation name wrong, or is the contract missing it?

  probes:
    - trigger: "answer reveals a typo in either side"
      ask: |
        Which side is canonical — fix the other one. Auth-matrix
        operations are descriptive; openapi paths are the contract.
        Usually you fix the auth-matrix to match the contract.

  good_example: |
    "Typo in auth-matrix — 'POST /v1/item' should be '/v1/items'."

  bad_example:
    answer: "Just delete the auth-matrix row."
    rebuttal: |
      If the operation isn't in the contract, why is it in the
      auth-matrix? Resolve the inconsistency, don't paper over it.

  reflect_template: |
    Updating {{which_file}} to match: {{change}}. Sound right?
