import os


os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['TORCH_USE_CUDA_DSA'] = '0'
# Disable CUDA completely
os.environ['TORCH_CUDA_ARCH_LIST'] = ''
# Force CPU device
os.environ['TORCH_DEVICE'] = 'cpu'

from dotenv import load_dotenv
from pathlib import Path

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    BaseSettings = None
    SettingsConfigDict = None

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")


try:
    from langchain_huggingface import HuggingFaceEmbeddings
    from transformers import AutoTokenizer
    from sentence_transformers import SentenceTransformer
    from app.utils.CustomEmbedding import CustomEmbedding
    from openai import OpenAI
    from langchain_core.runnables import Runnable
    from langchain_core.language_models import BaseChatModel
    from langchain_core.messages import AIMessage
    from app.utils.llm import OpenRouterLLM
    from qdrant_client import QdrantClient
    ML_IMPORTS_AVAILABLE = True
except ImportError:
 
    ML_IMPORTS_AVAILABLE = False
    HuggingFaceEmbeddings = None
    AutoTokenizer = None
    SentenceTransformer = None
    CustomEmbedding = None
    OpenAI = None
    Runnable = None
    BaseChatModel = None
    AIMessage = None
    OpenRouterLLM = None
    QdrantClient = None


# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL")
FRONTEND_HOST = os.getenv("FRONTEND_HOST")
HOST = os.getenv("HOST")
# Qdrant Configuration
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
# Only initialize Qdrant client if ML imports are available
if ML_IMPORTS_AVAILABLE and QdrantClient is not None:
    qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
else:
    qdrant_client = None

# MinIO Configuration
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_PUBLIC_ENDPOINT = os.getenv("MINIO_PUBLIC_ENDPOINT", "localhost:9000")  
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
MINIO_BUCKET_NAME = os.getenv("MINIO_BUCKET_NAME")

# Redis Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "1"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
REDIS_URL = os.getenv("REDIS_URL", f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")

# Observability Configuration
OBSERVABILITY_ENABLED = os.getenv("OBSERVABILITY_ENABLED", "true").lower() == "true"
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3001")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9091")
LOKI_URL = os.getenv("LOKI_URL", "http://localhost:3100")

# Cache Configuration
CACHE_TTL_EMBEDDINGS = int(os.getenv("CACHE_TTL_EMBEDDINGS", "86400"))  # 24 hours
CACHE_TTL_RESPONSES = int(os.getenv("CACHE_TTL_RESPONSES", "3600"))     # 1 hour
CACHE_TTL_DOCUMENTS = int(os.getenv("CACHE_TTL_DOCUMENTS", "7200"))    # 2 hours
CACHE_TTL_CHAT_HISTORY = int(os.getenv("CACHE_TTL_CHAT_HISTORY", "1800"))  # 30 minutes

# AI Model Configuration
MODEL_NAME = os.getenv("MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

RERANKER_MODEL = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
CROSS_ENCODER_MODEL = os.getenv("CROSS_ENCODER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))

# Security Configuration
SECRET_KEY = os.getenv("SECRET_KEY")
REFRESH_SECRET_KEY = os.getenv("REFRESH_SECRET_KEY")

# Validate required secrets at startup
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is required. Please set it in your .env file.")
if not REFRESH_SECRET_KEY:
    raise ValueError("REFRESH_SECRET_KEY environment variable is required. Please set it in your .env file.")
ALGORITHM = os.getenv("ALGORITHM", "HS256")



ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Email Configuration
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

# File Upload Configuration
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads/")
ALLOWED_EXTENSIONS = {
    "pdf", "txt", "csv", "md"
}
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "200"))

# Document Processing Configuration
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))

# Language Configuration
LANGUAGE_MAP = {
    "en": "English",
    "fr": "French",
    "ar": "Arabic",
    "es": "Spanish",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean"
}


# CORS Configuration
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://192.168.22.1:3000").split(",")

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,host.docker.internal").split(",")

# Frontend URL for redirects
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


model = None
encoder = None
tokenizer = None

