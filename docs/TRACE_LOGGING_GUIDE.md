# Reconciliation Client - Enhanced Trace Logging Guide

## Overview

The reconciliation client now includes comprehensive trace logging to help diagnose connection failures and other issues. All logs use the `[RECON]` prefix for easy filtering.

## Log Levels

- **DEBUG**: Detailed operation traces (URLs, parameters, response parsing)
- **INFO**: Successful operations and milestones
- **ERROR**: Connection failures, timeouts, HTTP errors, and exceptions

## What Gets Logged

### 1. Client Initialization
```
[RECON] Creating new httpx.AsyncClient with timeout=30.0s
[RECON] Client created successfully for base_url=http://localhost:8000
```

### 2. Batch Reconciliation
```
[RECON] Starting batch reconciliation: 5 queries
[RECON] Query IDs: ['q0', 'q1', 'q2', 'q3', 'q4']
[RECON] Target URL: http://localhost:8000/reconcile
[RECON] Timeout: 30.0s
[RECON] Client obtained, making POST request...
[RECON] POST http://localhost:8000/reconcile
[RECON] Response received: status=200
[RECON] Response headers: {...}
[RECON] Response status OK
[RECON] Parsing response data...
[RECON] Response parsed successfully, 5 query results
[RECON] Batch reconciliation completed: 5 queries, 12 total candidates
```

### 3. Connection Errors
When the service is unreachable:
```
[RECON] Connection failed to http://localhost:8000: ConnectError: All connection attempts failed
[RECON] Connection error details: httpx._exceptions.ConnectError
[RECON] Underlying cause: OSError: [Errno 111] Connection refused
```

### 4. Timeout Errors
When requests exceed the timeout:
```
[RECON] Request timeout after 30.0s: TimeoutException
```

### 5. HTTP Status Errors
When the server returns an error status:
```
[RECON] HTTP error: 500 - Internal server error occurred while processing reconciliation request
```

### 6. Health Check
```
[RECON] Health check: http://localhost:8000/reconcile
[RECON] Sending GET request to health endpoint...
[RECON] Health check response: status=200
[RECON] Service is ONLINE: SEAD Reconciliation Service
```

Or when offline:
```
[RECON] Health check - Connection failed: ConnectError: [Errno 111] Connection refused
[RECON] Health check - Underlying cause: OSError: [Errno 111] Connection refused
```

## Filtering Logs

### View only reconciliation logs:
```bash
grep "\[RECON\]" logs/endpoint_errors.log
```

### View only errors:
```bash
grep "\[RECON\].*ERROR" logs/endpoint_errors.log
```

### View connection failures:
```bash
grep "\[RECON\].*Connection failed" logs/endpoint_errors.log
```

## Common Issues and What to Look For

### Issue: "All connection attempts failed"

**Look for these log entries:**
1. `[RECON] Target URL:` - Verify the URL is correct
2. `[RECON] Connection failed` - Shows the exact error type
3. `[RECON] Underlying cause:` - Shows the root OS-level error

**Common causes:**
- Service not running (Connection refused)
- Wrong port number
- Network firewall blocking connection
- Service bound to 127.0.0.1 instead of 0.0.0.0

**Example diagnosis:**
```
[RECON] Target URL: http://localhost:8000/reconcile
[RECON] Connection failed to http://localhost:8000: ConnectError
[RECON] Underlying cause: OSError: [Errno 111] Connection refused
```
→ The service is not running on port 8000

### Issue: Timeout

**Look for:**
- `[RECON] Timeout:` - Shows configured timeout
- `[RECON] Request timeout after` - Confirms timeout occurred

**Common causes:**
- Service running but overloaded
- Network latency
- Large dataset taking too long to process

### Issue: HTTP Errors (500, 404, etc.)

**Look for:**
- `[RECON] HTTP error:` - Shows status code and error message
- Response text excerpt for debugging

**Common causes:**
- Service internal error
- Wrong endpoint path
- Invalid query format

## Testing the Logging

Run the connection test to verify logging is working:
```bash
cd /home/roger/source/sead_shape_shifter
source .venv/bin/activate
PYTHONPATH=.:backend uv run pytest backend/tests/test_reconciliation_client.py::TestReconciliationClientConnection::test_connection_to_port_8000 -v -s
```

## Log File Location

All endpoint errors (including reconciliation) are logged to:
```
/home/roger/source/sead_shape_shifter/logs/endpoint_errors.log
```

The log file automatically rotates at 10 MB and keeps 30 days of history.
