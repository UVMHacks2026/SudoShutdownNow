import numpy as np
import psycopg2
from psycopg2.extras import execute_values
import os
from dotenv import load_dotenv
from typing import Dict, Tuple, Optional
import logging


# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- DATABASE CONFIGURATION ---
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/sudoshutdown")
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", 0.40))
FACE_MODEL = os.getenv("FACE_MODEL", "buffalo_l")  # lightweight model
GPU_ENABLED = os.getenv("GPU_ENABLED", "false").lower() == "true"

# --- GLOBAL VARIABLES ---
authorized_users: Dict[str, np.ndarray] = {}
last_known_authorized_centers: Dict[str, Tuple[int, int]] = {}
conn = None
face_app = None


# --- DATABASE INITIALIZATION ---
def init_db():
    """Initialize database connection and create tables if needed."""
    global conn
    try:
        conn = psycopg2.connect(DATABASE_URL)
        logger.info("Database connection established")
        
        # Create users table if it doesn't exist
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) UNIQUE NOT NULL,
                    embedding BYTEA NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Create index on name for faster lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_name ON users(name);
            """)
            
        conn.commit()
        logger.info("Database tables initialized")
    
    except psycopg2.Error as e:
        logger.error(f"Database connection error: {e}")
        raise


def load_users():
    global authorized_users, conn
        
    if conn is None:
        init_db()
        
    authorized_users.clear()
        
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT name, embedding FROM users;")
            rows = cursor.fetchall()
            
        conn.commit()  # Close the read transaction to avoid Idle-In-Transaction
                
        for name, embedding_bytes in rows:
            # Deserialize embedding from bytes safely using numpy
            embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
            authorized_users[name] = embedding
            logger.info(f"Loaded user: {name}")
            
        logger.info(f"Total users loaded: {len(authorized_users)}")
        
    except psycopg2.Error as e:
        logger.error(f"Error loading users: {e}")
        if conn:
            conn.rollback()
        raise


def save_user(name: str, embedding: np.ndarray) -> bool:
    global conn
    if conn is None:
        init_db()
        
    try:
        # Validate embedding
        if not isinstance(embedding, np.ndarray):
            embedding = np.array(embedding)
        
        if embedding.shape[0] != 512:  # InsightFace uses 512-dim embeddings
            logger.warning(f"Unexpected embedding dimension: {embedding.shape[0]}")
        
        # Serialize embedding to bytes securely using numpy
        embedding_bytes = embedding.astype(np.float32).tobytes()
        
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO users (name, embedding) 
                VALUES (%s, %s)
                ON CONFLICT (name) DO UPDATE 
                SET embedding = EXCLUDED.embedding, updated_at = CURRENT_TIMESTAMP;
                """,
                (name, embedding_bytes)
            )
        conn.commit()
        
        # Update in-memory dictionary so it's instantly available
        authorized_users[name] = embedding.astype(np.float32)
        
        logger.info(f"User {name} saved successfully")
        return True
    
    except psycopg2.Error as e:
        logger.error(f"Error saving user {name}: {e}")
        if conn:
            conn.rollback()
        return False
    except Exception as e:
        logger.error(f"Unexpected error saving user {name}: {e}")
        if conn:
            conn.rollback()
        return False

# Function to try to compute similarity between two embeddings
def compute_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    try:
        # Ensure inputs are numpy arrays
        if not isinstance(embedding1, np.ndarray):
            embedding1 = np.array(embedding1)
        if not isinstance(embedding2, np.ndarray):
            embedding2 = np.array(embedding2)
        
        # InsightFace features are already L2 normalized. 
        # The dot product is equivalent to cosine similarity.
        similarity = np.dot(embedding1, embedding2)
        similarity = np.clip(similarity, -1.0, 1.0)  # Ensure the value is within valid cosine similarity range
        return float(similarity)
    
    except Exception as e:
        logger.error(f"Error computing similarity: {e}")
        return 0.0


def init_face_app():
    # Initialize InsightFace recognition model.
    global face_app
    
    try:
        logger.info(f"Initializing face recognition model: {FACE_MODEL}")
        
        # Create FaceAnalysis app
        face_app = FaceAnalysis(
            name=FACE_MODEL,
            root=os.path.expanduser("~/.insightface"),
            providers=['CUDAExecutionProvider', 'CPUExecutionProvider'] if GPU_ENABLED else ['CPUExecutionProvider']
        )
        
        # Prepare the model (required for insightface)
        face_app.prepare(ctx_id=0 if GPU_ENABLED else -1, det_size=(640, 640))
        
        logger.info("Face recognition model initialized successfully")
    
    except Exception as e:
        logger.error(f"Error initializing face app: {e}")
        raise


def get_face_embedding(frame: np.ndarray) -> Optional[np.ndarray]:
    try:
        if face_app is None:
            logger.error("Face app not initialized")
            return None
        
        # Detect faces in the frame
        faces = face_app.get(frame)
        
        if len(faces) == 0:
            return None
        
        # Return embedding of the first (most prominent) face
        # This embedding is already L2-normalized by InsightFace
        embedding = faces[0].normed_embedding
        return embedding
    
    except Exception as e:
        logger.error(f"Error extracting face embedding: {e}")
        return None


def match_face(embedding: np.ndarray, threshold: float = SIMILARITY_THRESHOLD) -> Tuple[Optional[str], float]:
    best_match_name = None
    best_similarity = 0.0
    
    for name, registered_embedding in authorized_users.items():
        similarity = compute_similarity(embedding, registered_embedding)
        
        if similarity > best_similarity:
            best_similarity = similarity
            best_match_name = name if similarity >= threshold else None
    
    return best_match_name, best_similarity


def delete_user(name: str) -> bool:
    global conn
    if conn is None:
        init_db()
        
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM users WHERE name = %s;", (name,))
        conn.commit()
        
        if name in authorized_users:
            del authorized_users[name]
        
        logger.info(f"User {name} deleted successfully")
        return True
    
    except psycopg2.Error as e:
        logger.error(f"Error deleting user {name}: {e}")
        if conn:
            conn.rollback()
        return False


def get_all_users() -> Dict[str, dict]:
    global conn
    if conn is None:
        init_db()
        
    try:
        users_info = {}
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, name, created_at, updated_at FROM users;")
            rows = cursor.fetchall()
            
        conn.commit()  # Close the read transaction to avoid Idle-In-Transaction
            
        for user_id, name, created_at, updated_at in rows:
            users_info[name] = {
                "id": user_id,
                "created_at": str(created_at),
                "updated_at": str(updated_at)
            }
        
        return users_info
    
    except psycopg2.Error as e:
        logger.error(f"Error fetching users: {e}")
        if conn:
            conn.rollback()
        return {}

# --- INITIALIZATION ---
if __name__ != "__main__":
    # Initialize on module import
    try:
        init_db()
        init_face_app()
        load_users()
        logger.info("Facial recognition system initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize facial recognition system: {e}")
        raise