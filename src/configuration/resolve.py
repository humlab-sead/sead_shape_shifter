from __future__ import annotations

import copy
import dataclasses
import re
from pathlib import Path
from typing import Any, Protocol

import yaml
from dotenv import load_dotenv
from loguru import logger

from src.path_resolution import resolve_contained_path
from src.utility import Registry, dget, dotexists, dotexpand, dotget, replace_env_vars

from .utility import is_path_to_existing_file, load_data_file, load_yaml_file


@dataclasses.dataclass
class ResolutionContext:
    """Immutable context passed through directive resolution.

    Carries all the state that was previously scattered across resolver
    instance attributes (env_prefix, runtime_root, etc.) so resolvers can
    remain stateless.
    """

    env_prefix: str | None = None
    runtime_root: Path | None = None
    application_root_env_var: str = "APPLICATION_ROOT"
    source_path: str | None = None
    source_folder: Path | None = None
    root_data: dict[str, Any] = dataclasses.field(default_factory=dict)
    env_filename: str | None = None
    try_without_prefix: bool = True
    allowed_roots: tuple[Path, ...] = ()
    allowed_vars: frozenset[str] | set[str] | None = None

    def for_loaded_source(self, source_path: str, root_data: dict[str, Any]) -> "ResolutionContext":
        """Return a context for resolving a newly loaded document.

        Updates source_path, source_folder, and root_data to the loaded file
        while preserving environment-related settings.
        """
        return ResolutionContext(
            env_prefix=self.env_prefix,
            runtime_root=self.runtime_root,
            application_root_env_var=self.application_root_env_var,
            source_path=source_path,
            # source_folder=Path(source_path).parent if is_path_to_existing_file(source_path) else None,
            source_folder=Path(source_path).resolve().parent,
            root_data=root_data,
            env_filename=self.env_filename,
            try_without_prefix=self.try_without_prefix,
            allowed_roots=self.allowed_roots,
            allowed_vars=self.allowed_vars,
        )


class RequestedReferenceResolutionError(ValueError):
    """A requested reference could not be resolved without walking the full project."""

    def __init__(self, reason_code: str, message: str) -> None:
        super().__init__(message)
        self.reason_code = reason_code


@dataclasses.dataclass
class ResolvedDirective:
    """Result returned by a directive resolver's load() method.

    Attributes:
        value: The loaded data (dict, list, etc.).
        should_resolve_recursively: If True, the orchestrator recursively
            resolves directives in the loaded value. @include uses True;
            @load uses False.
        source_path: Path to the file that was loaded, if any.
    """

    value: Any
    should_resolve_recursively: bool = True
    source_path: str | None = None


class DirectiveResolver(Protocol):
    """Protocol for directive handler classes.

    Each resolver handles one directive pattern (e.g. @include, @load, ${...}).
    It is stateless — all runtime state comes from ResolutionContext.
    """

    key: str

    def can_handle(self, value: str) -> bool:
        """Return True when *value* matches this resolver's directive pattern."""
        ...

    def resolve_directive(self, value: str, context: ResolutionContext) -> ResolvedDirective:
        """Resolve the directive in *value* and return a ResolvedDirective."""
        ...


class ResolverRegistry(Registry[type["DirectiveResolver"]]):
    """Registry for directive resolvers.

    Each resolver is registered under its directive prefix (e.g. @include, @load).
    """

    items: dict[str, type["DirectiveResolver"]] = {}


# ---------------------------------------------------------------------------
# Public API — resolve_directives
# ---------------------------------------------------------------------------


