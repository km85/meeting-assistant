import os
import hashlib
import time
from typing import List, Optional, Dict, Any

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer

from app.config import get_settings

settings = get_settings()


class KnowledgeBase:
    """Vector knowledge base for project documents."""
    
    def __init__(self):
        self.client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
        )
        self.model = SentenceTransformer(settings.embedding_model)
        self.vector_size = self.model.get_sentence_embedding_dimension()
    
    def _get_collection_name(self, project_id: str) -> str:
        """Generate safe collection name from project ID."""
        # Hash project_id to ensure valid collection name
        hashed = hashlib.md5(project_id.encode('utf-8')).hexdigest()[:16]
        return f"project_{hashed}"
    
    def create_project_collection(self, project_id: str) -> bool:
        """Create vector collection for a project."""
        collection_name = self._get_collection_name(project_id)
        
        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            exists = any(c.name == collection_name for c in collections)
            
            if exists:
                return True
            
            # Create new collection
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE,
                ),
            )
            return True
            
        except Exception as e:
            print(f"Failed to create collection: {e}")
            return False
    
    def delete_project_collection(self, project_id: str) -> bool:
        """Delete vector collection for a project."""
        collection_name = self._get_collection_name(project_id)
        
        try:
            self.client.delete_collection(collection_name)
            return True
        except Exception as e:
            print(f"Failed to delete collection: {e}")
            return False
    
    def add_documents(
        self,
        project_id: str,
        chunks: List[str],
        metadata: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """Add document chunks to project knowledge base."""
        collection_name = self._get_collection_name(project_id)
        
        # Ensure collection exists
        if not self.create_project_collection(project_id):
            return False
        
        try:
            # Generate embeddings
            embeddings = self.model.encode(chunks, show_progress_bar=False)
            
            # Prepare points
            points = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                point_meta = metadata[i] if metadata and i < len(metadata) else {}
                point_meta["text"] = chunk
                point_meta["timestamp"] = time.time()
                
                points.append(PointStruct(
                    id=i,
                    vector=embedding.tolist(),
                    payload=point_meta,
                ))
            
            # Upload to Qdrant
            self.client.upsert(
                collection_name=collection_name,
                points=points,
            )
            
            return True
            
        except Exception as e:
            print(f"Failed to add documents: {e}")
            return False
    
    def search(
        self,
        project_id: str,
        query: str,
        limit: int = 5,
        score_threshold: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Search project knowledge base."""
        collection_name = self._get_collection_name(project_id)
        
        try:
            # Generate query embedding
            query_embedding = self.model.encode([query])[0]
            
            # Search
            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_embedding.tolist(),
                limit=limit,
                score_threshold=score_threshold,
            )
            
            return [
                {
                    "text": r.payload.get("text", ""),
                    "score": r.score,
                    "metadata": {k: v for k, v in r.payload.items() if k != "text"},
                }
                for r in results
            ]
            
        except Exception as e:
            print(f"Search failed: {e}")
            return []
    
    def get_project_stats(self, project_id: str) -> Dict[str, Any]:
        """Get project knowledge base stats."""
        collection_name = self._get_collection_name(project_id)
        
        try:
            info = self.client.get_collection(collection_name)
            return {
                "exists": True,
                "vectors_count": info.vectors_count,
                "indexed_vectors_count": info.indexed_vectors_count,
            }
        except Exception:
            return {"exists": False, "vectors_count": 0}


# Global instance
knowledge_base = KnowledgeBase()
