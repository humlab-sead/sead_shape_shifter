#!/usr/bin/env python3
"""
Normalize an Arbodat "Data Survey" CSV export into several tables
and write them as sheets in a single Excel file.

Usage:
    python arbodat_normalize_to_excel.py input.csv output.xlsx

Assumptions:
- Each row = one Sample × Taxon (species) record.
- ProbNr identifies a sample; many rows may share the same ProbNr.
- ProjektNr identifies a project.
- BNam (+ TaxAut) identifies a taxon.
"""

import asyncio
import os
from pathlib import Path
from unittest import runner

import click
from click.testing import Result
from loguru import logger

import pandas as pd

from src.configuration.resolve import ConfigValue
from src.configuration.setup import setup_config_store

# ------------- small helpers -------------------------------------------------


def read_arbodat_csv(path: str | Path, sep: str = "\t") -> pd.DataFrame:
    """
    Read Arbodat CSV (usually tab-separated).
    If sep='\t' fails badly, you can change to ',' when calling.
    """
    df: pd.DataFrame = pd.read_csv(path, sep=sep, dtype=str, keep_default_na=False)
    return df


def subset(df: pd.DataFrame, cols: list[str], drop_duplicates: bool = False, raise_if_missing: bool = True) -> pd.DataFrame:
    """Return df with only the columns that actually exist and drop duplicates if requested."""
    if any(c not in df.columns for c in cols):
        missing: list[str] = [c for c in cols if c not in df.columns]
        if raise_if_missing:
            raise ValueError(f"Columns not found in DataFrame: {missing}")
        else:
            logger.warning(f"Columns not found in DataFrame and will be skipped: {missing}")

    existing: list[str] = [c for c in cols if c in df.columns]
    result: pd.DataFrame = df[existing]
    if drop_duplicates:
        result = result.drop_duplicates()
    return result


def add_surrogate_id(df: pd.DataFrame, id_name: str) -> pd.DataFrame:
    """Add an integer surrogate ID starting at 1."""
    df = df.reset_index(drop=True).copy()
    df[id_name] = range(1, len(df) + 1)
    return df


# ------------- build tables --------------------------------------------------


def build_projects(df: pd.DataFrame) -> pd.DataFrame:
    proj: pd.DataFrame = subset(df, ["ProjektNr"]).drop_duplicates()
    proj = add_surrogate_id(proj, "project_id")
    return proj


def build_sites(df: pd.DataFrame, projects: pd.DataFrame) -> pd.DataFrame:
    cols: list[str] = ConfigValue[list[str]]("entities.site.columns").resolve()  # type: ignore[assignment]
    sites: pd.DataFrame = subset(df, cols, drop_duplicates=True)
    sites = sites.merge(projects[["project_id", "ProjektNr"]], on="ProjektNr", how="left")
    sites = add_surrogate_id(sites, "site_id")
    return sites


def build_natural_regions(sites: pd.DataFrame) -> pd.DataFrame:
    cols: list[str] = ConfigValue[list[str]]("entities.natural_regions.columns").resolve()  # type: ignore[assignment]
    nat: pd.DataFrame = subset(sites, cols, drop_duplicates=True)
    nat = add_surrogate_id(nat, "natural_region_id")
    return nat


def attach_natural_region_id(sites: pd.DataFrame, nat: pd.DataFrame) -> pd.DataFrame:
    cols: list[str] = ConfigValue[list[str]]("entities.natural_regions.columns").resolve()  # type: ignore[assignment]
    sites = sites.merge(
        nat[["natural_region_id"] + cols],
        on=cols,
        how="left",
    )
    return sites


def build_features(df: pd.DataFrame, sites: pd.DataFrame) -> pd.DataFrame:
    cols: list[str] = ConfigValue[list[str]]("entities.feature.columns").resolve()  # type: ignore[assignment]
    feat: pd.DataFrame = subset(df, cols, drop_duplicates=True)

    # attach site_id via ProjektNr+Fustel+EVNr
    site_key_columns: list[str] = ConfigValue[list[str]]("entities.site.keys").resolve()  # type: ignore[assignment]
    feat = feat.merge(
        sites[["site_id"] + site_key_columns],
        on=site_key_columns,
        how="left",
    )
    feat = add_surrogate_id(feat, "feature_id")
    return feat


