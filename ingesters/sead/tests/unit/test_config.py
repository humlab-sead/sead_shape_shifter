from src.configuration import ConfigStore


def test_config_store():
    """Test ConfigStore initialization and configuration loading."""
    store: ConfigStore = ConfigStore.get_instance().configure_context(
        source="tests/test_data/config.yml", env_filename="tests/test_data/.env", env_prefix="SEAD_IMPORT"
    )
    assert store
    assert store.context == "default"
    config = store.get_config("default")
    assert config is not None
    assert "test" in config.data.keys()
