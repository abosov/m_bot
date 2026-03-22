# US-AUTO-40 PROMPT 1

## Role

You are the System Architect + Workflow Designer + Developer + Tech Writer + QA for Zumbot, working under the CODEX Operating System workflow.

## Story

US-AUTO-40 — Review artifact fidelity to actual HEAD diff

## Context

The workflow already improved one important invariant in US-AUTO-39:

- review/gate is now HEAD-bound;
- stale checkout HEAD mismatch is rejected fail-closed;
- review gate result records `reviewed_head` and `checkout_head`.

That solved "wrong HEAD" approval.

A new integrity gap remains:

- review artifacts can still describe a change set that does not fully match the actual branch HEAD diff;
- artifact content may become stale after follow-up commits or partial bundle updates;
- review may therefore operate on an incomplete or misleading narrative of the real branch delta.

This story is about **artifact fidelity to actual HEAD diff**.

## Objective

Design and implement a strict workflow contract ensuring that review artifacts used by the review/gate flow are faithful to the actual code under review.

The contract must make the actual branch diff the authoritative technical reality and prevent approval when review artifacts materially drift from that reality.

## Required Design Principles

1. **Actual diff is authoritative**
   The workflow must have one clear authoritative diff for review, based on the real branch comparison against base (normally `origin/main...HEAD`, unless the current automation contract already defines a tighter equivalent).

2. **Fail closed**
   If review artifacts are stale, partial, or materially inconsistent with the authoritative diff, review/gate must reject or fail rather than silently continue.

3. **No duplicate competing truth**
   Do not introduce a second ambiguous contract for "what is being reviewed".
   The implementation should clarify and enforce one authoritative relationship between:
   - actual git diff
   - review artifacts
   - review/gate decision

4. **Minimal blast radius**
   Keep the solution tightly scoped to artifact fidelity.
   Do not try to solve the broader "single source of truth for