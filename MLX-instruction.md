# Using DeepWiki with MLX: Guide for Apple Silicon Macs

DeepWiki supports local AI models through [MLX](https://github.com/ml-explore/mlx), Apple's machine learning framework optimized for Apple Silicon. This is perfect if you:

- Have an Apple Silicon Mac (M1/M2/M3/M4)
- Want maximum performance from your Mac's unified memory
- Want to run everything locally without cloud APIs
- Prefer using models optimized specifically for Apple hardware

## Prerequisites

- **Apple Silicon Mac** (M1, M2, M3, M4 or later)
- **Python 3.10+**
- **macOS 13.5+** (Ventura or later)

## Step 1: Install MLX LM

Install the MLX LM package which includes both the model runtime and an OpenAI-compatible server:

```bash
pip install mlx-lm
```

## Step 2: Start the MLX LM Server

The MLX LM server exposes an OpenAI-compatible API. Start it with your desired model:

```bash
# For text generation (chat/wiki generation)
mlx_lm.server --model mlx-community/Qwen3-1.7B-4bit --port 8080
```

> **Note:** The first time you run a model, it will be downloaded automatically from Hugging Face.

For embeddings, you will need an embedding model. You can either:
- Run a second MLX server instance on a different port for embeddings
- Use a different embedder (e.g., OpenAI, Ollama) alongside the MLX generator

## Step 3: Set Up DeepWiki

Clone the DeepWiki repository:
```bash
git clone https://github.com/AsyncFuncAI/deepwiki-open.git
cd deepwiki-open
```

Create a `.env` file in the project root:
```env
# MLX LM server host (default: http://localhost:8080)
MLX_HOST=http://localhost:8080

# Optional: If you want to use MLX for embeddings too,
# set the embedder type to mlx
DEEPWIKI_EMBEDDER_TYPE=mlx
```

### Option A: Use MLX for Both Generation and Embeddings

Configure the local embedder for MLX:
```bash
cp api/config/embedder.mlx.json.bak api/config/embedder.json
```

### Option B: Use MLX for Generation Only (with OpenAI Embeddings)

Keep the default `embedder.json` and just set your OpenAI API key:
```env
OPENAI_API_KEY=your_openai_api_key
MLX_HOST=http://localhost:8080
```

Start the backend:
```bash
python -m pip install poetry==2.0.1 && poetry install
python -m api.main
```

Start the frontend:
```bash
npm install
npm run dev
```

## Step 4: Use DeepWiki with MLX

1. Open http://localhost:3000 in your browser
2. Enter a GitHub, GitLab, or Bitbucket repository URL
3. Select **"Mlx"** as the model provider from the provider dropdown
4. Choose a model (e.g., `mlx-community/Qwen3-1.7B-4bit`)
5. Click "Generate Wiki"

## Available Models

MLX has a large ecosystem of quantized models optimized for Apple Silicon. Here are some recommended ones:

### Text Generation Models

| Model | Size | Speed | Quality | Use Case |
|-------|------|-------|---------|----------|
| `mlx-community/Qwen3-1.7B-4bit` | ~1.2GB | Fast | Good | Default, good balance |
| `mlx-community/Llama-3.2-3B-Instruct-4bit` | ~2GB | Medium | Better | More complex analysis |
| `mlx-community/Mistral-7B-Instruct-v0.3-4bit` | ~4GB | Slower | Best | Detailed documentation |

### Embedding Models

| Model | Size | Dimensions | Use Case |
|-------|------|------------|----------|
| `mlx-community/all-MiniLM-L6-v2-4bit` | ~23MB | 384 | Default, fast and efficient |

Browse more models at [mlx-community on Hugging Face](https://huggingface.co/mlx-community).

## Advanced: Using Different Models

### Changing the Generation Model

You can modify `api/config/generator.json` to add or change MLX models:

```json
"mlx": {
  "client_class": "MLXClient",
  "default_model": "mlx-community/Qwen3-1.7B-4bit",
  "supportsCustomModel": true,
  "models": {
    "mlx-community/Qwen3-1.7B-4bit": {
      "temperature": 0.7,
      "top_p": 0.8
    }
  }
}
```

### Changing the Embedding Model

You can modify `api/config/embedder.json`:

```json
"embedder_mlx": {
  "client_class": "MLXClient",
  "model_kwargs": {
    "model": "mlx-community/all-MiniLM-L6-v2-4bit"
  }
}
```

### Running Multiple MLX Servers

You can run separate MLX servers for generation and embeddings:

```bash
# Terminal 1: Generation server
mlx_lm.server --model mlx-community/Qwen3-1.7B-4bit --port 8080

# Terminal 2: Embedding server  
mlx_lm.server --model mlx-community/all-MiniLM-L6-v2-4bit --port 8081
```

Then configure your `.env`:
```env
MLX_HOST=http://localhost:8080
```

## Performance Considerations

### Why MLX on Apple Silicon?

- **Unified Memory**: MLX leverages Apple Silicon's unified memory architecture, allowing models to use both CPU and GPU memory seamlessly
- **Metal Acceleration**: Computations are accelerated by Apple's Metal GPU framework
- **Lazy Evaluation**: MLX uses lazy evaluation for efficient memory usage
- **Quantized Models**: 4-bit quantized models run efficiently with minimal quality loss

### Hardware Recommendations

| Mac | RAM | Recommended Model |
|-----|-----|-------------------|
| M1/M2 (8GB) | 8GB | `mlx-community/Qwen3-1.7B-4bit` |
| M1/M2 Pro (16GB) | 16GB | `mlx-community/Llama-3.2-3B-Instruct-4bit` |
| M1/M2 Max (32GB+) | 32GB+ | `mlx-community/Mistral-7B-Instruct-v0.3-4bit` |
| M3/M4 Pro/Max | 18GB+ | Any model that fits in memory |

### MLX vs Ollama

| Feature | MLX | Ollama |
|---------|-----|--------|
| Platform | Apple Silicon only | Cross-platform |
| Performance | Optimized for Apple Silicon | Good general performance |
| Model Format | MLX format (from HuggingFace) | GGUF format |
| Memory Usage | Efficient (unified memory) | Good |
| Setup | `pip install mlx-lm` | Download Ollama app |
| GPU Support | Metal (Apple GPU) | CUDA, Metal, ROCm |

## Troubleshooting

### "Cannot connect to MLX LM server"
- Make sure the MLX LM server is running: `mlx_lm.server --model <model_name> --port 8080`
- Verify the port matches your `MLX_HOST` environment variable
- Check that no other service is using the same port

### "Model not found"
- The model may not be downloaded yet. The first `mlx_lm.server` run will download it.
- Check that the model name matches exactly (e.g., `mlx-community/Qwen3-1.7B-4bit`)
- Browse available models at [huggingface.co/mlx-community](https://huggingface.co/mlx-community)

### Slow generation
- Use a smaller quantized model (4-bit models are fastest)
- Close other memory-intensive applications
- Consider using a model appropriate for your Mac's RAM

### Out of memory errors
- Use a smaller model that fits within your available memory
- Close other applications to free up unified memory
- Check model memory requirements on the Hugging Face model page

## Limitations

When using MLX with DeepWiki:

1. **Apple Silicon Only**: MLX only works on Apple Silicon Macs (M1/M2/M3/M4)
2. **Limited Context Window**: Local models typically have smaller context windows than cloud APIs
3. **Single Model per Server**: Each MLX server instance loads one model at a time
4. **Embedding Support**: Not all MLX models support embeddings; use dedicated embedding models

## Conclusion

Using DeepWiki with MLX gives you a high-performance, fully local solution optimized for Apple Silicon. It leverages your Mac's unified memory and Metal GPU acceleration for fast inference without relying on cloud services.

Enjoy using DeepWiki with MLX on your Mac!
