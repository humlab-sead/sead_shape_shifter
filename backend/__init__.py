"""Backend application initialization."""

from pathlib import Path

# Create backend directory structure
BACKEND_DIR = Path(__file__).parent
APP_DIR = BACKEND_DIR / "app"
MODELS_DIR = APP_DIR / "models"
SERVICES_DIR = APP_DIR / "services"
API_DIR = APP_DIR / "api"
TESTS_DIR = BACKEND_DIR / "tests"

# Ensure directories exist
for directory in [MODELS_DIR, SERVICES_DIR, API_DIR, TESTS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "__init__.py").touch(exist_ok=True)
