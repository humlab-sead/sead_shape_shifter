import pandas as pd
from loguru import logger

# pylint: disable=line-too-long


def extract_translation_map(
    fields_metadata: list[dict[str, str]], from_field: str = "arbodat_field", to_field: str = "english_column_name"
) -> dict[str, str]:
    """Get translation map from config."""

    if not fields_metadata:
        return {}

    if any(c not in fields_metadata[0] for c in [from_field, to_field]):
        logger.warning(f"[translation] Translation config is missing required keys '{from_field}' and '{to_field}'. Skipping translation.")
        return {}

    translations_map: dict[str, str] = {t[from_field]: t[to_field] for t in fields_metadata if from_field in t and to_field in t}

    return translations_map


def translate(data: dict[str, pd.DataFrame], translations_map: dict[str, str] | None) -> dict[str, pd.DataFrame]:
    """Translate column names using translation from config."""

    if not translations_map:
        return data

    def fx(col: str, columns: list[str]) -> str:
        translated_column: str = translations_map.get(col, col)
        if translated_column in columns:
            return col
        return translated_column

    for entity, table in data.items():
        columns: list[str] = table.columns.tolist()
        table.columns = [fx(col, columns) for col in columns]
        data[entity] = table

    return data
