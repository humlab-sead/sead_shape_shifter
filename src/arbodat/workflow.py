from typing import Literal

import click

from src.arbodat.normalizer import ArbodatSurveyNormalizer


def workflow(
    input_csv: str,
    target: str,
    sep: str,
    verbose: bool,
    translate: bool,
    mode: Literal["xlsx", "csv", "db"],
    drop_foreign_keys: bool,
) -> None:

    normalizer: ArbodatSurveyNormalizer = ArbodatSurveyNormalizer.load(path=input_csv, sep=sep)

    if verbose:
        click.echo(f"Loaded {len(normalizer.survey)} rows with {len(normalizer.survey.columns)} columns")
        click.echo("Building normalized tables...")

    normalizer.normalize()

    if drop_foreign_keys:
        normalizer.drop_foreign_key_columns()

    if translate:
        normalizer.translate()

    normalizer.store(target=target, mode=mode)

    if verbose:
        click.echo("\nTable Summary:")
        for name, table in normalizer.data.items():
            click.echo(f"  - {name}: {len(table)} rows")
