import os
from typing import Any

import jpype
import pandas as pd

from src.loaders.database_loaders import UCanAccessSqlLoader

UCANACCESS_HOME = os.path.abspath("lib/ucanaccess")
ARBODAT_DATA_MDB = os.path.abspath("./input/ArchBotDaten.mdb")
ARBODAT_LOOKUP_MDB = os.path.abspath("./input/ArchBotStrukDat.mdb")


def test_can_load_ucanaccess():
    opts: dict[str, Any] = {
        "filename": ARBODAT_LOOKUP_MDB,
        "ucanaccess_dir": UCANACCESS_HOME,
    }
    loader = UCanAccessSqlLoader(opts)

    df: pd.DataFrame = loader.read_sql_sync("SELECT * FROM [Kulturgruppen]")

    assert not df.empty


def test_can_load_ucanaccess_queries() -> None:

    loader: UCanAccessSqlLoader = UCanAccessSqlLoader()
    jar_files = loader._find_jar_files(UCANACCESS_HOME)  # pylint: disable=protected-access

    classpath = ":".join(jar_files)
    filename: str = ARBODAT_LOOKUP_MDB

    jpype.startJVM(jpype.getDefaultJVMPath(), "-ea", f"-Djava.class.path={classpath}")

    conn = jpype.java.sql.DriverManager.getConnection(f"jdbc:ucanaccess:///{filename}")

    for query in conn.getDbIO().getQueries():
        print(query.getName())
        print(query.toSQLString())
