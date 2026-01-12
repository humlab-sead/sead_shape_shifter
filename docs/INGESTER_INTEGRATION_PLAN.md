# SEAD Clearinghouse Ingester Integration Plan

## Executive Summary

This document outlines the detailed implementation plan for integrating the SEAD Clearinghouse Import system into Shape Shifter as a modular ingester. The integration will allow users to:

1. Execute the Shape Shifter workflow to generate Excel output
2. Optionally validate the Excel file against SEAD database schema requirements
3. Automatically ingest the Excel file into a SEAD PostgreSQL database

The integration maintains modularity by placing the ingester in a separate `backend/app/ingesters/` directory with a well-defined interface, enabling future ingester implementations.

---

## Current Architecture Analysis

### Shape Shifter Workflow

**Current Pipeline:**
```
Project Config → ShapeShifter.normalize() → Dispatcher → Output File/DB
```

**Key Components:**
- `ExecuteService`: Orchestrates workflow execution
- `Dispatchers`: Registry of output formatters (Excel, CSV, PostgreSQL, SQLite)
- `ShapeShiftProject`: Project configuration model
- `ValidationService`: Project configuration validation

**Current Execute Endpoint:**
- `POST /api/v1/execute/projects/{name}/execute`
- Returns `ExecuteResult` with success status and download path

### SEAD Clearinghouse Import Workflow

**Current Pipeline:**
```
Excel File → Submission → Policies → Validation → CSV Dispatch → DB Upload → Explode
```

**Key Components:**
- `ImportService`: Orchestrates import workflow
- `Submission`: Excel data wrapper with pandas DataFrames
- `Policies`: Auto-registered transformation rules (Registry pattern)
- `Specifications`: Auto-registered validation rules (Registry pattern)
- `SchemaService`: Loads SEAD database schema metadata
- `SubmissionRepository`: Database operations

**Entry Point:**
- CLI script: `importer/scripts/import_excel.py`
- Key options: `--check-only`, `--register`, `--explode`

---

## Design Goals

1. **Modularity**: Keep ingester decoupled from core Shape Shifter logic
2. **Interface-based**: Define clear ingester protocol/interface
3. **Registry Pattern**: Auto-discover available ingesters
4. **Validation First**: Users can validate before ingesting
5. **CLI Support**: Maintain command-line workflow capability
6. **No Domain Sharing**: Excel file is the API contract
7. **Future-proof**: Easy to add new ingesters later

---

## Architecture Design

### 1. Ingester Interface (Protocol)

Define a standard interface that all ingesters must implement:

```python
# backend/app/ingesters/protocol.py

from typing import Protocol, runtime_checkable
from dataclasses import dataclass
from pathlib import Path


@dataclass
class IngesterMetadata:
    """Metadata about an ingester."""
    key: str
    name: str
    description: str
    version: str
    supported_formats: list[str]  # e.g., ["xlsx", "xls"]
    requires_config: bool


@dataclass
class ValidationResult:
    """Result of ingester validation."""
    is_valid: bool
    errors: list[str]
    warnings: list[str]
    infos: list[str]
    
    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0


@dataclass
class IngestionResult:
    """Result of ingestion operation."""
    success: bool
    message: str
    submission_id: int | None
    tables_processed: int
    records_inserted: int
    error_details: str | None


@dataclass
class IngesterConfig:
    """Configuration for an ingester instance."""
    # Database connection
    host: str
    port: int
    dbname: str
    user: str
    password: str | None = None
    
    # Ingestion options
    submission_name: str
    data_types: str
    output_folder: str = "output"
    check_only: bool = False
    register: bool = True
    explode: bool = True
    
    # Extra options (ingester-specific)
    extra: dict[str, Any] | None = None


@runtime_checkable
class Ingester(Protocol):
    """Protocol defining the ingester interface."""
    
    @classmethod
    def get_metadata(cls) -> IngesterMetadata:
        """Get ingester metadata."""
        ...
    
    def __init__(self, config: IngesterConfig) -> None:
        """Initialize ingester with configuration."""
        ...
    
    async def validate(self, excel_file: Path | str) -> ValidationResult:
        """
        Validate Excel file without ingesting.
        
        Args:
            excel_file: Path to Excel file to validate
            
        Returns:
            ValidationResult with errors, warnings, and info messages
        """
        ...
    
    async def ingest(
        self, 
        excel_file: Path | str,
        validate_first: bool = True
    ) -> IngestionResult:
        """
        Ingest Excel file into target system.
        
        Args:
            excel_file: Path to Excel file to ingest
            validate_first: Run validation before ingesting
            
        Returns:
            IngestionResult with success status and details
        """
        ...
```

### 2. Ingester Registry

Similar to Shape Shifter's Dispatcher registry:

