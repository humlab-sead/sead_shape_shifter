# Integration Tests for Reconciliation Client

## Overview

Integration tests that connect to the **live** OpenRefine reconciliation service on port 8000.
These tests are marked with `@pytest.mark.integration` and are skipped by default.

## Prerequisites

The OpenRefine reconciliation service must be running on `localhost:8000`.

### Check if service is running:
```bash
# Check port
lsof -i :8000

# Or check with curl
curl http://localhost:8000/reconcile
```

## Running Integration Tests

### Run all integration tests:
```bash
cd /home/roger/source/sead_shape_shifter
source .venv/bin/activate
PYTHONPATH=.:backend uv run pytest backend/tests/test_reconciliation_client.py -v -s -m integration
```

### Run specific integration test:
```bash
# Connection diagnostics (most useful for debugging)
PYTHONPATH=.:backend uv run pytest backend/tests/test_reconciliation_client.py::TestReconciliationClientIntegration::test_live_connection_diagnostics -v -s -m integration

# Health check
PYTHONPATH=.:backend uv run pytest backend/tests/test_reconciliation_client.py::TestReconciliationClientIntegration::test_live_health_check -v -s -m integration

# Service manifest
PYTHONPATH=.:backend uv run pytest backend/tests/test_reconciliation_client.py::TestReconciliationClientIntegration::test_live_service_manifest -v -s -m integration

# Batch reconciliation
PYTHONPATH=.:backend uv run pytest backend/tests/test_reconciliation_client.py::TestReconciliationClientIntegration::test_live_reconcile_batch_single_query -v -s -m integration

# Entity suggestions
PYTHONPATH=.:backend uv run pytest backend/tests/test_reconciliation_client.py::TestReconciliationClientIntegration::test_live_suggest_entities -v -s -m integration
```

### Skip integration tests (default behavior):
```bash
# Run all tests except integration tests
PYTHONPATH=.:backend uv run pytest backend/tests/test_reconciliation_client.py -v -m "not integration"
```

## Available Integration Tests

### 1. `test_live_connection_diagnostics` ⭐ **Start Here**
**Most comprehensive diagnostic test** - performs multiple checks:
- DNS resolution for 'localhost'
- TCP connection to port 8000
- HTTP health check
- Detailed troubleshooting output

**Example output:**
```
=== Connection Diagnostics ===

1. DNS Resolution for 'localhost':
   ✓ Resolved to: 127.0.0.1

2. TCP Connection to localhost:8000:
   ✗ Port 8000 is CLOSED (error code: 111)

   Troubleshooting:
   - Check if service is running: lsof -i :8000
   - Check firewall rules
   - Verify service is bound to localhost:8000
```

### 2. `test_live_health_check`
Tests the health check endpoint and displays service status.

**Success output:**
```
=== Testing Health Check ===
Target: http://localhost:8000/reconcile
Timeout: 10.0s

Health Check Result:
  Status: online
  Service URL: http://localhost:8000
  Service Name: SEAD Reconciliation Service

✓ Service is ONLINE
```

**Failure output:**
```
Health Check Result:
  Status: offline
  Service URL: http://localhost:8000
  Error: All connection attempts failed

✗ Service is OFFLINE

Troubleshooting:
  1. Verify service is running: docker ps | grep reconcile
  2. Check service logs: docker logs <container_id>
  3. Verify port mapping: docker port <container_id>
  4. Test direct connection: curl http://localhost:8000/reconcile
```

### 3. `test_live_service_manifest`
Retrieves the service manifest showing supported entity types.

**Output:**
```
=== Testing Service Manifest ===

Manifest Retrieved:
  Service Name: SEAD Reconciliation Service
  Identifier Space: http://sead.se/entity/
  Schema Space: http://sead.se/schema/

  Supported Types (5):
    - Site: Archaeological Site
    - Taxon: Taxonomic Entity
    - Location: Geographic Location
    - Sample: Sample Record
    - Method: Analysis Method
    ... and 3 more

✓ Service manifest retrieved successfully
```

### 4. `test_live_reconcile_batch_single_query`
Tests actual batch reconciliation with a single test query.

**Output:**
```
=== Testing Batch Reconciliation ===

Query: 'Test Site'
Type: Site
Limit: 3

Reconciliation Result:
  Queries processed: 1
  Candidates found: 3

  Candidate 1:
    ID: https://w3id.org/sead/id/site/123
    Name: Test Site Alpha
    Score: 95.5
    Match: True

  Candidate 2:
    ID: https://w3id.org/sead/id/site/456
    Name: Test Site Beta
    Score: 85.0
    Match: False

✓ Batch reconciliation completed successfully
```

### 5. `test_live_suggest_entities`
Tests autocomplete/suggestion functionality.

## Checking Enhanced Logs

All integration tests produce detailed logs with the `[RECON]` prefix.

```bash
# Watch logs in real-time while running tests
tail -f logs/endpoint_errors.log | grep "\[RECON\]"

# View all reconciliation logs
grep "\[RECON\]" logs/endpoint_errors.log

# View only errors
grep "\[RECON\].*ERROR" logs/endpoint_errors.log
```

## Troubleshooting Common Issues

### Port 8000 is CLOSED
**Cause:** Service is not running or running on a different port.

**Solution:**
```bash
# Check what's running on port 8000
lsof -i :8000

# If using Docker, check container
docker ps | grep reconcile
docker port <container_id>

# Start the service (adjust command as needed)
docker-compose up reconciliation-service
```

### Connection Refused (errno 111)
**Cause:** No service listening on the port.

**Solution:** Start the OpenRefine reconciliation service.

### Connection Timeout
**Cause:** Service is overloaded or network issue.

**Solution:** 
- Check service logs for errors
- Increase timeout in test (default is 10s)
- Check network connectivity

### Service is OFFLINE but port is OPEN
**Cause:** Service is running but not responding correctly.

**Solution:**
- Check service logs: `docker logs <container_id>`
- Verify service health: `curl http://localhost:8000/reconcile`
- Restart the service

## Example Workflow

1. **Start with diagnostics:**
   ```bash
   PYTHONPATH=.:backend uv run pytest backend/tests/test_reconciliation_client.py::TestReconciliationClientIntegration::test_live_connection_diagnostics -v -s -m integration
   ```

2. **If diagnostics pass, test health check:**
   ```bash
   PYTHONPATH=.:backend uv run pytest backend/tests/test_reconciliation_client.py::TestReconciliationClientIntegration::test_live_health_check -v -s -m integration
   ```

3. **Test actual reconciliation:**
   ```bash
   PYTHONPATH=.:backend uv run pytest backend/tests/test_reconciliation_client.py::TestReconciliationClientIntegration::test_live_reconcile_batch_single_query -v -s -m integration
   ```

4. **Check logs for detailed traces:**
   ```bash
   grep "\[RECON\]" logs/endpoint_errors.log | tail -30
   ```

## Related Documentation

- [TRACE_LOGGING_GUIDE.md](TRACE_LOGGING_GUIDE.md) - Understanding enhanced logging
- [backend/tests/test_reconciliation_client.py](backend/tests/test_reconciliation_client.py) - Full test source code