def build_samples(df: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    sample_columns: list[str] = ConfigValue[list[str]]("entities.sample.columns").resolve()  # type: ignore[assignment]
    samples = subset(df, sample_columns, drop_duplicates=True)
    # attach feature_id via ProjektNr+Befu
    feature_keys: list[str] = ConfigValue[list[str]]("entities.feature.keys").resolve()  # type: ignore[assignment]
    samples: pd.DataFrame = samples.merge(
        features[["feature_id"] + feature_keys],
        on=feature_keys,
        how="left",
    )
    samples = add_surrogate_id(samples, "sample_id")
    return samples


def build_sample_processing(samples: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
    """Build per-sample processing table, if fraction columns exist."""
    frac_cols: list[str] = ConfigValue[list[str]]("entities.sample_processing.columns").resolve()  # type: ignore[assignment]
    sample_keys: list[str] = ConfigValue[list[str]]("entities.sample.keys").resolve()  # type: ignore[assignment]
    cols: list[str] = sample_keys + [c for c in frac_cols if c in df.columns]
    if len(cols) <= 3:
        return pd.DataFrame(columns=["sample_id"])  # no fraction data

    tmp: pd.DataFrame = subset(df, cols, drop_duplicates=True)
    # attach sample_id
    tmp = tmp.merge(
        samples[["sample_id"] + sample_keys],
        on=sample_keys,
        how="left",
    )
    # only keep one row per sample_id
    tmp = tmp.drop_duplicates(subset=["sample_id"])
    return tmp


def build_taxa(df: pd.DataFrame) -> pd.DataFrame:
    cols: list[str] =ConfigValue[list[str]]("entities.taxa.columns").resolve()  # type: ignore[assignment]
    taxa: pd.DataFrame = subset(df, cols, drop_duplicates=True)
    taxa = add_surrogate_id(taxa, "taxon_id")
    return taxa


def build_sample_taxa(df: pd.DataFrame, samples: pd.DataFrame, taxa: pd.DataFrame) -> pd.DataFrame:
    """
    Fact table: one row per sample × taxon combination.
    """
    # attach sample_id
    sample_keys: list[str] = ConfigValue[list[str]]("entities.sample.keys").resolve()  # type: ignore[assignment]
    tmp: pd.DataFrame = df.merge(
        samples[["sample_id"] + sample_keys],
        on=sample_keys,
        how="left",
    )
    # attach taxon_id
    taxon_keys: list[str] = ConfigValue[list[str]]("entities.taxa.keys").resolve()  # type: ignore[assignment]
    tmp = tmp.merge(
        taxa[["taxon_id"] + taxon_keys],
        on=taxon_keys,
        how="left",
    )

    cols: list[str] = [
        "sample_id",
        "taxon_id",
        "PCODE",
        "RTyp",
        "RTypGrup",
        "Zust",
        "Zustand",
        "SumFAnzahl",
        "SumFGewicht",
        "geschätzt",
        "SumFFrag",
        "SumPflR",
        "Vorfu",
        "BotBest",
        "BestJa",
        "cf",
        "Anmerkung",
        "BotBear",
    ]
    st: pd.DataFrame = subset(tmp, cols, drop_duplicates=False).copy()
    st = add_surrogate_id(st, "sample_taxon_id")
    return st


def build_chronology(samples: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    cols: list[str] =  ConfigValue[list[str]]("entities.chronology.columns").resolve()  # type: ignore[assignment]
    chron: pd.DataFrame = subset(samples, cols, drop_duplicates=True)
    chron = add_surrogate_id(chron, "chronology_id")

    # Attach chronology_id back to samples
    samples_with_chron: pd.DataFrame = samples.merge(chron, on=cols, how="left")
    return chron, samples_with_chron


def build_natural_region_for_sites(sites: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    nat: pd.DataFrame = build_natural_regions(sites)
    sites2: pd.DataFrame = attach_natural_region_id(sites, nat)
    return nat, sites2


def build_ecocode(taxa: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
    eco_cols: list[str] = ConfigValue[list[str]]("entities.ecocode.columns").resolve()  # type: ignore[assignment]
    eco: pd.DataFrame = subset(df, eco_cols, drop_duplicates=False).drop_duplicates(subset=["BNam", "TaxAut"])
    # attach taxon_id
    taxon_keys: list[str] = ConfigValue[list[str]]("entities.taxa.keys").resolve()  # type: ignore[assignment]
    eco = eco.merge(
        taxa[["taxon_id"] + taxon_keys],
        on=taxon_keys,
        how="left",
    )
    # move taxon_id first and drop name columns if you like
    eco = eco.drop(columns=taxon_keys)
    eco = eco.drop_duplicates(subset=["taxon_id"])
    return eco


def build_use_categories(taxa: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
    cols: list[str] =ConfigValue[list[str]]("entities.use_categories.columns").resolve()  # type: ignore[assignment]
    use: pd.DataFrame = subset(df, cols, drop_duplicates=False).drop_duplicates(subset=["BNam", "TaxAut"])
    taxon_keys: list[str] = ConfigValue[list[str]]("entities.taxa.keys").resolve()  # type: ignore[assignment]
    use = use.merge(
        taxa[["taxon_id"] + taxon_keys],
        on=taxon_keys,
        how="left",
    )
    use = use.drop(columns=taxon_keys)
    use = use.drop_duplicates(subset=["taxon_id"])
    return use


def build_actors(df: pd.DataFrame) -> pd.DataFrame:
    cols: list[str] = ConfigValue[list[str]]("entities.actors.columns").resolve()  # type: ignore[assignment]
    act: pd.DataFrame = subset(df, cols, drop_duplicates=True)
    act = add_surrogate_id(act, "actor_record_id")
    return act


@click.command()
@click.argument("input_csv")  # type=click.Path(exists=True, dir_okay=False, readable=True))
@click.argument("output_xlsx")  # type=click.Path(dir_okay=False, writable=True))
@click.option("--sep", "-s", default=";", show_default=True, help='Field separator character. Use "," for comma-separated files.')
@click.option("--config-file", "-c", type=click.Path(exists=True, dir_okay=False, readable=True), help="Path to configuration file.")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output.")
def main(input_csv: str, output_xlsx: str, sep: str, config_file: str, verbose: bool) -> None:
    """
    Normalize an Arbodat "Data Survey" CSV export into several tables.

    Reads INPUT_CSV and writes normalized data as multiple sheets to OUTPUT_XLSX.

    The input CSV should contain one row per Sample × Taxon combination, with
    columns identifying projects, sites, features, samples, and taxa.
    """
    if verbose:
        click.echo(f"Reading Arbodat CSV from: {input_csv}")
        click.echo(f"Using separator: {repr(sep)}")

    if config_file:
        click.echo(f"Using configuration file: {config_file}")

    df: pd.DataFrame = read_arbodat_csv(input_csv, sep=sep)

    if verbose:
        click.echo(f"Loaded {len(df)} rows with {len(df.columns)} columns")
        click.echo("Building normalized tables...")

    if not config_file:
        config_file = os.path.join(os.path.dirname(__file__), "config.yml")

    if not config_file or not Path(config_file).exists():
        raise FileNotFoundError(f"Configuration file not found: {config_file or 'undefined'}")

    asyncio.run(setup_config_store(config_file))

    d = ConfigValue("entities.site.columns").resolve()
    projects: pd.DataFrame = build_projects(df)
    sites: pd.DataFrame = build_sites(df, projects)
    natural_regions: pd.DataFrame
    sites: pd.DataFrame
    natural_regions, sites = build_natural_region_for_sites(sites)
    features: pd.DataFrame = build_features(df, sites)
    samples: pd.DataFrame = build_samples(df, features)
    taxa: pd.DataFrame = build_taxa(df)
    sample_taxa: pd.DataFrame = build_sample_taxa(df, samples, taxa)
    sample_processing: pd.DataFrame = build_sample_processing(samples, df)
    chronology: pd.DataFrame
    samples: pd.DataFrame
    chronology, samples = build_chronology(samples)
    ecocode: pd.DataFrame = build_ecocode(taxa, df)
    use_category: pd.DataFrame = build_use_categories(taxa, df)
    actors: pd.DataFrame = build_actors(df)

    if verbose:
        click.echo("\nTable Summary:")
        click.echo(f"  - projects: {len(projects)} rows")
        click.echo(f"  - sites: {len(sites)} rows")
        click.echo(f"  - natural_regions: {len(natural_regions)} rows")
        click.echo(f"  - features: {len(features)} rows")
        click.echo(f"  - samples: {len(samples)} rows")
        click.echo(f"  - taxa: {len(taxa)} rows")
        click.echo(f"  - sample_taxa: {len(sample_taxa)} rows")
        click.echo(f"  - chronology: {len(chronology)} rows")
        click.echo(f"\nWriting to Excel: {output_xlsx}")

    # Write to Excel
    with pd.ExcelWriter(output_xlsx, engine="openpyxl") as writer:
        projects.to_excel(writer, sheet_name="projects", index=False)
        sites.to_excel(writer, sheet_name="sites", index=False)
        natural_regions.to_excel(writer, sheet_name="natural_regions", index=False)
        features.to_excel(writer, sheet_name="features", index=False)
        samples.to_excel(writer, sheet_name="samples", index=False)
        taxa.to_excel(writer, sheet_name="taxa", index=False)
        sample_taxa.to_excel(writer, sheet_name="sample_taxa", index=False)
        sample_processing.to_excel(writer, sheet_name="sample_processing", index=False)
        chronology.to_excel(writer, sheet_name="chronology", index=False)
        ecocode.to_excel(writer, sheet_name="ecocode", index=False)
        use_category.to_excel(writer, sheet_name="use_category", index=False)
        actors.to_excel(writer, sheet_name="actors", index=False)

    click.secho(f"✓ Successfully written normalized workbook to {output_xlsx}", fg="green")


if __name__ == "__main__":
    # main()
    from click.testing import CliRunner

    runner = CliRunner()
    result: Result = runner.invoke(main, ["--sep", ";", "--config-file", "src/arbodat/config.yml", "src/arbodat/arbodat_mal_elena_input.csv", "output.xlsx"])

    print(result.output)