```python
# backend/app/ingesters/registry.py

from typing import Type
from backend.app.ingesters.protocol import Ingester, IngesterMetadata
from src.utility import Registry


class IngesterRegistry(Registry[Type[Ingester]]):
    """Registry for data ingesters."""
    items: dict[str, Type[Ingester]] = {}
    
    def get_metadata_list(self) -> list[IngesterMetadata]:
        """Get metadata for all registered ingesters."""
        return [cls.get_metadata() for cls in self.items.values()]


# Global registry instance
Ingesters = IngesterRegistry()
```

### 3. SEAD Ingester Implementation

Move clearinghouse import code to `backend/app/ingesters/sead/`:

```
backend/app/ingesters/
├── __init__.py
├── protocol.py                 # Ingester interface definition
├── registry.py                 # IngesterRegistry
├── service.py                  # IngesterService (facade)
└── sead/
    ├── __init__.py
    ├── ingester.py             # SeadIngester implementation
    ├── metadata.py             # SeadSchema (from clearinghouse)
    ├── policies.py             # Policy transformations
    ├── specification.py        # Validation specifications
    ├── submission.py           # Submission data wrapper
    ├── repository.py           # Database operations
    ├── utility.py              # Helper functions
    ├── dispatchers/
    │   └── to_csv.py          # CSV dispatcher
    └── uploader/
        ├── base_uploader.py
        └── csv_uploader.py
```

**SeadIngester Implementation:**

```python
# backend/app/ingesters/sead/ingester.py

from pathlib import Path
from loguru import logger

from backend.app.ingesters.protocol import (
    Ingester, IngesterMetadata, IngesterConfig,
    ValidationResult, IngestionResult
)
from backend.app.ingesters.registry import Ingesters
from ingesters.sead.metadata import SchemaService, SeadSchema
from ingesters.sead.submission import Submission
from ingesters.sead.specification import SubmissionSpecification
from ingesters.sead.repository import SubmissionRepository
from ingesters.sead.process import ImportService, Options


@Ingesters.register(key="sead")
class SeadIngester:
    """Ingester for SEAD Clearinghouse database."""
    
    def __init__(self, config: IngesterConfig) -> None:
        self.config = config
        
        # Initialize schema service
        db_uri = self._build_db_uri()
        self.schema_service = SchemaService(db_uri)
        self.schema: SeadSchema | None = None
        
    @classmethod
    def get_metadata(cls) -> IngesterMetadata:
        return IngesterMetadata(
            key="sead",
            name="SEAD Clearinghouse",
            description="Ingest data into SEAD Clearinghouse PostgreSQL database",
            version="1.0.0",
            supported_formats=["xlsx"],
            requires_config=True,
        )
    
    def _build_db_uri(self) -> str:
        """Build PostgreSQL URI from config."""
        password_part = f":{self.config.password}" if self.config.password else ""
        return (
            f"postgresql+psycopg://{self.config.user}{password_part}"
            f"@{self.config.host}:{self.config.port}/{self.config.dbname}"
        )
    
    async def _load_schema(self) -> SeadSchema:
        """Load schema if not already loaded."""
        if self.schema is None:
            self.schema = self.schema_service.load()
        return self.schema
    
    async def validate(self, excel_file: Path | str) -> ValidationResult:
        """Validate Excel file against SEAD schema."""
        try:
            schema = await self._load_schema()
            
            # Load submission with policies
            submission = Submission.load(
                schema=schema,
                source=str(excel_file),
                service=self.schema_service,
                apply_policies=True
            )
            
            # Run validation
            specification = SubmissionSpecification(
                schema=schema,
                ignore_columns=self.config.extra.get("ignore_columns") if self.config.extra else None,
                raise_errors=False
            )
            
            is_valid = specification.is_satisfied_by(submission)
            
            return ValidationResult(
                is_valid=is_valid,
                errors=specification.errors,
                warnings=specification.warnings,
                infos=specification.infos
            )
            
        except Exception as e:
            logger.exception(f"Validation failed: {e}")
            return ValidationResult(
                is_valid=False,
                errors=[f"Validation error: {str(e)}"],
                warnings=[],
                infos=[]
            )
    
    async def ingest(
        self, 
        excel_file: Path | str,
        validate_first: bool = True
    ) -> IngestionResult:
        """Ingest Excel file into SEAD database."""
        try:
            # Validate first if requested
            if validate_first:
                validation = await self.validate(excel_file)
                if not validation.is_valid:
                    return IngestionResult(
                        success=False,
                        message="Validation failed",
                        submission_id=None,
                        tables_processed=0,
                        records_inserted=0,
                        error_details="\n".join(validation.errors)
                    )
            
            # Build import options
            opts = Options(
                filename=str(excel_file),
                skip=False,
                submission_id=None,
                submission_name=self.config.submission_name,
                data_types=self.config.data_types,
                table_names=[],
                check_only=self.config.check_only,
                register=self.config.register,
                explode=self.config.explode,
                timestamp=True,
                ignore_columns=self.config.extra.get("ignore_columns") if self.config.extra else None,
                output_folder=self.config.output_folder,
                database={
                    "host": self.config.host,
                    "port": self.config.port,
                    "dbname": self.config.dbname,
                    "user": self.config.user,
                },
                transfer_format="csv",
                dump_to_csv=False,
            )
            
            schema = await self._load_schema()
            
            # Execute import service
            import_service = ImportService(
                opts=opts,
                schema=schema,
                service=self.schema_service
            )
            
            # Process submission
            import_service.process(process_target=str(excel_file))
            
            # Extract results (would need to extend ImportService to return these)
            return IngestionResult(
                success=True,
                message=f"Successfully ingested submission '{self.config.submission_name}'",
                submission_id=opts.submission_id,
                tables_processed=len(schema.keys()),
                records_inserted=0,  # Would need to track this
                error_details=None
            )
            
        except Exception as e:
            logger.exception(f"Ingestion failed: {e}")
            return IngestionResult(
                success=False,
                message="Ingestion failed",
                submission_id=None,
                tables_processed=0,
                records_inserted=0,
                error_details=str(e)
            )
```

