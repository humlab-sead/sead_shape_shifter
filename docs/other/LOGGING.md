# Logging Architecture

Shape Shifter uses a consolidated logging system with [loguru](https://github.com/Delgan/loguru) for structured, flexible logging across all components.

## Architecture Overview

### Backend API Logging
**Location**: `backend/app/core/logging_config.py`

The backend API uses centralized logging configuration initialized at application startup:

```python
from backend.app.core.logging_config import configure_logging

configure_logging(
    log_dir=settings.LOGS_DIR,
    log_level=settings.LOG_LEVEL,
    enable_file_logging=settings.LOG_FILE_ENABLED,
    enable_console_logging=settings.LOG_CONSOLE_ENABLED,
    rotation=settings.LOG_ROTATION,
    retention=settings.LOG_RETENTION,
    compression=settings.LOG_COMPRESSION,
)
```

**Features**:
- **Console logging**: Colored output with timestamps, module:function:line references
- **File logging**: Two separate files with automatic rotation and compression
  - `logs/app.log` - All logs (INFO and above)
  - `logs/error.log` - Only ERROR and CRITICAL logs
- **Full exception dumps**: `backtrace=True` and `diagnose=True` for complete stack traces
- **Thread-safe**: `enqueue=True` for async/multi-threaded safety
- **Rotation**: Automatically rotates at configurable size (default: 10 MB)
- **Retention**: Keeps logs for configurable period (default: 30 days)
- **Compression**: Rotated logs are compressed (default: zip)

**Configuration** (via environment variables with `SHAPE_SHIFTER_` prefix):
```bash
SHAPE_SHIFTER_LOG_LEVEL=DEBUG          # DEBUG, INFO, WARNING, ERROR, CRITICAL
SHAPE_SHIFTER_LOG_FILE_ENABLED=true    # Enable/disable file logging
SHAPE_SHIFTER_LOG_CONSOLE_ENABLED=true # Enable/disable console logging
SHAPE_SHIFTER_LOG_ROTATION=10 MB       # Size-based rotation
SHAPE_SHIFTER_LOG_RETENTION=30 days    # How long to keep old logs
SHAPE_SHIFTER_LOG_COMPRESSION=zip      # Compression format
SHAPE_SHIFTER_LOGS_DIR=./logs          # Log directory path
```

### CLI/Script Logging
**Location**: `src/utility.py::setup_logging()`

For standalone scripts, CLI tools, and core processing, use the simpler `setup_logging()` function:

```python
from src.utility import setup_logging

# Simple usage
setup_logging(verbose=True)  # DEBUG level with detailed format

# With log file
setup_logging(verbose=True, log_file="output/process.log")

# Normal mode (INFO level, simple format)
setup_logging()
```

**Features**:
- **Verbose mode**: DEBUG level with detailed format including module:function:line
- **Normal mode**: INFO level with simple message-only format
- **Message deduplication**: In normal mode, each unique message is logged only once per run
- **Optional file logging**: Can write to a file in addition to console
- **Full exception dumps**: Always enabled with `backtrace=True` and `diagnose=True`

**When to use**:
- Command-line scripts (e.g., `backend/app/scripts/ingest.py`)
- Core processing pipelines (e.g., `src/normalizer.py`)
- Test utilities
- Standalone tools

## Error Handling Integration

The backend uses a global exception handler in `backend/app/main.py` that automatically logs all unhandled exceptions with full tracebacks:

```python
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception during {request.method} {request.url.path}: {exc}")
    # ... return error response
```

Additionally, the `@handle_endpoint_errors` decorator in `backend/app/utils/error_handlers.py` provides structured error handling for API endpoints with automatic logging at appropriate levels:

- **404 errors**: `logger.debug()` - Not found errors (expected)
- **400/409 errors**: `logger.warning()` - Bad requests, conflicts
- **500 errors**: `logger.exception()` - Server errors with full traceback

## Log File Locations

```
logs/
├── app.log              # All application logs (rotated)
├── app.log.2026-01-30.zip  # Compressed rotated logs
├── error.log            # Error-level logs only (rotated)
└── error.log.2026-01-30.zip
```

## Usage Examples

### Backend Service
```python
from loguru import logger

class MyService:
    def process_data(self):
        logger.info("Starting data processing")
        try:
            # ... processing logic
            logger.debug(f"Processed {count} records")
        except Exception as e:
            logger.exception(f"Processing failed: {e}")
            raise
```

### CLI Script
```python
from loguru import logger
from src.utility import setup_logging

def main():
    setup_logging(verbose=True, log_file="output/my_script.log")
    
    logger.info("Script started")
    # ... script logic
    logger.info("Script completed")

if __name__ == "__main__":
    main()
```

### Endpoint Handler
```python
from loguru import logger
from backend.app.utils.error_handlers import handle_endpoint_errors

@router.post("/process")
@handle_endpoint_errors
async def process_endpoint(data: InputData):
    logger.info(f"Processing request with {len(data.items)} items")
    # Errors are automatically caught, logged, and converted to HTTPException
    result = await service.process(data)
    logger.debug(f"Processing result: {result}")
    return result
```

## Migration Notes

**Removed redundant code**:
- Old `configure_logging()` in `src/utility.py` (lines 265-298) - Replaced with `setup_logging()`
- Old `configure_logging()` in `ingesters/sead/utility.py` - Now uses `src.utility.setup_logging()`
- Updated `src/configuration/setup.py` to use `setup_logging()` instead

**Consolidated architecture**:
- **Backend API**: `backend/app/core/logging_config.py` - Full-featured with rotation, retention, compression
- **CLI/Scripts**: `src/utility.py::setup_logging()` - Simple, focused on developer experience
- **Error handling**: Integrated with FastAPI exception handlers for automatic logging

## Best Practices

1. **Use appropriate log levels**:
   - `DEBUG`: Detailed diagnostic information
   - `INFO`: General informational messages
   - `WARNING`: Warning messages (degraded functionality)
   - `ERROR`: Error messages (functionality impacted)
   - `CRITICAL`: Critical errors (system failure)

2. **Include context**: Add relevant details to log messages
   ```python
   logger.info(f"Processing entity '{entity_name}' with {row_count} rows")
   ```

3. **Use exception logging**: For caught exceptions, use `logger.exception()`
   ```python
   try:
       process_data()
   except Exception as e:
       logger.exception(f"Failed to process: {e}")
   ```

4. **Avoid logging sensitive data**: Never log passwords, tokens, or PII

5. **Use structured logging**: Include machine-readable context
   ```python
   logger.bind(entity=entity_name, row_count=row_count).info("Processing complete")
   ```

## Troubleshooting

**Logs not appearing**:
- Check `SHAPE_SHIFTER_LOG_LEVEL` environment variable
- Verify `SHAPE_SHIFTER_LOG_FILE_ENABLED=true`
- Ensure `logs/` directory is writable

**Log files too large**:
- Reduce `SHAPE_SHIFTER_LOG_RETENTION` value
- Decrease `SHAPE_SHIFTER_LOG_ROTATION` threshold
- Increase log level (INFO → WARNING → ERROR)

**Performance issues**:
- File logging is thread-safe (`enqueue=True`) but adds minimal overhead
- For high-throughput scenarios, consider disabling console logging
- Compression happens asynchronously and shouldn't impact performance

**Debugging issues**:
- Set `SHAPE_SHIFTER_LOG_LEVEL=DEBUG` for verbose output
- Check `logs/error.log` for full exception tracebacks
- Use `logger.bind()` to add context to related log messages