def resolve_directives(
    data: dict[str, Any],
    *,
    env_filename: str | None = None,
    env_prefix: str | None = None,
    runtime_root: str | Path | None = None,
    application_root_env_var: str = "APPLICATION_ROOT",
    source_path: str | None = None,
    inplace: bool = False,
    strict: bool = False,
    try_without_prefix: bool = True,
    allowed_roots: tuple[str | Path, ...] = (),
    allowed_vars: frozenset[str] | set[str] | None = None,
) -> dict[str, Any]:
    """Resolve configuration directives in the provided data dictionary.

    Processing order:
    1. Walk the data tree once, dispatching @include, @load, and ${ENV_VAR}
       directives to stateless resolver handlers.  Included YAML files are
       resolved recursively by the orchestrator.
    2. Apply @value cross-references (post-processing pass).

    This method does not mutate the input data unless inplace=True. It creates a
    deep copy by default so the original input stays unchanged.

    Environment variables are expected to already be loaded in os.environ.
    The env_filename parameter is kept for backward compatibility but not used.
    """
    if not inplace:
        data = copy.deepcopy(data)

    resolved_runtime_root: Path | None = _resolve_runtime_root(runtime_root, env_prefix, application_root_env_var)

    # Build the resolution context
    source_folder: Path | None = Path(source_path).parent if source_path and is_path_to_existing_file(source_path) else None
    ctx = ResolutionContext(
        env_prefix=env_prefix,
        runtime_root=resolved_runtime_root,
        application_root_env_var=application_root_env_var,
        source_path=source_path,
        source_folder=source_folder,
        root_data=data,
        env_filename=env_filename,
        try_without_prefix=try_without_prefix,
        allowed_roots=tuple(Path(root).resolve() for root in allowed_roots),
        allowed_vars=allowed_vars,
    )

    # Build directive resolver map (order does not matter — each resolver only
    # handles its own directive prefix)
    resolvers: dict[str, DirectiveResolver] = {key: cls() for key, cls in ResolverRegistry.items.items()}

    # Single orchestration path: the orchestrator owns all traversal and dispatch.
    # Included documents are recursively resolved by re-entering this traversal.
    data = _resolve_node(data, context=ctx, resolvers=resolvers)

    # Post-processing: @value cross-references
    data = ReferenceResolver().resolve_all(data)

    if strict:
        _raise_on_unresolved_directives(data)

    return data


