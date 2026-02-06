# Project Loading Fault Tolerance Improvements

## Problem Analysis

### Current Behavior
A YAML syntax error (like the `contraints` typo) causes:
1. `YamlService.load()` throws `YamlLoadError` with generic error message
2. `ProjectService.load_project()` catches and re-raises as `ConfigurationError` 
3. **CRITICAL**: `/projects/{name}/raw-yaml` endpoint calls `load_project()` first, so **raw YAML is inaccessible**
4. Frontend receives HTTP 400 error with no way to access/fix the YAML
5. Users are **completely blocked** from editing their configuration

### Root Cause Issues
1. **No separation between YAML parsing and validation**
2. **Raw YAML endpoint validates before returning raw content** (line 476 in `projects.py`)
3. **Poor error context** - no line numbers, column numbers, or precise error location
4. **All-or-nothing loading** - no partial/degraded mode for broken configs

---

## Recommended Solutions

### 1. ✅ **Fix Raw YAML Endpoint** (CRITICAL - Quick Win)

**Problem**: `/projects/{name}/raw-yaml` calls `load_project()` before returning raw content, blocking access to broken YAML.

**Solution**: Remove validation from raw YAML getter - just verify file exists and return content.

```python
# backend/app/api/v1/endpoints/projects.py

@router.get("/projects/{name}/raw-yaml", response_model=dict[str, str])
@handle_endpoint_errors
async def get_project_raw_yaml(name: str) -> dict[str, str]:
    """
    Get project as raw YAML string.
    
    Does NOT validate - returns raw content even if YAML is malformed.
    This allows users to fix broken configuration files.
    """
    project_service: ProjectService = get_project_service()
    
    # REMOVE: project_service.load_project(name)  # Don't validate!
    
    project_path = settings.PROJECTS_DIR / f"{name}.yml"
    if not project_path.exists():
        raise NotFoundError(f"Project file not found: {name}.yml")

    yaml_content = project_path.read_text(encoding="utf-8")
    
    logger.info(f"Retrieved raw YAML for project '{name}' (no validation)")
    
    return {"yaml_content": yaml_content}
```

**Impact**: Users can now access and edit broken YAML files through the editor.

---

### 2. ✅ **Enhance YAML Error Messages** (HIGH Priority)

**Problem**: Generic "Failed to parse YAML" messages with no line/column information.

**Solution**: Extract detailed parse error from ruamel.yaml and include in exception.

```python
# backend/app/services/yaml_service.py

from ruamel.yaml.error import YAMLError as RuamelYAMLError, MarkedYAMLError

class YamlLoadError(YamlServiceError):
    """Raised when YAML file cannot be loaded."""
    
    def __init__(self, message: str, line: int | None = None, column: int | None = None, snippet: str | None = None):
        super().__init__(message)
        self.line = line
        self.column = column
        self.snippet = snippet
    
    def to_dict(self) -> dict[str, Any]:
        """Return structured error with location info."""
        return {
            "message": str(self),
            "line": self.line,
            "column": self.column,
            "snippet": self.snippet,
            "error_type": "YamlParseError"
        }

def load(self, filename: str | Path) -> dict[str, Any]:
    """Load YAML file with enhanced error reporting."""
    path = Path(filename)
    
    if not path.exists():
        raise YamlLoadError(f"File not found: {path}")
    
    if not path.is_file():
        raise YamlLoadError(f"Not a file: {path}")
    
    try:
        logger.debug(f"Loading YAML file: {path}")
        with path.open("r", encoding="utf-8") as f:
            data = self.yaml.load(f)
        
        # ... rest of processing ...
        
    except MarkedYAMLError as e:
        # Extract line, column, and context from ruamel.yaml
        line = e.problem_mark.line + 1 if e.problem_mark else None
        column = e.problem_mark.column + 1 if e.problem_mark else None
        
        # Get snippet of problematic line
        snippet = None
        if e.problem_mark:
            try:
                lines = path.read_text().splitlines()
                if 0 <= e.problem_mark.line < len(lines):
                    snippet = lines[e.problem_mark.line]
            except Exception:
                pass
        
        error_msg = f"YAML syntax error in {path.name}"
        if line:
            error_msg += f" at line {line}, column {column}"
        if e.problem:
            error_msg += f": {e.problem}"
        if snippet:
            error_msg += f"\n  {snippet}\n  {' ' * (column - 1) if column else ''}^"
        
        logger.error(error_msg)
        raise YamlLoadError(error_msg, line=line, column=column, snippet=snippet) from e
        
    except Exception as e:
        logger.error(f"Failed to load YAML file {path}: {e}")
        raise YamlLoadError(f"Failed to parse YAML file {path}: {e}") from e
```

**Example Error Output**:
```
YAML syntax error in arbodat-riia.yml at line 246, column 38: 
found duplicate key "constraints"
  foreign_keys: [{entity: project, ..., contraints: {...}, constraints: {...}}]
                                                           ^
```

---

### 3. ✅ **Add Validate-Only Endpoint** (MEDIUM Priority)

