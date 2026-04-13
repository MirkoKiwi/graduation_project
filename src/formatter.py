import os
from fpdf import FPDF
from config import config


def save_bibtex(content, filename):
    path = config.bib_dir / filename
    path.write_text(content, encoding="utf-8")
    return path