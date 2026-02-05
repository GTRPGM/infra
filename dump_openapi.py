import sys
import json
import os
import importlib
from unittest.mock import MagicMock

# Usage: python dump_openapi.py <sys_path> <module_name> <app_attribute_name>

if len(sys.argv) < 4:
    print(
        "Usage: python dump_openapi.py <sys_path> <module_name> <app_attribute_name>",
        file=sys.stderr,
    )
    sys.exit(1)

target_path = sys.argv[1]
module_name = sys.argv[2]
app_attr = sys.argv[3]

# Add target path to sys.path
sys.path.insert(0, target_path)

# Set dummy environment variables
os.environ.setdefault("APP_ENV", "local")
os.environ.setdefault("APP_PORT", "8000")
os.environ.setdefault("WEB_PORT", "3000")
os.environ.setdefault("REMOTE_HOST", "localhost")
os.environ.setdefault("DB_USER", "postgres")
os.environ.setdefault("DB_PASSWORD", "password")
os.environ.setdefault("DB_DB", "db")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")
os.environ.setdefault("OPENAI_API_KEY", "dummy")
os.environ.setdefault("GCP_PROJECT_ID", "dummy")
os.environ.setdefault("GCP_LOCATION", "us-central1")
os.environ.setdefault("GEMINI_MODEL_NAME", "gemini-pro")

# Specific Mocks for Rule Engine to avoid DB/Redis connections at module level
# rule-engine/src/main.py imports 'configs.database' and 'configs.redis_conn'
# We must mock these BEFORE import_module is called.

mock_db = MagicMock()
mock_db.check_db_connection = MagicMock()
# Mock connection_pool if accessed directly
mock_db.connection_pool = MagicMock()

mock_redis = MagicMock()
mock_redis.check_redis_connection = MagicMock()

# Inject mocks into sys.modules
# We mock both 'configs.database' and 'src.configs.database' to cover different import styles
sys.modules["configs.database"] = mock_db
sys.modules["src.configs.database"] = mock_db
sys.modules["configs.redis_conn"] = mock_redis
sys.modules["src.configs.redis_conn"] = mock_redis

try:
    # Attempt to import the module
    module = importlib.import_module(module_name)
    app = getattr(module, app_attr)

    # Generate OpenAPI schema
    openapi_schema = app.openapi()

    # Print to stdout
    print(json.dumps(openapi_schema, indent=2))

except ImportError as e:
    print(f"ImportError: {e}", file=sys.stderr)
    sys.exit(1)
except AttributeError as e:
    print(f"AttributeError: {e}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"RuntimeError: {e}", file=sys.stderr)
    sys.exit(1)