**Problem**: No way to validate YAML without attempting to load it.

**Solution**: Add dedicated validation endpoint that returns detailed diagnostics.

```python
# backend/app/api/v1/endpoints/projects.py

from pydantic import BaseModel

class YamlValidationResult(BaseModel):
    """Result of YAML validation check."""
    is_valid: bool
    syntax_valid: bool  # YAML parses correctly
    schema_valid: bool  # Has required keys (entities, metadata)
    errors: list[dict[str, Any]]
    warnings: list[str]
    line_count: int
    project_name: str | None = None

@router.post("/projects/{name}/validate-syntax", response_model=YamlValidationResult)
@handle_endpoint_errors
async def validate_project_syntax(name: str) -> YamlValidationResult:
    """
    Validate project YAML syntax without full loading.
    
    This performs lightweight validation:
    1. YAML syntax check (does it parse?)
    2. Basic structure check (has entities?)
    
    Does NOT perform full validation (FK checks, dependencies, etc).
    Use POST /projects/{name}/validate for complete validation.
    """
    project_service: ProjectService = get_project_service()
    yaml_service = project_service.yaml_service
    
    project_path = settings.PROJECTS_DIR / f"{name}.yml"
    if not project_path.exists():
        raise NotFoundError(f"Project file not found: {name}.yml")
    
    errors = []
    warnings = []
    syntax_valid = False
    schema_valid = False
    project_name = None
    
    # Count lines for context
    line_count = len(project_path.read_text().splitlines())
    
    # 1. Test YAML syntax
    try:
        with project_path.open("r") as f:
            data = yaml_service.yaml.load(f)
        syntax_valid = True
        
        # 2. Test basic structure
        if isinstance(data, dict):
            if "entities" in data:
                schema_valid = True
                if "metadata" in data and isinstance(data["metadata"], dict):
                    project_name = data["metadata"].get("name")
            else:
                errors.append({
                    "error_type": "MissingEntitiesKey",
                    "message": "Project file must have 'entities' key",
                    "severity": "error"
                })
        else:
            errors.append({
                "error_type": "InvalidRootType",
                "message": f"YAML root must be dictionary, got {type(data).__name__}",
                "severity": "error"
            })
            
    except YamlLoadError as e:
        errors.append({
            "error_type": "YamlSyntaxError",
            "message": str(e),
            "line": getattr(e, 'line', None),
            "column": getattr(e, 'column', None),
            "snippet": getattr(e, 'snippet', None),
            "severity": "error"
        })
    except Exception as e:
        errors.append({
            "error_type": "UnexpectedError",
            "message": str(e),
            "severity": "error"
        })
    
    return YamlValidationResult(
        is_valid=syntax_valid and schema_valid,
        syntax_valid=syntax_valid,
        schema_valid=schema_valid,
        errors=errors,
        warnings=warnings,
        line_count=line_count,
        project_name=project_name
    )
```

**Usage**: Frontend can call this before attempting full load to give users early feedback.

---

### 4. ✅ **Add Safe Load Mode** (MEDIUM Priority)

**Problem**: load_project() is all-or-nothing - no degraded mode for broken configs.

**Solution**: Add `safe_mode` parameter that returns partial data with error annotations.

```python
# backend/app/services/project_service.py

def load_project(
    self, 
    name: str, 
    *, 
    safe_mode: bool = False
) -> Project:
    """
    Load project by name.
    
    Args:
        name: Project name (without .yml extension)
        safe_mode: If True, returns partial data even if validation fails.
                  Sets is_valid=False and includes error details.
    
    Returns:
        Project object (may have is_valid=False in safe mode)
    
    Raises:
        ResourceNotFoundError: If project not found
        ConfigurationError: If project is invalid (unless safe_mode=True)
    """
    filename: Path = self.projects_dir / (f"{name.removesuffix('.yml')}.yml")
    if not filename.exists():
        raise ResourceNotFoundError(
            resource_type="project", 
            resource_id=name, 
            message=f"Project not found: {name}"
        )
    
    validation_errors = []
    
    try:
        data: dict[str, Any] = self.yaml_service.load(filename)
        
        if not self.specification.is_satisfied_by(data):
            error_msg = f"Invalid project file '{name}': missing required 'entities' key"
            if safe_mode:
                validation_errors.append(error_msg)
            else:
                raise ConfigurationError(message=error_msg)
        
        project: Project = ProjectMapper.to_api_config(data, name)
        
        assert project.metadata is not None
        
        project.metadata.file_path = str(filename)
        project.metadata.created_at = filename.stat().st_ctime
        project.metadata.modified_at = filename.stat().st_mtime
        project.metadata.entity_count = len(project.entities or {})
        project.metadata.is_valid = len(validation_errors) == 0
        
        if validation_errors:
            # Store errors in metadata for safe mode
            setattr(project.metadata, 'validation_errors', validation_errors)
        
        self.state.update_version(name)
        
        logger.info(
            f"Loaded project '{name}' with {len(project.entities)} entities"
            f"{' (safe mode - has errors)' if validation_errors else ''}"
        )
        return project
        
    except ConfigurationError:
        if not safe_mode:
            raise
        # In safe mode, return minimal project with error info
        return self._create_error_project(name, filename, str(e))
        
    except YamlLoadError as e:
        if not safe_mode:
            raise ConfigurationError(
                message=f"Invalid YAML in project '{name}': {e}"
            ) from e
        return self._create_error_project(name, filename, str(e))
        
    except Exception as e:
        logger.error(f"Failed to load project '{name}': {e}")
        if not safe_mode:
            raise ConfigurationError(
                message=f"Failed to load project '{name}': {e}"
            ) from e
        return self._create_error_project(name, filename, str(e))

def _create_error_project(
    self, 
    name: str, 
    filepath: Path, 
    error_msg: str
) -> Project:
    """Create minimal Project object for failed load in safe mode."""
    from backend.app.models.project import ProjectMetadata
    
    return Project(
        metadata=ProjectMetadata(
            name=name,
            description="Failed to load - see validation_errors",
            file_path=str(filepath),
            entity_count=0,
            is_valid=False,
            validation_errors=[error_msg]
        ),
        entities={},
        options={}
    )
```

