# AGENTS.md

## Project goal

This repository contains a Master's Thesis software project for an audio-based
personal diary.

Read `docs/scope.md` and `docs/architecture.md` before implementing features.

Do not expand the scope without explicit approval.

## Development priorities

1. Make the smallest useful feature work end-to-end.
2. Prefer simple solutions over sophisticated architecture.
3. Do not add infrastructure unless a concrete requirement justifies it.
4. Do not introduce Kubernetes, Traefik, MinIO, RabbitMQ or similar components
   unless explicitly requested.
5. Keep components replaceable where this provides a clear practical benefit.
6. Avoid speculative abstractions.

## Incremental work

Work in small, reviewable steps.

Do not implement several major subsystems in a single task unless explicitly
requested.

Before a significant implementation:

- explain what will change;
- explain why it is needed;
- identify important dependencies.

After implementation, report:

1. what changed;
2. why it was implemented that way;
3. how the main pieces work;
4. how to test it;
5. which concepts the thesis author should understand to explain the change.

## Learning requirement

The project author is learning the technologies while developing the thesis.

Explanations must therefore be clear and concise.

Do not hide important architectural decisions behind generated code.

When introducing a new concept, explain it in Spanish using simple terminology
and relate it to the concrete project.

## Dependencies

Do not add a dependency merely for convenience.

Before adding an important dependency, explain:

- what problem it solves;
- why the standard library or an existing dependency is insufficient;
- important alternatives when relevant.

## Tests

Add automated tests for important behavior.

Prefer tests that demonstrate project requirements rather than tests created only
to increase coverage numbers.

## Security and privacy

Never commit secrets, API keys, real personal recordings or private
transcriptions.

Secrets belong in `.env`.

`.env.example` may contain variable names and example values but never real
credentials.

Audio and real personal data must remain ignored by Git.

External LLM use must be clearly separated from local processing.

## Git

Do not rewrite Git history.

Do not force push.

Do not commit unless explicitly requested.

Before proposing a commit, summarize the changes.

## Documentation

Keep `docs/architecture.md` consistent with the implemented architecture.

Do not silently modify `docs/scope.md`.

Changes to project scope require explicit approval.
