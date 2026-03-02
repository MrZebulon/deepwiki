"""
MLX document processor for embeddings.

Like the Ollama document processor, this handles embedding documents
one at a time since the local MLX embedding server may not support
large batch requests efficiently.
"""

from typing import Sequence, List
from copy import deepcopy
from tqdm import tqdm
import logging
import adalflow as adal
from adalflow.core.types import Document
from adalflow.core.component import DataComponent

from api.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


class MLXDocumentProcessor(DataComponent):
    """
    Process documents for MLX embeddings by processing one document at a time.

    The local MLX LM embedding server may not efficiently handle large batches,
    so we process each document individually (same approach as OllamaDocumentProcessor).
    """

    def __init__(self, embedder: adal.Embedder) -> None:
        super().__init__()
        self.embedder = embedder

    def __call__(self, documents: Sequence[Document]) -> Sequence[Document]:
        output = deepcopy(documents)
        logger.info(f"Processing {len(output)} documents individually for MLX embeddings")

        successful_docs = []
        expected_embedding_size = None

        for i, doc in enumerate(tqdm(output, desc="Processing documents for MLX embeddings")):
            try:
                # Get embedding for a single document
                result = self.embedder(input=doc.text)
                if result.data and len(result.data) > 0:
                    embedding = result.data[0].embedding

                    # Validate embedding size consistency
                    if expected_embedding_size is None:
                        expected_embedding_size = len(embedding)
                        logger.info(f"Expected embedding size set to: {expected_embedding_size}")
                    elif len(embedding) != expected_embedding_size:
                        file_path = getattr(doc, 'meta_data', {}).get('file_path', f'document_{i}')
                        logger.warning(
                            f"Document '{file_path}' has inconsistent embedding size "
                            f"{len(embedding)} != {expected_embedding_size}, skipping"
                        )
                        continue

                    # Assign the embedding to the document
                    output[i].vector = embedding
                    successful_docs.append(output[i])
                else:
                    file_path = getattr(doc, 'meta_data', {}).get('file_path', f'document_{i}')
                    logger.warning(f"Failed to get embedding for document '{file_path}', skipping")
            except Exception as e:
                file_path = getattr(doc, 'meta_data', {}).get('file_path', f'document_{i}')
                logger.error(f"Error processing document '{file_path}': {e}, skipping")

        logger.info(
            f"Successfully processed {len(successful_docs)}/{len(output)} "
            f"documents with consistent embeddings"
        )
        return successful_docs