def resolve_requested_reference(
    data: dict[str, Any],
    requested_path: str,
    *,
    env_filename: str | None = None,
    env_prefix: str | None = None,
    runtime_root: str | Path | None = None,
    application_root_env_var: str = "APPLICATION_ROOT",
    source_path: str | None = None,
    try_without_prefix: bool = True,
    allowed_roots: tuple[str | Path, ...] = (),
    allowed_vars: frozenset[str] | set[str] | None = None,
) -> Any:
    """Resolve one path and only the directive values reached from that path.

    The input mapping is copied. Missing or circular references and failures in
    reached include/load/environment directives raise a classified error.
    """
    working_data = copy.deepcopy(data)
    runtime_root_path = _resolve_runtime_root(runtime_root, env_prefix, application_root_env_var)
    source_folder = Path(source_path).parent if source_path and is_path_to_existing_file(source_path) else None
    context = ResolutionContext(
        env_prefix=env_prefix,
        runtime_root=runtime_root_path,
        application_root_env_var=application_root_env_var,
        source_path=source_path,
        source_folder=source_folder,
        root_data=working_data,
        env_filename=env_filename,
        try_without_prefix=try_without_prefix,
        allowed_roots=tuple(Path(root).resolve() for root in allowed_roots),
        allowed_vars=allowed_vars,
    )
    registered_resolvers: dict[str, DirectiveResolver] = {
        key: resolver_type() for key, resolver_type in ResolverRegistry.items.items() if resolver_type is not ReferenceResolver
    }
    reference_resolver = ReferenceResolver()
    active_paths: list[str] = []

    def get_value(path: str) -> Any:
        """Read a dotted path while preserving the project's path aliases."""
        for expanded_path in dotexpand(path):
            value: Any = working_data
            for segment in expanded_path.split("."):
                if not isinstance(value, dict) or segment not in value:
                    value = _REQUESTED_PATH_MISSING
                    break
                value = value[segment]
                if value is None:
                    value = _REQUESTED_PATH_MISSING
                    break
            if value is not _REQUESTED_PATH_MISSING:
                return value
        return _REQUESTED_PATH_MISSING

    def set_value(path: str, value: Any) -> None:
        """Replace a path already present in the copied mapping."""
        for expanded_path in dotexpand(path):
            segments = expanded_path.split(".")
            parent: Any = working_data
            for segment in segments[:-1]:
                if not isinstance(parent, dict) or segment not in parent or not isinstance(parent[segment], dict):
                    parent = _REQUESTED_PATH_MISSING
                    break
                parent = parent[segment]
            if parent is not _REQUESTED_PATH_MISSING and segments[-1] in parent:
                parent[segments[-1]] = value
                return
        raise RequestedReferenceResolutionError("missing_path", f"Reference path '{path}' was not found.")

    def preprocess(value: Any, current_context: ResolutionContext, include_stack: tuple[str, ...]) -> Any:
        """Apply include, load, and environment directives using the full resolver handlers."""
        if isinstance(value, dict):
            return {key: preprocess(child, current_context, include_stack) for key, child in value.items()}
        if isinstance(value, list):
            return [preprocess(item, current_context, include_stack) for item in value]
        if not isinstance(value, str):
            return value

        for resolver in registered_resolvers.values():
            if not resolver.can_handle(value):
                continue
            try:
                resolved = resolver.resolve_directive(value, current_context)
                if not resolved.should_resolve_recursively:
                    return resolved.value
                next_context = (
                    current_context.for_loaded_source(resolved.source_path, resolved.value) if resolved.source_path else current_context
                )
                if resolved.source_path:
                    resolved_path = str(Path(resolved.source_path).resolve())
                    if resolved_path in include_stack:
                        raise RequestedReferenceResolutionError(
                            "circular_reference", f"Included configuration file '{resolved.source_path}' is circular."
                        )
                    next_stack = (*include_stack, resolved_path)
                else:
                    next_stack = include_stack
                return preprocess(resolved.value, next_context, next_stack)
            except RequestedReferenceResolutionError:
                raise
            except Exception as exc:  # pylint: disable=broad-exception-caught
                raise RequestedReferenceResolutionError(
                    "dependency_failure", f"A directive needed by reference path could not be resolved: {exc}"
                ) from exc
        return value

    def resolve_expression(expression: str) -> list[Any]:
        """Resolve a supported list expression without dropping failed operands."""
        tokens = split_reference_expression(expression)
        if tokens is None:
            raise RequestedReferenceResolutionError("dependency_failure", "The reference expression is malformed.")

        result: list[Any] = []
        for token in tokens:
            if token.startswith(reference_resolver.resolve_key):
                dependency_path = token[len(reference_resolver.resolve_key) :].strip()
                if not dependency_path:
                    raise RequestedReferenceResolutionError("missing_path", "A reference expression has an empty path.")
                dependency = resolve_path(dependency_path)
                if isinstance(dependency, list):
                    if any(isinstance(item, list) for item in dependency):
                        raise RequestedReferenceResolutionError(
                            "dependency_failure", "A reference expression cannot flatten a nested list."
                        )
                    result.extend(dependency)
                else:
                    result.append(dependency)
            elif token.startswith("[") and token.endswith("]"):
                try:
                    literal = yaml.safe_load(token)
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    raise RequestedReferenceResolutionError(
                        "dependency_failure", "The reference expression contains an invalid list."
                    ) from exc
                if not isinstance(literal, list) or any(isinstance(item, list) for item in literal):
                    raise RequestedReferenceResolutionError("dependency_failure", "The reference expression contains an unsupported list.")
                result.extend(literal)
            else:
                raise RequestedReferenceResolutionError("dependency_failure", "The reference expression contains an unsupported operand.")
        if not result:
            raise RequestedReferenceResolutionError("dependency_failure", "The reference expression resolved to no values.")
        return result

    def resolve_values(value: Any, current_path: str, include_stack: tuple[str, ...]) -> Any:
        """Resolve @value references inside a reached value and flatten list-item references."""
        if isinstance(value, dict):
            return {key: resolve_values(child, f"{current_path}.{key}", include_stack) for key, child in value.items()}
        if isinstance(value, list):
            result: list[Any] = []
            for index, item in enumerate(value):
                resolved_item = resolve_values(item, f"{current_path}[{index}]", include_stack)
                if isinstance(item, str) and item.strip().startswith(reference_resolver.resolve_key) and isinstance(resolved_item, list):
                    result.extend(resolved_item)
                else:
                    result.append(resolved_item)
            return result
        if not isinstance(value, str):
            return value

        contains_reference = reference_resolver.resolve_key in value
        is_expression = contains_reference and "+" in value or "[" in value and "+" in value
        if is_expression:
            return resolve_expression(value)
        if value.startswith(reference_resolver.resolve_key):
            dependency_path = value[len(reference_resolver.resolve_key) :].strip()
            if not dependency_path:
                raise RequestedReferenceResolutionError("missing_path", "The reference path is empty.")
            return resolve_path(dependency_path)
        if contains_reference:
            raise RequestedReferenceResolutionError(
                "dependency_failure", f"A reference directive in '{current_path}' is not a supported simple path."
            )
        return value

    def resolve_path(path: str) -> Any:
        """Resolve one path and cache its result in the copied mapping for later dependencies."""
        if path in active_paths:
            chain = " -> ".join((*active_paths, path))
            raise RequestedReferenceResolutionError("circular_reference", f"Reference cycle detected: {chain}.")
        active_paths.append(path)
        try:
            expanded_paths = dotexpand(path)
            if not expanded_paths:
                raise RequestedReferenceResolutionError("missing_path", "The reference path is empty.")
            for expanded_path in expanded_paths:
                segments = expanded_path.split(".")
                for segment_count in range(1, len(segments)):
                    parent_path = ".".join(segments[:segment_count])
                    parent_value = get_value(parent_path)
                    if isinstance(parent_value, str) and (
                        reference_resolver.can_handle(parent_value)
                        or any(resolver.can_handle(parent_value) for resolver in registered_resolvers.values())
                    ):
                        prepared_parent = preprocess(parent_value, context, ())
                        prepared_parent = resolve_values(prepared_parent, parent_path, ())
                        set_value(parent_path, prepared_parent)

            value = get_value(path)
            if value is _REQUESTED_PATH_MISSING:
                raise RequestedReferenceResolutionError("missing_path", f"Reference path '{path}' was not found.")
            prepared_value = preprocess(value, context, ())
            resolved_value = resolve_values(prepared_value, path, ())
            if find_unresolved_directives(resolved_value):
                raise RequestedReferenceResolutionError(
                    "dependency_failure", f"Reference path '{path}' depends on an unresolved directive."
                )
            set_value(path, resolved_value)
            return resolved_value
        except RequestedReferenceResolutionError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            raise RequestedReferenceResolutionError("dependency_failure", f"Reference path '{path}' could not be resolved: {exc}") from exc
        finally:
            active_paths.pop()

    try:
        return resolve_path(requested_path)
    except RequestedReferenceResolutionError:
        raise
    except Exception as exc:  # pylint: disable=broad-exception-caught
        raise RequestedReferenceResolutionError(
            "dependency_failure", f"Reference path '{requested_path}' could not be resolved: {exc}"
        ) from exc


