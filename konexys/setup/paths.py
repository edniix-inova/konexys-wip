import os
from pathlib import Path

# Repo-root discovery: konexys/setup/paths.py -> <module> -> konexys -> repo
REPO_ROOT = Path(__file__).resolve().parents[2]

# Default locations (refactor phase)
DEFAULT_DATA_DIR = REPO_ROOT / "data"
DEFAULT_SUMO_PATH = "/usr/share/sumo"
DEFAULT_SUMO_BIN_PATH = "/usr/share/sumo/bin"
DEFAULT_SUMO_TOOLS_PATH = "/usr/share/sumo/tools"

def _env_path(var_name: str, default: Path | None = None) -> Path:
    """
    Resolve an environment variable to a Path.

    If unset, returns `default` (if provided) or raises a RuntimeError.
    """
    value = os.environ.get(var_name)
    if value:
        return Path(value).expanduser().resolve()
    if default is not None:
        return default.resolve()
    raise RuntimeError(f"Environment variable '{var_name}' is not set and no default was provided.")

# TODO(config): Remove defaults and require env vars once data/tool locations are finalized.
PATH_DATA_DIR = str(DEFAULT_DATA_DIR)
PATH_SUMO = DEFAULT_SUMO_PATH
PATH_SUMO_BIN = DEFAULT_SUMO_BIN_PATH
PATH_SUMO_TOOLS = DEFAULT_SUMO_TOOLS_PATH

# Specific datasets/tools
PATH_ELEVATION_DATA = str(_env_path("ELEVATION_DATA", DEFAULT_DATA_DIR / "elevation"))
# PATH_SOME_TOOL = str(_env_path("SOME_TOOL_PATH", REPO_ROOT / "tools" / "some_tool"))

# Legacy implementation
# PATH_SUMO = str(os.environ.get('SUMO_HOME'))
# PATH_SUMO_BIN = PATH_SUMO + os.sep + 'bin'
# PATH_SUMO_TOOLS = PATH_SUMO + os.sep + 'tools'
# PATH_ELEVATION_DATA = str(os.environ.get('ELEVATION_DATA'))
# PATH_OSM_IMPORTER = str(os.environ.get('OSM_IMPORTER_PATH'))
# PATH_JAVA = str(os.environ.get('JAVA_HOME'))
# PATH_JAVA_BIN = PATH_JAVA + os.sep + 'bin'
# PATH_NEO4J = os.environ.get('NEO4J_PATH')