### 4. Backend API Endpoints

Add new endpoints for ingester operations:

```python
# backend/app/api/v1/endpoints/ingesters.py

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from loguru import logger

from backend.app.ingesters.protocol import IngesterMetadata, ValidationResult, IngestionResult
from backend.app.ingesters.registry import Ingesters
from backend.app.ingesters.service import IngesterService, get_ingester_service
from backend.app.utils.error_handlers import handle_endpoint_errors

router = APIRouter()


class IngesterListItem(BaseModel):
    """Ingester metadata for listing."""
    key: str
    name: str
    description: str
    version: str
    supported_formats: list[str]
    requires_config: bool


class ValidateIngesterRequest(BaseModel):
    """Request to validate a file with an ingester."""
    excel_path: str = Field(..., description="Path to Excel file (from previous workflow execution)")
    config: dict[str, Any] = Field(..., description="Ingester-specific configuration")


class IngestRequest(BaseModel):
    """Request to ingest a file."""
    excel_path: str = Field(..., description="Path to Excel file (from previous workflow execution)")
    config: dict[str, Any] = Field(..., description="Ingester-specific configuration")
    validate_first: bool = Field(True, description="Run validation before ingesting")


@router.get("/ingesters", response_model=list[IngesterListItem])
@handle_endpoint_errors
async def list_ingesters() -> list[IngesterListItem]:
    """
    List all available ingesters.
    
    Returns:
        List of ingester metadata
    """
    service = get_ingester_service()
    metadata_list = service.list_ingesters()
    
    return [
        IngesterListItem(
            key=meta.key,
            name=meta.name,
            description=meta.description,
            version=meta.version,
            supported_formats=meta.supported_formats,
            requires_config=meta.requires_config
        )
        for meta in metadata_list
    ]


@router.get("/ingesters/{key}/info", response_model=IngesterMetadata)
@handle_endpoint_errors
async def get_ingester_info(key: str) -> IngesterMetadata:
    """
    Get detailed information about a specific ingester.
    
    Args:
        key: Ingester key (e.g., 'sead')
        
    Returns:
        Detailed ingester metadata
    """
    service = get_ingester_service()
    metadata = service.get_ingester_metadata(key)
    
    if metadata is None:
        raise HTTPException(status_code=404, detail=f"Ingester '{key}' not found")
    
    return metadata


@router.post("/ingesters/{key}/validate", response_model=ValidationResult)
@handle_endpoint_errors
async def validate_with_ingester(key: str, request: ValidateIngesterRequest) -> ValidationResult:
    """
    Validate an Excel file using the specified ingester.
    
    Args:
        key: Ingester key (e.g., 'sead')
        request: Validation request with Excel path and config
        
    Returns:
        ValidationResult with errors, warnings, and info messages
    """
    service = get_ingester_service()
    
    logger.info(f"Validating file '{request.excel_path}' with ingester '{key}'")
    
    result = await service.validate(
        ingester_key=key,
        excel_path=request.excel_path,
        config=request.config
    )
    
    if result.has_errors:
        logger.warning(f"Validation failed with {len(result.errors)} errors")
    else:
        logger.info("Validation passed successfully")
    
    return result


@router.post("/ingesters/{key}/ingest", response_model=IngestionResult)
@handle_endpoint_errors
async def ingest_with_ingester(key: str, request: IngestRequest) -> IngestionResult:
    """
    Ingest an Excel file using the specified ingester.
    
    Args:
        key: Ingester key (e.g., 'sead')
        request: Ingestion request with Excel path, config, and options
        
    Returns:
        IngestionResult with success status and details
    """
    service = get_ingester_service()
    
    logger.info(f"Ingesting file '{request.excel_path}' with ingester '{key}'")
    
    result = await service.ingest(
        ingester_key=key,
        excel_path=request.excel_path,
        config=request.config,
        validate_first=request.validate_first
    )
    
    if result.success:
        logger.info(f"Ingestion completed: {result.message}")
    else:
        logger.error(f"Ingestion failed: {result.message}")
    
    return result
```

### 5. Ingester Service (Facade)

Service layer to orchestrate ingester operations:

