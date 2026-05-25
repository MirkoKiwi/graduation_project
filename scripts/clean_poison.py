import sys

from src.vector_db import VectorDB


def remove_poison():
    doc_id = "my_poison"
    db = VectorDB()
    db._delete_doc_by_id(doc_id)


if __name__ == "__main__":
    remove_poison()