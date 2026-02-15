from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, cast

import pandas as pd
from loguru import logger


@dataclass(frozen=True, slots=True)
class RuleContext:
    entity_name: str
    column_name: str
    normalize_ops: Sequence[str]
    coerce: str | None
    negate: bool
    report_replaced: bool
    report_unmatched: bool
    report_top: int


class ReplacementRules:
    items: dict[str, type["ReplacementRule"]] = {}

    @classmethod
    def register(cls, *, key: str):
        def decorator(rule_cls: type[ReplacementRule]) -> type[ReplacementRule]:
            cls.items[key] = rule_cls
            rule_cls.key = key
            return rule_cls

        return decorator

    @classmethod
    def get(cls, key: str) -> type["ReplacementRule"] | None:
        return cls.items.get(key)


class ReplacementRule:
    key: str

    @classmethod
    def apply(cls, series: pd.Series, *, rule: Mapping[str, Any], ctx: RuleContext) -> pd.Series:
        raise NotImplementedError


def apply_replacements(df: pd.DataFrame, *, replacements: Mapping[str, Any], entity_name: str) -> pd.DataFrame:
    """Apply column replacements to a DataFrame.

    Backwards compatible forms (per column):
      - Mapping => Series.replace(mapping)
      - scalar/list/tuple/set => blank out those values then forward-fill

    Advanced form (per column):
      - list of dict rules (ordered)
    """
    out: pd.DataFrame = df
    for col, spec in replacements.items():
        if col not in out.columns:
            continue

        # ---- Advanced rules list (ordered) ----
        if isinstance(spec, list) and all(isinstance(item, Mapping) for item in spec):
            series: pd.Series[Any] = out[col]
            for rule in spec:
                series = _apply_replacement_rule(series, rule=rule, entity_name=entity_name, column_name=col)
            out[col] = series
            continue

        # ---- Simple mapping ----
        if isinstance(spec, Mapping):
            out[col] = out[col].replace(to_replace=spec)
            continue

        # ---- Legacy scalar/list blank-out + ffill ----
        out[col] = out[col].replace(to_replace=spec, value=pd.NA).ffill()

    return out


def _apply_replacement_rule(series: pd.Series, *, rule: Mapping[str, Any], entity_name: str, column_name: str) -> pd.Series:
    """Apply a single replacement rule to a Series.

    Dispatches to a registered rule strategy based on the rule shape.
    """
    if not rule:
        return series

    rule_key, negate = _infer_rule_key(rule)

    ctx = RuleContext(
        entity_name=entity_name,
        column_name=column_name,
        normalize_ops=rule.get("normalize", []) or [],
        coerce=(str(rule.get("coerce")).lower() if rule.get("coerce") is not None else None),
        negate=negate,
        report_replaced=bool(rule.get("report_replaced", False)),
        report_unmatched=bool(rule.get("report_unmatched", False)),
        report_top=int(rule.get("report_top", 10) or 10),
    )

    rule_cls: type[ReplacementRule] | None = ReplacementRules.get(rule_key)
    if not rule_cls:
        logger.warning(f"{entity_name}[replacements]: {column_name}: unknown rule type: {rule_key!r}")
        return series
    return rule_cls.apply(series, rule=rule, ctx=ctx)


def _infer_rule_key(rule: Mapping[str, Any]) -> tuple[str, bool]:
    """Infer the rule type from the rule dictionary.

    Returns:
        tuple of (rule_key, negate_flag)
    """
    if "blank_out" in rule:
        return "blank_out", False
    if "map" in rule:
        return "map", False

    # Check if this is a transform-only rule (no match/from condition)
    # Transform rules only have normalize/coerce/to without match/from/map/blank_out
    has_match_condition = "match" in rule or "from" in rule
    has_transform = "normalize" in rule or "coerce" in rule

    if not has_match_condition and has_transform:
        return "transform", False

    match_type = str(rule.get("match", "equals")).lower()
    if match_type == "not_in":
        return "in", True
    if match_type == "not_contains":
        return "contains", True
    if match_type == "not_startswith":
        return "startswith", True
    if match_type == "not_endswith":
        return "endswith", True
    if match_type == "not_regex":
        return "regex", True
    if match_type == "not_equals":
        return "equals", True
    return match_type, False


