import chromadb
import ollama

from config import config, settings



class VectorDB:
    def __init__(self):
        self._client     = chromadb.PersistentClient(path=str(config.vec_db_dir))
        self._collection = self._client.get_or_create_collection(name="references")

    def add_docs(self, documents: list[str], ids: list[str], metadatas: list[dict]):
        try:
            self._collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
        except Exception as e:
            print(f"Error adding documents to ChromaDB: {e}")

    def query_context(self, query_text: str, n_results: int = 5):
        try:
            results = self._collection.query(
                query_texts=[query_text],
                n_results=n_results
            )
            
            if not results or not results['documents']:
                return ""
                
            return "\n\n".join(results['documents'][0])
            
        except Exception as e:
            print(f"Error querying ChromaDB: {e}")
            return ""