_REQUESTED_PATH_MISSING = object()


def split_reference_expression(expression: str) -> list[str] | None:
    """Return supported @value and list-literal operands in expression order.

    The returned tokens keep their original text apart from surrounding
    whitespace. A malformed expression or an unsupported operand returns
    None.
    """
    if expression.count("[") != expression.count("]"):
        return None

    tokens: list[str] = []
    current_token = ""
    bracket_depth = 0
    for char in expression:
        if char == "[":
            bracket_depth += 1
            current_token += char
        elif char == "]":
            bracket_depth -= 1
            current_token += char
            if bracket_depth < 0:
                return None
        elif char == "+" and bracket_depth == 0:
            token = current_token.strip()
            if not token:
                return None
            tokens.append(token)
            current_token = ""
        else:
            current_token += char

    token = current_token.strip()
    if bracket_depth != 0 or not token:
        return None
    tokens.append(token)
    if len(tokens) < 2:
        return None

    for token in tokens:
        if token.startswith("@value:"):
            if not token[len("@value:") :].strip():
                return None
            continue
        if not (token.startswith("[") and token.endswith("]")):
            return None
        try:
            literal = yaml.safe_load(token)
        except Exception:  # pylint: disable=broad-exception-caught
            return None
        if not isinstance(literal, list) or any(isinstance(item, list) for item in literal):
            return None

    return tokens


