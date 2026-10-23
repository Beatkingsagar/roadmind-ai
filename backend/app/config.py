"""Configuration management for RoadMind AI backend.

Handles paths, SQLite database settings, private evidence storage,
and automatic injection of local workspace dependencies into sys.path.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from pydantic import BaseModel, Field

# Ensure local .python_packages is available in sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
LOCAL_PACKAGES = WORKSPACE_ROOT / ".python_packages"
if LOCAL_PACKAGES.exists() and str(LOCAL_PACKAGES) not in sys.path:
    sys.path.insert(0, str(LOCAL_PACKAGES))


class Settings(BaseModel):
    app_name: str = "RoadMind AI"
    version: str = "1.0.0"
    environment: str = Field(default_factory=lambda: os.getenv("ROADMIND_ENV", "development"))
    
    # Storage paths
    workspace_root: Path = WORKSPACE_ROOT
    data_dir: Path = WORKSPACE_ROOT / "data"
    fixtures_dir: Path = WORKSPACE_ROOT / "data" / "fixtures"
    manifests_dir: Path = WORKSPACE_ROOT / "data" / "manifests"
    evidence_storage_dir: Path = WORKSPACE_ROOT / "backend" / "storage" / "evidence"
    
    # Database URL
    sqlite_db_path: Path = WORKSPACE_ROOT / "backend" / "roadmind.db"
    database_url: str = Field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL",
            f"sqlite:///{WORKSPACE_ROOT / 'backend' / 'roadmind.db'}"
        )
    )
    
    # Deterministic generation defaults
    fixture_random_seed: int = 42
    graph_version: str = "v1.0.0"
    data_mode: str = "synthetic"

    # API and Operator Security Settings
    api_prefix: str = "/api/v1"
    operator_token: str = Field(
        default_factory=lambda: os.getenv("ROADMIND_OPERATOR_TOKEN", "traffic_operator_secret_2026")
    )
    cors_origins: list[str] = ["*"]

    # External Provider URLs
    osrm_routing_url: str = Field(
        default_factory=lambda: os.getenv("OSRM_ROUTING_URL", "https://router.project-osrm.org")
    )

    def ensure_directories(self) -> None:
        """Create required storage and data directories if they do not exist."""
        self.evidence_storage_dir.mkdir(parents=True, exist_ok=True)
        self.fixtures_dir.mkdir(parents=True, exist_ok=True)
        self.manifests_dir.mkdir(parents=True, exist_ok=True)
        self.sqlite_db_path.parent.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()
