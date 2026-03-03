import json
import logging
import shutil
import importlib.util
from pathlib import Path
from typing import List, Union, Dict, Any, Optional

logger = logging.getLogger(__name__)

from api.openai_client import OpenAIClient
from api.openrouter_client import OpenRouterClient
from api.bedrock_client import BedrockClient
from api.google_embedder_client import GoogleEmbedderClient
from api.azureai_client import AzureAIClient
from api.dashscope_client import DashscopeClient
from api.mlx_client import MLXClient
from adalflow import GoogleGenAIClient, OllamaClient
from api.runtime_settings import load_runtime_settings, update_runtime_settings

# Runtime settings-backed globals (kept for compatibility with existing imports)
OPENAI_API_KEY = ""
GOOGLE_API_KEY = ""
OPENROUTER_API_KEY = ""
AWS_ACCESS_KEY_ID = ""
AWS_SECRET_ACCESS_KEY = ""
AWS_SESSION_TOKEN = ""
AWS_REGION = "us-east-1"
AWS_ROLE_ARN = ""
WIKI_AUTH_MODE = False
WIKI_AUTH_CODE = ""
EMBEDDER_TYPE = "openai"

# Configuration directory is fixed to repository config folder.
CONFIG_DIR = None

# Client class mapping
CLIENT_CLASSES = {
    "GoogleGenAIClient": GoogleGenAIClient,
    "GoogleEmbedderClient": GoogleEmbedderClient,
    "OpenAIClient": OpenAIClient,
    "OpenRouterClient": OpenRouterClient,
    "OllamaClient": OllamaClient,
    "BedrockClient": BedrockClient,
    "AzureAIClient": AzureAIClient,
    "DashscopeClient": DashscopeClient,
    "MLXClient": MLXClient
}


def _get_runtime_settings() -> Dict[str, Any]:
    return load_runtime_settings()


def _sync_compatibility_globals() -> None:
    global OPENAI_API_KEY, GOOGLE_API_KEY, OPENROUTER_API_KEY
    global AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN, AWS_REGION, AWS_ROLE_ARN
    global WIKI_AUTH_MODE, WIKI_AUTH_CODE, EMBEDDER_TYPE

    settings = _get_runtime_settings()
    provider_keys = settings.get("provider_keys", {})

    openai = provider_keys.get("openai", {})
    google = provider_keys.get("google", {})
    openrouter = provider_keys.get("openrouter", {})
    bedrock = provider_keys.get("bedrock", {})
    auth = settings.get("auth", {})
    embedder = settings.get("embedder", {})

    OPENAI_API_KEY = (openai.get("apiKey") or "").strip()
    GOOGLE_API_KEY = (google.get("apiKey") or "").strip()
    OPENROUTER_API_KEY = (openrouter.get("apiKey") or "").strip()

    AWS_ACCESS_KEY_ID = (bedrock.get("accessKeyId") or "").strip()
    AWS_SECRET_ACCESS_KEY = (bedrock.get("secretAccessKey") or "").strip()
    AWS_SESSION_TOKEN = (bedrock.get("sessionToken") or "").strip()
    AWS_REGION = (bedrock.get("region") or "us-east-1").strip()
    AWS_ROLE_ARN = (bedrock.get("roleArn") or "").strip()

    WIKI_AUTH_MODE = bool(auth.get("enabled", False))
    WIKI_AUTH_CODE = (auth.get("code") or "").strip()

    EMBEDDER_TYPE = (embedder.get("type") or "openai").strip().lower()


def get_provider_credentials(provider_id: str) -> Dict[str, Any]:
    settings = _get_runtime_settings()
    return settings.get("provider_keys", {}).get(provider_id, {})