```python
# backend/app/ingesters/service.py

from pathlib import Path
from typing import Any
from functools import lru_cache

from loguru import logger

from backend.app.ingesters.protocol import (
    Ingester, IngesterMetadata, IngesterConfig,
    ValidationResult, IngestionResult
)
from backend.app.ingesters.registry import Ingesters


class IngesterService:
    """Service for managing ingesters."""
    
    def list_ingesters(self) -> list[IngesterMetadata]:
        """List all registered ingesters."""
        return Ingesters.get_metadata_list()
    
    def get_ingester_metadata(self, key: str) -> IngesterMetadata | None:
        """Get metadata for a specific ingester."""
        ingester_cls = Ingesters.get(key)
        if ingester_cls is None:
            return None
        return ingester_cls.get_metadata()
    
    def _create_ingester_config(self, config_dict: dict[str, Any]) -> IngesterConfig:
        """Create IngesterConfig from dictionary."""
        return IngesterConfig(**config_dict)
    
    async def validate(
        self,
        ingester_key: str,
        excel_path: str,
        config: dict[str, Any]
    ) -> ValidationResult:
        """Validate Excel file with specified ingester."""
        ingester_cls = Ingesters.get(ingester_key)
        if ingester_cls is None:
            raise ValueError(f"Ingester '{ingester_key}' not found")
        
        ingester_config = self._create_ingester_config(config)
        ingester = ingester_cls(ingester_config)
        
        return await ingester.validate(excel_path)
    
    async def ingest(
        self,
        ingester_key: str,
        excel_path: str,
        config: dict[str, Any],
        validate_first: bool = True
    ) -> IngestionResult:
        """Ingest Excel file with specified ingester."""
        ingester_cls = Ingesters.get(ingester_key)
        if ingester_cls is None:
            raise ValueError(f"Ingester '{ingester_key}' not found")
        
        ingester_config = self._create_ingester_config(config)
        ingester = ingester_cls(ingester_config)
        
        return await ingester.ingest(excel_path, validate_first=validate_first)


@lru_cache
def get_ingester_service() -> IngesterService:
    """Get singleton IngesterService instance."""
    return IngesterService()
```

### 6. Frontend Integration

Add ingester UI components to the Execute workflow dialog:

**Components:**
- `IngesterSelector.vue` - Dropdown to select ingester
- `IngesterConfig.vue` - Dynamic form for ingester configuration
- `ValidationFeedback.vue` - Display validation results
- `IngestionProgress.vue` - Show ingestion progress

**User Flow:**

```
Execute Dialog
├── [Existing] Select Dispatcher (Excel, CSV, etc.)
├── [Existing] Configure Target Path
├── [Existing] Run Workflow Button
│
└── [NEW] Post-Execution Actions
    ├── Validate with Ingester (optional)
    │   ├── Select Ingester (dropdown)
    │   ├── Configure Connection
    │   └── Run Validation Button
    │       └── Display Results (errors/warnings/info)
    │
    └── Ingest to Database
        ├── Ingester Config (from validation step)
        ├── Validate First (checkbox, default: true)
        └── Ingest Button
            └── Display Results (success/errors)
```

**Implementation:**

