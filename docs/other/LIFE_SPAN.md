FastAPI’s **lifespan cycle** is the framework’s way to let your application **run startup and shutdown logic in a single, well-defined async context**.

Think of it as:

> “Everything that should exist for the *entire lifetime* of the app goes here.”

---

## 1. What “lifespan” means conceptually

A FastAPI app has three phases:

```
┌────────────┐
│  Startup   │  ← create shared resources
├────────────┤
│  Running   │  ← handle requests
├────────────┤
│ Shutdown   │  ← clean up resources
└────────────┘
```

The **lifespan** API lets you describe **startup + shutdown together**, instead of splitting them into separate hooks.

---

## 2. The lifespan function (core idea)

A lifespan function is:

* **async**
* A **context manager**
* Runs once per application process

Minimal example:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    print("Starting up")
    yield
    # SHUTDOWN
    print("Shutting down")

app = FastAPI(lifespan=lifespan)
```

### Execution order

1. Code **before `yield`** → startup
2. App serves requests
3. Code **after `yield`** → shutdown

---

## 3. Why lifespan exists (vs `@app.on_event`)

Older FastAPI versions used:

```python
@app.on_event("startup")
async def startup(): ...

@app.on_event("shutdown")
async def shutdown(): ...
```

Problems with that model:

* Startup and shutdown logic were **disconnected**
* Resource pairing (open/close) was implicit
* Harder to reason about failures

### Lifespan fixes this by:

* Making resource lifetime explicit
* Using Python’s `with` semantics
* Matching how ASGI servers actually manage apps

**Status**:

* `@app.on_event` still works
* Lifespan is the **recommended** approach going forward

---

## 4. Typical real-world use cases

### Database connection pool

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = await create_pool()
    try:
        yield
    finally:
        await app.state.db.close()
```

### HTTP client

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient()
    yield
    await app.state.http.aclose()
```

### Caches, ML models, config loading, background tasks

Anything that is:

* Expensive to create
* Shared across requests
* Needs cleanup

---

## 5. Accessing lifespan resources

Resources are usually stored on `app.state`:

```python
from fastapi import Request

@app.get("/items")
async def items(request: Request):
    db = request.app.state.db
    ...
```

This keeps handlers stateless while still sharing infrastructure.

---

## 6. Error handling behavior

### If startup fails

* The app **never starts**
* Uvicorn exits
* No requests are served

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect()  # if this raises → app won’t start
    yield
```

### If shutdown fails

* Server is already stopping
* Errors are logged but requests are no longer served

---

## 7. Lifespan vs dependencies

| Use case               | Lifespan | Dependency |
| ---------------------- | -------- | ---------- |
| One global DB pool     | ✅        | ❌          |
| Per-request DB session | ❌        | ✅          |
| Load config once       | ✅        | ❌          |
| Auth per request       | ❌        | ✅          |

**Rule of thumb**:

* **Lifespan** → app-wide, long-lived
* **Dependencies** → request-scoped

---

## 8. Multiple lifespan concerns (composition)

You can compose lifespan logic:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with db_lifespan(app), http_lifespan(app):
        yield
```

Each sub-lifespan is itself an async context manager.

---

## 9. Relation to ASGI

FastAPI is ASGI-based. Under the hood:

* ASGI server sends `lifespan.startup`
* FastAPI runs code before `yield`
* ASGI server sends `lifespan.shutdown`
* FastAPI runs code after `yield`

This is why lifespan integrates cleanly with:

* Uvicorn
* Hypercorn
* Gunicorn + Uvicorn workers

---

## 10. Mental model (the key takeaway)

```python
async with app_lifespan():
    serve_requests()
```

That’s literally how FastAPI treats your app.

---

## Summary

* **Lifespan** defines the full lifetime of your FastAPI app
* It replaces most `startup` / `shutdown` event handlers
* It’s an async context manager with a single `yield`
* Use it for **shared, long-lived resources**
* Keep request-specific logic in dependencies
