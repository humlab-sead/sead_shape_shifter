# """This is a minimal Dependency Injection (DI) container supporting:
# - sync + async providers and targets
# - yield + async-yield providers with teardown
# - per-call cache + app cache
# - overrides
# - type-based injection via bind_type()
# - app lifecycle: startup()/shutdown()

# Lifecycle semantics:
# - call-scoped yield providers are torn down at end of call()/acall()
# - app-scoped yield providers are torn down at shutdown()
# - app-scoped caching persists across calls until shutdown()/clear_app_cache()

# Usage:
# ```python
# from configuration.di import DI, Depends
# di = DI()
# di.startup()  # optional explicit startup
# di.bind_type(Repo)  # type-based injection
# di.bind_type(Service)
# result = di.call(handler)  # sync call
# result = await di.acall(async_handler)  # async call
# await di.ashutdown()  # proper async shutdown
# ```

# Note! This is a ChatGPT-generated minimal DI container for demonstration and internal use.

# It's NOT used by Shape Shifter itself, which relies on FastAPI's DI system.

# This is a prototype that may be included in the src/configuration module for internal use in the future.


# """

# from __future__ import annotations

# import inspect
# from contextlib import AsyncExitStack, ExitStack
# from dataclasses import dataclass
# from types import UnionType
# from typing import Any, Callable, Dict, Optional, TypeVar, get_args, get_origin

# T = TypeVar("T")


# @dataclass(frozen=True)
# class Depends:
#     provider: Callable[..., Any]
#     use_cache: bool = True
#     scope: str = "call"  # "call" or "app"


# class DI:
#     """
#     Minimal DI container with:
#       - Depends(provider, scope="call"|"app")
#       - sync + async targets/providers
#       - yield + async-yield providers with teardown
#       - per-call cache + app cache
#       - overrides
#       - type-based injection via bind_type()
#       - app lifecycle: startup()/shutdown()

#     Lifecycle semantics:
#       - call-scoped yield providers are torn down at end of call()/acall()
#       - app-scoped yield providers are torn down at shutdown()
#       - app-scoped caching persists across calls until shutdown()/clear_app_cache()
#     """

#     def __init__(self) -> None:
#         self._overrides: Dict[Callable[..., Any], Callable[..., Any]] = {}
#         self._type_bindings: Dict[type, Callable[..., Any]] = {}

#         self._app_cache: Dict[Callable[..., Any], Any] = {}

#         # App-lifetime teardown stacks
#         self._app_stack: Optional[ExitStack] = None
#         self._app_astack: Optional[AsyncExitStack] = None

#     # -------- Configuration --------

#     def override(self, provider: Callable[..., Any], with_: Callable[..., Any]) -> None:
#         self._overrides[provider] = with_

#     def clear_overrides(self) -> None:
#         self._overrides.clear()

#     def bind_type(self, typ: type, provider: Callable[..., Any] | None = None) -> None:
#         self._type_bindings[typ] = provider or typ

#     def clear_app_cache(self) -> None:
#         self._app_cache.clear()

#     # -------- Lifecycle --------

#     def startup(self) -> None:
#         """
#         Prepare app-lifetime teardown stacks.
#         Call once at process/app startup.
#         """
#         if self._app_stack is None:
#             self._app_stack = ExitStack()
#         if self._app_astack is None:
#             self._app_astack = AsyncExitStack()

#     async def astartup(self) -> None:
#         """
#         Async startup for symmetry. Currently just ensures stacks exist.
#         """
#         self.startup()

#     def shutdown(self) -> None:
#         """
#         Close app-lifetime teardown stacks and clear app cache.
#         Call once at process/app shutdown.
#         """
#         # Close sync teardown stack
#         if self._app_stack is not None:
#             self._app_stack.close()
#             self._app_stack = None

#         # Async teardown stack must be closed from async context.
#         if self._app_astack is not None:
#             raise RuntimeError("Use `await di.ashutdown()` to close async app resources.")

#         self._app_cache.clear()

#     async def ashutdown(self) -> None:
#         """
#         Close async app-lifetime teardown stack (and sync stack too).
#         """
#         if self._app_stack is not None:
#             self._app_stack.close()
#             self._app_stack = None

#         if self._app_astack is not None:
#             await self._app_astack.aclose()
#             self._app_astack = None

#         self._app_cache.clear()

#     # -------- Public API --------

#     def call(self, target: Callable[..., T], /, **runtime_kwargs: Any) -> T:
#         call_cache: Dict[Callable[..., Any], Any] = {}
#         with ExitStack() as call_stack:
#             return self._resolve_and_call_sync(target, runtime_kwargs, call_cache, call_stack)

#     async def acall(self, target: Callable[..., Any], /, **runtime_kwargs: Any) -> Any:
#         call_cache: Dict[Callable[..., Any], Any] = {}
#         async with AsyncExitStack() as call_astack:
#             return await self._resolve_and_call_async(target, runtime_kwargs, call_cache, call_astack)

#     # -------- Internals: common helpers --------