```vue
<!-- frontend/src/components/execute/IngesterPanel.vue -->

<template>
  <v-card v-if="showIngesters && executeResult?.success">
    <v-card-title>Post-Execution: Ingest to Database</v-card-title>
    
    <v-card-text>
      <v-select
        v-model="selectedIngester"
        :items="availableIngesters"
        item-title="name"
        item-value="key"
        label="Select Ingester"
        hint="Choose the target system for data ingestion"
        persistent-hint
      />
      
      <v-expand-transition>
        <div v-if="selectedIngester">
          <IngesterConfig 
            :ingester-key="selectedIngester"
            v-model="ingesterConfig"
          />
          
          <v-checkbox
            v-model="validateFirst"
            label="Validate before ingesting"
            hint="Recommended: check data validity before database insertion"
          />
          
          <v-btn
            color="primary"
            @click="handleValidate"
            :loading="validating"
            :disabled="!canValidate"
          >
            <v-icon left>mdi-check-circle</v-icon>
            Validate
          </v-btn>
          
          <v-btn
            v-if="validationResult"
            color="success"
            @click="handleIngest"
            :loading="ingesting"
            :disabled="!canIngest"
          >
            <v-icon left>mdi-database-import</v-icon>
            Ingest to {{ selectedIngesterName }}
          </v-btn>
        </div>
      </v-expand-transition>
      
      <ValidationFeedback
        v-if="validationResult"
        :result="validationResult"
      />
      
      <IngestionFeedback
        v-if="ingestionResult"
        :result="ingestionResult"
      />
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { apiClient } from '@/api/client'
import type { 
  IngesterMetadata, 
  ValidationResult, 
  IngestionResult,
  ExecuteResult 
} from '@/types'

interface Props {
  executeResult: ExecuteResult | null
  showIngesters: boolean
}

const props = defineProps<Props>()

const availableIngesters = ref<IngesterMetadata[]>([])
const selectedIngester = ref<string | null>(null)
const ingesterConfig = ref<Record<string, any>>({})
const validateFirst = ref(true)
const validating = ref(false)
const ingesting = ref(false)
const validationResult = ref<ValidationResult | null>(null)
const ingestionResult = ref<IngestionResult | null>(null)

const selectedIngesterName = computed(() => {
  const ingester = availableIngesters.value.find(i => i.key === selectedIngester.value)
  return ingester?.name || ''
})

const canValidate = computed(() => {
  return selectedIngester.value && ingesterConfig.value && !validating.value
})

const canIngest = computed(() => {
  return canValidate.value && 
         (!validateFirst.value || validationResult.value?.is_valid) &&
         !ingesting.value
})

async function loadIngesters() {
  try {
    const response = await apiClient.get('/ingesters')
    availableIngesters.value = response.data
  } catch (error) {
    console.error('Failed to load ingesters:', error)
  }
}

async function handleValidate() {
  if (!props.executeResult?.target || !selectedIngester.value) return
  
  validating.value = true
  validationResult.value = null
  
  try {
    const response = await apiClient.post(
      `/ingesters/${selectedIngester.value}/validate`,
      {
        excel_path: props.executeResult.target,
        config: ingesterConfig.value
      }
    )
    validationResult.value = response.data
  } catch (error) {
    console.error('Validation failed:', error)
  } finally {
    validating.value = false
  }
}

async function handleIngest() {
  if (!props.executeResult?.target || !selectedIngester.value) return
  
  ingesting.value = true
  ingestionResult.value = null
  
  try {
    const response = await apiClient.post(
      `/ingesters/${selectedIngester.value}/ingest`,
      {
        excel_path: props.executeResult.target,
        config: ingesterConfig.value,
        validate_first: validateFirst.value
      }
    )
    ingestionResult.value = response.data
  } catch (error) {
    console.error('Ingestion failed:', error)
  } finally {
    ingesting.value = false
  }
}

onMounted(() => {
  loadIngesters()
})
</script>
```

### 7. CLI Integration

Add CLI command for ingestion workflow:

```python
# backend/app/cli/ingest.py

import asyncio
import click
from pathlib import Path
from loguru import logger

from backend.app.ingesters.service import IngesterService
from backend.app.ingesters.protocol import IngesterConfig


@click.group()
def ingest():
    """Ingester commands."""
    pass


@ingest.command()
def list_ingesters():
    """List available ingesters."""
    service = IngesterService()
    ingesters = service.list_ingesters()
    
    click.echo("Available ingesters:")
    for ingester in ingesters:
        click.echo(f"  {ingester.key}: {ingester.name} (v{ingester.version})")
        click.echo(f"    {ingester.description}")


@ingest.command()
@click.argument("ingester_key")
@click.argument("excel_file", type=click.Path(exists=True))
@click.option("--host", required=True, help="Database host")
@click.option("--port", default=5432, help="Database port")
@click.option("--dbname", required=True, help="Database name")
@click.option("--user", required=True, help="Database user")
@click.option("--password", help="Database password")
@click.option("--submission-name", required=True, help="Submission name")
@click.option("--data-types", default="", help="Data types description")
@click.option("--check-only", is_flag=True, help="Only validate, don't ingest")
@click.option("--no-register", is_flag=True, help="Skip registration step")
@click.option("--no-explode", is_flag=True, help="Skip explode step")
def run(
    ingester_key: str,
    excel_file: str,
    host: str,
    port: int,
    dbname: str,
    user: str,
    password: str | None,
    submission_name: str,
    data_types: str,
    check_only: bool,
    no_register: bool,
    no_explode: bool,
):
    """Run ingestion workflow."""
    
    config_dict = {
        "host": host,
        "port": port,
        "dbname": dbname,
        "user": user,
        "password": password,
        "submission_name": submission_name,
        "data_types": data_types,
        "check_only": check_only,
        "register": not no_register,
        "explode": not no_explode,
    }
    
    async def run_async():
        service = IngesterService()
        
        if check_only:
            click.echo(f"Validating {excel_file} with {ingester_key}...")
            result = await service.validate(ingester_key, excel_file, config_dict)
            
            if result.is_valid:
                click.echo("✓ Validation passed")
            else:
                click.echo(f"✗ Validation failed with {len(result.errors)} errors:")
                for error in result.errors:
                    click.echo(f"  - {error}")
        else:
            click.echo(f"Ingesting {excel_file} with {ingester_key}...")
            result = await service.ingest(ingester_key, excel_file, config_dict)
            
            if result.success:
                click.echo(f"✓ {result.message}")
                click.echo(f"  Submission ID: {result.submission_id}")
                click.echo(f"  Tables: {result.tables_processed}")
            else:
                click.echo(f"✗ Ingestion failed: {result.message}")
                if result.error_details:
                    click.echo(f"  Details: {result.error_details}")
    
    asyncio.run(run_async())
```

---

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1)

**Tasks:**

