#!/usr/bin/env python3
"""
Normalize an Arbodat "Data Survey" CSV export into several tables
and write them as sheets in a single Excel file.

Usage:
    python arbodat_normalize_to_excel.py input.csv output.xlsx

"""

import asyncio
import os
from pathlib import Path
from typing import Any, Literal
from unittest import runner

import click
import pandas as pd
from click.testing import Result
from loguru import logger

from src.configuration.resolve import ConfigValue
from src.configuration.setup import setup_config_store


def add_surrogate_id(target: pd.DataFrame, id_name: str) -> pd.DataFrame:
    """Add an integer surrogate ID starting at 1."""
    target = target.reset_index(drop=True).copy()
    target[id_name] = range(1, len(target) + 1)
    return target


def get_subset(
    source: pd.DataFrame,
    columns: list[str],
    drop_duplicates: bool | list[str] = False,
    raise_if_missing: bool = True,
    surrogate_id: str | None = None,
) -> pd.DataFrame:
    """Return data with only the columns that actually exist and drop duplicates if requested."""
    if source is None:
        raise ValueError("Source DataFrame must be provided")

    if any(c not in source.columns for c in columns):
        missing: list[str] = [c for c in columns if c not in source.columns]
        if raise_if_missing:
            raise ValueError(f"Columns not found in DataFrame: {missing}")
        else:
            logger.warning(f"Columns not found in DataFrame and will be skipped: {missing}")

    existing: list[str] = [c for c in columns if c in source.columns]
    result: pd.DataFrame = source[existing]

    if drop_duplicates:
        if isinstance(drop_duplicates, list):
            result = result.drop_duplicates(subset=drop_duplicates)
        else:
            result = result.drop_duplicates()

    if surrogate_id and surrogate_id not in result.columns:
        result = add_surrogate_id(result, surrogate_id)

    return result


