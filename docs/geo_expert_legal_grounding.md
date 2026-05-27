# Geo Expert Legal Grounding

Geo Expert v1.6 adds grounded legal review helpers on top of real legal text corpora.

## What It Does

- parses legal citations from retrieved legal text
- extracts law name, article number, paragraph/item markers, and penalty phrases
- maps user requests and workflows to issue tags
- builds applicability checklists
- produces expert-review-draft legal sections for reports

## What It Does Not Do

- it does not produce a formal legal opinion
- it does not determine that a site is definitively illegal
- it does not replace field verification, parcel review, or lawyer / official review

## Main Outputs

- `issue_tags`
- `citations`
- `applicability_checklist`
- `facts_available`
- `facts_missing`
- `human_review_required = true`

## Formality Boundary

Use the legal grounding output as:

- `preliminary_screening`
- `expert_review_draft`
- `not_official_decision`

Do not use it as:

- final enforcement decision
- official legal conclusion
- final penalty decision
