"""
Centralized path management for the assistant.
"""
import os
from pathlib import Path

# Base project directory
# Priority: 1. Environment variable ASSISTANT_HOME
#          2. Parent of src directory
#          3. Default location
ASSISTANT_HOME = Path(os.environ.get(
    'ASSISTANT_HOME',
    Path(__file__).parent.parent.parent
))

# Fallback to legacy path for existing installations
if not ASSISTANT_HOME.exists():
    legacy_path = Path("/home/orangepi/asistente2")
    if legacy_path.exists():
        ASSISTANT_HOME = legacy_path

# Core directories
PROJECT_DIR = ASSISTANT_HOME
MODELS_DIR = PROJECT_DIR / "models"
CONFIG_DIR = PROJECT_DIR / "config"
LOGS_DIR = PROJECT_DIR / "logs"
SRC_DIR = PROJECT_DIR / "src"

# Create directories if they don't exist
for dir_path in [MODELS_DIR, CONFIG_DIR, LOGS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)
