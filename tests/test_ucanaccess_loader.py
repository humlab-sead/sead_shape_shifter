import os

import jpype
import pandas as pd

from src.config_model import DataSourceConfig
from loaders.sql_loaders import UCanAccessSqlLoader

UCANACCESS_HOME = os.path.abspath("lib/ucanaccess")
ARBODAT_DATA_MDB = os.path.abspath("./input/ArchBotDaten.mdb")
ARBODAT_LOOKUP_MDB = os.path.abspath("./input/ArchBotStrukDat.mdb")

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
