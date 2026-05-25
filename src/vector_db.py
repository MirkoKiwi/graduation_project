import chromadb
import ollama

from config import config, settings



class VectorDB:
    def __init__(self):
        self._client     = chromadb.PersistentClient(path=str(config.vec_db_dir))
        self._collection = self._client.get_or_create_collection(name="references")


    @property
    def count(self) -> int:
        return self._collection.count()


    # DEBUG
    def _delete_db(self) -> None:
        try:
            collection_name = self._collection.name
            self._client.delete_collection(name=collection_name)
            self._collection = self._client.get_or_create_collection(name=collection_name)
            print(f"Collection \"{collection_name}\" deleted")
        except Exception as e:
            print(f"Error deleting \"{collection_name}\": {e}")


    def _delete_doc_by_id(self, doc_id: str) -> None:
        try:
            self._collection.delete(ids=[doc_id])
            print(f"Doc \"{doc_id}\" removed")
        except Exception as e:
            print(f"Error removing \"{doc_id}\": {e}")
    

    def add_docs(self, documents: list[str], ids: list[str], metadatas: list[dict]) -> None:
        try:
            self._collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
        except Exception as e:
            print(f"Error adding documents to ChromaDB: {e}")


    # Retrieval
    def query_context(self, query_text: str, n_results: int = 5) -> str:
        try:
            results = self._collection.query(
                query_texts=[query_text],
                n_results=n_results
            )
            
            if not results or not results.get('documents') or not results['documents'][0]:
                return ""
                
            return "\n\n".join(results['documents'][0])
            
        except Exception as e:
            print(f"Error querying ChromaDB: {e}")
            return ""
