# NFRs question bank — Phase 5
#
# YAML by content; .md extension per SUITE-DESIGN §5 convention.

- id: NFR-THRESHOLD-MEASURABLE
  binds_to_check: NFR-THRESHOLD-MEASURABLE

  lead_in: |
    NFR '{{nfr_id}}' has no measurable threshold (no digit, percentage,
    time, or pXX percentile in the body). For this NFR: is it a real
    quantitative requirement that needs a number (resolve), a
    behavioural guarantee that's quantitative in a different sense
    (n-a with reason), or a placeholder that should move to
    _ambiguities.md (defer with required_by)?

  probes:
    - trigger: "answer is 'fast', 'scalable', 'robust' — vague adjectives"
      ask: |
        That's the aspirational language nfr.md explicitly bans.
        What's the number? p95 latency, percentage uptime, requests
        per second — pick the measurable form.
    - trigger: "answer describes a behavioural rule"
      ask: |
        Behavioural-but-not-numeric is a legitimate n-a here (e.g.
        'every event publish records its channel id'). Capture the
        n-a reason as 'behavioural guarantee, not threshold-bearing'.
    - trigger: "answer says 'we don't know yet'"
      ask: |
        Then it shouldn't live in nfr.md. Move the entry to
        _ambiguities.md with `required_by: <phase>` so the audit
        forces resolution before that phase.

  good_example: |
    "p95 read latency ≤ 150ms under 50 rps steady state against a 10k
     item catalogue."

  bad_example:
    answer: "The API should be fast."
    rebuttal: |
      'Fast' is exactly what nfr.md rejects. p95 in what units, under
      what load? Numbers please.

  reflect_template: |
    {{action}} for '{{nfr_id}}': {{detail}}. Sound right?

- id: ACCEPTANCE-SCENARIO-GWT
  binds_to_check: ACCEPTANCE-SCENARIO-GWT

  lead_in: |
    Scenario '{{scenario_id}}' is missing {{missing_keywords}} step(s).
    Every scenario needs at least a When (the action) and a Then (the
    observable outcome) inside a ```gherkin block — both are required
    for the scenario to be machine-consumable by downstream test
    suites. What's the missing step?

  probes:
    - trigger: "answer is unclear which step is missing"
      ask: |
        Walk me through the scenario as 'I do X, and then Y happens'.
        The 'I do X' is the When; the 'Y happens' is the Then. Both
        have to be in the block.

  good_example: |
    "When I POST /v1/items with name='X'. Then the response status
     is 201 and the body matches schema Item."

  bad_example:
    answer: "It's obvious."
    rebuttal: |
      Obvious to you, not to the test runner that'll lift these into
      a contract test suite. Write each step out.

  reflect_template: |
    Adding {{missing}} step to '{{scenario_id}}':
    {{summary}}
    Sound right?