def has_provider_credentials(provider_id: str) -> bool:
    provider_id = provider_id.lower()
    creds = get_provider_credentials(provider_id)

    if provider_id in {"openai", "google", "openrouter", "dashscope"}:
        return bool((creds.get("apiKey") or "").strip())

    if provider_id == "azure":
        return bool(
            (creds.get("apiKey") or "").strip()
            and (creds.get("endpoint") or "").strip()
            and (creds.get("apiVersion") or "").strip()
        )

    if provider_id == "bedrock":
        has_static = bool(
            (creds.get("accessKeyId") or "").strip()
            and (creds.get("secretAccessKey") or "").strip()
        )
        has_role_or_profile = bool((creds.get("roleArn") or "").strip() or (creds.get("profile") or "").strip())
        return has_static or has_role_or_profile

    return True


def is_model_provider_available(provider_id: str) -> bool:
    provider_id = (provider_id or "").strip().lower()

    if provider_id in {"openai", "google", "openrouter", "azure", "dashscope", "bedrock"}:
        return has_provider_credentials(provider_id)

    if provider_id == "ollama":
        return shutil.which("ollama") is not None

    if provider_id == "mlx":
        has_mlx_server_cli = shutil.which("mlx_lm.server") is not None
        has_mlx_package = importlib.util.find_spec("mlx_lm") is not None
        return has_mlx_server_cli or has_mlx_package

    # Unknown/custom providers remain available to avoid breaking custom setups.
    return True


def resolve_model_provider(preferred: Optional[str] = None) -> str:
    configured = (preferred or configs.get("default_provider") or "").strip().lower()

    if configured and is_model_provider_available(configured):
        return configured

    # Favor local providers first so a fresh install works with no API keys.
    for fallback in ["ollama", "mlx", "openai", "google", "openrouter", "azure", "dashscope", "bedrock"]:
        if is_model_provider_available(fallback) and fallback in configs.get("providers", {}):
            return fallback

    # Last resort: first configured provider in generator config, if any.
    for provider_id in configs.get("providers", {}).keys():
        if is_model_provider_available(provider_id):
            return provider_id

    return configured or (next(iter(configs.get("providers", {}).keys()), ""))


def is_embedder_available(embedder_type: str) -> bool:
    embedder_type = (embedder_type or "").strip().lower()

    if embedder_type in {"openai", "google", "bedrock"}:
        return has_provider_credentials(embedder_type)

    if embedder_type == "ollama":
        return shutil.which("ollama") is not None

    if embedder_type == "mlx":
        has_mlx_server_cli = shutil.which("mlx_lm.server") is not None
        has_mlx_package = importlib.util.find_spec("mlx_lm") is not None
        return has_mlx_server_cli or has_mlx_package

    return False


def resolve_embedder_type(preferred: Optional[str] = None) -> str:
    configured = (preferred or _get_runtime_settings().get("embedder", {}).get("type") or "openai").strip().lower()

    supported_types = [
        "openai",
        "google",
        "bedrock",
        "ollama",
        "mlx",
    ]

    if configured in supported_types and is_embedder_available(configured):
        return configured

    for fallback in ["ollama", "mlx", "openai", "google", "bedrock"]:
        if is_embedder_available(fallback):
            return fallback

    # As a last resort, return the configured value to preserve behavior and surface clear runtime errors.
    return configured or "openai"


def get_auth_config() -> Dict[str, Any]:
    settings = _get_runtime_settings()
    auth = settings.get("auth", {})
    return {
        "enabled": bool(auth.get("enabled", False)),
        "code": (auth.get("code") or "").strip(),
    }


def get_embedder_preference() -> str:
    return resolve_embedder_type()


def update_runtime_preferences(payload: Dict[str, Any]) -> Dict[str, Any]:
    updated = update_runtime_settings(payload)
    _sync_compatibility_globals()
    return updated


_sync_compatibility_globals()

