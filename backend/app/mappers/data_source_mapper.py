
from backend.app.models.data_source import DataSourceConfig as ApiDataSourceConfig
from src.config_model import DataSourceConfig as CoreDataSourceConfig

class DataSourceMapper:
    
    def to_core_config(self, ds_config: ApiDataSourceConfig) -> CoreDataSourceConfig:
        """Map DataSourceConfig to CoreDataSourceConfig."""
        core_config: CoreDataSourceConfig = CoreDataSourceConfig(
            name=ds_config.name,
            cfg= {
                "driver": ds_config.driver,
                "host": ds_config.host,
                "port": ds_config.port,
                "database": ds_config.database,
                "username": ds_config.username,
                "password": ds_config.password,
                "options": ds_config.options
            } or {},
        )

            #         legacy_opts: dict[str, str|int|None] = {
            #     "driver": config.get_loader_driver(),
            # }

            # if config.driver in (DataSourceType.POSTGRESQL, DataSourceType.POSTGRES):
            #     legacy_opts.update(
            #         {
            #             "host": config.host or "localhost",
            #             "port": config.port or 5432,
            #             "dbname": config.effective_database,
            #             "username": config.username,
            #         }
            #     )
            #     if config.password:
            #         legacy_opts["password"] = config.password.get_secret_value()

            # elif config.driver in (DataSourceType.ACCESS, DataSourceType.UCANACCESS):
            #     if not config.effective_file_path:
            #         raise ValueError("Access database requires 'filename' or 'file_path'")
            #     legacy_opts["filename"] = config.effective_file_path
            #     if config.options and "ucanaccess_dir" in config.options:
            #         legacy_opts["ucanaccess_dir"] = config.options["ucanaccess_dir"]

            # elif config.driver == DataSourceType.SQLITE:
            #     if not config.effective_file_path:
            #         raise ValueError("SQLite database requires 'filename' or 'file_path'")
            #     legacy_opts["filename"] = config.effective_file_path

            # # Merge with additional options
            # if config.options:
            #     legacy_opts.update(config.options)

            # legacy_data_source = LegacyDataSourceConfig(
            #     cfg={"driver": legacy_opts.pop("driver"), "options": legacy_opts},
            #     name=config.name,
            # )

        return core_config
    