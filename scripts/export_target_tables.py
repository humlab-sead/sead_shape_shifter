"""Export target-model entities from a PostgreSQL schema to one Excel workbook."""

from pathlib import Path

import click
import pandas as pd
import psycopg
import sqlalchemy
import yaml
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.styles import Font
from openpyxl.worksheet.worksheet import Worksheet
from psycopg import sql

ROLES = ("bridge", "classifier", "fact", "lookup")
DEFAULT_FONT_NAME = "Calibri"
DEFAULT_FONT_SIZE = 10
DEFAULT_MODEL = Path(__file__).resolve().parent.parent / "resources" / "target_models" / "sead_superset_model.yml"


def _vault() -> dict[str, str]:
    """Read the KEY=VALUE credential file for the SEAD staging cluster.

    Returns an empty dict when the file does not exist.
    """
    path = Path.home().joinpath("vault/sead_staging@staging_cluster")
    if not path.exists():
        return {}
    lines: list[str] = path.read_text(encoding="utf-8").splitlines()
    return {k: v for k, _, v in (line.partition("=") for line in lines if "=" in line)}


def load_entities(model_path: Path, roles: tuple[str, ...]) -> dict[str, dict]:
    """Return the model entities that have a target table and one of the selected roles.

    An empty roles tuple keeps every role.
    """
    model: dict = yaml.safe_load(model_path.read_text(encoding="utf-8"))
    entities: dict[str, dict] = model.get("entities") or {}
    candidates = [(k, v) for k, v in entities.items() if not roles or v.get("role") in roles]
    selected = dict(sorted((k, v) for k, v in candidates if v.get("target_table")))
    skipped = [k for k, v in candidates if not v.get("target_table")]
    if skipped:
        click.echo(f"Skipping entities without target_table: {', '.join(skipped)}")
    return selected


def sheet_name(entity_name: str) -> str:
    """Keep sheet names within Excel's 31-character limit."""
    return entity_name[:31]


def format_sheet(worksheet: Worksheet, max_width: int = 60) -> None:
    """Apply the default font, bold the header row, and size columns to their content.

    pandas writes an explicit font on every cell it exports, so each cell is
    restyled here to keep the workbook on Calibri 10.
    """
    font = Font(name=DEFAULT_FONT_NAME, size=DEFAULT_FONT_SIZE)
    header_font = Font(name=DEFAULT_FONT_NAME, size=DEFAULT_FONT_SIZE, bold=True)
    for row in worksheet.iter_rows():
        for cell in row:
            cell.font = header_font if cell.row == 1 else font
    for column in worksheet.columns:
        longest = max((len(str(cell.value)) for cell in column if cell.value is not None), default=8)
        worksheet.column_dimensions[column[0].column_letter].width = min(longest + 2, max_width)


@click.command()
@click.argument("output", type=click.Path(dir_okay=False, writable=True, path_type=Path))
@click.option("--model", "model_path", type=click.Path(exists=True, dir_okay=False, path_type=Path),
              default=DEFAULT_MODEL, show_default=True, help="Target model YAML file defining the entities to export.")
@click.option("--role", "roles", multiple=True, type=click.Choice(ROLES),
              help="Only export entities with this role. Repeatable; the default exports all roles.")