def _compile_regex(pattern_value: Any, *, flags_spec: Any) -> re.Pattern[str]:
    flags = 0
    for f in flags_spec or []:
        if str(f).lower() in ("i", "ignorecase"):
            flags |= re.IGNORECASE
        elif str(f).lower() in ("m", "multiline"):
            flags |= re.MULTILINE
        elif str(f).lower() in ("s", "dotall"):
            flags |= re.DOTALL
    return re.compile(str(pattern_value), flags=flags)


def _is_ignore_case(flags_spec: Any) -> bool:
    for f in flags_spec or []:
        if str(f).lower() in ("i", "ignorecase"):
            return True
    return False


def _as_sequence(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def _coerce_series_for_match(series: pd.Series, *, coerce: str | None) -> pd.Series:
    if not coerce or coerce in ("string", "str"):
        return series.astype("string")
    if coerce in ("int", "int64", "integer"):
        numeric = pd.to_numeric(series, errors="coerce")
        numeric = numeric.where((numeric % 1) == 0)
        return numeric.astype("Int64")
    if coerce in ("float", "double", "number"):
        return pd.to_numeric(series, errors="coerce")
    logger.warning(f"replacements: unknown coerce: {coerce!r}")
    return series


def _coerce_scalar_for_match(value: Any, *, coerce: str | None) -> Any:
    if value is None:
        return pd.NA
    if not coerce or coerce in ("string", "str"):
        return str(value)
    if coerce in ("int", "int64", "integer"):
        try:
            f = float(value)
            if f.is_integer():
                return int(f)
            return pd.NA
        except Exception:  #  pylint: disable=broad-except
            return pd.NA
    if coerce in ("float", "double", "number"):
        try:
            return float(value)
        except Exception:  #  pylint: disable=broad-except
            return pd.NA
    return value


def _coerce_values_for_match(values: Any, *, coerce: str | None) -> list[Any]:
    out: list[Any] = []
    for v in _as_sequence(values):
        coerced = _coerce_scalar_for_match(v, coerce=coerce)
        if coerced is pd.NA:
            continue
        out.append(coerced)
    return out


@ReplacementRules.register(key="blank_out")
class BlankOutRule(ReplacementRule):
    """Blank out specified values (replacing with NA) with optional fill policy for resulting blanks."""

    @classmethod
    def apply(cls, series: pd.Series, *, rule: Mapping[str, Any], ctx: RuleContext) -> pd.Series:
        to_blank: Any | None = rule.get("blank_out")
        before: pd.Series[Any] = series

        # Preserve historical semantics unless coercion is explicitly requested.
        if not ctx.coerce:
            out: pd.Series[Any] = series.replace(to_replace=to_blank, value=pd.NA)
        else:
            match_series = _coerce_series_for_match(series, coerce=ctx.coerce)
            values = _coerce_values_for_match(to_blank, coerce=ctx.coerce)
            mask = match_series.isin(values).fillna(False)
            out = series.where(~mask, cast(Any, pd.NA))

        if ctx.report_replaced:
            replaced_count = int((before.notna() & out.isna()).sum())
            logger.info(f"{ctx.entity_name}[replacements]: {ctx.column_name}: blank_out replaced {replaced_count} value(s)")

        fill = rule.get("fill", "forward")
        if fill in (None, "none", False):
            return out
        if fill == "forward":
            return out.ffill()
        if fill == "backward":
            return out.bfill()
        if isinstance(fill, Mapping) and "constant" in fill:
            return out.fillna(fill.get("constant"))

        logger.warning(f"{ctx.entity_name}[replacements]: {ctx.column_name}: unknown fill policy: {fill!r}")
        return out


@ReplacementRules.register(key="map")
class MapRule(ReplacementRule):
    """Replace values based on a mapping, with optional normalization and unmatched reporting."""

    @classmethod
    def apply(cls, series: pd.Series, *, rule: Mapping[str, Any], ctx: RuleContext) -> pd.Series:
        mapping_raw: Any | None = rule.get("map")
        if not isinstance(mapping_raw, Mapping):
            return series
        mapping: Mapping[Any, Any] = mapping_raw

        if ctx.report_unmatched:
            if ctx.normalize_ops:
                keys_norm: set[str] = {_normalize_scalar(k, ops=ctx.normalize_ops) for k in mapping.keys()}
                norm: pd.Series[Any] = _normalize_for_match(series, ops=ctx.normalize_ops)
                unmatched_mask: pd.Series[bool] = norm.notna() & ~norm.isin(list(keys_norm))
            elif ctx.coerce:
                keys_coerced = {
                    _coerce_scalar_for_match(k, coerce=ctx.coerce)
                    for k in mapping.keys()
                    if _coerce_scalar_for_match(k, coerce=ctx.coerce) is not pd.NA
                }
                match_series = _coerce_series_for_match(series, coerce=ctx.coerce)
                unmatched_mask = match_series.notna() & ~match_series.isin(list(keys_coerced))
            else:
                keys_norm = {_normalize_scalar(k, ops=[]) for k in mapping.keys()}
                norm = _normalize_for_match(series, ops=[])
                unmatched_mask = norm.notna() & ~norm.isin(list(keys_norm))

            if bool(unmatched_mask.any()):
                top: pd.Series[int] = series[unmatched_mask].astype("string").value_counts(dropna=True).head(ctx.report_top)
                n_unmatched = int(unmatched_mask.sum())
                logger.info(
                    f"{ctx.entity_name}[replacements]: {ctx.column_name}: "
                    f"{n_unmatched} unmatched value(s) (top {len(top)}): {top.to_dict()}"
                )

        if not ctx.normalize_ops and not ctx.coerce:
            out: pd.Series[Any] = series.replace(to_replace=mapping)
            if ctx.report_replaced:
                changed = int((series.astype("string") != out.astype("string")).fillna(False).sum())
                logger.info(f"{ctx.entity_name}[replacements]: {ctx.column_name}: map replaced {changed} value(s)")
            return out

        if not ctx.normalize_ops and ctx.coerce:
            match_series = _coerce_series_for_match(series, coerce=ctx.coerce)
            out = series.copy()
            changed_total = 0
            for old_value, new_value in mapping.items():
                old_coerced = _coerce_scalar_for_match(old_value, coerce=ctx.coerce)
                if old_coerced is pd.NA:
                    continue
                mask = (match_series == old_coerced).fillna(False)
                if mask.any():
                    out = out.where(~mask, new_value)
                    changed_total += int(mask.sum())

            if ctx.report_replaced:
                logger.info(
                    f"{ctx.entity_name}[replacements]: {ctx.column_name}: map(coerced={ctx.coerce}) replaced {changed_total} value(s)"
                )
            return out

        norm = _normalize_for_match(series, ops=ctx.normalize_ops)
        out = series.copy()

        changed_total = 0
        for old_value, new_value in mapping.items():
            old_norm: str = _normalize_scalar(old_value, ops=ctx.normalize_ops)
            mask: pd.Series[bool] = norm == old_norm
            if mask.any():
                out = out.where(~mask, new_value)
                changed_total += int(mask.sum())

        if ctx.report_replaced:
            logger.info(f"{ctx.entity_name}[replacements]: {ctx.column_name}: map(normalized) replaced {changed_total} value(s)")
        return out


@ReplacementRules.register(key="transform")
class TransformRule(ReplacementRule):
    """Apply normalize and/or coerce operations to all values without filtering."""

    @classmethod
    def apply(cls, series: pd.Series, *, rule: Mapping[str, Any], ctx: RuleContext) -> pd.Series:
        """Transform all values with normalize/coerce operations.

        This rule doesn't require a match condition - it applies to all values.
        Useful for operations like: strip whitespace, convert to lowercase, coerce types.
        """
        # Apply normalization operations if specified
        if ctx.normalize_ops:
            out = _normalize_for_match(series, ops=ctx.normalize_ops)
            if ctx.report_replaced:
                changed = int((series.astype("string").fillna("") != out.astype("string").fillna("")).sum())
                logger.info(
                    f"{ctx.entity_name}[replacements]: {ctx.column_name}: "
                    f"transform(normalize={ctx.normalize_ops}) changed {changed} value(s)"
                )
        else:
            out = series

        # Apply coercion if specified
        if ctx.coerce:
            before = out
            out = _coerce_series_for_match(out, coerce=ctx.coerce)
            if ctx.report_replaced:
                # Count non-null values that changed
                before_str = before.astype("string").fillna("")
                after_str = out.astype("string").fillna("")
                changed = int((before_str != after_str).sum())
                logger.info(
                    f"{ctx.entity_name}[replacements]: {ctx.column_name}: " f"transform(coerce={ctx.coerce}) changed {changed} value(s)"
                )

        return out


@ReplacementRules.register(key="contains")
class ContainsRule(ReplacementRule):
    """Replace values that contain a substring (with optional normalization and case sensitivity)."""

    @classmethod
    def apply(cls, series: pd.Series, *, rule: Mapping[str, Any], ctx: RuleContext) -> pd.Series:
        from_value: Any | None = rule.get("from")
        to_value: Any | None = rule.get("to")
        if from_value is None:
            return series

        case_sensitive = True
        for f in rule.get("flags") or []:
            if str(f).lower() in ("i", "ignorecase"):
                case_sensitive = False

        norm: pd.Series[Any] = _normalize_for_match(series, ops=ctx.normalize_ops)
        needle: str = _normalize_scalar(from_value, ops=ctx.normalize_ops)
        contains_mask: pd.Series[bool] = (
            norm.astype("string").fillna(pd.NA).str.contains(needle, case=case_sensitive, regex=False, na=False)
        )

        mask = contains_mask
        if ctx.negate:
            mask = (~contains_mask) & norm.notna()

        if not mask.any():
            if ctx.report_unmatched:
                op = "not_contains" if ctx.negate else "contains"
                logger.info(f"{ctx.entity_name}[replacements]: {ctx.column_name}: {op} matched 0 value(s) for {from_value!r}")
            return series
        if ctx.report_replaced:
            op = "not_contains" if ctx.negate else "contains"
            logger.info(f"{ctx.entity_name}[replacements]: {ctx.column_name}: {op} replaced {int(mask.sum())} value(s)")
        return series.where(~mask, cast(Any, to_value))


@ReplacementRules.register(key="equals")
class EqualsRule(ReplacementRule):
    @classmethod
    def apply(cls, series: pd.Series, *, rule: Mapping[str, Any], ctx: RuleContext) -> pd.Series:
        from_value: Any | None = rule.get("from")
        to_value: Any | None = rule.get("to")

        if not ctx.normalize_ops and ctx.coerce:
            match_series = _coerce_series_for_match(series, coerce=ctx.coerce)
            from_coerced = _coerce_scalar_for_match(from_value, coerce=ctx.coerce)
            equals_mask = (match_series == from_coerced).fillna(False)
            mask = equals_mask
            if ctx.negate:
                mask = (~equals_mask) & match_series.notna()
            if not mask.any():
                if ctx.report_unmatched:
                    op = "not_equals" if ctx.negate else "equals"
                    logger.info(
                        f"{ctx.entity_name}[replacements]: {ctx.column_name}: "
                        f"{op}(coerced={ctx.coerce}) matched 0 value(s) for {from_value!r}"
                    )
                return series
            if ctx.report_replaced:
                op = "not_equals" if ctx.negate else "equals"
                logger.info(
                    f"{ctx.entity_name}[replacements]: {ctx.column_name}: {op}(coerced={ctx.coerce}) replaced {int(mask.sum())} value(s)"
                )
            return series.where(~mask, cast(Any, to_value))

        if not ctx.normalize_ops and not ctx.negate:
            out: pd.Series[Any] = series.replace(to_replace={from_value: to_value})
            if ctx.report_replaced:
                changed = int((series.astype("string") != out.astype("string")).fillna(False).sum())
                logger.info(f"{ctx.entity_name}[replacements]: {ctx.column_name}: equals replaced {changed} value(s)")
            if ctx.report_unmatched and out.equals(series):
                logger.info(f"{ctx.entity_name}[replacements]: {ctx.column_name}: equals matched 0 value(s) for {from_value!r}")
            return out

        if not ctx.normalize_ops and ctx.negate:
            equals_mask = (series == from_value).fillna(False)
            mask = (~equals_mask) & series.notna()
            if not mask.any():
                if ctx.report_unmatched:
                    logger.info(f"{ctx.entity_name}[replacements]: {ctx.column_name}: not_equals matched 0 value(s) for {from_value!r}")
                return series
            if ctx.report_replaced:
                logger.info(f"{ctx.entity_name}[replacements]: {ctx.column_name}: not_equals replaced {int(mask.sum())} value(s)")
            return series.where(~mask, cast(Any, to_value))

        norm: pd.Series[Any] = _normalize_for_match(series, ops=ctx.normalize_ops)
        from_norm: str = _normalize_scalar(from_value, ops=ctx.normalize_ops)
        equals_mask: pd.Series[bool] = (norm == from_norm).fillna(False)
        mask: pd.Series[bool] = equals_mask
        if ctx.negate:
            mask = (~equals_mask) & norm.notna()
        if not mask.any():
            if ctx.report_unmatched:
                op = "not_equals" if ctx.negate else "equals"
                logger.info(f"{ctx.entity_name}[replacements]: {ctx.column_name}: {op}(normalized) matched 0 value(s) for {from_value!r}")
            return series
        if ctx.report_replaced:
            op = "not_equals" if ctx.negate else "equals"
            logger.info(f"{ctx.entity_name}[replacements]: {ctx.column_name}: {op}(normalized) replaced {int(mask.sum())} value(s)")
        return series.where(~mask, cast(Any, to_value))


@ReplacementRules.register(key="startswith")
class StartsWithRule(ReplacementRule):

    @classmethod
    def apply(cls, series: pd.Series, *, rule: Mapping[str, Any], ctx: RuleContext) -> pd.Series:
        from_value: Any | None = rule.get("from")
        to_value: Any | None = rule.get("to")
        if from_value is None:
            return series

        norm: pd.Series[Any] = _normalize_for_match(series, ops=ctx.normalize_ops)
        prefix: str = _normalize_scalar(from_value, ops=ctx.normalize_ops)

        if _is_ignore_case(rule.get("flags")):
            norm = norm.astype("string").str.lower()
            prefix = prefix.lower()

        starts_mask: pd.Series[bool] = norm.astype("string").fillna(pd.NA).str.startswith(prefix, na=False)
        mask = starts_mask
        if ctx.negate:
            mask = (~starts_mask) & norm.notna()

        if not mask.any():
            if ctx.report_unmatched:
                op = "not_startswith" if ctx.negate else "startswith"
                logger.info(f"{ctx.entity_name}[replacements]: {ctx.column_name}: {op} matched 0 value(s) for {from_value!r}")
            return series
        if ctx.report_replaced:
            op = "not_startswith" if ctx.negate else "startswith"
            logger.info(f"{ctx.entity_name}[replacements]: {ctx.column_name}: {op} replaced {int(mask.sum())} value(s)")
        return series.where(~mask, cast(Any, to_value))


@ReplacementRules.register(key="endswith")
class EndsWithRule(ReplacementRule):
    @classmethod
    def apply(cls, series: pd.Series, *, rule: Mapping[str, Any], ctx: RuleContext) -> pd.Series:
        from_value: Any | None = rule.get("from")
        to_value: Any | None = rule.get("to")
        if from_value is None:
            return series

        norm: pd.Series[Any] = _normalize_for_match(series, ops=ctx.normalize_ops)
        suffix: str = _normalize_scalar(from_value, ops=ctx.normalize_ops)

        if _is_ignore_case(rule.get("flags")):
            norm = norm.astype("string").str.lower()
            suffix = suffix.lower()

        ends_mask: pd.Series[bool] = norm.astype("string").fillna(pd.NA).str.endswith(suffix, na=False)
        mask: pd.Series[bool] = ends_mask
        if ctx.negate:
            mask = (~ends_mask) & norm.notna()

        if not mask.any():
            if ctx.report_unmatched:
                op = "not_endswith" if ctx.negate else "endswith"
                logger.info(f"{ctx.entity_name}[replacements]: {ctx.column_name}: {op} matched 0 value(s) for {from_value!r}")
            return series
        if ctx.report_replaced:
            op = "not_endswith" if ctx.negate else "endswith"
            logger.info(f"{ctx.entity_name}[replacements]: {ctx.column_name}: {op} replaced {int(mask.sum())} value(s)")
        return series.where(~mask, cast(Any, to_value))


@ReplacementRules.register(key="in")
class InRule(ReplacementRule):
    @classmethod
    def apply(cls, series: pd.Series, *, rule: Mapping[str, Any], ctx: RuleContext) -> pd.Series:
        from_value: Any | None = rule.get("from")
        to_value: Any | None = rule.get("to")
        if from_value is None:
            return series

        if ctx.normalize_ops:
            match_series: pd.Series[str] = _normalize_for_match(series, ops=ctx.normalize_ops).astype("string")
            values: list[str] = [_normalize_scalar(v, ops=ctx.normalize_ops) for v in _as_sequence(from_value)]
            if _is_ignore_case(rule.get("flags")):
                match_series = match_series.str.lower()
                values = [str(v).lower() for v in values]
        elif ctx.coerce:
            match_series = _coerce_series_for_match(series, coerce=ctx.coerce)
            values = _coerce_values_for_match(from_value, coerce=ctx.coerce)
        else:
            if _is_ignore_case(rule.get("flags")):
                match_series = series.astype("string").str.lower()
                values = [str(v).lower() for v in _as_sequence(from_value)]
            else:
                match_series = series
                values = _as_sequence(from_value)

        mask: pd.Series[bool] = match_series.isin(values).fillna(False)
        if ctx.negate:
            mask = (~mask) & match_series.notna()
        if not mask.any():
            if ctx.report_unmatched:
                op: str = "not_in" if ctx.negate else "in"
                logger.info(f"{ctx.entity_name}[replacements]: {ctx.column_name}: {op} matched 0 value(s) for {from_value!r}")
            return series
        if ctx.report_replaced:
            op: str = "not_in" if ctx.negate else "in"
            logger.info(f"{ctx.entity_name}[replacements]: {ctx.column_name}: {op} replaced {int(mask.sum())} value(s)")
        return series.where(~mask, cast(Any, to_value))


@ReplacementRules.register(key="regex")
class RegexRule(ReplacementRule):
    @classmethod
    def apply(cls, series: pd.Series, *, rule: Mapping[str, Any], ctx: RuleContext) -> pd.Series:
        from_value: Any | None = rule.get("from")
        to_value: Any | None = rule.get("to")
        if from_value is None:
            return series

        pattern: re.Pattern[str] = _compile_regex(from_value, flags_spec=rule.get("flags"))
        norm: pd.Series[Any] = _normalize_for_match(series, ops=ctx.normalize_ops)
        matches: pd.Series[bool] = norm.astype("string").fillna(pd.NA).str.match(pattern, na=False)
        mask: pd.Series[bool] = matches
        if ctx.negate:
            mask = (~matches) & norm.notna()
        if not mask.any():
            if ctx.report_unmatched:
                op = "not_regex" if ctx.negate else "regex"
                logger.info(f"{ctx.entity_name}[replacements]: {ctx.column_name}: {op} matched 0 value(s) for pattern {str(from_value)!r}")
            return series
        if ctx.report_replaced:
            op = "not_regex" if ctx.negate else "regex"
            logger.info(f"{ctx.entity_name}[replacements]: {ctx.column_name}: {op} replaced {int(mask.sum())} value(s)")
        return series.where(~mask, cast(Any, to_value))


@ReplacementRules.register(key="regex_sub")
class RegexSubRule(ReplacementRule):
    """Apply a regex substitution to matching values in the series."""

    @classmethod
    def apply(cls, series: pd.Series, *, rule: Mapping[str, Any], ctx: RuleContext) -> pd.Series:
        from_value: Any | None = rule.get("from")
        to_value: Any | None = rule.get("to")
        if from_value is None:
            return series

        pattern: re.Pattern = _compile_regex(from_value, flags_spec=rule.get("flags"))
        before: pd.Series[str] = series.astype("string")

        # If `to` is explicitly null, treat it as "replace matching cells with NA"
        # (empty string replacement can be achieved with `to: ""`).
        if to_value is None:
            match_mask: pd.Series[bool] = before.fillna(pd.NA).str.contains(pattern, na=False)
            changed_count = int(match_mask.sum())
            if changed_count == 0:
                if ctx.report_unmatched:
                    logger.info(
                        f"{ctx.entity_name}[replacements]: {ctx.column_name}: regex_sub matched 0 value(s) for pattern {str(from_value)!r}"
                    )
                return series
            if ctx.report_replaced:
                logger.info(f"{ctx.entity_name}[replacements]: {ctx.column_name}: regex_sub replaced {changed_count} value(s)")
            return series.where(~match_mask, cast(Any, pd.NA))

        replacement = str(to_value)
        after: pd.Series[str] = before.str.replace(pattern, replacement, regex=True)

        changed_mask: pd.Series[bool] = before.fillna("<NA>") != after.fillna("<NA>")
        changed_count = int(changed_mask.sum())

        if changed_count == 0:
            if ctx.report_unmatched:
                logger.info(
                    f"{ctx.entity_name}[replacements]: {ctx.column_name}: regex_sub matched 0 value(s) for pattern {str(from_value)!r}"
                )
            return series

        if ctx.report_replaced:
            logger.info(f"{ctx.entity_name}[replacements]: {ctx.column_name}: regex_sub replaced {changed_count} value(s)")

        return after


def _normalize_for_match(series: pd.Series, *, ops: Sequence[str]) -> pd.Series:
    out: pd.Series = series.astype("string")
    for op in ops:
        out = _apply_normalize_op_series(out, op)
    return out


def _normalize_scalar(value: Any, *, ops: Sequence[str]) -> str:
    s: str = "" if value is None else str(value)
    for op in ops:
        s = _apply_normalize_op_scalar(s, op)
    return s


def _apply_normalize_op_series(series: pd.Series, op: str) -> pd.Series:
    op = str(op).lower()
    if op == "strip":
        return series.str.strip()
    if op == "lower":
        return series.str.lower()
    if op == "upper":
        return series.str.upper()
    if op in ("collapse_ws", "collapse_whitespace"):
        return series.str.replace(r"\s+", " ", regex=True).str.strip()
    logger.warning(f"normalize: unknown op: {op!r}")
    return series


def _apply_normalize_op_scalar(s: str, op: str) -> str:
    op = str(op).lower()
    if op == "strip":
        return s.strip()
    if op == "lower":
        return s.lower()
    if op == "upper":
        return s.upper()
    if op in ("collapse_ws", "collapse_whitespace"):
        return re.sub(r"\s+", " ", s).strip()
    logger.warning(f"normalize: unknown op: {op!r}")
    return s
