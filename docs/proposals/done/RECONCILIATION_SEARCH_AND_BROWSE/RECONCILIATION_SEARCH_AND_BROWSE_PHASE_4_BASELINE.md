# Reconciliation Search and Browse: Phase 4 Pilot Baseline

This record captures the initial Search/Browse measurements and per-capability decisions for the controlled pilot. It describes this workflow only and does not compare it with the previous workflow.

**Recorded:** 2026-11-21

**Environment:** `pilot-recon-2026-11-20`

Related documents: [approved proposal](./RECONCILIATION_SEARCH_AND_BROWSE.md), [Phase 1 task plan](./RECONCILIATION_SEARCH_AND_BROWSE_PHASE_1_TASK_PLAN.md), [Phase 4 plan](./RECONCILIATION_SEARCH_AND_BROWSE_PHASE_PLAN.md#phase-4-per-type-pilot-and-capability-release), and [Phase 4 task plan](./RECONCILIATION_SEARCH_AND_BROWSE_PHASE_4_TASK_PLAN.md).

## Environment and fixture

| Element | Value |
| --- | --- |
| Shape Shifter | `localhost/shape-shifter:pilot-7340510f`, revision `7340510ffb3d66ed150394605e1803ec196c7a08` |
| Authority Service | `localhost/sead-authority:pilot-1f3f1b8`, revision `1f3f1b8470e44b1d0730fb9d8b00e3318ec588eb` |
| Database | `sead_pilot_recon`, a 2026-11-20 snapshot of `sead_staging`; both services use the read-only `sead_ro` role |
| Network | Rootless Podman network `pilot-net`; Shape Shifter reaches Authority at `http://pilot-authority:8000` |
| Host endpoints | Authority `127.0.0.1:8025`; Shape Shifter `127.0.0.1:8026` |
| Fixture | `vm12-fixture`: 100 source rows per type, 10 matchable and 90 New, compound keys of width 2, and six duplicate labels per type |

The pilot's mounted Authority config enables all five capabilities for both types. The shipped Authority Service config keeps all five flags `false`. No shipped configuration was changed.

Raw run records are outside both repositories under `/data/roger/pilot-recon/measurements/`: `loopback.json`, `rtt-100.json`, `rtt-200.json`, `browse-rtt-100.json`, `browse-rtt-200.json`, `vm12-run.json`, `fixture-shape.txt`, `too-large.json`, and `verification-export.json`.

## Measurement methods

- **Search:** `scripts/pilot/measure_selection.py --runs 100` sent 100 measured requests per type after its 10-request warm-up, through the Shape Shifter backend. The configured p95 budget was 2,000 ms. The delay proxy added 50 ms or 100 ms one-way, approximately 100 ms or 200 ms round-trip, between the services.
- **Browse:** The VM-12 run timed 10 complete Browse responses per type at loopback. Additional runs timed 10 complete responses per type at each delayed RTT level through the backend. The response body was read before stopping the timer. The p95 calculation used the same percentile-index rule as the VM-12 script; with 10 samples, p95 is the maximum.
- **Decision times and requests:** `/data/roger/pilot-recon/scripts/run_vm12_scenarios.py` measured the decision save requests. Accepted-decision stage-and-save time is the measured save time plus the median search time. New-decision time is the measured save-request time. These values exclude human deliberation and browser action time. The script timed 10 accepted decisions and 89 of the 90 New saves per type; the remaining New save was not included in the timing sample.
- **Interactions:** The scripted keyboard path counts four explicit actions per accepted or New decision.
- **Preview and normalization:** The VM-12 script counted `ShapeShift preview for entity` log entries before and after the scenario. This is the available combined log measure, not separate preview and normalization counters.

Loopback timings are a lower bound for network latency. The proxy models fixed one-way delay on one host; it does not model packet loss, jitter, or an internet path.

## Search and Browse timings

Median and p95 are in milliseconds. Each Search harness row has 100 measured requests per type; each Browse row has 10.

| Operation | Approx. RTT | Type | Median | p95 |
| --- | ---: | --- | ---: | ---: |
| Search harness | Loopback | `feature_type` | 59.0 | 68.3 |
| Search harness | Loopback | `country` | 59.7 | 69.2 |
| Search harness | 100 ms | `feature_type` | 516.4 | 571.4 |
| Search harness | 100 ms | `country` | 516.1 | 571.0 |
| Search harness | 200 ms | `feature_type` | 967.8 | 1,070.9 |
| Search harness | 200 ms | `country` | 966.3 | 1,069.8 |
| VM-12 label Search | Loopback | `feature_type` | 59.7 | 68.5 |
| VM-12 label Search | Loopback | `country` | 149.8 | 166.3 |
| Browse | Loopback | `feature_type` | 73.6 | 84.6 |
| Browse | Loopback | `country` | 367.6 | 472.1 |
| Browse | 100 ms | `feature_type` | 515.2 | 599.0 |
| Browse | 100 ms | `country` | 651.4 | 665.9 |
| Browse | 200 ms | `feature_type` | 869.6 | 970.2 |
| Browse | 200 ms | `country` | 1,051.4 | 1,061.7 |

The VM-12 Search numbers use its fixture-label query mix and are separate from the Search harness results. Search p95 stayed below the 2,000 ms budget at all measured RTTs. The observed Search p95 slope is about 5 ms per added millisecond of RTT, implying an approximate 385 ms RTT envelope for that budget. This is an extrapolation from the one-host proxy measurements, not a measured WAN limit. No separate Browse p95 budget was defined.

## Decision timings and request counts

| Type | Decision | Saved | Timed | Mean time | p95 save time | Requests per decision | Interactions per decision |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `feature_type` | Accepted | 10 | 10 | 304.6 ms stage-and-save; 244.8 ms save only | Not recorded | 2 | 4 |
| `feature_type` | New | 90 | 89 | 89.2 ms save only | 132.8 ms | 1 | 4 |
| `country` | Accepted | 10 | 10 | 539.9 ms stage-and-save; 390.1 ms save only | Not recorded | 2 | 4 |
| `country` | New | 90 | 89 | 397.9 ms save only | 499.7 ms | 1 | 4 |

The VM-12 scenario issued 435 requests:

| Request | Count |
| --- | ---: |
| Preview `GET` | 6 |
| Browse `GET` | 20 |
| Search `POST` | 202 |
| Decision-save `POST` | 204 |
| Export `POST` | 3 |
| **Total** | **435** |

The scenario added 206 `ShapeShift preview for entity` log entries. The delayed Browse timing requests are separate from the VM-12 scenario request total.

## Projection, limits, and pilot outcomes

| Type | Complete Authority list | Authority bytes | Backend projection bytes |
| --- | ---: | ---: | ---: |
| `feature_type` | 156 rows | 29,336 | 32,675 |
| `country` | 266 rows | 29,699 | 38,211 |

Both lists reported `completeness: complete`. Lowering the row limit to 100 and the byte limit to 20,000 each returned HTTP 409 with no partial items for both types. Restoring the limits to 500 rows and 1,048,576 bytes returned HTTP 200 with all 156 and 266 items.

The VM-12 fixture run exported 10 accepted records per type, all with `verified` outcomes, and recorded 90 New approvals per type. It rejected a stale source value and a duplicate business key without saving either batch. During the Authority outage, Search returned 503 while New-only save and export still succeeded. Source identity was unchanged.

The browser checklist passed for both types on 2026-11-21 with no deviations. It covered ranked Search, exact-ID Search, Browse filtering and sorting, keyboard staging, New, Save versus Export, and reload behavior.

The no-write check recorded unchanged counts before and after retrieval and review: `authority.feature_type` 156, `authority.feature` 2,669, `authority.location` 3,404, and `public.tbl_locations` 3,404. An attempted insert failed with `permission denied for view feature_type`. The snapshot has no SIMS identity tables, so SIMS state was unchanged vacuously.

## Per-capability pilot decisions

Advertise each capability only in the isolated pilot. The pilot `GET /records/types` response reports all five flags enabled for both types; the shipped Authority Service config remains disabled.

| Capability | `feature_type` | `country` |
| --- | --- | --- |
| `search_supported` | Advertise in pilot: Search timing and browser checks passed (Phase 4 `V-1`, `V-8`). | Advertise in pilot: Search timing and browser checks passed (Phase 4 `V-1`, `V-8`). |
| `identifier_search_supported` | Advertise in pilot: exact `id:` lookup returned the requested target (Phase 4 `V-8`). | Advertise in pilot: exact `id:` lookup passed (Phase 4 `V-8`). |
| `browse_supported` | Advertise in pilot: complete list, both limit errors, filtering, sorting, and delayed timings passed (Phase 4 `V-5`, `V-6`, `V-8`). | Advertise in pilot: complete list, both limit errors, filtering, sorting, and delayed timings passed (Phase 4 `V-5`, `V-6`, `V-8`). |
| `details_supported` | Advertise in pilot: URI lookup for `feature_type/31` returned `Ditch`; the [Phase 1 task plan](./RECONCILIATION_SEARCH_AND_BROWSE_PHASE_1_TASK_PLAN.md) covers URI and numeric details. | Advertise in pilot: URI lookup for `country/205` returned `Sweden`; the [Phase 1 task plan](./RECONCILIATION_SEARCH_AND_BROWSE_PHASE_1_TASK_PLAN.md) covers URI and numeric details. |
| `export_verification_supported` | Advertise in pilot: valid IDs verified; unknown IDs blocked export without a sidecar write (Phase 4 `V-7`, `V-10`). | Advertise in pilot: valid IDs verified; unknown IDs blocked export without a sidecar write (Phase 4 `V-7`, `V-10`). |

The two URI detail checks were read-only requests to the pilot Authority endpoint on 2026-11-21. This decision does not enable capabilities for general use or change the shipped configuration.
