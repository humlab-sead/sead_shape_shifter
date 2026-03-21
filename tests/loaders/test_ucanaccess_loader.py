import os
from pathlib import Path

import jpype
import pandas as pd
import pytest

from src.loaders.sql_loaders import UCanAccessSqlLoader, init_jvm_for_ucanaccess
from src.model import DataSourceConfig

UCANACCESS_HOME = os.path.abspath("lib/ucanaccess")
ARBODAT_DATA_MDB = os.path.abspath("./data/shared/shared-data/ArchBotDaten.mdb")
ARBODAT_LOOKUP_MDB = os.path.abspath("./data/shared/shared-data/ArchBotStrukDat.mdb")

RELATIVE_DATING_DEBUG_QUERY = """select [Projekt], [Befu], [ProbNr],
    'relative_dating' as [analysis_entity_type],
    [ArchDat] as [analysis_entity_value],
    null as [PCODE],
    null as [Fraktion],
    null as [cf],
    null as [RTyp],
    null as [Zust],
    [ArchDat]
from [Proben]
where [ArchDat] is not null and [ArchDat] <> '';"""

DATA_SOURCE_CONFIG = DataSourceConfig(
    cfg={
        "options": {
            "filename": ARBODAT_LOOKUP_MDB,
            "ucanaccess_dir": UCANACCESS_HOME,
        },
        "driver": "ucanaccess",
    },
    name="ucanaccess_test",
)


@pytest.fixture(scope="module", autouse=True)
def initialize_jvm():
    """Initialize JVM once for all tests in this module."""
    if not jpype.isJVMStarted():
        init_jvm_for_ucanaccess(UCANACCESS_HOME)
    yield
    # JVM shutdown is not recommended by JPype and causes issues with subsequent tests


def test_can_load_ucanaccess():
    loader = UCanAccessSqlLoader(DATA_SOURCE_CONFIG)
    df: pd.DataFrame = loader.read_sql_sync("SELECT * FROM [Kulturgruppen]")
    assert not df.empty


def test_can_load_ucanaccess_queries() -> None:

    loader: UCanAccessSqlLoader = UCanAccessSqlLoader(DATA_SOURCE_CONFIG)
    jar_files = loader._find_jar_files(UCANACCESS_HOME)  # pylint: disable=protected-access

    classpath = ":".join(jar_files)
    filename: str = ARBODAT_LOOKUP_MDB

    try:
        jpype.startJVM(jpype.getDefaultJVMPath(), "-ea", f"-Djava.class.path={classpath}")
    except OSError:
        pass

    conn = jpype.java.sql.DriverManager.getConnection(f"jdbc:ucanaccess:///{filename}")

    for query in conn.getDbIO().getQueries():
        print(query.getName())
        print(query.toSQLString())


@pytest.mark.manual
@pytest.mark.debug
@pytest.mark.skipif(not Path(ARBODAT_DATA_MDB).exists(), reason="Requires tests/test_data/shared/shared-data/ArchBotDaten.mdb")
def test_debug_relative_dating_query_against_real_arbodat_data(capsys: pytest.CaptureFixture[str]) -> None:
    """Temporary debug harness for inspecting raw Access metadata and columns."""
    data_source_config = DataSourceConfig(
        cfg={
            "options": {
                "filename": ARBODAT_DATA_MDB,
                "ucanaccess_dir": UCANACCESS_HOME,
            },
            "driver": "ucanaccess",
        },
        name="ucanaccess_debug_archbotdaten",
    )
    loader = UCanAccessSqlLoader(data_source_config)

    result = loader.read_sql_sync(RELATIVE_DATING_DEBUG_QUERY)

    print("query:")
    print(RELATIVE_DATING_DEBUG_QUERY)
    print("columns:", result.columns.tolist())
    print("duplicated:", result.columns.duplicated().tolist())
    print("head:")
    print(result.head(10).to_string(index=False))

    captured = capsys.readouterr()
    assert result.shape[1] == 11
    assert "columns:" in captured.out
