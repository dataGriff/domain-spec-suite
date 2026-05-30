# Discovery question bank — Phase 1
#
# One entry per gate-check id (per SUITE-DESIGN §7.5). The runner loads
# this file as YAML, indexes by `binds_to_check`, and uses entries during
# the phase loop: ask `lead_in` → on a vague answer walk the `probes` →
# if still vague, defer or mark non-applicable → on a resolved answer,
# run `reflect_template` → on confirmation, write the edit and re-run
# the affected check.
#
# The file is YAML by content; the `.md` extension is named per
# SUITE-DESIGN §5 convention. Build-time coverage (in
# scripts/check_questions_coverage.py) fails if any gate-check id in
# any phase's gate.yaml lacks an entry here.

- id: PRD-PROBLEM-USER-PAIN
  binds_to_check: PRD-PROBLEM-USER-PAIN

  lead_in: |
    Walk me through the problem this domain solves. Who has it, what
    specifically goes wrong for them today, and why is that worth
    fixing?

  probes:
    - trigger: "answer leads with the solution shape ('we build an X that...')"
      ask: |
        That tells me what you're building. What's the user pain that
        makes you want to build it — the moment in their day where
        things go wrong?
    - trigger: "answer is generic ('users want efficiency', 'teams need visibility')"
      ask: |
        Generic phrasing hides the real pain. Pick one user and one
        moment — what specifically went wrong for them this week?
    - trigger: "answer names a market or competitor but no user"
      ask: |
        Markets don't have pains; people do. Who's the human user, and
        what happens to their day when this problem bites?

  good_example: |
    "Small teams who share a stockroom track items in spreadsheets.
     Read-only colleagues accidentally overwrite cells when they
     open the sheet to look. The team has no audit trail and can't
     tell who broke what."

  bad_example:
    answer: "Teams need better inventory tooling."
    rebuttal: |
      That's a product category, not a problem. What specifically goes
      wrong for one team with their current tools, in a way the new
      domain would fix?

  reflect_template: |
    So the core problem is: {{summary}}. Capturing that as the
    Problem Statement — sound right?

- id: PRD-PERSONA-EXISTS
  binds_to_check: PRD-PERSONA-EXISTS

  lead_in: |
    Who's the first user of this domain? Give me a role and a
    memorable name (e.g. 'Stockroom Lead — Sam').

  probes:
    - trigger: "answer names a system, team, or company instead of a person"
      ask: |
        Systems don't have frustrations; people do. Which individual
        role inside that team or system is the actual user?
    - trigger: "answer is a job title without a name"
      ask: |
        Add a memorable first name. We'll refer to them by name in
        every user story — it forces concrete thinking.

  good_example: |
    "Stockroom Lead — Sam. They add and curate every item the team
     shares."

  bad_example:
    answer: "The product team."
    rebuttal: |
      'The product team' is too broad to write stories against. Pick
      one role inside that team — the person who actually touches
      this domain day to day.

  reflect_template: |
    Capturing first persona as **{{persona_heading}}**. Want to add
    a second one now, or move on?

- id: PRD-PERSONA-GOAL
  binds_to_check: PRD-PERSONA-GOAL

  lead_in: |
    What specifically is {{persona_name}} trying to accomplish with
    this domain — in concrete terms a colleague would recognise?

  probes:
    - trigger: "answer is a verb without an object ('be productive', 'manage things')"
      ask: |
        Productive at what? Give me the specific task — the thing they
        do that this domain has to support.
    - trigger: "answer describes a feeling ('feel confident', 'have peace of mind')"
      ask: |
        Feelings are downstream of actions. What action would give them
        that feeling? Capture the action.

  good_example: |
    "Add new items as they come in, mark stale items archived, fix
     typos in names and descriptions, and trust that the catalogue
     reflects what's actually on the shelf."

  bad_example:
    answer: "Manage their inventory better."
    rebuttal: |
      'Better' isn't a goal. What specific tasks do they do with the
      inventory that aren't working today?

  reflect_template: |
    So {{persona_name}}'s goal is: {{summary}}. Capturing that as
    the Goal line — sound right?

- id: PRD-PERSONA-FRUSTRATION
  binds_to_check: PRD-PERSONA-FRUSTRATION

  lead_in: |
    What specifically frustrates {{persona_name}} about how they
    work today?

  probes:
    - trigger: "answer describes a desired feature rather than current pain"
      ask: |
        That sounds like a feature wish. What's the current pain that
        creates the wish — the moment in their day where things go
        wrong?
    - trigger: "answer is qualitative ('it's slow', 'annoying')"
      ask: |
        Slow at what task, and by how much? Give me a number if you
        can — even rough.
    - trigger: "answer is hypothetical ('they might', 'sometimes')"
      ask: |
        Has this happened? How often, in the last month?

  good_example: |
    "The shared sheet has been silently overwritten three times in
     the last quarter when colleagues opened it to look and
     accidentally edited a cell."

  bad_example:
    answer: "It's slow."
    rebuttal: |
      'Slow' doesn't help me write a frustration into the PRD. Slow
      at what task, and by how much?

  reflect_template: |
    So {{persona_name}} is frustrated by: {{summary}}. Capturing
    that as the Frustration line — sound right?