def load_resolved_yaml(
    source: str | dict[str, Any],
    *,
    env_filename: str | None = None,
    env_prefix: str | None = None,
    runtime_root: str | Path | None = None,
    application_root_env_var: str = "APPLICATION_ROOT",
    strict: bool = False,
    try_without_prefix: bool = True,
) -> dict[str, Any]:
    """Load and resolve a YAML project file.

    Returns the fully resolved dict with @include, @load, ${ENV_VAR}, and
    @value: directives processed.  Does NOT inject env-prefixed values into
    the data — that behavior belongs to ``Config.resolve()`` for app settings.

    Args:
        source: Path to a YAML file or an already-loaded dict.
        env_filename: Optional .env file to load before resolution.
        env_prefix: Environment variable prefix for ${VAR} scoping.
        runtime_root: Base directory for anchoring relative env-derived paths.
        application_root_env_var: Env var name holding the application root.
        strict: If True, raise ValueError on unresolved directives.
        try_without_prefix: If True, try env vars without the prefix as fallback.

    Returns:
        Resolved configuration dict.
    """
    load_dotenv(dotenv_path=env_filename)

    if isinstance(source, dict):
        data: dict[str, Any] | None = source
    else:
        data = load_yaml_file(source)
        if not isinstance(data, dict):
            raise ValueError(f"Project file must contain a mapping: {source}")

    return resolve_directives(
        data,
        env_filename=env_filename,
        env_prefix=env_prefix,
        runtime_root=runtime_root,
        application_root_env_var=application_root_env_var,
        source_path=source if isinstance(source, str) else None,
        inplace=True,
        strict=strict,
        try_without_prefix=try_without_prefix,
    )


def _raise_on_unresolved_directives(data):
    unresolved: list[str] = find_unresolved_directives(data)
    if unresolved:
        paths: str = ", ".join(unresolved[:5])
        extra: str = "" if len(unresolved) <= 5 else f" (and {len(unresolved) - 5} more)"
        raise ValueError(f"Unresolved configuration directives at: {paths}{extra}")


def _resolve_runtime_root(runtime_root: str | Path | None, env_prefix: str | None, application_root_env_var: str) -> Path | None:
    """Return the base directory for env-derived relative paths."""
    if runtime_root:
        return Path(runtime_root).resolve()

    application_root: str = replace_env_vars(f"${{{application_root_env_var}}}", env_prefix=env_prefix or "", try_without_prefix=True)
    return Path(application_root).resolve() if application_root else None


def _resolve_directive_file_path(filename: str, context: ResolutionContext) -> str:
    """Resolve a directive file and require it to stay in an approved root."""
    if not context.allowed_roots:
        return filename

    path = Path(filename)
    for root in context.allowed_roots:
        try:
            return str(resolve_contained_path(path, root, allow_absolute=path.is_absolute()))
        except ValueError:
            continue

    raise ValueError("Directive file path is outside the approved data roots")


def _is_path_env_var(env_var_name: str, env_prefix: str | None, application_root_env_var: str) -> bool:
    """Return True when an environment variable is expected to contain a path."""
    normalized_prefix: str = (env_prefix or "").rstrip("_")
    normalized_name: str = env_var_name
    if normalized_prefix and normalized_name.startswith(f"{normalized_prefix}_"):
        normalized_name = normalized_name[len(normalized_prefix) + 1 :]

    normalized_name = normalized_name.upper()
    return normalized_name == application_root_env_var.upper() or normalized_name.endswith(("_DIR", "_PATH", "_FILE", "_FILENAME"))


def find_unresolved_directives(data: Any, path: str | None = None) -> list[str]:
    """Recursively find unresolved directive strings like @value:, @include:, @load:."""
    tags: list[str] = ["@value:", "@include", "@load"]
    hits: list[str] = []

    if isinstance(data, dict):
        for k, v in data.items():
            next_path = f"{path}.{k}" if path else str(k)
            hits.extend(find_unresolved_directives(v, next_path))
    elif isinstance(data, list):
        for idx, v in enumerate(data):
            next_path = f"{path}[{idx}]" if path else f"[{idx}]"
            hits.extend(find_unresolved_directives(v, next_path))
    elif isinstance(data, str):
        if any(tag in data for tag in tags) or "${" in data:
            hits.append(f"{path or '<root>'}: {data}")
    return hits


