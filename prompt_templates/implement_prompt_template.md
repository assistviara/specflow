# Codex Implementation Prompt Generation

You are generating an Implementation Prompt for Codex.

Use the approved Specification and approved Implementation Plan below as the authoritative implementation basis.

Do not invent requirements, decisions, implementation scope, allowed changes, or permissions that are not supported by the approved Specification or approved Implementation Plan.

You must not expand the approved Implementation Scope.

If implementation appears to require a change outside the approved scope, do not authorize Codex to perform it. The generated prompt must require Human Approval before any such change.

The generated prompt must not allow Codex to self-certify final Implementation Evidence. Codex may report execution results, but final evidence is constructed and verified outside Codex.

## Approved Specification

{{SPECIFICATION}}

## Approved Implementation Plan

{{IMPLEMENTATION_PLAN}}

## Implementation Target Path

{{IMPLEMENTATION_TARGET_PATH}}

## TDD Rules

{{TDD_RULES}}

## Completion Conditions

{{COMPLETION_CONDITIONS}}

## Stop Conditions

{{STOP_CONDITIONS}}

## Required Execution Result Reporting Requirements

{{EXECUTION_RESULT_REPORTING_REQUIREMENTS}}

Generate the Codex Implementation Prompt using exactly the following eight sections, in this order, with every section containing substantive content:

## Implementation Scope

State only the implementation scope supported by the approved Specification and approved Implementation Plan.

## Allowed Changes

State only changes that are permitted by the approved Specification and approved Implementation Plan.

## Forbidden Changes

State changes that are outside the approved scope or otherwise must not be performed.

## TDD Requirements

State the required TDD workflow and testing requirements.

## Completion Conditions

State the conditions that must be satisfied before Codex may report implementation work as complete.

## Stop Conditions

State conditions requiring Codex to stop rather than continue autonomously.

## Required Execution Result Reporting

State the execution results Codex must report, including the information required for later Implementation Evidence construction.

## Human Approval Required Conditions

State the conditions under which Codex must stop and request Human Approval before proceeding.

The generated prompt must remain traceable to the approved Specification and approved Implementation Plan supplied above.
