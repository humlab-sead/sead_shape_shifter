# Project Structure Restructuring - Implementation Plan

**Status:** Planning  
**Created:** February 11, 2026  
**Target:** Move from flat project structure to organized folder hierarchy

---

## Table of Contents

1. [Overview](#overview)
2. [Structure v2: Smart Separation](#structure-v2-smart-separation)
3. [Key Design Decisions](#key-design-decisions)
4. [Path Resolution](#path-resolution)
5. [Implementation Plan](#implementation-plan)
6. [Risk Assessment](#risk-assessment)
7. [Rollout Strategy](#rollout-strategy)

---

## Overview

### Current Problem

The `projects/` folder currently contains:
- 20+ project YAML files at root level
- Database files (.mdb, .accdb, .db) mixed with configs
- Excel/CSV source data scattered
- Global configuration files (mappings.yml, replacements.yml)
- Thousands of backups in separate root `backups/` folder
- Outputs in separate root `output/` folder

This structure:
- ❌ Becomes messy and hard to navigate
- ❌ Makes it unclear which files belong to which project
- ❌ Complicates backup management
- ❌ Doesn't scale well (already 20+ projects)
- ❌ No clear separation between shared and project-specific resources

### Goals

1. **Clear organization** - Each project has dedicated folder with all related files
2. **Resource sharing** - Explicit separation of shared vs. project-specific data
3. **Version control** - Shared data updates are conscious, tracked changes
4. **Provider isolation** - Different data providers don't accidentally share resources
5. **Maintainability** - Consistent, predictable structure across all projects

---

## Structure v2: Smart Separation

```
projects/
├── data_sources/              # Data source configs (YAML only) - SHARED
│   ├── arbodat-database.yml   # Connection configs, queries
│   ├── bugscep-options.yml
│   ├── sead-options.yml
│   └── digidiggie-options.yml
│
├── shared-data/              # Actual data files (versioned) - SHARED
│   ├── arbodat/              # Organized by provider
│   │   ├── ArchBotDaten.mdb
│   │   ├── ArchBotStrukDat.mdb
│   │   └── arbodat_mal_elena_input.csv
│   ├── bugscep/
│   │   └── bugsdata_20250608.mdb
│   ├── digidiggie/
│   │   └── digidiggie_dev.accdb
│   └── common/              # Cross-provider shared files
│       └── table_shapes.tsv
│
├── arbodat/                  # PROJECT: Arbodat delivery 2024
│   ├── shapeshifter.yml      # ⭐ Main config (FIXED NAME)
│   ├── mappings.yml          # Provider-specific: Arbodat → SEAD IDs
│   ├── replacements.yml      # Provider-specific: Arbodat value mappings
│   ├── translations.yml      # Provider-specific: Arbodat translations
│   ├── data/                # Project-specific data (overrides shared)
│   │   └── corrections.csv   # This project's custom fixes
│   ├── backups/             # Project-specific backups only
│   │   └── shapeshifter.backup.20260211_*.yml
│   └── output/              # Project-specific outputs
│       ├── sample.csv
│       └── site.csv
│
├── arbodat-2025/            # PROJECT: Arbodat delivery 2025
│   ├── shapeshifter.yml
│   ├── mappings.yml         # Could be symlink to ../arbodat/mappings.yml (future)
│   ├── replacements.yml     # Same provider = potentially shared
│   ├── translations.yml
│   ├── data/               # 2025-specific adjustments
│   ├── backups/
│   └── output/
│
├── bugs-test/               # PROJECT: BugsCEP (different provider)
│   ├── shapeshifter.yml
│   ├── mappings.yml         # BugsCEP-specific (CAN'T share with arbodat)
│   ├── replacements.yml     # Different provider = different mappings
│   ├── translations.yml
│   ├── backups/
│   └── output/
│
└── digidiggie-dev/
    ├── shapeshifter.yml
    ├── mappings.yml
    ├── data/
    ├── backups/
    └── output/
```

---

## Key Design Decisions

### 1. Fixed Filename: `shapeshifter.yml`

**Decision:** All projects use the same config filename: `shapeshifter.yml`

**Rationale:**
- ✅ **Instant recognition** - Developers know where to find config
- ✅ **CLI-friendly** - `find . -name shapeshifter.yml` works perfectly
- ✅ **Tool integration** - IDEs can favorite the pattern `**/shapeshifter.yml`
- ✅ **Cross-project consistency** - Every project follows same pattern
- ✅ **Industry standard** - Similar to `Makefile`, `Dockerfile`, `package.json`

**Alternative rejected:** Matching folder/file names (e.g., `arbodat/arbodat.yml`)
- ❌ Harder to find programmatically
- ❌ Name changes require file renames
- ❌ Inconsistent with hyphens/underscores

### 2. Data Sources: Centralized Configs

**Location:** `projects/data_sources/`

**What:** Data source YAML files (previously `*-options.yml`, `*-database.yml`)

**Contains:**
- Database connection configs (host, port, credentials)
- SQL queries
- CSV file paths (references to `shared-data/`)
- Driver configurations

**Why centralized:**
- ✅ Reusable across multiple projects
- ✅ Single point of updates for connection details
- ✅ Clear separation: configs vs. actual data

**Example:**
```yaml
# projects/data_sources/arbodat-database.yml
driver: ms_access
database: ../shared-data/arbodat/ArchBotDaten.mdb
driver_path: /path/to/ucanaccess
```

### 3. Shared Data: Provider-Organized

**Location:** `projects/shared-data/`

**Organization:**
```
shared-data/
├── {provider}/    # e.g., arbodat/, bugscep/
│   └── *.mdb, *.csv, *.xlsx
└── common/        # Cross-provider files
    └── *.tsv
```

**What:** Actual data files (.mdb, .accdb, .csv, .xlsx, .db)

**Why organized by provider:**
- ✅ Clear ownership and versioning
- ✅ Prevents accidental cross-provider contamination
- ✅ Easy to update all projects from one provider
- ✅ Conscious updates (commit = affects all projects using it)

**Provider detection logic:**
```python
PROVIDER_PATTERNS = {
    "arbodat": ["arbo", "Archo", "ArchBot"],
    "bugscep": ["bugs", "bugscep"],
    "digidiggie": ["digi", "diggie"],
    "strukke": ["struk", "strukke"],
}
```

**Override mechanism:**  
`project/data/` takes precedence over `shared-data/` for files with same name.

### 4. Provider-Specific Resources

**Files:** `mappings.yml`, `replacements.yml`, `translations.yml`

**Location:** Each project folder (project-specific by default)

**Why per-project:**
- ✅ Different providers have different SEAD ID mappings
- ✅ Can't accidentally share BugsCEP mappings with Arbodat
- ✅ Each delivery may have unique corrections

**Sharing strategy (future):**
- Same-provider projects CAN share via symlinks
- Manual creation (user decision)
- Copy-on-write: Editing materializes symlink to real file

### 5. Backups: Per-Project

**Location:** `projects/{project}/backups/`

**What:** Only backups for this project's `shapeshifter.yml`

**Migration:** Keep only last 30 days of backups

**Why per-project:**
- ✅ Clear isolation - each project owns its history
- ✅ Easy cleanup - delete old project = delete its backups
- ✅ No global backup pollution
- ✅ Project-specific retention policies possible

**Removed:** Global `SHAPE_SHIFTER_BACKUPS_DIR` setting

### 6. Outputs: Per-Project, Fresh Start

**Location:** `projects/{project}/output/`

**Migration:** Start fresh (don't migrate old outputs)

**Why:**
- ✅ Outputs are regenerable
- ✅ Old outputs in `output/` folder likely outdated
- ✅ Clean slate for new structure

---

## Path Resolution

### Priority Order

When resolving a file path:

```python
def resolve_data_file(project_name: str, filename: str) -> Path:
    """
    Priority order:
    1. Project-specific data (highest priority)
    2. Shared-data provider folder
    3. Shared-data common
    4. Not found
    """
    provider = detect_provider(project_name)
    
    # 1. Project-specific (overrides)
    project_path = projects_dir / project_name / "data" / filename
    if project_path.exists():
        return project_path
    
    # 2. Shared-data provider folder
    shared_provider_path = projects_dir / "shared-data" / provider / filename
    if shared_provider_path.exists():
        return shared_provider_path
    
    # 3. Shared-data common
    shared_common_path = projects_dir / "shared-data" / "common" / filename
    if shared_common_path.exists():
        return shared_common_path
    
    raise FileNotFoundError(f"Data file not found: {filename}")
```

### Examples

**Scenario 1: Project uses shared database**
```python
# arbodat/shapeshifter.yml references:
data_source: arbodat-database

# Resolves to:
projects/data_sources/arbodat-database.yml
  → database: ../shared-data/arbodat/ArchBotDaten.mdb
  → projects/shared-data/arbodat/ArchBotDaten.mdb
```

**Scenario 2: Project has custom corrections**
```python
# arbodat/shapeshifter.yml references:
data_source: corrections.csv

# Priority check:
1. projects/arbodat/data/corrections.csv  ✅ FOUND (project-specific)
2. (skip shared-data check)
```

**Scenario 3: Common resource**
```python
# Any project references:
data_source: table_shapes.tsv

# Priority check:
1. projects/{project}/data/table_shapes.tsv  ❌ Not found
2. projects/shared-data/{provider}/table_shapes.tsv  ❌ Not found
3. projects/shared-data/common/table_shapes.tsv  ✅ FOUND
```

---

## Implementation Plan

### **Phase 1: Backend Infrastructure Updates** (Foundation)

**Duration:** ~6 hours  
**Priority:** P0 (blocking)

#### 1.1 Update Configuration & Settings

**Files:**
- `backend/app/core/config.py`
- `.env` (root)

**Changes:**

```python
# backend/app/core/config.py
class Settings(BaseSettings):
    # Existing
    PROJECTS_DIR: Path = Path("./projects")
    
    # NEW: Add these constants
    PROJECT_CONFIG_FILENAME: str = "shapeshifter.yml"  # Fixed filename
    DATA_SOURCES_DIR: Path = PROJECTS_DIR / "data_sources"
    SHARED_DATA_DIR: Path = PROJECTS_DIR / "shared-data"
    
    # REMOVED: No longer needed
    # BACKUPS_DIR: Path = Path("./backups")  # DELETE THIS
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.PROJECTS_DIR.mkdir(exist_ok=True)
        self.DATA_SOURCES_DIR.mkdir(exist_ok=True)  # NEW
        self.SHARED_DATA_DIR.mkdir(exist_ok=True)   # NEW
```

```bash
# .env - REMOVE this line:
SHAPE_SHIFTER_BACKUPS_DIR="./backups"
```

**Tests:**
- Verify `DATA_SOURCES_DIR` is created on startup
- Verify `SHARED_DATA_DIR` is created on startup

---

#### 1.2 Create Path Resolution Service

**New file:** `backend/app/services/path_resolver.py`

**Purpose:** Centralize all file path resolution logic with proper priority

```python
"""
Path resolution service for project files and data sources.

Handles priority-based resolution:
1. Project-specific files (highest priority)
2. Shared-data provider files
3. Shared-data common files
"""

from pathlib import Path
from loguru import logger
from backend.app.core.config import settings

class PathResolver:
    """Resolve file paths with provider-aware priority."""
    
    PROVIDER_PATTERNS = {
        "arbodat": ["arbo", "Archo", "ArchBot"],
        "bugscep": ["bugs", "bugscep"],
        "digidiggie": ["digi", "diggie"],
        "strukke": ["struk", "strukke"],
    }
    
    def __init__(self, projects_dir: Path | None = None):
        self.projects_dir = projects_dir or settings.PROJECTS_DIR
        self.data_sources_dir = settings.DATA_SOURCES_DIR
        self.shared_data_dir = settings.SHARED_DATA_DIR
    
    def detect_provider(self, project_name: str) -> str:
        """
        Detect provider from project name.
        
        Examples:
            "arbodat" → "arbodat"
            "arbodat-2025" → "arbodat"
            "bugs-test" → "bugscep"
        
        Returns:
            Provider key or "unknown"
        """
        name_lower = project_name.lower()
        
        for provider, patterns in self.PROVIDER_PATTERNS.items():
            if any(pattern.lower() in name_lower for pattern in patterns):
                return provider
        
        return "unknown"
    
    def resolve_data_file(self, project_name: str, filename: str) -> Path:
        """
        Resolve data file path with priority order.
        
        Priority:
        1. projects/{project}/data/{filename}
        2. projects/shared-data/{provider}/{filename}
        3. projects/shared-data/common/{filename}
        
        Args:
            project_name: Name of the project
            filename: Data file to find
        
        Returns:
            Resolved path
        
        Raises:
            FileNotFoundError: If file not found in any location
        """
        provider = self.detect_provider(project_name)
        
        # 1. Project-specific data (overrides)
        project_path = self.projects_dir / project_name / "data" / filename
        if project_path.exists():
            logger.debug(f"Resolved {filename} → project-specific: {project_path}")
            return project_path
        
        # 2. Shared-data provider folder
        if provider != "unknown":
            shared_provider_path = self.shared_data_dir / provider / filename
            if shared_provider_path.exists():
                logger.debug(f"Resolved {filename} → shared provider: {shared_provider_path}")
                return shared_provider_path
        
        # 3. Shared-data common
        shared_common_path = self.shared_data_dir / "common" / filename
        if shared_common_path.exists():
            logger.debug(f"Resolved {filename} → shared common: {shared_common_path}")
            return shared_common_path
        
        # Not found
        raise FileNotFoundError(
            f"Data file '{filename}' not found for project '{project_name}'. "
            f"Searched: project data, shared-data/{provider}, shared-data/common"
        )
    
    def resolve_data_source_config(self, source_name: str) -> Path:
        """
        Resolve data source configuration file.
        
        Args:
            source_name: Name of data source (without .yml extension)
        
        Returns:
            Path to data source YAML
        
        Raises:
            FileNotFoundError: If config not found
        """
        # Add .yml extension if not present
        if not source_name.endswith('.yml'):
            source_name = f"{source_name}.yml"
        
        config_path = self.data_sources_dir / source_name
        
        if not config_path.exists():
            raise FileNotFoundError(
                f"Data source config '{source_name}' not found in {self.data_sources_dir}"
            )
        
        return config_path
    
    def get_project_config_path(self, project_name: str) -> Path:
        """
        Get path to project's main config file.
        
        Args:
            project_name: Name of the project
        
        Returns:
            Path to shapeshifter.yml
        """
        return self.projects_dir / project_name / settings.PROJECT_CONFIG_FILENAME
    
    def get_project_backups_dir(self, project_name: str) -> Path:
        """Get project's backup directory."""
        return self.projects_dir / project_name / "backups"
    
    def get_project_output_dir(self, project_name: str) -> Path:
        """Get project's output directory."""
        return self.projects_dir / project_name / "output"
    
    def get_project_data_dir(self, project_name: str) -> Path:
        """Get project's data directory."""
        return self.projects_dir / project_name / "data"


# Singleton instance
_path_resolver: PathResolver | None = None

def get_path_resolver() -> PathResolver:
    """Get global PathResolver instance."""
    global _path_resolver
    if _path_resolver is None:
        _path_resolver = PathResolver()
    return _path_resolver
```

**Tests:**
```python
# backend/tests/services/test_path_resolver.py
def test_detect_provider():
    resolver = PathResolver()
    assert resolver.detect_provider("arbodat") == "arbodat"
    assert resolver.detect_provider("arbodat-2025") == "arbodat"
    assert resolver.detect_provider("bugs-test") == "bugscep"

def test_resolve_data_file_priority(tmp_path):
    # Test priority: project > shared-provider > shared-common
    pass
```

---

#### 1.3 Update ProjectService

**File:** `backend/app/services/project_service.py`

**Changes:**

1. **Update `list_projects()`**: Look in subdirectories for `shapeshifter.yml`
2. **Update `load_project()`**: Change path resolution
3. **Update `save_project()`**: Save to new location
4. **Add helper methods**: Get backup/output dirs

```python
# Add import
from backend.app.services.path_resolver import get_path_resolver

class ProjectService:
    def __init__(self, projects_dir: Path | None = None, state: ApplicationStateManager | None = None):
        self.yaml_service: YamlService = get_yaml_service()
        self.projects_dir: Path = Path(projects_dir or settings.PROJECTS_DIR)
        self.specification = ProjectYamlSpecification()
        self.state: ApplicationStateManager = state or get_app_state_manager()
        self.path_resolver = get_path_resolver()  # NEW
    
    def list_projects(self) -> list[ProjectMetadata]:
        """
        List all projects by finding shapeshifter.yml in subdirectories.
        
        NEW: Looks in projects/**/shapeshifter.yml instead of projects/*.yml
        """
        if not self.projects_dir.exists():
            logger.warning(f"Projects directory does not exist: {self.projects_dir}")
            return []

        configs: list[ProjectMetadata] = []
        
        # NEW: Find all shapeshifter.yml files in subdirectories
        for config_file in self.projects_dir.glob(f"*/{settings.PROJECT_CONFIG_FILENAME}"):
            try:
                data: dict[str, Any] = self.yaml_service.load(config_file)

                if not self.specification.is_satisfied_by(data):
                    logger.debug(f"Skipping {config_file} - does not satisfy project specification")
                    continue

                # Project name is the parent folder name
                project_name = config_file.parent.name
                entity_count = len(data.get("entities", {}))

                metadata = ProjectMetadata(
                    name=project_name,
                    file_path=str(config_file),
                    entity_count=entity_count,
                    created_at=config_file.stat().st_ctime,
                    modified_at=config_file.stat().st_mtime,
                    is_valid=True,
                )
                configs.append(metadata)

            except Exception as e:
                logger.warning(f"Failed to load project {config_file}: {e}")

        logger.debug(f"Found {len(configs)} project(s)")
        return configs
    
    def load_project(self, name: str, force_reload: bool = False) -> Project:
        """
        Load project by name.
        
        NEW: Loads from projects/{name}/shapeshifter.yml
        OLD: Loaded from projects/{name}.yml
        """
        if force_reload:
            self.state.invalidate(name)
            logger.info(f"Force reload requested for '{name}', cache invalidated")
        
        # Check cache
        cached_project: Project | None = self.state.get(name)
        if cached_project:
            logger.debug(f"Loaded project '{name}' from cache")
            return cached_project

        # NEW: Use PathResolver
        filename: Path = self.path_resolver.get_project_config_path(name)
        
        if not filename.exists():
            raise ResourceNotFoundError(
                resource_type="project",
                resource_id=name,
                message=f"Project not found: {name} (expected at {filename})"
            )

        try:
            data: dict[str, Any] = self.yaml_service.load(filename)

            if not self.specification.is_satisfied_by(data):
                raise ConfigurationError(
                    message=f"Invalid project file '{name}': missing required metadata",
                )

            project: Project = ProjectMapper.to_api_config(data, name)

            assert project.metadata is not None

            project.metadata.file_path = str(filename)
            project.metadata.created_at = filename.stat().st_ctime
            project.metadata.modified_at = filename.stat().st_mtime
            project.metadata.entity_count = len(project.entities or {})
            project.metadata.is_valid = True

            # Cache
            self.state.activate(project)

            logger.info(f"Loaded project '{name}' from {filename}")
            return project

        except ConfigurationError:
            raise
        except YamlLoadError as e:
            raise ConfigurationError(message=f"Invalid YAML in project '{name}': {e}") from e
        except Exception as e:
            logger.error(f"Failed to load project '{name}': {e}")
            raise
    
    def save_project(self, project: Project, create_backup: bool = True) -> None:
        """
        Save project to disk.
        
        NEW: Saves to projects/{name}/shapeshifter.yml
             Backups go to projects/{name}/backups/
        """
        try:
            name = project.metadata.name
            file_path = self.path_resolver.get_project_config_path(name)
            
            # Ensure project directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create backup if requested and file exists
            if create_backup and file_path.exists():
                # NEW: Use project-specific backup directory
                backups_dir = self.path_resolver.get_project_backups_dir(name)
                backups_dir.mkdir(exist_ok=True)
                self.yaml_service.create_backup(file_path, backup_dir=backups_dir)
            
            # Convert to dict and save
            project_dict = ProjectMapper.to_core_dict(project)
            self.yaml_service.save(file_path, project_dict)
            
            # Update cache
            self.state.activate(project)
            
            logger.info(f"Saved project '{name}' to {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to save project: {e}")
            raise ProjectServiceError(f"Failed to save project: {e}") from e
    
    # NEW: Helper methods
    def get_project_backups_dir(self, project_name: str) -> Path:
        """Get backup directory for a project."""
        return self.path_resolver.get_project_backups_dir(project_name)
    
    def get_project_output_dir(self, project_name: str) -> Path:
        """Get output directory for a project."""
        return self.path_resolver.get_project_output_dir(project_name)
    
    def create_project_structure(self, project_name: str) -> None:
        """
        Create complete folder structure for a new project.
        
        Creates:
        - projects/{name}/
        - projects/{name}/backups/
        - projects/{name}/output/
        - projects/{name}/data/
        """
        project_dir = self.projects_dir / project_name
        project_dir.mkdir(exist_ok=True)
        
        (project_dir / "backups").mkdir(exist_ok=True)
        (project_dir / "output").mkdir(exist_ok=True)
        (project_dir / "data").mkdir(exist_ok=True)
        
        logger.info(f"Created project structure for '{project_name}'")
```

**Tests:**
- Test `list_projects()` finds projects in subdirectories
- Test `load_project()` from new path
- Test `save_project()` to new path with backup in project folder

---

#### 1.4 Update YamlService Backup Logic

**File:** `backend/app/services/yaml_service.py`

**Changes:** Add optional `backup_dir` parameter

```python
def create_backup(self, file_path: Path, backup_dir: Path | None = None) -> Path:
    """
    Create timestamped backup of a YAML file.
    
    Args:
        file_path: File to backup
        backup_dir: Optional backup directory (defaults to file's directory)
    
    Returns:
        Path to backup file
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Cannot backup non-existent file: {file_path}")
    
    # Use provided backup_dir or default to file's parent
    target_dir = backup_dir if backup_dir is not None else file_path.parent
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Create backup filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup_filename = f"{file_path.stem}.backup.{timestamp}{file_path.suffix}"
    backup_path = target_dir / backup_filename
    
    # Copy file
    shutil.copy2(file_path, backup_path)
    
    logger.debug(f"Created backup: {backup_path}")
    return backup_path
```

---

#### 1.5 Update AutoFixService

**File:** `backend/app/services/auto_fix_service.py`

**Changes:** Use project-specific backup paths

```python
# Add import
from backend.app.services.path_resolver import get_path_resolver

class AutoFixService:
    def __init__(self):
        self.yaml_service = get_yaml_service()
        self.path_resolver = get_path_resolver()  # NEW
    
    async def create_backup(self, project_name: str) -> str:
        """
        Create backup before applying fixes.
        
        NEW: Uses projects/{name}/backups/ instead of global backups/
        """
        project_path = self.path_resolver.get_project_config_path(project_name)
        backups_dir = self.path_resolver.get_project_backups_dir(project_name)
        backups_dir.mkdir(exist_ok=True)
        
        backup_path = self.yaml_service.create_backup(project_path, backup_dir=backups_dir)
        
        logger.info(f"Created backup for project '{project_name}': {backup_path}")
        return str(backup_path)
    
    async def restore_from_backup(self, project_name: str, backup_filename: str) -> None:
        """
        Restore project from backup.
        
        NEW: Looks in projects/{name}/backups/ instead of global backups/
        """
        backups_dir = self.path_resolver.get_project_backups_dir(project_name)
        backup_path = backups_dir / backup_filename
        
        if not backup_path.exists():
            raise ResourceNotFoundError(
                resource_type="backup",
                resource_id=backup_filename,
                message=f"Backup not found: {backup_filename}"
            )
        
        project_path = self.path_resolver.get_project_config_path(project_name)
        shutil.copy2(backup_path, project_path)
        
        logger.info(f"Restored project '{project_name}' from {backup_filename}")
```

---

### **Phase 2: Migration Script** (Data Reorganization)

**Duration:** ~6 hours  
**Priority:** P0 (blocking)

#### 2.1 Create Migration Script

**New file:** `scripts/migrate_project_structure.py`

```python
#!/usr/bin/env python3
"""
Project Structure Migration Script

Migrates from flat structure to organized folder hierarchy:
- Creates data_sources/ and shared-data/ folders
- Moves each project to its own folder with shapeshifter.yml
- Organizes shared data by provider
- Migrates recent backups to project folders
- Starts fresh with output/

Usage:
    python scripts/migrate_project_structure.py --dry-run   # Preview changes
    python scripts/migrate_project_structure.py --execute   # Execute migration
    python scripts/migrate_project_structure.py --verify    # Verify migration
"""

import argparse
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml
from loguru import logger

# Configuration
PROJECTS_DIR = Path("./projects")
DATA_SOURCES_DIR = PROJECTS_DIR / "data_sources"
SHARED_DATA_DIR = PROJECTS_DIR / "shared-data"
BACKUPS_DIR = Path("./backups")
OUTPUT_DIR = Path("./output")

BACKUP_RETENTION_DAYS = 30

PROVIDER_PATTERNS = {
    "arbodat": ["arbo", "Archo", "ArchBot"],
    "bugscep": ["bugs", "bugscep"],
    "digidiggie": ["digi", "diggie"],
    "strukke": ["struk", "strukke"],
}

DATA_SOURCE_PATTERNS = [
    "*-options.yml",
    "*-database.yml",
    "*-reconciliation*.yml",
]

SHARED_DATA_EXTENSIONS = [
    ".mdb",
    ".accdb",
    ".db",
]

SKIP_FILES = [
    ".env",
    "mappings.yml",  # Global - will be copied to each project
    "replacements.yml",
    "translations.yml",
]

class MigrationStats:
    def __init__(self):
        self.projects_migrated = 0
        self.data_sources_moved = 0
        self.shared_data_moved = 0
        self.backups_migrated = 0
        self.errors = []


class ProjectStructureMigration:
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.stats = MigrationStats()
        
    def detect_provider(self, name: str) -> str:
        """Detect provider from filename or project name."""
        name_lower = name.lower()
        for provider, patterns in PROVIDER_PATTERNS.items():
            if any(p.lower() in name_lower for p in patterns):
                return provider
        return "unknown"
    
    def is_project_yaml(self, file_path: Path) -> bool:
        """Check if YAML file is a project configuration."""
        try:
            with file_path.open('r') as f:
                data = yaml.safe_load(f)
                metadata = data.get("metadata", {})
                return metadata.get("type") == "shapeshifter-project"
        except Exception:
            return False
    
    def analyze_current_structure(self):
        """Scan and categorize current files."""
        logger.info("Analyzing current structure...")
        
        analysis = {
            "projects": [],
            "data_sources": [],
            "shared_data": {},
            "skip_files": [],
        }
        
        if not PROJECTS_DIR.exists():
            logger.error(f"Projects directory not found: {PROJECTS_DIR}")
            return analysis
        
        for file_path in PROJECTS_DIR.iterdir():
            if file_path.is_dir():
                continue
            
            filename = file_path.name
            
            # Skip certain files
            if filename in SKIP_FILES or filename.startswith('.'):
                analysis["skip_files"].append(filename)
                continue
            
            # Data source configs
            if any(file_path.match(pattern) for pattern in DATA_SOURCE_PATTERNS):
                analysis["data_sources"].append(file_path)
                continue
            
            # Shared data files
            if file_path.suffix in SHARED_DATA_EXTENSIONS:
                provider = self.detect_provider(filename)
                if provider not in analysis["shared_data"]:
                    analysis["shared_data"][provider] = []
                analysis["shared_data"][provider].append(file_path)
                continue
            
            # Project YAMLs
            if file_path.suffix == ".yml" and self.is_project_yaml(file_path):
                analysis["projects"].append(file_path)
        
        logger.info(f"Found {len(analysis['projects'])} projects")
        logger.info(f"Found {len(analysis['data_sources'])} data source configs")
        logger.info(f"Found {sum(len(v) for v in analysis['shared_data'].values())} shared data files")
        
        return analysis
    
    def create_new_structure(self):
        """Create new folder hierarchy."""
        logger.info("Creating new folder structure...")
        
        dirs_to_create = [
            DATA_SOURCES_DIR,
            SHARED_DATA_DIR,
            SHARED_DATA_DIR / "common",
        ]
        
        for provider in PROVIDER_PATTERNS.keys():
            dirs_to_create.append(SHARED_DATA_DIR / provider)
        
        for dir_path in dirs_to_create:
            if self.dry_run:
                logger.info(f"[DRY RUN] Would create: {dir_path}")
            else:
                dir_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created: {dir_path}")
    
    def migrate_projects(self, projects: list[Path]):
        """Move and rename project configs."""
        logger.info(f"Migrating {len(projects)} projects...")
        
        # Load global mappings/replacements/translations if they exist
        global_files = {}
        for filename in ["mappings.yml", "replacements.yml", "translations.yml"]:
            global_path = PROJECTS_DIR / filename
            if global_path.exists():
                global_files[filename] = global_path
        
        for project_path in projects:
            project_name = project_path.stem
            
            logger.info(f"Migrating project: {project_name}")
            
            # Create project folder structure
            project_dir = PROJECTS_DIR / project_name
            
            if self.dry_run:
                logger.info(f"[DRY RUN] Would create: {project_dir}")
                logger.info(f"[DRY RUN] Would create: {project_dir}/backups")
                logger.info(f"[DRY RUN] Would create: {project_dir}/output")
                logger.info(f"[DRY RUN] Would create: {project_dir}/data")
                logger.info(f"[DRY RUN] Would move: {project_path} → {project_dir}/shapeshifter.yml")
            else:
                project_dir.mkdir(exist_ok=True)
                (project_dir / "backups").mkdir(exist_ok=True)
                (project_dir / "output").mkdir(exist_ok=True)
                (project_dir / "data").mkdir(exist_ok=True)
                
                # Move and rename project file
                shutil.move(str(project_path), str(project_dir / "shapeshifter.yml"))
                logger.info(f"Moved: {project_path.name} → {project_dir}/shapeshifter.yml")
            
            # Copy global resource files if they exist
            for filename, source_path in global_files.items():
                target_path = project_dir / filename
                if self.dry_run:
                    logger.info(f"[DRY RUN] Would copy: {filename} → {project_dir}/")
                else:
                    shutil.copy2(source_path, target_path)
                    logger.info(f"Copied: {filename} → {project_dir}/")
            
            self.stats.projects_migrated += 1
    
    def migrate_data_sources(self, data_sources: list[Path]):
        """Move data source configs."""
        logger.info(f"Migrating {len(data_sources)} data source configs...")
        
        for source_path in data_sources:
            target_path = DATA_SOURCES_DIR / source_path.name
            
            if self.dry_run:
                logger.info(f"[DRY RUN] Would move: {source_path.name} → data_sources/")
            else:
                shutil.move(str(source_path), str(target_path))
                logger.info(f"Moved: {source_path.name} → data_sources/")
            
            self.stats.data_sources_moved += 1
    
    def migrate_shared_data(self, shared_data: dict[str, list[Path]]):
        """Organize shared data by provider."""
        total_files = sum(len(files) for files in shared_data.values())
        logger.info(f"Migrating {total_files} shared data files...")
        
        for provider, files in shared_data.items():
            provider_dir = SHARED_DATA_DIR / provider
            
            for file_path in files:
                target_path = provider_dir / file_path.name
                
                if self.dry_run:
                    logger.info(f"[DRY RUN] Would move: {file_path.name} → shared-data/{provider}/")
                else:
                    shutil.move(str(file_path), str(target_path))
                    logger.info(f"Moved: {file_path.name} → shared-data/{provider}/")
                
                self.stats.shared_data_moved += 1
    
    def migrate_recent_backups(self, projects: list[Path]):
        """Move recent backups to project folders."""
        if not BACKUPS_DIR.exists():
            logger.info("No backups directory found, skipping backup migration")
            return
        
        logger.info("Migrating recent backups (last 30 days)...")
        
        cutoff_date = datetime.now() - timedelta(days=BACKUP_RETENTION_DAYS)
        
        # Get all backup files
        backup_files = list(BACKUPS_DIR.glob("*.backup.*.yml"))
        
        # Group by project
        project_backups = {}
        for backup_path in backup_files:
            # Extract project name from backup filename
            # Format: {project}.backup.{timestamp}.yml
            parts = backup_path.stem.split('.backup.')
            if len(parts) != 2:
                continue
            
            project_name = parts[0]
            
            # Check if backup is recent
            mtime = datetime.fromtimestamp(backup_path.stat().st_mtime)
            if mtime < cutoff_date:
                continue
            
            if project_name not in project_backups:
                project_backups[project_name] = []
            project_backups[project_name].append(backup_path)
        
        # Move backups to project folders
        for project_name, backups in project_backups.items():
            project_backups_dir = PROJECTS_DIR / project_name / "backups"
            
            if not project_backups_dir.exists():
                logger.warning(f"Project folder not found: {project_name}, skipping backups")
                continue
            
            for backup_path in backups:
                target_path = project_backups_dir / backup_path.name
                
                if self.dry_run:
                    logger.info(f"[DRY RUN] Would move: {backup_path.name} → {project_name}/backups/")
                else:
                    shutil.move(str(backup_path), str(target_path))
                    logger.debug(f"Moved: {backup_path.name} → {project_name}/backups/")
                
                self.stats.backups_migrated += 1
        
        logger.info(f"Migrated {self.stats.backups_migrated} recent backups")
    
    def cleanup_old_structure(self):
        """Archive old backups and clear output."""
        logger.info("Cleaning up old structure...")
        
        # Archive old backups directory
        if BACKUPS_DIR.exists():
            archive_name = f"backups_archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            archive_path = BACKUPS_DIR.parent / archive_name
            
            if self.dry_run:
                logger.info(f"[DRY RUN] Would archive: {BACKUPS_DIR} → {archive_path}")
            else:
                shutil.move(str(BACKUPS_DIR), str(archive_path))
                logger.info(f"Archived: {BACKUPS_DIR} → {archive_path}")
        
        # Start fresh with output
        if OUTPUT_DIR.exists():
            if self.dry_run:
                logger.info(f"[DRY RUN] Would clear: {OUTPUT_DIR}")
            else:
                shutil.rmtree(OUTPUT_DIR)
                OUTPUT_DIR.mkdir()
                logger.info(f"Cleared: {OUTPUT_DIR}")
    
    def verify_migration(self):
        """Health checks after migration."""
        logger.info("Verifying migration...")
        
        issues = []
        
        # Check all projects have shapeshifter.yml
        project_dirs = [d for d in PROJECTS_DIR.iterdir() if d.is_dir() and d.name not in ["data_sources", "shared-data"]]
        
        for project_dir in project_dirs:
            config_path = project_dir / "shapeshifter.yml"
            if not config_path.exists():
                issues.append(f"Missing shapeshifter.yml in {project_dir.name}")
            
            # Check subdirectories exist
            for subdir in ["backups", "output", "data"]:
                if not (project_dir / subdir).exists():
                    issues.append(f"Missing {subdir}/ in {project_dir.name}")
        
        # Check data_sources exists
        if not DATA_SOURCES_DIR.exists():
            issues.append("Missing data_sources/ folder")
        
        # Check shared-data exists
        if not SHARED_DATA_DIR.exists():
            issues.append("Missing shared-data/ folder")
        
        if issues:
            logger.error(f"Verification found {len(issues)} issues:")
            for issue in issues:
                logger.error(f"  - {issue}")
            return False
        else:
            logger.info("✅ Migration verification passed!")
            return True
    
    def run(self):
        """Execute full migration."""
        logger.info("=" * 60)
        if self.dry_run:
            logger.info("DRY RUN MODE - No changes will be made")
        else:
            logger.info("EXECUTING MIGRATION")
        logger.info("=" * 60)
        
        # Step 1: Analyze
        analysis = self.analyze_current_structure()
        
        # Step 2: Create new structure
        self.create_new_structure()
        
        # Step 3: Migrate projects
        self.migrate_projects(analysis["projects"])
        
        # Step 4: Migrate data sources
        self.migrate_data_sources(analysis["data_sources"])
        
        # Step 5: Migrate shared data
        self.migrate_shared_data(analysis["shared_data"])
        
        # Step 6: Migrate recent backups
        self.migrate_recent_backups(analysis["projects"])
        
        # Step 7: Cleanup
        if not self.dry_run:
            self.cleanup_old_structure()
        
        # Print summary
        logger.info("=" * 60)
        logger.info("MIGRATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Projects migrated: {self.stats.projects_migrated}")
        logger.info(f"Data sources moved: {self.stats.data_sources_moved}")
        logger.info(f"Shared data files moved: {self.stats.shared_data_moved}")
        logger.info(f"Recent backups migrated: {self.stats.backups_migrated}")
        
        if self.stats.errors:
            logger.error(f"Errors encountered: {len(self.stats.errors)}")
            for error in self.stats.errors:
                logger.error(f"  - {error}")


def main():
    parser = argparse.ArgumentParser(description="Migrate project structure")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="Preview changes without executing")
    group.add_argument("--execute", action="store_true", help="Execute migration")
    group.add_argument("--verify", action="store_true", help="Verify migration completed successfully")
    
    args = parser.parse_args()
    
    if args.verify:
        migration = ProjectStructureMigration(dry_run=True)
        success = migration.verify_migration()
        exit(0 if success else 1)
    else:
        migration = ProjectStructureMigration(dry_run=args.dry_run)
        migration.run()
        
        if not args.dry_run:
            migration.verify_migration()


if __name__ == "__main__":
    main()
```

**Usage:**
```bash
# 1. Preview changes
python scripts/migrate_project_structure.py --dry-run

# 2. Execute migration
python scripts/migrate_project_structure.py --execute

# 3. Verify
python scripts/migrate_project_structure.py --verify
```

---

### **Phase 3-6: Summary**

**Phase 3: API Updates** - Update endpoints to work with new paths (2 hours)  
**Phase 4: Frontend** - Minor updates to project creation (1 hour)  
**Phase 5: Documentation** - Update all docs with new structure (2 hours)  
**Phase 6: Deployment** - Backup, migrate, verify, restart (1 hour)

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|---------|------------|
| Data loss during migration | Low | **High** | ✅ Full tar.gz backup before migration |
| Path resolution bugs | Medium | Medium | ✅ Comprehensive tests + dry-run mode |
| Breaking existing projects | Medium | **High** | ✅ Backward compat check + rollback plan |
| Migration script errors | Medium | Medium | ✅ Dry-run + verify mode |
| Backup corruption | Low | Medium | ✅ Keep original backups in archive/ |
| User confusion | Low | Low | ✅ Clear documentation |

---

## Rollout Strategy

### Pre-Migration Checklist

- [ ] Full backup: `tar -czf projects_backup_$(date +%Y%m%d).tar.gz projects/`
- [ ] Code review: Phase 1 backend changes
- [ ] Tests passing: Unit tests for new services
- [ ] Dry-run successful: Migration script preview looks correct

### Migration Steps

```bash
# 1. Backup
tar -czf projects_backup_$(date +%Y%m%d).tar.gz projects/
tar -czf backups_backup_$(date +%Y%m%d).tar.gz backups/

# 2. Dry run (review output carefully)
python scripts/migrate_project_structure.py --dry-run > migration_plan.txt
cat migration_plan.txt  # Review

# 3. Execute
python scripts/migrate_project_structure.py --execute

# 4. Verify
python scripts/migrate_project_structure.py --verify

# 5. Test
# - Load projects via API
# - Save a project
# - Check backups created in project folder

# 6. Restart backend
make backend-restart

# 7. Smoke test
# - Open frontend
# - Load project
# - Graph view works
# - Save project works
```

### Rollback Plan

If migration fails:

```bash
# 1. Stop backend
make backend-stop

# 2. Restore backup
rm -rf projects/
tar -xzf projects_backup_YYYYMMDD.tar.gz

# 3. Restore code
git checkout backend/app/

# 4. Restart
make backend-run
```

---

## Success Criteria

### After Phase 1 (Backend Infrastructure)
- ✅ New path resolution works for loading projects
- ✅ Backups created in project subfolder
- ✅ All tests pass

### After Phase 2 (Migration)
- ✅ All projects have `shapeshifter.yml` in dedicated folders
- ✅ Data sources in `data_sources/`
- ✅ Shared data organized by provider
- ✅ Recent backups migrated to project folders
- ✅ No orphaned files

### After Phase 6 (Deployment)
- ✅ Backend starts successfully
- ✅ Frontend can load all projects
- ✅ Graph view works
- ✅ Saving project creates backup in project folder
- ✅ No errors in logs

---

## Future Enhancements

### Phase 7: Symlink Support (Future)
- Copy-on-write pattern for shared resource files
- Auto-detection of identical mappings/replacements
- UI for managing symlinks

### Phase 8: Data Source Management UI
- Browse `data_sources/` configs
- Edit connection details
- Test connections

### Phase 9: Project File Browser
- View project's data/ folder
- Upload/download files
- Manage backups

---

## Appendix: Example Migration Output

```
==========================================================
EXECUTING MIGRATION
==========================================================
Analyzing current structure...
Found 12 projects
Found 5 data source configs
Found 8 shared data files

Creating new folder structure...
Created: projects/data_sources
Created: projects/shared-data
Created: projects/shared-data/common
Created: projects/shared-data/arbodat
Created: projects/shared-data/bugscep

Migrating 12 projects...
Migrating project: arbodat
Moved: arbodat.yml → arbodat/shapeshifter.yml
Copied: mappings.yml → arbodat/
Copied: replacements.yml → arbodat/
...

Migrating 5 data source configs...
Moved: arbodat-database.yml → data_sources/
Moved: sead-options.yml → data_sources/
...

Migrating 8 shared data files...
Moved: ArchBotDaten.mdb → shared-data/arbodat/
Moved: bugsdata_20250608.mdb → shared-data/bugscep/
...

Migrating recent backups (last 30 days)...
Migrated 45 recent backups

Cleaning up old structure...
Archived: backups/ → backups_archive_20260211_143022
Cleared: output/

==========================================================
MIGRATION SUMMARY
==========================================================
Projects migrated: 12
Data sources moved: 5
Shared data files moved: 8
Recent backups migrated: 45
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-11 | AI Assistant | Initial implementation plan |

---

**Next Step:** Proceed with Phase 1 implementation (backend infrastructure updates).