#     def _normalize_annotation(self, ann: Any) -> Optional[type]:
#         if ann is inspect._empty:
#             return None

#         origin = get_origin(ann)

#         if origin is None:
#             return ann if isinstance(ann, type) else None

#         # Covers Optional[T] and T | None
#         if origin is UnionType:
#             args = get_args(ann)
#             non_none = [a for a in args if a is not type(None)]
#             if len(non_none) == 1 and isinstance(non_none[0], type):
#                 return non_none[0]
#             return None

#         return None

#     def _get_cache_for_scope(
#         self,
#         scope: str,
#         call_cache: Dict[Callable[..., Any], Any],
#     ) -> Dict[Callable[..., Any], Any]:
#         if scope == "call":
#             return call_cache
#         if scope == "app":
#             return self._app_cache
#         raise ValueError(f"Unknown scope '{scope}'. Use 'call' or 'app'.")

#     def _get_stack_for_scope_sync(self, scope: str, call_stack: ExitStack) -> ExitStack:
#         if scope == "call":
#             return call_stack
#         if scope == "app":
#             if self._app_stack is None:
#                 # Lazy-init for convenience (but explicit startup() is recommended)
#                 self._app_stack = ExitStack()
#             return self._app_stack
#         raise ValueError(f"Unknown scope '{scope}'. Use 'call' or 'app'.")

#     def _get_stack_for_scope_async(self, scope: str, call_astack: AsyncExitStack) -> AsyncExitStack:
#         if scope == "call":
#             return call_astack
#         if scope == "app":
#             if self._app_astack is None:
#                 # Lazy-init for convenience (but explicit astartup() is recommended)
#                 self._app_astack = AsyncExitStack()
#             return self._app_astack
#         raise ValueError(f"Unknown scope '{scope}'. Use 'call' or 'app'.")

#     # -------- Sync resolution --------

#     def _resolve_and_call_sync(
#         self,
#         target: Callable[..., Any],
#         runtime_kwargs: Dict[str, Any],
#         call_cache: Dict[Callable[..., Any], Any],
#         call_stack: ExitStack,
#     ) -> Any:
#         target = self._overrides.get(target, target)

#         if inspect.iscoroutinefunction(target) or inspect.isasyncgenfunction(target):
#             raise TypeError(f"Async callable {target} encountered; use `await di.acall(...)`.")

#         sig = inspect.signature(target)
#         kwargs: Dict[str, Any] = {}

#         for name, param in sig.parameters.items():
#             if name in runtime_kwargs:
#                 kwargs[name] = runtime_kwargs[name]
#                 continue

#             default = param.default

#             if isinstance(default, Depends):
#                 kwargs[name] = self._resolve_provider_sync(default, runtime_kwargs, call_cache, call_stack)
#                 continue

#             if default is not inspect._empty:
#                 kwargs[name] = default
#                 continue

#             ann = self._normalize_annotation(param.annotation)
#             if ann in self._type_bindings:
#                 dep = Depends(self._type_bindings[ann], scope="call")
#                 kwargs[name] = self._resolve_provider_sync(dep, runtime_kwargs, call_cache, call_stack)
#                 continue

#             raise TypeError(f"Missing required argument '{name}' for {target}")

#         return target(**kwargs)

#     def _resolve_provider_sync(
#         self,
#         dep: Depends,
#         runtime_kwargs: Dict[str, Any],
#         call_cache: Dict[Callable[..., Any], Any],
#         call_stack: ExitStack,
#     ) -> Any:
#         provider = self._overrides.get(dep.provider, dep.provider)
#         cache = self._get_cache_for_scope(dep.scope, call_cache)

#         if dep.use_cache and provider in cache:
#             return cache[provider]

#         if inspect.iscoroutinefunction(provider) or inspect.isasyncgenfunction(provider):
#             raise TypeError(f"Async provider {provider} encountered; use `await di.acall(...)`.")

#         scope_stack = self._get_stack_for_scope_sync(dep.scope, call_stack)
#         value = self._enter_provider_sync(provider, runtime_kwargs, call_cache, scope_stack)

#         if dep.use_cache:
#             cache[provider] = value
#         return value

#     def _enter_provider_sync(
#         self,
#         provider: Callable[..., Any],
#         runtime_kwargs: Dict[str, Any],
#         call_cache: Dict[Callable[..., Any], Any],
#         scope_stack: ExitStack,
#     ) -> Any:
#         if inspect.isgeneratorfunction(provider):
#             gen = self._resolve_and_call_sync(provider, runtime_kwargs, call_cache, scope_stack)
#             try:
#                 value = next(gen)
#             except StopIteration:
#                 raise RuntimeError(f"Yield provider {provider} did not yield a value")
#             scope_stack.callback(gen.close)
#             return value

#         return self._resolve_and_call_sync(provider, runtime_kwargs, call_cache, scope_stack)

#     # -------- Async resolution --------

