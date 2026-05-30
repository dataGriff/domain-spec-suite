# Flows question bank — Phase 4
#
# YAML by content; .md extension per SUITE-DESIGN §5 convention.

- id: FLOW-DIAGRAM-HAS-TITLE-PARTICIPANTS
  binds_to_check: FLOW-DIAGRAM-HAS-TITLE-PARTICIPANTS

  lead_in: |
    Flow '{{flow_title}}' has no `participant` declarations in its
    diagram. Every sequence diagram needs explicit participants so a
    reader can tell who's involved before tracing the arrows. Who are
    the participants in this flow?

  probes:
    - trigger: "answer is one actor only"
      ask: |
        A sequence diagram with one participant isn't a sequence —
        it's a note. What's the second actor it's interacting with?
        Usually `API` for an inbound call, `EventBus` for a publish,
        or another role/system for a multi-party flow.

  good_example: |
    "Client, API, EventBus."

  bad_example:
    answer: "The user."
    rebuttal: |
      The user does what — interacts with the API? The other
      participant is what makes this a sequence.

  reflect_template: |
    Adding participants to '{{flow_title}}': {{participants}}.
    Sound right?

- id: FLOW-PARTICIPANT-IS-ROLE-OR-SYSTEM
  binds_to_check: FLOW-PARTICIPANT-IS-ROLE-OR-SYSTEM

  lead_in: |
    Participant '{{participant}}' isn't a known role from the auth
    matrix, a persona from the PRD, or a recognised system actor
    (API, EventBus, Worker, DB, etc.). Is it a real external system
    the spec set should name properly, or domain-specific
    infrastructure that's fine to leave as-is (mark n-a)?

  probes:
    - trigger: "answer reveals a typo'd role name"
      ask: |
        Fix the participant name to match the auth-matrix role.
        Mismatched casing causes downstream confusion.
    - trigger: "answer names a real external system"
      ask: |
        Capture it: add a brief note in the flow prose ('PaymentProvider
        — Stripe's webhook endpoint') so a reader knows what kind of
        external thing it is.

  good_example: |
    "It's a typo — should be `EventBus`, not `eventbus`."

  bad_example:
    answer: "Just leave it."
    rebuttal: |
      Either it's recognised or it's documented. Pick: rename to
      match a known actor, or mark n-a with a one-line note on
      what it is.

  reflect_template: |
    {{action}} for participant '{{participant}}': {{detail}}.
    Sound right?

- id: STORY-HAS-FLOW
  binds_to_check: STORY-HAS-FLOW

  lead_in: |
    The user-story group '{{group}}' ({{stories}}) has no matching
    flow in sequence-diagrams.md. For each story in this group, is
    the interaction shape obvious enough to be skipped (mark n-a) or
    does it deserve a flow (resolve by drafting one)?

  probes:
    - trigger: "answer says 'covered by Flow N'"
      ask: |
        Then either rename Flow N's title to mention the group
        explicitly, or add the US-ids to Flow N's prose. The check
        passes when the cross-reference is explicit.
    - trigger: "answer says 'too trivial for a flow'"
      ask: |
        Mark n-a with a reason like 'the story is a simple GET
        with no multi-step interaction'. Reviewers know not to look
        for a flow then.

  good_example: |
    "Authentication is already covered by Flow 1 — rename Flow 1's
     title to 'Authentication — Register and Log In' so the
     cross-reference is explicit."

  bad_example:
    answer: "Skip it."
    rebuttal: |
      'Skip' doesn't tell a reviewer why. Either the group is
      covered (point at the flow) or it's genuinely trivial (mark
      n-a with reason).

  reflect_template: |
    {{action}} for story-group '{{group}}': {{detail}}.
    Sound right?

- id: LIFECYCLE-IN-FLOWS
  binds_to_check: LIFECYCLE-IN-FLOWS

  lead_in: |
    The lifecycle transition '{{from_state}} → {{to_state}}' for
    '{{entity}}' isn't shown in any flow. Either the transition is
    triggered by an operation that should appear in a flow (resolve)
    or it's a system-internal transition (e.g. an expiry job) that
    doesn't have a sequence shape (mark n-a with reason).

  probes:
    - trigger: "answer names a trigger that already appears in another flow"
      ask: |
        Add a Note in that flow that mentions the lifecycle
        transition explicitly. Something like 'Note over API:
        order moves from pending → confirmed'.

  good_example: |
    "The active → archived transition is triggered by PATCH
     /v1/items, which appears in Flow 2. Add a Note about the
     lifecycle change there."

  bad_example:
    answer: "It just happens."
    rebuttal: |
      'Just happens' isn't auditable. Either something triggers it
      (add to the flow that contains the trigger) or it's a system-
      internal job (mark n-a, document it).

  reflect_template: |
    {{action}} for transition '{{from_state}} → {{to_state}}':
    {{detail}}. Sound right?
