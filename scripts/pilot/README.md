# Pilot Measurement Scripts

Tools for the Phase 4 checks in
[RECONCILIATION_SEARCH_AND_BROWSE_PHASE_4_TASK_PLAN.md](../../docs/proposals/RECONCILIATION_SEARCH_AND_BROWSE/RECONCILIATION_SEARCH_AND_BROWSE_PHASE_4_TASK_PLAN.md).
They measure a running pilot pair; they do not start one.

The environment these numbers are recorded against is `pilot-recon-2026-11-20`,
described in the Phase 4 task plan.

## `measure_selection.py`

Times interactive record selection through the Shape Shifter backend and reports
median and p95 per pilot type against the 2,000 ms budget.

```bash
# Against a pilot on the default port
python3 scripts/pilot/measure_selection.py --runs 100 --label pilot-recon-2026-11-20

# Record the summary for the baseline
python3 scripts/pilot/measure_selection.py --runs 100 \
  --label pilot-recon-2026-11-20 \
  --json-out measurements/baseline.json
```

The script reads each type's labels from its complete browse list and builds a
query mix of whole labels, mid-label fragments, single words, and deliberate
non-matches. Ten requests are discarded as warm-up so first-request costs do not
enter the distribution. The exit code is zero only when every type meets the
budget, so the script can gate a check directly.

Two behaviors worth knowing when reading the output:

- `empty_results` counts searches that succeeded and matched nothing. Short
  fragments can fall below the configured label threshold, so a non-zero value is
  expected and is not an error.
- `failures` counts requests that did not return 200. Any non-zero value means the
  run describes a broken pair, not a slow one.

Both pilot types must exist in the target environment with the names in
`PILOT_SPECS`. Change that tuple, not the call sites, to measure a different pair.

## `delay_proxy.py`

Adds a fixed one-way delay to the Shape Shifter to Authority hop, so one host can
approximate a network path that is not loopback.

```bash
# On the pilot network, in front of the Authority Service
podman run -d --name pilot-delay --network pilot-net --user 0 \
  -v "$PWD/scripts/pilot/delay_proxy.py:/proxy/delay_proxy.py:ro" \
  python:3.13-slim python /proxy/delay_proxy.py \
  --listen 8000 --upstream pilot-authority:8000 --delay-ms 50
```

Point Shape Shifter at the proxy, then measure:

```bash
PILOT_AUTHORITY_URL=http://pilot-delay:8000 ./start-pair.sh
python3 scripts/pilot/measure_selection.py --runs 100 --label rtt-100ms
```

`--delay-ms` is one way, so the round trip is roughly double it. A 50 ms setting
models about 100 ms round trip. Label results by round trip, not by the flag
value, or the record will understate the path.

The proxy is measurement tooling. It must never sit on a deployed request path:
it forwards bytes without parsing them and will not scale or fail safely.

## Reading the results

Delay raises p95 roughly linearly while the service is healthy. If p95 grows much
faster than the added round trip, the run is measuring connection churn rather
than service time, which usually means the client opened a new connection per
request.

Reported figures describe the named pilot environment and its database snapshot.
They are not production numbers, and the phase does not compare them against the
previous workflow.
