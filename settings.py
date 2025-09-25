import os
from llama_index.core import Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.cerebras import Cerebras

# LLM (OpenAI-compatible)
Settings.llm = Cerebras(model=os.getenv("CEREBRAS_MODEL", "llama-3.3-70b"))

# Dense embeddings
Settings.embed_model = HuggingFaceEmbedding(
    model_name=os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5"),
    query_instruction="Represent this sentence for searching relevant passages: "
)

# Chunking
Settings.chunk_size = int(os.getenv("CHUNK_SIZE", "512"))
