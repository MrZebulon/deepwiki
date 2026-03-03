import json
import logging
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

SETTINGS_FILE_PATH = Path(__file__).parent / "config" / "runtime_settings.json"

DEFAULT_SETTINGS: Dict[str, Any] = {
    "provider_keys": {
        "openai": {"apiKey": "", "baseUrl": "https://api.openai.com/v1"},
        "google": {"apiKey": ""},
        "openrouter": {"apiKey": ""},
        "azure": {
            "apiKey": "",
            "endpoint": "",
            "apiVersion": "",
        },
        "dashscope": {
            "apiKey": "",
            "workspaceId": "",
            "baseUrl": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        },
        "bedrock": {
            "accessKeyId": "",
            "secretAccessKey": "",
            "sessionToken": "",
            "region": "us-east-1",
            "roleArn": "",
            "profile": "",
        },
    },
    "embedder": {
        "type": "openai",
    },
    "auth": {
        "enabled": False,
        "code": "",
    },
    "local": {
        "ollamaHost": "http://localhost:11434",
        "mlxHost": "http://localhost:8080",
    },
}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _ensure_file_exists() -> None:
    if SETTINGS_FILE_PATH.exists():
        return

    SETTINGS_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE_PATH.write_text(json.dumps(DEFAULT_SETTINGS, indent=2), encoding="utf-8")


def load_runtime_settings() -> Dict[str, Any]:
    _ensure_file_exists()
    try:
        loaded = json.loads(SETTINGS_FILE_PATH.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            logger.warning("runtime_settings.json is malformed, resetting to defaults")
            return deepcopy(DEFAULT_SETTINGS)
        return _deep_merge(DEFAULT_SETTINGS, loaded)
    except Exception as e:
        logger.error(f"Failed to load runtime settings: {e}")
        return deepcopy(DEFAULT_SETTINGS)


def save_runtime_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    merged = _deep_merge(DEFAULT_SETTINGS, settings if isinstance(settings, dict) else {})
    SETTINGS_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE_PATH.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    return merged


def update_runtime_settings(partial: Dict[str, Any]) -> Dict[str, Any]:
    current = load_runtime_settings()
    updated = _deep_merge(current, partial if isinstance(partial, dict) else {})
    return save_runtime_settings(updated)