#     async def _resolve_and_call_async(
#         self,
#         target: Callable[..., Any],
#         runtime_kwargs: Dict[str, Any],
#         call_cache: Dict[Callable[..., Any], Any],
#         call_astack: AsyncExitStack,
#     ) -> Any:
#         target = self._overrides.get(target, target)

#         sig = inspect.signature(target)
#         kwargs: Dict[str, Any] = {}

#         for name, param in sig.parameters.items():
#             if name in runtime_kwargs:
#                 kwargs[name] = runtime_kwargs[name]
#                 continue

#             default = param.default

#             if isinstance(default, Depends):
#                 kwargs[name] = await self._resolve_provider_async(default, runtime_kwargs, call_cache, call_astack)
#                 continue

#             if default is not inspect._empty:
#                 kwargs[name] = default
#                 continue

#             ann = self._normalize_annotation(param.annotation)
#             if ann in self._type_bindings:
#                 dep = Depends(self._type_bindings[ann], scope="call")
#                 kwargs[name] = await self._resolve_provider_async(dep, runtime_kwargs, call_cache, call_astack)
#                 continue

#             raise TypeError(f"Missing required argument '{name}' for {target}")

#         result = target(**kwargs)
#         if inspect.isawaitable(result):
#             return await result
#         return result

#     async def _resolve_provider_async(
#         self,
#         dep: Depends,
#         runtime_kwargs: Dict[str, Any],
#         call_cache: Dict[Callable[..., Any], Any],
#         call_astack: AsyncExitStack,
#     ) -> Any:
#         provider = self._overrides.get(dep.provider, dep.provider)
#         cache = self._get_cache_for_scope(dep.scope, call_cache)

#         if dep.use_cache and provider in cache:
#             return cache[provider]

#         scope_astack = self._get_stack_for_scope_async(dep.scope, call_astack)
#         value = await self._enter_provider_async(provider, runtime_kwargs, call_cache, scope_astack)

#         if dep.use_cache:
#             cache[provider] = value
#         return value

#     async def _enter_provider_async(
#         self,
#         provider: Callable[..., Any],
#         runtime_kwargs: Dict[str, Any],
#         call_cache: Dict[Callable[..., Any], Any],
#         scope_astack: AsyncExitStack,
#     ) -> Any:
#         if inspect.isasyncgenfunction(provider):
#             agen = await self._resolve_and_call_async(provider, runtime_kwargs, call_cache, scope_astack)
#             try:
#                 value = await agen.__anext__()
#             except StopAsyncIteration:
#                 raise RuntimeError(f"Async-yield provider {provider} did not yield a value")
#             scope_astack.push_async_callback(agen.aclose)
#             return value

#         if inspect.isgeneratorfunction(provider):
#             gen = await self._resolve_and_call_async(provider, runtime_kwargs, call_cache, scope_astack)
#             try:
#                 value = next(gen)
#             except StopIteration:
#                 raise RuntimeError(f"Yield provider {provider} did not yield a value")

#             async def _close() -> None:
#                 gen.close()

#             scope_astack.push_async_callback(_close)
#             return value

#         result = await self._resolve_and_call_async(provider, runtime_kwargs, call_cache, scope_astack)
#         if inspect.isawaitable(result):
#             result = await result
#         return result


# # ---------------------------
# # Example usage
# # ---------------------------
# """Example usage of DI container.

# def get_config() -> dict:
#     print("config built")
#     return {"dsn": "postgresql://localhost/db"}

# def get_pool(config: dict = Depends(get_config, scope="app")):
#     print("SETUP pool", config["dsn"])
#     pool = {"pool_for": config["dsn"]}
#     try:
#         yield pool
#     finally:
#         print("TEARDOWN pool")

# def get_db(pool: dict = Depends(get_pool, scope="app")):
#     print("SETUP db (borrows from pool)")
#     db = {"connected_to": pool["pool_for"]}
#     try:
#         yield db
#     finally:
#         print("TEARDOWN db")

# class Repo:
#     def __init__(self, db: dict = Depends(get_db)):  # per-call by default (but db is app-scoped above)
#         self.db = db

# class Service:
#     def __init__(self, repo: Repo):
#         self.repo = repo

# def handler(svc: Service) -> str:
#     return f"dsn={svc.repo.db['connected_to']}"

# async def get_client():
#     print("SETUP async client")
#     client = object()
#     try:
#         yield client
#     finally:
#         print("TEARDOWN async client")

# async def async_handler(svc: Service, client: object = Depends(get_client, scope="app")) -> dict:
#     return {"dsn": svc.repo.db["connected_to"], "client": str(type(client))}


# if __name__ == "__main__":
#     di = DI()

#     # Recommended: explicit lifecycle hooks
#     di.startup()

#     # Type-based injection bindings
#     di.bind_type(Repo)
#     di.bind_type(Service)

#     print(di.call(handler))
#     print(di.call(handler))  # app-scoped pool/db not rebuilt

#     import asyncio
#     print(asyncio.run(di.acall(async_handler)))

#     # Proper async shutdown closes async app-scoped resources too
#     asyncio.run(di.ashutdown())
# """
