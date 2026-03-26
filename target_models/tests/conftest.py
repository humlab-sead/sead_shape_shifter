from pathlib import Path
import sys


TARGET_MODELS_SRC = Path(__file__).resolve().parents[1] / "src"
target_models_src = str(TARGET_MODELS_SRC)

if target_models_src not in sys.path:
    sys.path.insert(0, target_models_src)