def _resolve_path(
    path: str,
    *,
    base_path: Path | None = None,
    env_prefix: str | None = None,
    runtime_root: Path | None = None,
    env_filename: str | None = None,
    raise_if_missing: bool = False,
) -> str:
    """Resolve a file path with environment variable expansion and relative path support.

    Supports partial replacement in paths (e.g., ${DATA_DIR}/subfolder/file.xlsx).

    Args:
        path: Path string potentially containing ${VAR} references
        base_path: Base directory for resolving relative paths
        env_prefix: Environment variable prefix for scoped resolution
        runtime_root: Base directory for anchoring env-derived relative paths
        env_filename: Path to .env file for resolving env-variable paths
        raise_if_missing: If True, raise ValueError for unresolved env vars

    Returns:
        Resolved absolute path string

    Raises:
        ValueError: If raise_if_missing=True and env var cannot be resolved
    """
    if not path:
        return path

    # Step 1: Expand environment variables
    resolved_path: str = replace_env_vars(
        path,
        raise_if_unresolved=raise_if_missing,
        env_prefix=env_prefix,  # type: ignore[arg-type]
        try_without_prefix=True,
    )
    is_expanded: bool = resolved_path != path

    path_obj = Path(resolved_path)
    if path_obj.is_absolute():
        return str(path_obj)

    if is_expanded and runtime_root is not None:
        return str((runtime_root / path_obj).resolve())

    if is_expanded and env_filename:
        env_base_path = Path(env_filename).resolve().parent
        resolved_path = str(env_base_path / resolved_path)

    # Step 2: Handle absolute vs relative paths
    path_obj = Path(resolved_path)

    if path_obj.is_absolute():
        return str(path_obj)

    # Step 3: Resolve relative paths
    if base_path is not None:
        return str(base_path / resolved_path)

    return resolved_path


# ---------------------------------------------------------------------------
# Core tree traversal (single-pass orchestrator)
# ---------------------------------------------------------------------------


def _resolve_node(value: Any, *, context: ResolutionContext, resolvers: dict[str, DirectiveResolver]) -> Any:
    """Recursively walk *value* and dispatch directive strings to resolvers.

    Dicts and lists are recursed into.  Strings are checked against every
    registered resolver.  When a resolver produces a ``ResolvedDirective``
    with ``should_resolve_recursively=True`` the loaded value is resolved
    again (with an updated context), otherwise it is returned as-is.
    """
    if isinstance(value, dict):
        return {key: _resolve_node(child, context=context, resolvers=resolvers) for key, child in value.items()}

    if isinstance(value, list):
        return [_resolve_node(item, context=context, resolvers=resolvers) for item in value]

    if isinstance(value, str):
        for resolver in resolvers.values():
            if resolver.can_handle(value):
                result: ResolvedDirective = resolver.resolve_directive(value, context)
                if result.should_resolve_recursively:
                    next_context: ResolutionContext = (
                        context.for_loaded_source(result.source_path, result.value) if result.source_path else context
                    )
                    return _resolve_node(result.value, context=next_context, resolvers=resolvers)
                return result.value

    return value


# ---------------------------------------------------------------------------
# Stateless directive resolvers
# ---------------------------------------------------------------------------


@ResolverRegistry.register(key="@include")
class IncludeResolver(DirectiveResolver):
    """Load nested YAML configuration files referenced by @include.

    The directive argument is treated as a config file path.  Relative paths
    are resolved against the current configuration file.  The orchestrator
    handles recursive resolution of the loaded document — this resolver only
    loads and returns the raw YAML.

    Example:
        database: "@include:config/database.yml"
        api: "@include:config/api.yml"
    """

    def can_handle(self, value: str) -> bool:
        """Return True when *value* starts with @include."""
        return value.startswith(self.key)

    def resolve_directive(self, value: str, context: ResolutionContext) -> ResolvedDirective:
        """Load the YAML file referenced by *argument*.

        Returns a ``ResolvedDirective`` with ``should_resolve_recursively=True``
        so the orchestrator resolves directives inside the loaded document.
        """
        argument: str = value[len(self.key) :].lstrip(":").strip()
        filename: str = _resolve_path(
            argument,
            base_path=context.source_folder,
            env_prefix=context.env_prefix,
            runtime_root=context.runtime_root,
            env_filename=context.env_filename,
        )
        filename = _resolve_directive_file_path(filename, context)

        load_dotenv(dotenv_path=context.env_filename)

        data: dict[str, Any] | str | None = load_yaml_file(filename)

        if not isinstance(data, dict):
            raise ValueError(f"Included file must contain a mapping: {filename}")

        return ResolvedDirective(value=data, should_resolve_recursively=True, source_path=filename)


