"""
MLX ModelClient integration.

MLX LM provides an OpenAI-compatible server via `mlx_lm.server`.
This client communicates with that local server for both LLM generation
and embeddings, following the same pattern as the Ollama provider.
"""

import os
import json
import logging
import requests
from typing import (
    Dict,
    Sequence,
    Optional,
    List,
    Any,
    Union,
    AsyncGenerator,
)

import backoff
import aiohttp

from adalflow.core.model_client import ModelClient
from adalflow.core.types import (
    ModelType,
    EmbedderOutput,
    CompletionUsage,
    GeneratorOutput,
)

from api.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

class MLXModelNotFoundError(Exception):
    """Custom exception for when an MLX model is not available."""
    pass


def _base_url() -> str:
    """Return the base URL for the MLX server, stripping trailing slashes."""
    try:
        from api.runtime_settings import load_runtime_settings
        host = load_runtime_settings().get("local", {}).get("mlxHost", "http://localhost:8080")
    except Exception:
        host = "http://localhost:8080"
    return host.rstrip("/")


def check_mlx_server_running(mlx_host: Optional[str] = None) -> bool:
    """
    Check if the MLX LM server is running and reachable.

    Args:
        mlx_host: MLX server URL, defaults to MLX_HOST env var.

    Returns:
        bool: True if server is reachable, False otherwise.
    """
    if mlx_host is None:
        mlx_host = _base_url()

    try:
        response = requests.get(f"{mlx_host}/v1/models", timeout=5)
        if response.status_code == 200:
            logger.info("MLX LM server is reachable")
            return True
        else:
            logger.warning(f"MLX LM server returned status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        logger.warning(f"Could not connect to MLX LM server at {mlx_host}: {e}")
        return False


def check_mlx_model_exists(model_name: str, mlx_host: Optional[str] = None) -> bool:
    """
    Check if a specific model is loaded on the MLX LM server.

    Args:
        model_name: Name of the model to check.
        mlx_host: MLX server URL.

    Returns:
        bool: True if model is available, False otherwise.
    """
    if mlx_host is None:
        mlx_host = _base_url()

    try:
        response = requests.get(f"{mlx_host}/v1/models", timeout=5)
        if response.status_code == 200:
            models_data = response.json()
            available_models = [
                m.get("id", "") for m in models_data.get("data", [])
            ]
            is_available = model_name in available_models
            if is_available:
                logger.info(f"MLX model '{model_name}' is available")
            else:
                logger.warning(
                    f"MLX model '{model_name}' is not available. "
                    f"Available models: {available_models}"
                )
            return is_available
        else:
            logger.warning(f"Could not check MLX models, status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        logger.warning(f"Could not connect to MLX LM server to check models: {e}")
        return False
    except Exception as e:
        logger.warning(f"Error checking MLX model availability: {e}")
        return False


class MLXClient(ModelClient):
    """
    A ModelClient implementation for MLX LM server.

    The MLX LM server exposes an OpenAI-compatible API, so this client
    sends requests to the /v1/chat/completions and /v1/embeddings endpoints.
    """

    def __init__(self, host: Optional[str] = None):
        """
        Initialize the MLX client.

        Args:
            host: The MLX LM server host URL. Defaults to MLX_HOST env var.
        """
        super().__init__()
        self.host = (host or _base_url()).rstrip("/")
        self.sync_client = requests.Session()
        self.async_client = None  # Created lazily

    def _get_async_session(self) -> aiohttp.ClientSession:
        """Get or create the async HTTP session."""
        if self.async_client is None or self.async_client.closed:
            self.async_client = aiohttp.ClientSession()
        return self.async_client

    # ------------------------------------------------------------------ #
    #  ModelClient interface
    # ------------------------------------------------------------------ #

    def convert_inputs_to_api_kwargs(
        self,
        input: Any,
        model_kwargs: Dict = {},
        model_type: ModelType = ModelType.UNDEFINED,
    ) -> Dict:
        """
        Convert adalflow inputs to API keyword arguments.

        Args:
            input: The input text or messages.
            model_kwargs: Additional model parameters.
            model_type: The type of model (LLM or EMBEDDER).

        Returns:
            Dict of API keyword arguments.
        """
        api_kwargs = {**model_kwargs}

        if model_type == ModelType.LLM:
            # Chat completion
            if isinstance(input, str):
                api_kwargs["messages"] = [{"role": "user", "content": input}]
            elif isinstance(input, list):
                api_kwargs["messages"] = input
            else:
                api_kwargs["messages"] = [{"role": "user", "content": str(input)}]

        elif model_type == ModelType.EMBEDDER:
            # Embeddings
            if isinstance(input, str):
                api_kwargs["input"] = input
            elif isinstance(input, list):
                api_kwargs["input"] = input
            else:
                api_kwargs["input"] = str(input)

        return api_kwargs

    @backoff.on_exception(
        backoff.expo,
        (requests.exceptions.RequestException,),
        max_time=5,
    )
    def call(self, api_kwargs: Dict = {}, model_type: ModelType = ModelType.UNDEFINED):
        """
        Synchronous call to the MLX LM server.

        Args:
            api_kwargs: API keyword arguments.
            model_type: The type of model call.

        Returns:
            Parsed response from the server.
        """
        if model_type == ModelType.LLM:
            return self._call_llm(api_kwargs)
        elif model_type == ModelType.EMBEDDER:
            return self._call_embedder(api_kwargs)
        else:
            raise ValueError(f"Unsupported model type: {model_type}")

    async def acall(self, api_kwargs: Dict = {}, model_type: ModelType = ModelType.UNDEFINED):
        """
        Asynchronous call to the MLX LM server.

        Args:
            api_kwargs: API keyword arguments.
            model_type: The type of model call.

        Returns:
            For LLM with stream=True: an async generator of text chunks.
            For LLM without stream: parsed response.
            For EMBEDDER: parsed embedding response.
        """
        if model_type == ModelType.LLM:
            if api_kwargs.get("stream", False):
                return self._astream_llm(api_kwargs)
            else:
                return await self._acall_llm(api_kwargs)
        elif model_type == ModelType.EMBEDDER:
            return await self._acall_embedder(api_kwargs)
        else:
            raise ValueError(f"Unsupported model type: {model_type}")

    def parse_chat_completion(self, completion: Any) -> GeneratorOutput:
        """Parse a chat completion response."""
        try:
            if isinstance(completion, dict):
                choices = completion.get("choices", [])
                if choices:
                    message = choices[0].get("message", {})
                    content = message.get("content", "")
                    usage = completion.get("usage", {})
                    return GeneratorOutput(
                        data=content,
                        usage=CompletionUsage(
                            prompt_tokens=usage.get("prompt_tokens", 0),
                            completion_tokens=usage.get("completion_tokens", 0),
                            total_tokens=usage.get("total_tokens", 0),
                        ),
                    )
            return GeneratorOutput(data=str(completion))
        except Exception as e:
            logger.error(f"Error parsing chat completion: {e}")
            return GeneratorOutput(data=str(completion), error=str(e))

    def parse_embedding_response(self, response: Any) -> EmbedderOutput:
        """Parse an embedding response into EmbedderOutput."""
        from dataclasses import dataclass, field

        @dataclass
        class EmbeddingData:
            embedding: List[float]
            index: int = 0

        try:
            if isinstance(response, dict):
                data = response.get("data", [])
                embeddings = []
                for item in data:
                    embedding = item.get("embedding", [])
                    index = item.get("index", 0)
                    embeddings.append(EmbeddingData(embedding=embedding, index=index))

                usage = response.get("usage", {})
                return EmbedderOutput(
                    data=embeddings,
                    error=None,
                    usage=CompletionUsage(
                        prompt_tokens=usage.get("prompt_tokens", 0),
                        completion_tokens=0,
                        total_tokens=usage.get("total_tokens", 0),
                    ),
                )
            return EmbedderOutput(data=[], error=f"Unexpected response type: {type(response)}")
        except Exception as e:
            logger.error(f"Error parsing embedding response: {e}")
            return EmbedderOutput(data=[], error=str(e))

    # ------------------------------------------------------------------ #
    #  Synchronous helpers
    # ------------------------------------------------------------------ #

    def _call_llm(self, api_kwargs: Dict) -> Dict:
        """Synchronous LLM call."""
        url = f"{self.host}/v1/chat/completions"
        # Remove stream for sync call
        payload = {k: v for k, v in api_kwargs.items() if k != "stream"}
        payload["stream"] = False

        response = self.sync_client.post(url, json=payload, timeout=300)
        response.raise_for_status()
        return response.json()

    def _call_embedder(self, api_kwargs: Dict) -> Dict:
        """Synchronous embedding call."""
        url = f"{self.host}/v1/embeddings"
        payload = {k: v for k, v in api_kwargs.items()}

        response = self.sync_client.post(url, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------ #
    #  Asynchronous helpers
    # ------------------------------------------------------------------ #

    async def _acall_llm(self, api_kwargs: Dict) -> Dict:
        """Async non-streaming LLM call."""
        url = f"{self.host}/v1/chat/completions"
        payload = {k: v for k, v in api_kwargs.items() if k != "stream"}
        payload["stream"] = False

        session = self._get_async_session()
        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=300)) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def _astream_llm(self, api_kwargs: Dict) -> AsyncGenerator[str, None]:
        """Async streaming LLM call – yields text chunks."""
        url = f"{self.host}/v1/chat/completions"
        payload = {**api_kwargs, "stream": True}

        session = self._get_async_session()
        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=600)) as resp:
            resp.raise_for_status()
            async for line in resp.content:
                decoded = line.decode("utf-8").strip()
                if not decoded or not decoded.startswith("data: "):
                    continue
                data_str = decoded[len("data: "):]
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    choices = chunk.get("choices", [])
                    if choices:
                        delta = choices[0].get("delta", {})
                        content = delta.get("content")
                        if content:
                            yield content
                except json.JSONDecodeError:
                    continue

    async def _acall_embedder(self, api_kwargs: Dict) -> Dict:
        """Async embedding call."""
        url = f"{self.host}/v1/embeddings"
        payload = {k: v for k, v in api_kwargs.items()}

        session = self._get_async_session()
        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=120)) as resp:
            resp.raise_for_status()
            return await resp.json()
