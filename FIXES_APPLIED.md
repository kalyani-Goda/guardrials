# System Fixes Applied

## Summary
Fixed compatibility issues to get the medi-triage system running in the `grenv` conda environment.

## Issues Fixed

### 1. **Logging Configuration - Missing Attribute**
- **Issue**: `AttributeError: 'Settings' object has no attribute 'log_level'`
- **Cause**: Logging config was using lowercase `settings.log_level` but Settings class had `LOG_LEVEL` (uppercase)
- **Fix**: Updated `config/logging_config.py` line 46 to use `settings.LOG_LEVEL.upper()` instead of `settings.log_level.upper()`

### 2. **SQLAlchemy Reserved Attribute**
- **Issue**: `sqlalchemy.exc.InvalidRequestError: Attribute name 'metadata' is reserved when using the Declarative API`
- **Cause**: In SQLAlchemy 2.0+, 'metadata' is a reserved attribute
- **Fix**: Renamed in `app/local_database.py`:
  - `TriageSession.metadata` → `TriageSession.session_metadata`
  - `Appointment.metadata` → `Appointment.appointment_metadata`

### 3. **NumPy Compatibility with PyTorch**
- **Issue**: `Failed to initialize NumPy: _ARRAY_API not found` when importing torch/presidio
- **Cause**: NumPy 2.x compatibility issues with PyTorch
- **Fix**: 
  - Added `numpy<2` constraint to `requirements.txt`
  - Downgraded numpy in grenv environment: `pip install 'numpy<2'`

### 4. **Missing Redis Package**
- **Issue**: `ModuleNotFoundError: No module named 'redis'`
- **Cause**: Redis client library not installed in grenv
- **Fix**: Installed redis: `pip install redis`

### 5. **Missing Settings Attributes**
- **Issue**: Multiple `'Settings' object has no attribute` errors
- **Cause**: Settings class missing attributes used in app layers
- **Fix**: Added missing settings to `config/settings.py`:
  ```python
  REDIS_TIMEOUT: int = 5
  REDIS_MAX_RETRIES: int = 3
  EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
  PII_ENTITIES_TO_DETECT: list = ["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD", "SSN"]
  SECRET_KEY: str = "your-secret-key-change-in-production"
  EHR_API_BASE_URL: str = "http://localhost:8000"
  EHR_API_KEY: str = ""
  EHR_API_TIMEOUT: int = 30
  ```

### 6. **Settings Case Sensitivity Issues**
- **Issue**: Code using lowercase settings (e.g., `settings.redis_timeout`) but class has uppercase
- **Cause**: Inconsistent naming conventions
- **Fix**: Updated references in:
  - `app/input_layer.py`: `settings.redis_timeout` → `settings.REDIS_TIMEOUT`
  - `app/input_layer.py`: `settings.presidio_anonymizer_threshold` → `settings.PRESIDIO_ANONYMIZER_THRESHOLD`
  - `app/input_layer.py`: `settings.pii_entities_to_detect` → `settings.PII_ENTITIES_TO_DETECT`
  - `app/reasoning_layer.py`: `settings.embedding_model` → `settings.EMBEDDING_MODEL`
  - `app/reasoning_layer.py`: `settings.vector_store_path` → `settings.VECTOR_STORE_PATH`
  - `app/reasoning_layer.py`: `settings.ragas_faithfulness_threshold` → `settings.RAGAS_FAITHFULNESS_THRESHOLD`
  - `app/tool_layer.py`: `settings.secret_key` → `settings.SECRET_KEY`
  - `app/tool_layer.py`: `settings.ehr_api_base_url` → `settings.EHR_API_BASE_URL`
  - `app/tool_layer.py`: `settings.ehr_api_key` → `settings.EHR_API_KEY`
  - `app/tool_layer.py`: `settings.ehr_api_timeout` → `settings.EHR_API_TIMEOUT`

### 7. **Duplicate get_settings() Function**
- **Issue**: `get_settings()` was defined twice in `config/settings.py`
- **Fix**: Removed duplicate definition and kept single clean implementation

### 8. **Missing Settings Helper Methods**
- **Issue**: Code calling `settings.get_redis_url()` and `settings.get_database_url()`
- **Fix**: Added methods to Settings class:
  ```python
  def get_redis_url(self) -> str:
      password = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
      return f"redis://{password}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

  def get_database_url(self) -> str:
      return self.DATABASE_URL
  ```

## Files Modified

1. **config/logging_config.py** - Fixed log level attribute case
2. **config/settings.py** - Added missing attributes, methods, and fixed duplicates
3. **app/local_database.py** - Renamed reserved 'metadata' attributes
4. **app/input_layer.py** - Fixed settings case sensitivity
5. **app/reasoning_layer.py** - Fixed settings case sensitivity
6. **app/tool_layer.py** - Fixed settings case sensitivity
7. **requirements.txt** - Added numpy<2 constraint

## Installation Steps (for grenv environment)

```bash
# Activate conda environment
conda activate grenv

# Install all requirements (includes fixes)
pip install -r requirements.txt

# Verify installation
python -c "from app.local_database import get_local_database; print('✓ Database module works')"
python -c "from app.google_llm_integration import get_google_llm; print('✓ Google LLM wrapper works')"
```

## Verification

All 5 layers now import successfully:
```bash
conda activate grenv
python -c "
from app.input_layer import get_anonymizer
from app.dialog_layer import get_dialog_orchestrator  
from app.reasoning_layer import get_reasoning_engine
from app.tool_layer import get_scheduling_tool
from app.workflow_layer import get_workflow_orchestrator
print('✓ All 5 layers imported successfully')
"
```

## Status

✅ **System Ready**: All core issues resolved, system is operational in grenv environment.

---

**Last Updated**: 2026-02-18
**Tested With**: Python 3.10.18, grenv conda environment