@ResolverRegistry.register(key="@load")
class LoadResolver(DirectiveResolver):
    """Load external data payloads referenced by @load.

    The directive argument may be a file path or a dotted path into the
    current configuration.  If the dotted path resolves to a string, that
    value is treated as the filename.  If it resolves to a dict, the
    resolver uses its ``filename`` and ``delimiter`` keys.

    Loaded data is returned as-is and is **not** recursively resolved for
    more directives.

    Example:
        values: "@load:data/translations.csv"
        values: "@load:options.data_sources.my_source"
    """

    def can_handle(self, value: str) -> bool:
        """Return True when *value* starts with @load."""
        return value.startswith(self.key)

    def resolve_directive(self, value: str, context: ResolutionContext) -> ResolvedDirective:
        """Load the data file referenced by *argument*.

        Returns a ``ResolvedDirective`` with ``should_resolve_recursively=False``
        so the loaded payload is inserted as-is.
        """
        argument: str = value[len(self.key) :].lstrip(":").strip()
        filename: Any
        sep: str

        if dotexists(context.root_data, argument):
            opts: Any = dget(context.root_data, argument)

            if not isinstance(opts, dict):
                filename, sep = opts, ","
            else:
                if "filename" not in opts:
                    logger.warning(f"ignoring load directive for path '{argument}' since no filename is specified in options")
                    return ResolvedDirective(value=opts, should_resolve_recursively=False)

                filename, sep = opts["filename"], opts.get("delimiter", ",")

        else:
            filename, sep = argument, ","

        # Resolve environment variables and relative paths
        filename = _resolve_path(
            filename,
            base_path=context.source_folder,
            env_prefix=context.env_prefix,
            runtime_root=context.runtime_root,
            env_filename=context.env_filename,
            raise_if_missing=False,
        )
        filename = _resolve_directive_file_path(filename, context)

        loaded_data = load_data_file(filename, sep)
        result = loaded_data if loaded_data is not None else argument
        return ResolvedDirective(value=result, should_resolve_recursively=False)


@ResolverRegistry.register(key="${")
class EnvironmentVariableResolver(DirectiveResolver):
    """Resolve ${ENV_VAR} references in configuration values.

    Handles full-string values like ``"${API_URL}"`` and partial replacements
    like ``"prefix_${VAR}_suffix"``.  Path-like environment variables (names
    ending in ``_DIR``, ``_PATH``, ``_FILE``, ``_FILENAME``, or matching
    ``application_root_env_var``) are anchored to ``runtime_root`` when their
    resolved value is relative.

    Returns ``should_resolve_recursively=False`` — the resolved string is
    never walked again for more directives.
    """

    def can_handle(self, value: str) -> bool:
        """Return True when *value* contains a ${...} reference."""
        return "${" in value

    def resolve_directive(self, value: str, context: ResolutionContext) -> ResolvedDirective:
        """Replace all ${ENV_VAR} references in *value* with environment values."""

        def replacer(match: re.Match[str]) -> str:
            env_var_name = match.group(1)
            resolved_value = replace_env_vars(
                match.group(0),
                env_prefix=context.env_prefix or "",
                try_without_prefix=context.try_without_prefix,
                allowed_vars=context.allowed_vars,
            )
            if not resolved_value:
                return resolved_value
            if (
                context.runtime_root is not None
                and _is_path_env_var(env_var_name, context.env_prefix, context.application_root_env_var)
                and not Path(resolved_value).is_absolute()
            ):
                return str((context.runtime_root / resolved_value).resolve())
            return resolved_value

        result = re.sub(r"\$\{([^}]+)\}", replacer, value)
        return ResolvedDirective(value=result, should_resolve_recursively=False)