# Load JSON configuration file
def load_json_config(filename):
    try:
        # If environment variable is set, use the directory specified by it
        if CONFIG_DIR:
            config_path = Path(CONFIG_DIR) / filename
        else:
            # Otherwise use default directory
            config_path = Path(__file__).parent / "config" / filename

        logger.info(f"Loading configuration from {config_path}")

        if not config_path.exists():
            logger.warning(f"Configuration file {config_path} does not exist")
            return {}

        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            return config
    except Exception as e:
        logger.error(f"Error loading configuration file {filename}: {str(e)}")
        return {}

# Load generator model configuration
def load_generator_config():
    generator_config = load_json_config("generator.json")

    # Add client classes to each provider
    if "providers" in generator_config:
        for provider_id, provider_config in generator_config["providers"].items():
            # Try to set client class from client_class
            if provider_config.get("client_class") in CLIENT_CLASSES:
                provider_config["model_client"] = CLIENT_CLASSES[provider_config["client_class"]]
            # Fall back to default mapping based on provider_id
            elif provider_id in ["google", "openai", "openrouter", "ollama", "bedrock", "azure", "dashscope", "mlx"]:
                default_map = {
                    "google": GoogleGenAIClient,
                    "openai": OpenAIClient,
                    "openrouter": OpenRouterClient,
                    "ollama": OllamaClient,
                    "bedrock": BedrockClient,
                    "azure": AzureAIClient,
                    "dashscope": DashscopeClient,
                    "mlx": MLXClient
                }
                provider_config["model_client"] = default_map[provider_id]
            else:
                logger.warning(f"Unknown provider or client class: {provider_id}")

    return generator_config

# Load embedder configuration
def load_embedder_config():
    embedder_config = load_json_config("embedder.json")

    # Process client classes
    for key in ["embedder", "embedder_ollama", "embedder_google", "embedder_bedrock", "embedder_mlx"]:
        if key in embedder_config and "client_class" in embedder_config[key]:
            class_name = embedder_config[key]["client_class"]
            if class_name in CLIENT_CLASSES:
                embedder_config[key]["model_client"] = CLIENT_CLASSES[class_name]

    return embedder_config

def get_embedder_config(embedder_type: Optional[str] = None):
    """
    Get the current embedder configuration based on DEEPWIKI_EMBEDDER_TYPE.

    Returns:
        dict: The embedder configuration with model_client resolved
    """
    embedder_type = resolve_embedder_type(embedder_type)
    if embedder_type == 'bedrock' and 'embedder_bedrock' in configs:
        return configs.get("embedder_bedrock", {})
    elif embedder_type == 'google' and 'embedder_google' in configs:
        return configs.get("embedder_google", {})
    elif embedder_type == 'ollama' and 'embedder_ollama' in configs:
        return configs.get("embedder_ollama", {})
    elif embedder_type == 'mlx' and 'embedder_mlx' in configs:
        return configs.get("embedder_mlx", {})
    else:
        return configs.get("embedder", {})

def is_ollama_embedder():
    """
    Check if the current embedder configuration uses OllamaClient.

    Returns:
        bool: True if using OllamaClient, False otherwise
    """
    embedder_config = get_embedder_config()
    if not embedder_config:
        return False

    # Check if model_client is OllamaClient
    model_client = embedder_config.get("model_client")
    if model_client:
        return model_client.__name__ == "OllamaClient"

    # Fallback: check client_class string
    client_class = embedder_config.get("client_class", "")
    return client_class == "OllamaClient"

def is_google_embedder():
    """
    Check if the current embedder configuration uses GoogleEmbedderClient.

    Returns:
        bool: True if using GoogleEmbedderClient, False otherwise
    """
    embedder_config = get_embedder_config()
    if not embedder_config:
        return False

    # Check if model_client is GoogleEmbedderClient
    model_client = embedder_config.get("model_client")
    if model_client:
        return model_client.__name__ == "GoogleEmbedderClient"

    # Fallback: check client_class string
    client_class = embedder_config.get("client_class", "")
    return client_class == "GoogleEmbedderClient"

