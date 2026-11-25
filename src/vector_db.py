import chromadb

from config import config



class VectorDB:
    def __init__(self, collection_name: str = "acl_title_abstract"):
        self._client         = chromadb.PersistentClient(path=str(config.vec_db_dir))
        self.collection_name = collection_name
        self._collection     = self._client.get_or_create_collection(name=self.collection_name)


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
            self._collection.upsert(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
        except Exception as e:
            print(f"Error adding documents to ChromaDB: {e}")


    # Retrieval
    def retrieve_context(self, query_text: str, n_results: int = 5) -> dict:
        template = {"ids": [], "documents": [], "metadatas": [], "distances": []}

        try:
            total = self.count
            if total == 0:
                return template

            results = self._collection.query(
                query_texts=[query_text],
                include=["documents", "metadatas", "distances"],
                n_results=min(n_results, total),
            )
            if not results or not results.get("documents") or not results["documents"][0]:
                return template

            return {
                "ids":       results["ids"][0],
                "documents": results["documents"][0],
                "metadatas": results["metadatas"][0],
                "distances": results["distances"][0],
            }
            
        except Exception as e:
            print(f"Error querying ChromaDB: {e}")
            return template


    def query_context(self, query_text: str, n_results: int = 5) -> str:
        res = self.retrieve_context(query_text, n_results=n_results)
        if not res["documents"]:
            return ""

        context_blocks = []
        for idx, (doc, meta) in enumerate(zip(res["documents"], res["metadatas"]), start=1):
            bib = ((meta or {}).get("bibtex") or "").strip()
            block = f"[SOURCE {idx}]\nDOCUMENT CONTENT:\n{doc.strip()}\n\nCORRESPONDING BIBTEX:\n{bib}"
            context_blocks.append(block)

        return "\n\n---\n\n".join(context_blocks)