@click.option("--host", help="Database host. Defaults to the vault file when it exists.")
@click.option("--port", type=int, help="Database port. Defaults to the vault file when it exists.")
@click.option("--dbname", help="Database name. Defaults to the vault file when it exists.")
@click.option("--user", help="Database user. Defaults to the vault file when it exists.")
@click.option("--schema", default="public", show_default=True, help="Schema holding the target tables.")
def main(output: Path, model_path: Path, roles: tuple[str, ...], host: str | None, port: int | None,
         dbname: str | None, user: str | None, schema: str) -> None:
    """Export the target-model entities' tables to an Excel workbook.

    OUTPUT is the workbook file to write. Entities are read from the target
    model YAML and filtered by --role; each entity's target_table is queried
    for exactly the columns listed in the model. Connection settings default
    to the vault file ~/vault/sead_staging@staging_cluster when it exists;
    --host, --port, --dbname and --user override single values from it.
    A password missing from the vault falls back to ~/.pgpass.
    """
    entities: dict[str, dict] = load_entities(model_path, roles)
    click.echo(f"Selected {len(entities)} entities for roles {roles or ROLES}")

    vault: dict[str, str] = _vault()
    con_args: dict[str, str | int] = {}
    if vault:
        con_args = {
            "host": vault["HOST"],
            "port": int(vault["PORT"]),
            "dbname": vault["DATABASE"],
            "user": vault["USER"],
        }
        password: str | None = vault.get("PASSWORD")
        if password:
            con_args["password"] = password
    for key, value in (("host", host), ("port", port), ("dbname", dbname), ("user", user)):
        if value is not None:
            con_args[key] = value
    missing = [key for key in ("host", "dbname", "user") if key not in con_args]
    if missing:
        raise click.UsageError(f"Missing connection settings: {', '.join(missing)}. Pass them as options or create the vault file.")

    with psycopg.connect(**con_args) as conn:  # type: ignore
        # pandas supports SQLAlchemy connectables, not raw psycopg3 connections.
        engine = sqlalchemy.create_engine("postgresql+psycopg://", creator=lambda: conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE table_schema = %s
                """,
                (schema,),
            )
            db_columns: dict[str, set[str]] = {}
            for table, column in cur.fetchall():
                db_columns.setdefault(str(table), set()).add(str(column))

            with engine.connect() as sa_conn, pd.ExcelWriter(output, engine="openpyxl") as writer:
                # The Normal style is the default font for cells without an explicit one.
                writer.book._named_styles["Normal"].font = Font(name=DEFAULT_FONT_NAME, size=DEFAULT_FONT_SIZE)
                for name, entity in entities.items():
                    table: str = entity["target_table"]
                    if table not in db_columns:
                        click.echo(f"  SKIPPED: {name}: table {schema}.{table} not found")
                        continue
                    columns: list[str] = [c for c in entity["columns"] if c in db_columns[table]]
                    absent: list[str] = [c for c in entity["columns"] if c not in db_columns[table]]
                    if absent:
                        click.echo(f"  WARNING: {name}: columns not in {schema}.{table}, exporting without them: {', '.join(absent)}")
                    if not columns:
                        click.echo(f"  SKIPPED: {name}: no model columns found in {schema}.{table}")
                        continue
                    # The primary key leads the sheet and orders the rows.
                    public_id: str | None = entity.get("public_id")
                    order_by: str | None = public_id if public_id in db_columns[table] else None
                    if public_id and not order_by:
                        click.echo(f"  WARNING: {name}: primary key {public_id} not in {schema}.{table}, exporting without it")
                    if order_by:
                        columns = [public_id] + [c for c in columns if c != public_id]
                    query = (
                        sql.SQL("SELECT {} FROM {}")
                        .format(
                            sql.SQL(", ").join(sql.Identifier(c) for c in columns),
                            sql.Identifier(schema, table),
                        )
                        .as_string(conn)
                    )
                    if order_by:
                        query = sql.SQL("{} ORDER BY {}").format(sql.SQL(query), sql.Identifier(order_by)).as_string(conn)  # type: ignore
                    frame: pd.DataFrame = pd.read_sql_query(sqlalchemy.text(query), sa_conn)
                    # Excel rejects control characters that can occur in database text.
                    for column in frame.select_dtypes(include="object").columns:
                        frame[column] = frame[column].map(lambda v: ILLEGAL_CHARACTERS_RE.sub("", v) if isinstance(v, str) else v)
                    sheet = sheet_name(name)
                    frame.to_excel(writer, sheet_name=sheet, index=False)
                    format_sheet(writer.sheets[sheet])
                    click.echo(f"  {name} ({table}): {len(frame)} rows")

    click.echo(f"Workbook written: {output}")


if __name__ == "__main__":
    main()