def is_bedrock_embedder():
    """
    Check if the current embedder configuration uses BedrockClient.

    Returns:
        bool: True if using BedrockClient, False otherwise
    """
    embedder_config = get_embedder_config()
    if not embedder_config:
        return False

    model_client = embedder_config.get("model_client")
    if model_client:
        return model_client.__name__ == "BedrockClient"

    client_class = embedder_config.get("client_class", "")
    return client_class == "BedrockClient"

def is_mlx_embedder():
    """
    Check if the current embedder configuration uses MLXClient.

    Returns:
        bool: True if using MLXClient, False otherwise
    """
    embedder_config = get_embedder_config()
    if not embedder_config:
        return False

    model_client = embedder_config.get("model_client")
    if model_client:
        return model_client.__name__ == "MLXClient"

    client_class = embedder_config.get("client_class", "")
    return client_class == "MLXClient"

def get_embedder_type(embedder_type: Optional[str] = None):
    """
    Get the current embedder type based on configuration.
    
    Returns:
        str: 'bedrock', 'ollama', 'google', 'mlx', or 'openai' (default)
    """
    return resolve_embedder_type(embedder_type)

# Load repository and file filters configuration
def load_repo_config():
    return load_json_config("repo.json")

# Load language configuration
def load_lang_config():
    default_config = {
        "supported_languages": {
            "en": "English",
            "ja": "Japanese (日本語)",
            "zh": "Mandarin Chinese (中文)",
            "zh-tw": "Traditional Chinese (繁體中文)",
            "es": "Spanish (Español)",
            "kr": "Korean (한국어)",
            "vi": "Vietnamese (Tiếng Việt)",
            "pt-br": "Brazilian Portuguese (Português Brasileiro)",
            "fr": "Français (French)",
            "ru": "Русский (Russian)"
        },
        "default": "en"
    }

    loaded_config = load_json_config("lang.json") # Let load_json_config handle path and loading

    if not loaded_config:
        return default_config

    if "supported_languages" not in loaded_config or "default" not in loaded_config:
        logger.warning("Language configuration file 'lang.json' is malformed. Using default language configuration.")
        return default_config

    return loaded_config

# Default excluded directories and files
DEFAULT_EXCLUDED_DIRS: List[str] = [
    # Virtual environments and package managers
    "./.venv/", "./venv/", "./env/", "./virtualenv/",
    "./node_modules/", "./bower_components/", "./jspm_packages/",
    # Version control
    "./.git/", "./.svn/", "./.hg/", "./.bzr/",
    # Cache and compiled files
    "./__pycache__/", "./.pytest_cache/", "./.mypy_cache/", "./.ruff_cache/", "./.coverage/",
    # Build and distribution
    "./dist/", "./build/", "./out/", "./target/", "./bin/", "./obj/",
    # Documentation
    "./docs/", "./_docs/", "./site-docs/", "./_site/",
    # IDE specific
    "./.idea/", "./.vscode/", "./.vs/", "./.eclipse/", "./.settings/",
    # Logs and temporary files
    "./logs/", "./log/", "./tmp/", "./temp/",
]

