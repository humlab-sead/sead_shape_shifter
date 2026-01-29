import os

import jpype
import pandas as pd
import pytest

from src.loaders.sql_loaders import UCanAccessSqlLoader, init_jvm_for_ucanaccess
from src.model import DataSourceConfig

UCANACCESS_HOME = os.path.abspath("lib/ucanaccess")
ARBODAT_DATA_MDB = os.path.abspath("./projects/ArchBotDaten.mdb")
ARBODAT_LOOKUP_MDB = os.path.abspath("./projects/ArchBotStrukDat.mdb")

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