if ML_IMPORTS_AVAILABLE:
    # Always try to use cached model path if available (works in both online and offline mode)
    hf_home = os.getenv("HF_HOME", os.path.expanduser("~/.cache/huggingface"))
    
    # Normalize model name - ensure it has the full path
    embedding_model_name = EMBEDDING_MODEL
    if not embedding_model_name.startswith("sentence-transformers/"):
        embedding_model_name = f"sentence-transformers/{embedding_model_name}"
    
    # Look for cached model in hub directory
    cached_model_path = os.path.join(hf_home, "hub", f"models--{embedding_model_name.replace('/', '--')}")
    model_path = embedding_model_name
    if os.path.exists(cached_model_path):
        # Find the snapshot directory
        snapshots_dir = os.path.join(cached_model_path, "snapshots")
        if os.path.exists(snapshots_dir):
            snapshots = [d for d in os.listdir(snapshots_dir) if os.path.isdir(os.path.join(snapshots_dir, d))]
            if snapshots:
                model_path = os.path.join(snapshots_dir, snapshots[0])
                print(f"  Using cached model path: {model_path}")
    
    try:
        print(f"  Attempting to load model from: {model_path}")
        model = SentenceTransformer(model_path)
        print(f"✓ SentenceTransformer model loaded: {EMBEDDING_MODEL}")
    except Exception as e:
        print(f"⚠ Warning: Could not load SentenceTransformer model '{EMBEDDING_MODEL}': {e}")
        print(f"  Tried path: {model_path}")
        model = None

    # Use cached path for embeddings if available
    encoder_model_path = model_path if os.path.exists(model_path) and model_path != embedding_model_name else MODEL_NAME
    try:
        encoder = HuggingFaceEmbeddings(
            model_name=encoder_model_path, 
            model_kwargs={"device": "cpu"}
        )
        print(f"✓ HuggingFace embeddings loaded: {MODEL_NAME}")
    except Exception as e:
        print(f"⚠ Warning: Could not load HuggingFace embeddings '{MODEL_NAME}': {e}")

    # Use cached path for tokenizer if available
    tokenizer_model_path = model_path if os.path.exists(model_path) and model_path != embedding_model_name else MODEL_NAME
    try:
        tokenizer = AutoTokenizer.from_pretrained(tokenizer_model_path)
        print(f"✓ Tokenizer loaded: {MODEL_NAME}")
    except Exception as e:
        print(f"⚠ Warning: Could not load tokenizer '{MODEL_NAME}': {e}")
else:
    pass



# Settings class - only define if pydantic is available
if PYDANTIC_AVAILABLE and BaseSettings is not None:
    class Settings(BaseSettings):
        app_name: str = "RAG API"
        admin_email: str = os.getenv("ADMIN_EMAIL", "default@example.com")
        items_per_user: int = int(os.getenv("ITEMS_PER_USER", "50"))
        
        model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
        model_config.update({"extra": "ignore"})
    
    settings = Settings()
else:
    # In lightweight images, create a simple settings object
    class SimpleSettings:
        app_name: str = "RAG API"
        admin_email: str = os.getenv("ADMIN_EMAIL", "default@example.com")
        items_per_user: int = int(os.getenv("ITEMS_PER_USER", "50"))
    
    settings = SimpleSettings()

# OpenRouter Configuration
openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
openrouter_model = os.getenv("OPENROUTER_MODEL", "mistralai/mistral-7b-instruct:free")
# Fallback models to use if primary model hits rate limit (comma-separated)
openrouter_fallback_models = [
    model.strip() 
    for model in os.getenv("OPENROUTER_FALLBACK_MODELS", "meta-llama/llama-3.3-70b-instruct:free").split(",")
    if model.strip()
]



llm = None

# Only initialize LLM if ML imports are available
if ML_IMPORTS_AVAILABLE and openrouter_api_key:
    try:
        # Initialize OpenAI client with OpenRouter base URL
        openai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_api_key,
        )
        # Wrap it to be compatible with LangChain
        llm = OpenRouterLLM(
            client=openai_client,
            model=openrouter_model,
            temperature=LLM_TEMPERATURE,
            fallback_models=openrouter_fallback_models
        )
        fallback_info = f" with fallbacks: {', '.join(openrouter_fallback_models)}" if openrouter_fallback_models else ""
        print(f"✓ OpenRouter client initialized successfully with model: {openrouter_model}{fallback_info}")
    except Exception as e:
        print(f"Warning: Could not initialize OpenRouter client: {e}")
elif not ML_IMPORTS_AVAILABLE:
    # In lightweight images, skip LLM initialization
    pass
else:
    print("Warning: OPENROUTER_API_KEY not set")

# Final fallback message (only in backend-image)
if ML_IMPORTS_AVAILABLE and llm is None:
    print("Warning: No LLM provider configured")
    print("Set OPENROUTER_API_KEY in .env file to enable AI features")