- id: PRD-NON-GOAL
  binds_to_check: PRD-NON-GOAL

  lead_in: |
    What's explicitly out of scope for this domain — the things you
    deliberately are NOT building? Naming them now protects later
    phases from scope creep.

  probes:
    - trigger: "answer claims 'nothing is out of scope' or 'everything's in'"
      ask: |
        There's always something. Adjacent products, more complex
        states, integrations — pick one thing a stakeholder might
        ask for that you'd push back on, and capture it.
    - trigger: "answer is a feature absence ('we don't have bulk export') rather than a scope boundary"
      ask: |
        Missing feature ≠ non-goal. Non-goals are categories of work
        you're deliberately refusing — 'we are not building an asset
        register'. What's the category-level boundary?

  good_example: |
    "A real vertical product. Items deliberately stays generic — it
     is not a stock-control system, an asset register, or an
     inventory platform."

  bad_example:
    answer: "Nothing — we want to keep options open."
    rebuttal: |
      Keeping options open is how scope creeps. What's the first
      thing you'd push back on if a stakeholder asked for it next
      quarter?

  reflect_template: |
    Adding non-goal: {{summary}}. Want to add another, or move on?

- id: PRD-STORY-ACCEPTANCE
  binds_to_check: PRD-STORY-ACCEPTANCE

  lead_in: |
    For {{story_id}} ('{{story_title}}'), what specifically needs to
    be true for the story to be 'done'? A criterion should be
    checkable by a reviewer without asking the author what they meant.

  probes:
    - trigger: "answer is a single 'it works' criterion"
      ask: |
        'Works' isn't checkable. Break it down: what API call returns
        what status? What event is published? What error code on
        which failure?
    - trigger: "answer mentions UI behaviour without API/event detail"
      ask: |
        This spec set is implementation-agnostic, so UI behaviour
        isn't a criterion. What's the contract-level evidence — the
        HTTP call, the event on the channel, the error code?

  good_example: |
    "POST /v1/items creates an item with status: active.
     The new item is associated with the authenticated contributor's
     id. Viewers cannot add items (403 with FORBIDDEN).
     An ItemAdded event is published on items.item.added."

  bad_example:
    answer: "The user can add an item."
    rebuttal: |
      That restates the story. What's checkable evidence the story is
      done — the endpoint, the status code, the event, the failure
      mode?

  reflect_template: |
    Adding acceptance criteria to {{story_id}}:
    {{summary}}
    Sound right?

- id: PRD-STORY-PERSONA-LINK
  binds_to_check: PRD-STORY-PERSONA-LINK

  lead_in: |
    {{story_id}} names actor '{{actor}}', but I don't recognise that
    as a persona declared in the PRD. Which persona is performing
    this action — or is the story actually for an actor we haven't
    captured yet?

  probes:
    - trigger: "answer renames an existing persona by accident"
      ask: |
        Sounds like you mean {{closest_persona}}. Want me to swap the
        story's actor to match, or rename the persona heading?
    - trigger: "answer describes a system actor (scheduler, webhook)"
      ask: |
        System actors are valid but they belong as a named system in
        the Constraints section, not as a persona. Capture it there
        instead?
    - trigger: "answer reveals a missing persona"
      ask: |
        Then we need to add the persona first. Give me a role and a
        memorable name, then I'll wire the story up to it.

  good_example: |
    "Yes, that's the Stockroom Lead — Sam. The story should say
     'As a stockroom lead'."

  bad_example:
    answer: "Doesn't matter, just pick one."
    rebuttal: |
      It matters — the persona is how downstream phases know what
      permissions and flows to build for. Which one is right?

  reflect_template: |
    Updating {{story_id}}'s 'As a ...' line to {{actor_resolved}}.
    Sound right?

- id: PRD-METRICS-MEASURABLE
  binds_to_check: PRD-METRICS-MEASURABLE

  lead_in: |
    For the metric '{{metric_summary}}', what's the specific number,
    count, or pass/fail check that would prove the metric was met?

  probes:
    - trigger: "answer is qualitative ('users are happy', 'team feels confident')"
      ask: |
        Feelings aren't metrics. What measurable signal would tell
        you, six months in, that the metric was hit?
    - trigger: "answer cites a number with no unit or timeframe"
      ask: |
        Number with no unit doesn't help. '10' what, measured how,
        over what window?

  good_example: |
    "Contract integrity: all three contract files validate against
     their respective linting rulesets without errors or warnings."

  bad_example:
    answer: "Users love the new system."
    rebuttal: |
      'Love' isn't measurable. NPS? Survey score? Retention curve?
      Pick the signal and the threshold.

  reflect_template: |
    Capturing metric as: {{summary}}. Sound right?
