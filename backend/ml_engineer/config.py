"""
Configuration for ML Engineer Agent
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Configuration settings for the ML Engineer Agent"""

    # OpenAI settings
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-5")

    # Reasoning effort for GPT-5 and reasoning models
    DEFAULT_REASONING_EFFORT = os.getenv("REASONING_EFFORT", "medium")  # low, medium, high

    # Paths
    BASE_DIR = Path(__file__).parent.parent
    DATASETS_DIR = BASE_DIR / "datasets"
    RUNS_DIR = BASE_DIR / "runs"
    ARTIFACTS_DIR = BASE_DIR / "artifacts"

    # Agent settings
    MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "15"))
    TIMEOUT_SECONDS = int(os.getenv("TIMEOUT_SECONDS", "60"))

    # Execution settings
    PERSISTENT_NAMESPACE = True
    CAPTURE_PLOTS = True

    @classmethod
    def ensure_directories(cls):
        """Ensure all required directories exist"""
        cls.RUNS_DIR.mkdir(exist_ok=True)
        cls.ARTIFACTS_DIR.mkdir(exist_ok=True)
        cls.DATASETS_DIR.mkdir(exist_ok=True)


# Ensure directories exist on import
Config.ensure_directories()