DEFAULT_EXCLUDED_FILES: List[str] = [
    "yarn.lock", "pnpm-lock.yaml", "npm-shrinkwrap.json", "poetry.lock",
    "Pipfile.lock", "requirements.txt.lock", "Cargo.lock", "composer.lock",
    ".lock", ".DS_Store", "Thumbs.db", "desktop.ini", "*.lnk", ".env",
    ".env.*", "*.env", "*.cfg", "*.ini", ".flaskenv", ".gitignore",
    ".gitattributes", ".gitmodules", ".github", ".gitlab-ci.yml",
    ".prettierrc", ".eslintrc", ".eslintignore", ".stylelintrc",
    ".editorconfig", ".jshintrc", ".pylintrc", ".flake8", "mypy.ini",
    "pyproject.toml", "tsconfig.json", "webpack.config.js", "babel.config.js",
    "rollup.config.js", "jest.config.js", "karma.conf.js", "vite.config.js",
    "next.config.js", "*.min.js", "*.min.css", "*.bundle.js", "*.bundle.css",
    "*.map", "*.gz", "*.zip", "*.tar", "*.tgz", "*.rar", "*.7z", "*.iso",
    "*.dmg", "*.img", "*.msix", "*.appx", "*.appxbundle", "*.xap", "*.ipa",
    "*.deb", "*.rpm", "*.msi", "*.exe", "*.dll", "*.so", "*.dylib", "*.o",
    "*.obj", "*.jar", "*.war", "*.ear", "*.jsm", "*.class", "*.pyc", "*.pyd",
    "*.pyo", "__pycache__", "*.a", "*.lib", "*.lo", "*.la", "*.slo", "*.dSYM",
    "*.egg", "*.egg-info", "*.dist-info", "*.eggs", "node_modules",
    "bower_components", "jspm_packages", "lib-cov", "coverage", "htmlcov",
    ".nyc_output", ".tox", "dist", "build", "bld", "out", "bin", "target",
    "packages/*/dist", "packages/*/build", ".output"
]

# Initialize empty configuration
configs = {}

# Load all configuration files
generator_config = load_generator_config()
embedder_config = load_embedder_config()
repo_config = load_repo_config()
lang_config = load_lang_config()

# Update configuration
if generator_config:
    configs["default_provider"] = generator_config.get("default_provider", "google")
    configs["providers"] = generator_config.get("providers", {})

# Update embedder configuration
if embedder_config:
    for key in ["embedder", "embedder_ollama", "embedder_google", "embedder_bedrock", "embedder_mlx", "retriever", "text_splitter"]:
        if key in embedder_config:
            configs[key] = embedder_config[key]

# Update repository configuration
if repo_config:
    for key in ["file_filters", "repository"]:
        if key in repo_config:
            configs[key] = repo_config[key]

# Update language configuration
if lang_config:
    configs["lang_config"] = lang_config


def get_model_config(provider="google", model=None):
    """
    Get configuration for the specified provider and model

    Parameters:
        provider (str): Model provider ('google', 'openai', 'openrouter', 'ollama', 'bedrock')
        model (str): Model name, or None to use default model

    Returns:
        dict: Configuration containing model_client, model and other parameters
    """
    # Get provider configuration
    if "providers" not in configs:
        raise ValueError("Provider configuration not loaded")

    provider_config = configs["providers"].get(provider)
    if not provider_config:
        raise ValueError(f"Configuration for provider '{provider}' not found")

    model_client = provider_config.get("model_client")
    if not model_client:
        raise ValueError(f"Model client not specified for provider '{provider}'")

    # If model not provided, use default model for the provider
    if not model:
        model = provider_config.get("default_model")
        if not model:
            raise ValueError(f"No default model specified for provider '{provider}'")

    # Get model parameters (if present)
    model_params = {}
    if model in provider_config.get("models", {}):
        model_params = provider_config["models"][model]
    else:
        default_model = provider_config.get("default_model")
        model_params = provider_config["models"][default_model]

    # Prepare base configuration
    result = {
        "model_client": model_client,
    }

    # Provider-specific adjustments
    if provider == "ollama":
        # Ollama uses a slightly different parameter structure
        if "options" in model_params:
            result["model_kwargs"] = {"model": model, **model_params["options"]}
        else:
            result["model_kwargs"] = {"model": model}
    elif provider == "mlx":
        # MLX uses a similar structure to Ollama
        if "options" in model_params:
            result["model_kwargs"] = {"model": model, **model_params["options"]}
        else:
            result["model_kwargs"] = {"model": model, **model_params}
    else:
        # Standard structure for other providers
        result["model_kwargs"] = {"model": model, **model_params}

    return result