class ArbodatSurveyNormalizer:

    def __init__(self, df: pd.DataFrame):
        self.data: dict[str, pd.DataFrame] = {"survey": df}

    @property
    def survey(self) -> pd.DataFrame:
        return self.data["survey"]

    def resolve_source(self, source: pd.DataFrame | str | None = None) -> pd.DataFrame:
        if source is None:
            return self.survey
        elif isinstance(source, str):
            if not source in self.data:
                raise ValueError(f"Source DataFrame '{source}' not found in stored data")
            return self.data[source]
        else:
            return source

    def register(self, name: str, df: pd.DataFrame) -> pd.DataFrame:
        self.data[name] = df
        return df

    def add_surrogate_id(self, target: pd.DataFrame, id_name: str) -> pd.DataFrame:
        """Add an integer surrogate ID starting at 1."""
        target = target.reset_index(drop=True).copy()
        target[id_name] = range(1, len(target) + 1)
        return target

    @staticmethod
    def load(path: str | Path, sep: str = "\t") -> "ArbodatSurveyNormalizer":
        """
        Read Arbodat CSV (usually tab-separated).
        If sep='\t' fails badly, you can change to ',' when calling.
        """
        df: pd.DataFrame = pd.read_csv(path, sep=sep, dtype=str, keep_default_na=False)
        return ArbodatSurveyNormalizer(df)

    def get_config_value[T](self, entity: str, key: str, default: T = None) -> T | None:
        """Get configuration value for the given key."""
        return ConfigValue[T](f"entities.{entity}.{key}").resolve() or default

    def extract_entity(
        self,
        entity_name: str,
        *,
        source: pd.DataFrame | str | None = None,
        surrogate_id: str | None = None,
        columns: list[str] | None = None,
        extra_fk_columns: list[str] | None = None,
        drop_duplicates: bool | list[str] | None = None,
    ) -> pd.DataFrame:
        """Extract entity DataFrame based on configuration."""

        source = self.resolve_source(source)

        if columns is None:
            columns = self.get_config_value(entity_name, "columns", default=[])

        if not isinstance(columns, list) or not all(isinstance(c, str) for c in columns):
            raise ValueError(f"Invalid columns configuration for entity '{entity_name}': {columns}")

        if surrogate_id is None:
            surrogate_id = self.get_config_value(entity_name, "surrogate_id")

        if drop_duplicates is None:
            drop_duplicates = self.get_config_value(entity_name, "options.drop_duplicates", default=bool(drop_duplicates)) or False

        if extra_fk_columns is None:
            foreign_keys: list[dict[str, Any]] = self.get_config_value(entity_name, "foreign_keys", default=[]) or []
            if foreign_keys is not None:
                extra_columns: set[str] = set()
                for fk in foreign_keys:
                    extra_columns = extra_columns.union(set(fk.get("local_keys", [])))
                extra_fk_columns = list(extra_columns)

        if extra_fk_columns:
            # extra foreign key columns to include for future joins to foreign table(s)
            columns = columns + [column for column in extra_fk_columns if column not in columns]

        data: pd.DataFrame = get_subset(source, columns, drop_duplicates=drop_duplicates, surrogate_id=surrogate_id)

        return data

    def get_dependencies(self, entity_name: str) -> set[str]:
        """Get dependencies for the given entity."""
        return self.get_config_value(entity_name, "depends_on", default=set()) or set()

    def normalize(self) -> None:
        """Extract all configured entities and store them."""
        unprocessed: list[str] = list(set(ConfigValue[list[str]]("entities").resolve() or []))
        while len(unprocessed) > 0:

            entity: str = unprocessed[0]
            unprocessed = unprocessed[1:]

            if entity in self.data:
                continue

            depends_on: list[str] = self.get_dependencies(entity)
            if not all(d in self.data for d in depends_on):
                unprocessed.append(entity)
                continue

            logger.info(f"normalizing entity '{entity}'...")

            data: pd.DataFrame = self.extract_entity(entity)

            self.register(entity, data)

    def link(self, is_final: bool = False) -> None:
        """Link entities based on foreign key configuration."""
        for entity_name in self.data.keys():
            foreign_keys: list[dict[str, Any]] = self.get_config_value(entity_name, "options.foreign_keys", default=[]) or []
            for fk in foreign_keys:
                local_keys: list[str] = fk.get("local_keys", [])
                remote_keys: list[str] = fk.get("remote_keys", [])
                remote_entity: str = fk.get("entity", "")

                remote_id: str | None = self.get_config_value(remote_entity, "surrogate_id", default=f"{remote_entity}_id")
                if remote_entity not in self.data or remote_id is None:
                    raise ValueError(f"Remote entity '{remote_entity}' or surrogate_id not found for linking with '{entity_name}'")

                local_df: pd.DataFrame = self.data[entity_name]
                remote_df: pd.DataFrame = self.data[remote_entity]

                # Check that linking keys exist in both dataframes
                for key in local_keys:
                    if key not in local_df.columns:
                        if is_final:
                            raise ValueError(f"Local key '{key}' not found in entity '{entity_name}'")
                        logger.info(f"Deferring link since local key '{key}' not found in entity '{entity_name}'")
                        continue

                for key in remote_keys:
                    if key not in remote_df.columns:
                        if is_final:
                            raise ValueError(f"Remote key '{key}' not found in entity '{remote_entity}'")
                        logger.info(f"Deferring link since remote key '{key}' not found in entity '{remote_entity}'")
                        continue

                if remote_id in local_df.columns:
                    logger.info(f"Entity '{entity_name}' already has foreign key column '{remote_id}'")
                    continue

                # Perform the merge to link entities
                linked_df: pd.DataFrame = local_df.merge(
                    remote_df[[remote_id] + remote_keys],
                    left_on=local_keys,
                    right_on=remote_keys,
                    how="left",
                    suffixes=("", f"_{remote_entity}"),
                )

                self.data[entity_name] = linked_df

        # link: site -> project
        # sites = sites.merge(projects[["project_id", "ProjektNr"]], on="ProjektNr", how="left")

        # link: site -> natural_region
        # columns: list[str] = ConfigValue[list[str]]("entities.natural_regions.columns").resolve()  # type: ignore[assignment]
        # sites = sites.merge(nat[["natural_region_id"] + columns], on=columns, how="left")

        # link: feature -> site via ProjektNr+Fustel+EVNr
        # site_key_columns: list[str] = ConfigValue[list[str]]("entities.site.keys").resolve()  # type: ignore[assignment]
        # feat = feat.merge(sites[["site_id"] + site_key_columns], on=site_key_columns, how="left")

        # link: sample -> feature via ProjektNr+Befu
        # feature_keys: list[str] = ConfigValue[list[str]]("entities.feature.keys").resolve()  # type: ignore[assignment]
        # samples: pd.DataFrame = samples.merge(
        #     features[["feature_id"] + feature_keys],
        #     on=feature_keys,
        #     how="left",
        # )

        # link: chronology -> sample via sample keys
        #       Attach chronology_id back to samples
        #       Possibly reverse: attach sample_id to chronology
        # samples_with_chron: pd.DataFrame = samples.merge(chron, on=cols, how="left")
        # return chron, samples_with_chron

        # sample -> sample_processing
        # def build_sample_processing(self) -> pd.DataFrame:
        #     """Build per-sample processing table, if fraction columns exist."""
        #     frac_cols: list[str] = ConfigValue[list[str]]("entities.sample_processing.columns").resolve()  # type: ignore[assignment]
        #     sample_keys: list[str] = ConfigValue[list[str]]("entities.sample.keys").resolve()  # type: ignore[assignment]
        #     cols: list[str] = sample_keys + [c for c in frac_cols if c in self.survey.columns]
        #     sample_methods: pd.DataFrame = get_subset(source=self.survey, columns=cols, drop_duplicates=True)
        #     samples: pd.DataFrame = self.data["sample"]
        #     sample_methods = sample_methods.merge( samples[["sample_id"] + sample_keys], on=sample_keys, how="left" )
        #     sample_methods = sample_methods.drop_duplicates(subset=["sample_id"])
        #     return sample_methods

    def store(self, target: str, mode: Literal["xlsx", "csv"]) -> None:
        """Write to Excel or CSV based on the specified mode."""
        if mode == "xlsx":
            with pd.ExcelWriter(target, engine="openpyxl") as writer:
                for entity_name, table in self.data.items():
                    table.to_excel(writer, sheet_name=entity_name, index=False)
        elif mode == "csv":
            output_dir = Path(target)
            output_dir.mkdir(parents=True, exist_ok=True)
            for entity_name, table in self.data.items():
                table.to_csv(output_dir / f"{entity_name}.csv", index=False)
        else:
            raise ValueError(f"Unsupported storage mode: {mode}")

    def unnest(self) -> None:
        """Unnest data frames based on configuration."""
        for entity, table in self.data.items():

            unnest_config: dict[str, Any] = self.get_config_value(entity, "unnest", default={}) or {}

            if not unnest_config:
                continue

            id_vars: list[str] = unnest_config.get("id_vars", [])
            value_vars: list[str] = unnest_config.get("value_vars", [])
            var_name: str = unnest_config.get("var_name", "variable")
            value_name: str = unnest_config.get("value_name", "value")

            table_unnested: pd.DataFrame = pd.melt(table, id_vars=id_vars, value_vars=value_vars, var_name=var_name, value_name=value_name)
            self.data[entity] = table_unnested

    def translate(self) -> None:
        """Translate Arbodat column names to english snake-cased names."""
        translations: dict[str, str] = ConfigValue[dict[str, str]]("translations").resolve() or {}

        def fx(col: str) -> str:
            return translations.get(col, col)

        for entity, table in self.data.items():
            columns: list[str] = table.columns.tolist()
            translated_columns: list[str] = [fx(col) for col in columns]
            table.columns = translated_columns
            self.data[entity] = table

    def drop_foreign_key_columns(self) -> None:
        """Drop foreign key columns used for linking that are no longer needed after linking. Keep if in columns list."""
        for entity_name in self.data.keys():
            columns: list[str] = self.get_config_value(entity_name, "columns", default=[]) or []
            foreign_keys: list[dict[str, Any]] = self.get_config_value(entity_name, "options.foreign_keys", default=[]) or []
            fk_columns: set[str] = set()
            for fk in foreign_keys:
                local_keys: list[str] = fk.get("local_keys", [])
                fk_columns.update(key for key in local_keys if key not in columns)
            if fk_columns:
                table: pd.DataFrame = self.data[entity_name]
                table = table.drop(columns=fk_columns, errors="ignore")
                self.data[entity_name] = table