---

### 5. ✅ **Improve Error Handler Status Codes** (LOW Priority - Already Working)

**Current**: `ConfigurationError` → `ValidationError` → HTTP 400 ✅  
**Status**: Actually working correctly! Initial assumption of 500 was wrong.

However, we should add more specific error codes for better frontend handling:

```python
# backend/app/exceptions.py

class YamlSyntaxError(ValidationError):
    """YAML file has syntax errors (malformed YAML)."""
    
    error_code = "YAML_SYNTAX_ERROR"
    
    def __init__(
        self,
        message: str,
        line: int | None = None,
        column: int | None = None,
        snippet: str | None = None,
        **kwargs: Any
    ):
        context = kwargs.pop("context", {})
        if line is not None:
            context["line"] = line
        if column is not None:
            context["column"] = column
        if snippet:
            context["snippet"] = snippet
        
        super().__init__(message, context=context, **kwargs)
```

---

## Implementation Priority

### Phase 1: Critical (Immediate)
1. **Fix Raw YAML Endpoint** - Remove `load_project()` call (5 min fix)
2. **Enhanced YAML Error Messages** - Add line/column info (30 min)

### Phase 2: High (Next Sprint)
3. **Validate-Only Endpoint** - Lightweight syntax check (1 hour)
4. **Safe Load Mode** - Degraded loading for broken configs (2 hours)

### Phase 3: Nice-to-Have (Future)
5. **Frontend Error Display** - Monaco editor error highlighting
6. **Auto-Fix Suggestions** - Detect common errors and suggest fixes
7. **Schema Validation UI** - Visual feedback on structure issues

---

## Testing Strategy

### Test Cases to Add

1. **Malformed YAML Access**
   - Verify raw YAML endpoint works with syntax errors
   - Verify Monaco editor can display broken YAML

2. **Error Message Quality**
   - Test line/column reporting accuracy
   - Verify snippet extraction and formatting

3. **Validation Endpoint**
   - Test with valid YAML
   - Test with syntax errors
   - Test with missing required keys

4. **Safe Mode Loading**
   - Verify partial data returned for broken configs
   - Verify error annotations in metadata

---

## Example User Flow (After Fix)

### Before (Current - BROKEN)
1. User uploads YAML with typo (`contraints`)
2. Tries to load project → HTTP 400 error
3. Tries to access raw YAML → **HTTP 400 (blocked!)**
4. User is stuck, can't edit config

### After (Proposed - ROBUST)
1. User uploads YAML with typo (`contraints`)
2. Tries to load project → HTTP 400 with **detailed error**:
   ```json
   {
     "error_type": "YamlSyntaxError",
     "message": "Duplicate key 'constraints' at line 246, column 38",
     "line": 246,
     "column": 38,
     "snippet": "foreign_keys: [{..., contraints: {...}, constraints: {...}}]",
     "tips": ["Check for duplicate keys in YAML", "Review YAML syntax guide"]
   }
   ```
3. Clicks "Edit YAML" → **Raw YAML loads successfully**
4. Monaco editor shows error at line 246 with red squiggle
5. User fixes typo, saves
6. Validation passes ✅

---

## Backward Compatibility

All changes are backward compatible:
- Existing endpoints with full validation still work
- New `safe_mode` parameter defaults to `False`
- Error structure enhanced but old clients ignore extra fields
- Raw YAML endpoint becomes more permissive (good!)

---

## Conclusion

The key insight is **separation of concerns**:
- **YAML Access** ≠ **YAML Validation** ≠ **Business Logic Validation**

Users must be able to:
1. ✅ Access raw YAML (even if malformed)
2. ✅ Get precise error locations
3. ✅ Validate syntax before full load
4. ✅ Work with partially broken configs

This transforms a **blocking error** into a **fixable warning**.
