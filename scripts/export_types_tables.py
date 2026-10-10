"""Export all *_types tables from a PostgreSQL schema to one Excel workbook."""

from pathlib import Path

import click
import pandas as pd
import psycopg
from psycopg import sql


def _vault() -> dict[str, str]:
    """Read the KEY=VALUE credential file for the SEAD staging cluster.

    Returns an empty dict when the file does not exist.
    """
    path = Path.home().joinpath("vault/sead_staging@staging_cluster")
    if not path.exists():
        return {}
    lines: list[str] = path.read_text(encoding="utf-8").splitlines()
    return {k: v for k, _, v in (line.partition("=") for line in lines if "=" in line)}


QUERY = """
SELECT table_name
FROM information_schema.tables
WHERE table_schema = %s
  AND table_type = 'BASE TABLE'
  AND table_name LIKE '%%\\_types'
ORDER BY table_name
"""


def sheet_name(table_name: str) -> str:
    """Keep sheet names within Excel's 31-character limit by dropping the tbl_ prefix."""
    name = table_name.removeprefix("tbl_")
    return name[:31]


@click.command()
@click.argument("output", type=click.Path(dir_okay=False, writable=True, path_type=Path))
@click.option("--host", help="Database host. Defaults to the vault file when it exists.")
@click.option("--port", type=int, help="Database port. Defaults to the vault file when it exists.")
@click.option("--dbname", help="Database name. Defaults to the vault file when it exists.")
@click.option("--user", help="Database user. Defaults to the vault file when it exists.")
@click.option("--schema", default="public", show_default=True, help="Schema containing the *_types tables.")
def main(output: Path, host: str | None, port: int | None, dbname: str | None, user: str | None, schema: str) -> None:
    """Export every table named *_types in SCHEMA to an Excel workbook.

    OUTPUT is the workbook file to write. Connection settings default to the
    vault file ~/vault/sead_staging@staging_cluster when it exists; the
    --host, --port, --dbname and --user options override single values from it.
    A password missing from the vault falls back to ~/.pgpass.
    """
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
        with conn.cursor() as cur:
            cur.execute(QUERY, (schema,))
            tables: list[str] = [str(row[0]) for row in cur.fetchall()]
            click.echo(f"Found {len(tables)} tables: {', '.join(tables)}")

            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                for table in tables:
                    query = sql.SQL("SELECT * FROM {}").format(sql.Identifier(schema, table)).as_string(conn)
                    frame: pd.DataFrame = pd.read_sql_query(query, conn)  # type: ignore
                    frame = frame.drop(columns=["date_updated"], errors="ignore")
                    frame.to_excel(writer, sheet_name=sheet_name(table), index=False)
                    click.echo(f"  {table}: {len(frame)} rows")

    click.echo(f"Workbook written: {output}")


if __name__ == "__main__":
    main()  # type: ignore ; pylint: disable=no-value-for-parameter
