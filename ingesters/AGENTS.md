# Shape Shifter – Ingesters (`ingesters/`) Agent Rules

Rules here apply when working in `ingesters/`. Also read the root `AGENTS.md` for cross-cutting rules.

## Structure

- Each ingester lives in its own directory: `ingesters/<name>/`.
- Implement the protocol defined in `backend/app/ingesters/protocol.py`.
- Register with `@Ingesters.register(key="<name>")` — discovery is automatic via `IngesterRegistry.discover()`.
- Do not add manual imports into `backend/app/ingesters/__init__.py` unless the existing system requires it.

## Implementation Rules

- Keep `validate()` and `ingest()` responsibilities strictly separate.
- Return structured result types from both methods — do not raise for domain-level failures.
- Put ingester-specific settings in `IngesterConfig.extra` — do not extend `IngesterConfig` for one-off fields.
- Use explicit `IngesterConfig` values in tests — do not rely on `ConfigValue` or `ConfigStore` in test code.

## References

- Protocol and CLI details: `backend/app/ingesters/README.md` and `ingesters/README.md`.
- Prompt template: `.github/prompts/add-loader.prompt.md` (closest analogue for data-reading ingesters).

## Testing

- Mock external services and file I/O — do not hit real databases or APIs in unit tests.
- Test `validate()` and `ingest()` independently with explicit config fixtures.
- Use `@pytest.mark.asyncio` if the ingester is async.
