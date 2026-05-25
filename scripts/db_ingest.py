import sqlite3
import os

from src.vector_db import VectorDB
from config import config


# Load Dataset
def start_ingest():
    vec_db = VectorDB()
    print(f"[*] DB Init. Current docs: {vec_db.count}")

    db_filename = "acl.db"
    sqlite_path = config.data_dir / db_filename
    
    if not os.path.exists(sqlite_path):
        print(f"Error: {sqlite_path} not found")
        return

    print(f"[*] Connecting to {sqlite_path}...")
    conn   = sqlite3.connect(sqlite_path)
    cursor = conn.cursor()

    try:
        query = """
            SELECT
                p.id,
                p.title,
                p.url,
                p.doi,
                a.name
            FROM publications p
            LEFT JOIN publication_authors pa ON p.id = pa.pub_id
            LEFT JOIN authors a ON pa.author_id = a.id
            ORDER BY p.id, pa.position
        """
        cursor.execute(query)
        rows = cursor.fetchall()
    except Exception as e:
        print(f"[!] SQL Error: {e}")
        return

    papers = {}
    for p_id, title, url, doi, author_name in rows:
        if p_id not in papers:
            papers[p_id] = {
                "title": title,
                "url": url or "",
                "doi": doi or "",
                "authors": []
            }
        if author_name:
            papers[p_id]["authors"].append(author_name)


    # Chunking
    documents = []
    ids       = []
    metadatas = []
    for p_id, info in papers.items():
        title = info["title"]
        authors_list = info["authors"]
        authors_comma = ", ".join(authors_list) if authors_list else "Unknown"
        authors_and = " and ".join(authors_list) if authors_list else "Unknown"
        url = info["url"]
        doi = info["doi"]
        

        full_text = f"Title: {title}\nAuthors: {authors_comma}"
        
        bib_entry = f"""
            @article{{{p_id},
            title={{{title}}},
            author={{{authors_and}}},
            journal={{ACL Anthology}},
            year={{2023}},
            url={{{url}}},
            doi={{{doi}}}
        }}
        """

        documents.append(full_text)
        ids.append(str(p_id))
        metadatas.append({"bibtex": bib_entry, "url": url, "doi": doi})


    # Load in batches
    batch_size = 1000
    total_docs = len(documents)
    print(f"[*] Loading {total_docs} docs in ChromaDB (batch size: {batch_size})...")
    
    for i in range(0, total_docs, batch_size):
        batch_docs = documents[i : i + batch_size]
        batch_ids  = ids[i : i + batch_size]
        batch_meta = metadatas[i : i + batch_size]
        
        # Embedding -> Indexing
        vec_db.add_docs(documents=batch_docs, ids=batch_ids, metadatas=batch_meta)
        print(f" -> Progress: {min(i + batch_size, total_docs)}/{total_docs} loaded...")
    
    print(f"[+] Ingest done. Docs count: {vec_db.count}")
    conn.close()    



if __name__ == "__main__":
    start_ingest()