@ResolverRegistry.register(key="@value")
class ReferenceResolver(DirectiveResolver):
    """Resolve @value: cross-references within the resolved configuration.

    Unlike other resolvers, this is NOT dispatched by ``_resolve_node`` during
    the tree walk.  It is called explicitly via ``resolve_all()`` after all
    @include/@load/${ENV_VAR} resolution is complete, because it needs the
    fully resolved document to perform dotted-path lookups.

    Supports:
      - Simple: ``"@value: entities.foo.keys"``
      - List concatenation: ``"@value: base + ['b', 'c']"``
      - YAML-list flattening: ``["@value: path1", "@value: path2", "col_a"]``
    """

    @property
    def resolve_key(self) -> str:
        """Return the directive key handled by this resolver."""
        return f"{self.key}:"

    def can_handle(self, value: str) -> bool:
        """Return True when *value* contains an @value: directive."""
        return self.resolve_key in value

    def resolve_directive(self, value: str, context: ResolutionContext) -> ResolvedDirective:
        """Resolve a single @value: reference string."""
        resolved = self._resolve_ref_value(value, full_data=context.root_data)
        return ResolvedDirective(value=resolved, should_resolve_recursively=False)

    def resolve_all(self, data: dict[str, Any] | list[Any] | str) -> dict[str, Any] | list[Any] | str:
        """Resolve all @value: references in *data* (post-processing entry point)."""
        return self._resolve_ref_value(data, full_data=data)  # type: ignore[arg-type]

    def _resolve_ref_value(
        self, data: dict[str, Any] | list[Any] | str, full_data: dict[str, Any] | list[Any] | str
    ) -> dict[str, Any] | list[Any] | str:
        """Recursive helper for @value: reference resolution."""
        if isinstance(data, dict):
            return {k: self._resolve_ref_value(v, full_data=full_data) for k, v in data.items()}
        if isinstance(data, list):
            result: list[Any] = []
            for item in data:
                resolved = self._resolve_ref_value(item, full_data=full_data)
                if isinstance(item, str) and item.strip().startswith(self.resolve_key) and isinstance(resolved, list):
                    result.extend(resolved)
                else:
                    result.append(resolved)
            return result
        if isinstance(data, str):
            if (self.resolve_key in data and "+" in data) or (data.count("[") > 0 and "+" in data):
                parsed = self._parse_list_expression(data, full_data)  # type: ignore[arg-type]
                if parsed != data and not isinstance(parsed, str):
                    return self._resolve_ref_value(parsed, full_data=full_data)
                if isinstance(parsed, str):
                    data = parsed
            if data.startswith(self.resolve_key):
                ref_path: str = data[len(self.resolve_key) :].strip()
                if not dotexists(full_data, ref_path):  # type: ignore[arg-type]
                    logger.error(f"Reference path '{ref_path}' not found in configuration data.")
                ref_value: Any = dotget(full_data, ref_path)  # type: ignore[arg-type]
                ref_value = self._resolve_ref_value(ref_value, full_data=full_data)
                return ref_value if ref_value is not None else data
        return data

    def _parse_list_expression(self, expr: str, full_data: dict[str, Any]) -> list[Any] | str:
        """Parse @value: list concatenation expressions like "@value: base + ['b']".

        Constraints: no nested lists, no brackets in list values.
        """
        if self.resolve_key not in expr and "[" not in expr:
            return expr
        if expr.count("[") != expr.count("]"):
            return expr
        if "+" not in expr:
            return expr

        tokens: list[str] = []
        current_token: str = ""
        bracket_depth: int = 0

        for char in expr:
            if char == "[":
                bracket_depth += 1
                current_token += char
            elif char == "]":
                bracket_depth -= 1
                current_token += char
                if bracket_depth < 0:
                    return expr
            elif char == "+" and bracket_depth == 0:
                if current_token.strip():
                    tokens.append(current_token.strip())
                current_token = ""
            else:
                current_token += char

        if current_token.strip():
            tokens.append(current_token.strip())
        if bracket_depth != 0:
            return expr
        if len(tokens) == 1 and tokens[0].startswith(self.resolve_key):
            return tokens[0]

        result: list[Any] = []
        for token in tokens:
            if token.startswith(self.resolve_key):
                ref_path: str = token[len(self.resolve_key) :].strip()
                ref_value = dotget(full_data, ref_path)  # type: ignore[arg-type]
                if ref_value is None:
                    continue
                ref_value = self._resolve_ref_value(ref_value, full_data=full_data)
                if isinstance(ref_value, list):
                    if any(isinstance(item, list) for item in ref_value):
                        return expr
                    result.extend(ref_value)
                else:
                    result.append(ref_value)
            elif token.startswith("[") and token.endswith("]"):
                inner: str = token[1:-1]
                if "[" in inner or "]" in inner:
                    return expr
                try:
                    list_value = yaml.safe_load(token)
                    if isinstance(list_value, list):
                        if any(isinstance(item, list) for item in list_value):
                            return expr
                        result.extend(list_value)
                    else:
                        result.append(list_value)
                except Exception:  # pylint: disable=broad-exception-caught
                    return expr

        return result if result else expr