1. **Create ingester protocol and registry** (2 days)
   - [ ] Create `backend/app/ingesters/protocol.py` with interfaces
   - [ ] Create `backend/app/ingesters/registry.py` with IngesterRegistry
   - [ ] Write unit tests for registry pattern
   - [ ] Update AGENTS.md with ingester patterns

2. **Copy clearinghouse code to ingesters/sead/** (1 day)
   - [ ] Create `backend/app/ingesters/sead/` directory structure
   - [ ] Copy relevant modules (metadata, policies, specification, etc.)
   - [ ] Exclude `configuration/` module (use Shape Shifter's)
   - [x] Update imports to use `ingesters.sead` namespace
   - [ ] Remove deprecated code

3. **Implement SeadIngester class** (2 days)
   - [ ] Create `backend/app/ingesters/sead/ingester.py`
   - [ ] Implement `get_metadata()` class method
   - [ ] Implement `validate()` method
   - [ ] Implement `ingest()` method
   - [ ] Register with `@Ingesters.register(key="sead")`
   - [ ] Write unit tests

**Milestone:** Core ingester infrastructure complete, SEAD ingester functional

---

### Phase 2: Backend API (Week 2)

**Tasks:**

1. **Create IngesterService** (1 day)
   - [ ] Create `backend/app/ingesters/service.py`
   - [ ] Implement `list_ingesters()`, `validate()`, `ingest()`
   - [ ] Add singleton getter `get_ingester_service()`
   - [ ] Write service tests

2. **Create API endpoints** (2 days)
   - [ ] Create `backend/app/api/v1/endpoints/ingesters.py`
   - [ ] Implement `GET /ingesters` (list)
   - [ ] Implement `GET /ingesters/{key}/info` (metadata)
   - [ ] Implement `POST /ingesters/{key}/validate`
   - [ ] Implement `POST /ingesters/{key}/ingest`
   - [ ] Register router in `backend/app/api/v1/api.py`
   - [ ] Write endpoint tests

3. **Create Pydantic models** (1 day)
   - [ ] Create `backend/app/models/ingester.py`
   - [ ] Add request/response models
   - [ ] Update API documentation

**Milestone:** Backend API complete and tested

---

### Phase 3: Frontend Integration (Week 3)

**Tasks:**

1. **Create ingester types and API client** (1 day)
   - [ ] Create `frontend/src/types/ingester.ts`
   - [ ] Add API methods to `frontend/src/api/ingesters.ts`
   - [ ] Create Pinia store `frontend/src/stores/ingester.ts`

2. **Build ingester UI components** (3 days)
   - [ ] Create `IngesterSelector.vue` (ingester dropdown)
   - [ ] Create `IngesterConfig.vue` (dynamic config form)
   - [ ] Create `ValidationFeedback.vue` (validation results)
   - [ ] Create `IngestionFeedback.vue` (ingestion results)
   - [ ] Create `IngesterPanel.vue` (main panel component)

3. **Integrate with Execute dialog** (1 day)
   - [ ] Update `ExecuteDialog.vue` to include IngesterPanel
   - [ ] Add "Post-Execution Actions" section
   - [ ] Wire up event handlers and state management
   - [ ] Test complete workflow

**Milestone:** Frontend integration complete

---

### Phase 4: CLI and Documentation (Week 4)

**Tasks:**

1. **Implement CLI commands** (2 days)
   - [ ] Create `backend/app/cli/ingest.py`
   - [ ] Implement `ingest list-ingesters`
   - [ ] Implement `ingest run`
   - [ ] Register CLI commands in main CLI
   - [ ] Write CLI usage examples

2. **Write documentation** (2 days)
   - [ ] Create `docs/INGESTER_GUIDE.md` (user guide)
   - [ ] Create `docs/INGESTER_DEVELOPMENT.md` (developer guide)
   - [ ] Update `AGENTS.md` with ingester patterns
   - [ ] Update `README.md` with ingestion features
   - [ ] Add API documentation for endpoints

3. **Write tests** (1 day)
   - [ ] Integration tests for full workflow
   - [ ] End-to-end tests with mock database
   - [ ] Test error handling and edge cases

**Milestone:** Complete feature ready for production

---

## Configuration Management

### Backend Configuration

Add ingester configuration to `backend/app/core/settings.py`:

```python
class Settings(BaseSettings):
    # ... existing settings ...
    
    # Ingester settings
    INGESTERS_ENABLED: bool = True
    SEAD_DB_HOST: str = Field(default="localhost")
    SEAD_DB_PORT: int = Field(default=5432)
    SEAD_DB_NAME: str = Field(default="sead_staging")
    SEAD_DB_USER: str = Field(default="sead_user")
    SEAD_DB_PASSWORD: SecretStr | None = None
    
    class Config:
        env_file = ".env"
        env_prefix = "SEAD_"
```

### Environment Variables

```bash
# .env
SEAD_INGESTERS_ENABLED=true
SEAD_DB_HOST=localhost
SEAD_DB_PORT=5432
SEAD_DB_NAME=sead_staging_202501
SEAD_DB_USER=sead_admin
SEAD_DB_PASSWORD=secret
```

---

## Testing Strategy

### Unit Tests

```python
# tests/ingesters/test_sead_ingester.py

import pytest
from pathlib import Path
from ingesters.sead.ingester import SeadIngester
from backend.app.ingesters.protocol import IngesterConfig, ValidationResult


@pytest.fixture
def ingester_config() -> IngesterConfig:
    return IngesterConfig(
        host="localhost",
        port=5432,
        dbname="test_db",
        user="test_user",
        submission_name="test_submission",
        data_types="test",
    )


@pytest.fixture
def ingester(ingester_config: IngesterConfig) -> SeadIngester:
    return SeadIngester(ingester_config)


def test_get_metadata():
    """Test ingester metadata."""
    metadata = SeadIngester.get_metadata()
    assert metadata.key == "sead"
    assert metadata.name == "SEAD Clearinghouse"
    assert "xlsx" in metadata.supported_formats


@pytest.mark.asyncio
async def test_validate_valid_file(ingester: SeadIngester, test_excel_file: Path):
    """Test validation with valid Excel file."""
    result = await ingester.validate(test_excel_file)
    assert isinstance(result, ValidationResult)
    assert result.is_valid
    assert len(result.errors) == 0


@pytest.mark.asyncio
async def test_validate_invalid_file(ingester: SeadIngester, invalid_excel_file: Path):
    """Test validation with invalid Excel file."""
    result = await ingester.validate(invalid_excel_file)
    assert not result.is_valid
    assert len(result.errors) > 0
```

### Integration Tests

```python
# tests/integration/test_ingester_workflow.py

import pytest
from pathlib import Path
from backend.app.ingesters.service import IngesterService


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_ingestion_workflow(test_db, test_excel_file: Path):
    """Test complete ingestion workflow."""
    service = IngesterService()
    
    config = {
        "host": test_db.host,
        "port": test_db.port,
        "dbname": test_db.name,
        "user": test_db.user,
        "submission_name": "test_submission",
        "data_types": "test",
        "register": True,
        "explode": True,
    }
    
    # Validate
    validation_result = await service.validate("sead", str(test_excel_file), config)
    assert validation_result.is_valid
    
    # Ingest
    ingestion_result = await service.ingest("sead", str(test_excel_file), config)
    assert ingestion_result.success
    assert ingestion_result.submission_id is not None
```

---

## Security Considerations

1. **Database Credentials**
   - Store in environment variables or secrets manager
   - Never log passwords
   - Use encrypted connections (SSL/TLS)

2. **File Access**
   - Validate file paths to prevent directory traversal
   - Check file permissions before ingestion
   - Limit file size uploads

3. **API Security**
   - Add authentication/authorization for ingester endpoints
   - Rate limiting on ingestion operations
   - Audit logging for all database operations

---

## Performance Considerations

1. **Async Operations**
   - All ingester methods are async for non-blocking I/O
   - Database connections use connection pooling
   - Large files processed in chunks

2. **Caching**
   - Cache schema metadata to reduce DB queries
   - Reuse database connections
   - Cache validation results temporarily

3. **Resource Management**
   - Close database connections properly
   - Clean up temporary files
   - Limit concurrent ingestions

---

## Future Enhancements

1. **Additional Ingesters**
   - Generic PostgreSQL ingester
   - SQLite ingester
   - REST API ingester
   - Cloud storage ingester (S3, Azure Blob)

2. **Advanced Features**
   - Progress tracking with websockets
   - Batch ingestion support
   - Rollback/undo capabilities
   - Ingestion history and logs
   - Scheduled/automated ingestion

3. **Monitoring**
   - Ingestion metrics dashboard
   - Error rate monitoring
   - Performance profiling
   - Database health checks

---

## Dependencies

### New Python Packages

No new packages required! The clearinghouse import code already uses:
- `pandas` (already in Shape Shifter)
- `psycopg` (already in Shape Shifter)
- `openpyxl` (already in Shape Shifter)
- `loguru` (already in Shape Shifter)

### Frontend Dependencies

No new packages required! Use existing:
- Vue 3
- Vuetify
- Pinia
- Axios

---

## Migration Notes

### Differences from Current Clearinghouse Import

1. **Configuration**: Uses Shape Shifter's configuration system instead of its own
2. **Logging**: Uses Shape Shifter's loguru setup
3. **CLI**: New CLI interface, old `import_excel.py` remains for backward compatibility
4. **API**: RESTful endpoints instead of direct function calls
5. **Async**: All operations are async-first

### Backward Compatibility

- Keep original `sead_clearinghouse_import` repository for standalone use
- CLI script `import_excel.py` remains functional
- Can still be used independently of Shape Shifter

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Database schema changes | Medium | High | Version SEAD schema metadata, add migration support |
| Performance degradation | Low | Medium | Profile and optimize, add caching |
| Data corruption | Low | Critical | Transactions, validation, backups, dry-run mode |
| Breaking API changes | Low | Medium | Versioned API endpoints, deprecation warnings |
| Import conflicts | Medium | Low | Namespace separation, clear module boundaries |

---

## Success Criteria

1. ✅ Users can execute Shape Shifter workflow and get Excel output
2. ✅ Users can validate Excel file against SEAD schema via UI
3. ✅ Users can ingest validated Excel file into SEAD database via UI
4. ✅ CLI workflow remains functional
5. ✅ All tests pass (unit, integration, end-to-end)
6. ✅ Documentation complete and accurate
7. ✅ No regression in existing Shape Shifter functionality
8. ✅ Code follows existing patterns and conventions

---

## Appendix A: File Structure

```
backend/app/
├── ingesters/
│   ├── __init__.py
│   ├── protocol.py              # Ingester interface definitions
│   ├── registry.py              # IngesterRegistry class
│   ├── service.py               # IngesterService facade
│   │
│   └── sead/                    # SEAD ingester implementation
│       ├── __init__.py
│       ├── ingester.py          # SeadIngester class
│       ├── metadata.py          # SeadSchema, SchemaService
│       ├── policies.py          # Transformation policies
│       ├── specification.py     # Validation specifications
│       ├── submission.py        # Submission data wrapper
│       ├── repository.py        # Database operations
│       ├── utility.py           # Helper functions
│       │
│       ├── dispatchers/
│       │   └── to_csv.py       # CSV dispatcher
│       │
│       └── uploader/
│           ├── base_uploader.py
│           └── csv_uploader.py
│
├── api/v1/endpoints/
│   └── ingesters.py            # API endpoints for ingesters
│
├── models/
│   └── ingester.py             # Pydantic models for API
│
└── cli/
    └── ingest.py               # CLI commands for ingestion

frontend/src/
├── api/
│   └── ingesters.ts            # API client methods
│
├── types/
│   └── ingester.ts             # TypeScript types
│
├── stores/
│   └── ingester.ts             # Pinia store
│
└── components/execute/
    ├── IngesterPanel.vue       # Main ingester UI panel
    ├── IngesterSelector.vue    # Ingester dropdown
    ├── IngesterConfig.vue      # Configuration form
    ├── ValidationFeedback.vue  # Validation results
    └── IngestionFeedback.vue   # Ingestion results

docs/
├── INGESTER_INTEGRATION_PLAN.md  # This document
├── INGESTER_GUIDE.md             # User guide
└── INGESTER_DEVELOPMENT.md       # Developer guide
```

---

## Appendix B: Example Usage

### Via UI

1. Open project in Shape Shifter
2. Click "Execute" button
3. Select "Excel Workbook (xlsx)" dispatcher
4. Configure output path: `./output/my_data.xlsx`
5. Click "Run Workflow" → Excel file generated
6. In "Post-Execution Actions" section:
   - Select "SEAD Clearinghouse" ingester
   - Enter database connection details
   - Click "Validate" → See validation results
   - If valid, click "Ingest to SEAD" → Data ingested

### Via CLI

```bash
# Using Shape Shifter CLI
uv run python backend/app/cli/main.py ingest run sead \
  ./output/my_data.xlsx \
  --host localhost \
  --port 5432 \
  --dbname sead_staging \
  --user sead_admin \
  --submission-name "2026-01-11_MySubmission" \
  --data-types "dendro" \
  --check-only  # Validation only

# Full ingestion
uv run python backend/app/cli/main.py ingest run sead \
  ./output/my_data.xlsx \
  --host localhost \
  --port 5432 \
  --dbname sead_staging \
  --user sead_admin \
  --submission-name "2026-01-11_MySubmission" \
  --data-types "dendro"
```

### Via Python API

```python
from backend.app.ingesters.service import IngesterService
from backend.app.ingesters.protocol import IngesterConfig

service = IngesterService()

config = {
    "host": "localhost",
    "port": 5432,
    "dbname": "sead_staging",
    "user": "sead_admin",
    "submission_name": "2026-01-11_MySubmission",
    "data_types": "dendro",
}

# Validate
result = await service.validate("sead", "./output/my_data.xlsx", config)
print(f"Valid: {result.is_valid}")

# Ingest
if result.is_valid:
    result = await service.ingest("sead", "./output/my_data.xlsx", config)
    print(f"Success: {result.success}")
```

---

## Conclusion

This implementation plan provides a comprehensive roadmap for integrating the SEAD Clearinghouse Import system into Shape Shifter as a modular ingester. The design:

- **Maintains modularity** through clear interfaces and separation of concerns
- **Enables extensibility** via registry pattern for future ingesters
- **Preserves backward compatibility** with existing CLI workflows
- **Provides multiple interfaces** (UI, CLI, API) for different use cases
- **Follows Shape Shifter conventions** for consistency
- **Minimizes dependencies** by reusing existing packages

The phased implementation approach allows for incremental development and testing, with clear milestones to track progress. Each phase builds on the previous one, reducing risk and enabling early feedback.

Total estimated effort: **4 weeks** for full implementation including documentation and testing.
