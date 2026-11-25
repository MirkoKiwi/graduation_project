"""
Usage:
    python -m scripts.db_ingest --mode title_only
    python -m scripts.db_ingest --mode title_abstract
"""


import sqlite3
import os
import argparse
import sqlite3

from src.vector_db import VectorDB
from config import config



DB_FILENAME = "acl.db"

# Load Dataset
def start_ingest(mode="title_abstract"):
    
    collection_name = f"acl_{mode}"
    vec_db          = VectorDB(collection_name=collection_name)
    print(f"[*] DB Init.\n Mode: {mode} -> Collection: {collection_name}\n Current docs: {vec_db.count}")


    sqlite_path = config.data_dir / DB_FILENAME
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
                p.anthology_id,
                p.title,
                p.url,
                p.doi,
                p.abstract,
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
        conn.close()
        return

    papers = {}
    for p_id, anth_id, title, url, doi, abstract, author_name in rows:
        if p_id not in papers:
            papers[p_id] = {
                "anthology_id": anth_id or str(p_id),
                "title": title,
                "url": url or "",
                "doi": doi or "",
                "abstract": abstract or "",
                "authors": []
            }
        if author_name:
            papers[p_id]["authors"].append(author_name)


    # Chunking
    documents = []
    ids       = []
    metadatas = []
    for p_id, info in papers.items():
        title         = info["title"]
        authors_list  = info["authors"]
        
        authors_comma = ", ".join(authors_list) if authors_list else "Unknown"
        authors_and   = " and ".join(authors_list) if authors_list else "Unknown"
        
        url = info["url"]
        doi = info["doi"]
        abstract = info["abstract"]

        if mode == "title_only" or not abstract:
            full_text = f"Title: {title}\nAuthors: {authors_comma}"
        else:
            full_text = f"Title: {title}\nAuthors: {authors_comma}\nAbstract: {info['abstract']}"
        
        bib_entry = f"""
            @article{{{info['anthology_id']},
            title={{{title}}},
            author={{{authors_and}}},
            journal={{ACL Anthology}},
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["title_only", "title_abstract"], default="title_abstract")
    args = parser.parse_args()
    start_ingest(mode=args.mode)