@click.command()
@click.argument("input_csv")  # type=click.Path(exists=True, dir_okay=False, readable=True))
@click.argument("target")  # type=click.Path(dir_okay=False, writable=True))
@click.option("--sep", "-s", default=";", show_default=True, help='Field separator character. Use "," for comma-separated files.')
@click.option("--config-file", "-c", type=click.Path(exists=True, dir_okay=False, readable=True), help="Path to configuration file.")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output.")
@click.option("--translate", "-t", is_flag=True, help="Enable translation.")
@click.option("--mode", "-m", type=click.Choice(["xlsx", "csv"]), default="xlsx", show_default=True, help="Output file format.")
@click.option("--drop-foreign-keys", "-d", is_flag=True, help="Drop foreign key columns after linking.")
def main(
    input_csv: str,
    target: str,
    sep: str,
    config_file: str,
    verbose: bool,
    translate: bool,
    mode: Literal["xlsx", "csv"],
    drop_foreign_keys: bool,
) -> None:
    """
    Normalize an Arbodat "Data Survey" CSV export into several tables.

    Reads INPUT_CSV and writes normalized data as multiple sheets to TARGET.

    The input CSV should contain one row per Sample × Taxon combination, with
    columns identifying projects, sites, features, samples, and taxa.
    """
    if verbose:
        click.echo(f"Reading Arbodat CSV from: {input_csv}")
        click.echo(f"Using separator: {repr(sep)}")

    if config_file:
        click.echo(f"Using configuration file: {config_file}")

    if not config_file:
        config_file = os.path.join(os.path.dirname(__file__), "config.yml")

    if not config_file or not Path(config_file).exists():
        raise FileNotFoundError(f"Configuration file not found: {config_file or 'undefined'}")

    asyncio.run(setup_config_store(config_file))

    normalizer: ArbodatSurveyNormalizer = ArbodatSurveyNormalizer.load(path=input_csv, sep=sep)

    if verbose:
        click.echo(f"Loaded {len(normalizer.survey)} rows with {len(normalizer.survey.columns)} columns")
        click.echo("Building normalized tables...")

    normalizer.normalize()
    normalizer.link()

    if translate:
        normalizer.translate()

    if drop_foreign_keys:
        normalizer.drop_foreign_key_columns()

    normalizer.unnest()

    normalizer.link(is_final=True)

    normalizer.store(target=target, mode=mode)

    if verbose:
        click.echo("\nTable Summary:")
        for name, table in normalizer.data.items():
            click.echo(f"  - {name}: {len(table)} rows")

    click.secho(f"✓ Successfully written normalized workbook to {target}", fg="green")


if __name__ == "__main__":
    # main()
    from click.testing import CliRunner

    runner = CliRunner()
    result: Result = runner.invoke(
        main,
        [
            "--sep",
            ";",
            "--translate",
            "--config-file",
            "src/arbodat/config.yml",
            "src/arbodat/arbodat_mal_elena_input.csv",
            "output.xlsx",
        ],
    )

    print(result.output)
