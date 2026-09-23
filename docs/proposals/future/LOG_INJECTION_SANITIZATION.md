# Log Injection Sanitization

## Status

- Future proposal / not yet approved
- Scope: backend application log records (`backend/app/core/logging_config.py`)
- Goal: prevent user-supplied newlines from forging application log records
- Related: [DEPLOYMENT_VERIFICATION_HANDOFF.md](../CENTRALIZED_AUTHORIZATION_CUTOVER/DEPLOYMENT_VERIFICATION_HANDOFF.md) "Log review" check

## Summary

Strip or escape control characters in every logged message before it reaches a loguru sink, and prove it with a test, so one logged value always produces exactly one record line.

## Problem

`configure_logging()` adds loguru handlers whose `format` writes `{message}` verbatim. Loguru does not escape newlines in messages, so any endpoint, mapper, or loader that logs user-supplied data can inject a forged line into `app.log` or `error.log`. This undermines the handoff's requirement that "user-supplied newlines cannot forge a record".

## Recommended change

Add a loguru `filter` (or a patcher applied in `configure_logging`) that replaces `\r`, `\n`, and other C0 control characters in `record["message"]` with a visible escape such as `\n`, before the message reaches the sink.

## Validation

- A test that logs a value containing `\n` and asserts the log file holds exactly one line for that record and no injected line.
- The existing backend logging tests still pass.

## Non-Goals

- Changing log levels, rotation, retention, or the filtered-traceback behavior.
- Sanitizing nginx or PostgreSQL logs, which have their own access controls and formats.
