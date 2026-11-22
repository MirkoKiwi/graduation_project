"""
Usage:
    python3 -m pytest tests/test_hallucinator_eval.py -v
"""
from evaluation.hallucinator_eval import _parse_bibtex_to_references


class TestBibtexParser:

    def test_basic_parsing(self):
        raw = "@article{k1, title={Test Article}, author={John Dark Souls and Jane Silksong}, doi={10.1234/test}}"
        refs = _parse_bibtex_to_references(raw)

        assert len(refs) == 1
        assert refs[0].title == "Test Article"
        assert refs[0].authors == ["John Dark Souls", "Jane Silksong"]
        assert refs[0].doi == "10.1234/test"

    def test_multiple_authors(self):
        raw = "@article{k1, title={Test}, author={John Dark Souls and Jane Silksong and Garrus Vakarian}}"
        refs = _parse_bibtex_to_references(raw)

        assert refs[0].authors == ["John Dark Souls", "Jane Silksong", "Garrus Vakarian"]

    def test_multiple_entries(self):
        raw = """
        @article{k1, title={First}, author={John Dark Souls}}
        @inproceedings{k2, title={Second}, author={Jane Silksong}}
        @book{k3, title={Third}}
        """
        refs = _parse_bibtex_to_references(raw)

        assert len(refs) == 3
        assert [r.title for r in refs] == ["First", "Second", "Third"]

    def test_missing_closing_brace(self):
        raw = "@article{k1, title={Test}, author={John Dark Souls}"
        refs = _parse_bibtex_to_references(raw)

        assert len(refs) == 1
        assert refs[0].title == "Test"

    def test_nested_braces(self):
        raw = r"@article{k1, title={A {Nested} Title}}"
        refs = _parse_bibtex_to_references(raw)

        assert len(refs) == 1
        assert "Nested" in refs[0].title

    def test_escaped_characters(self):
        raw = r"@article{k1, title={An \& Improved Method}, author={John Dark Souls}}"
        refs = _parse_bibtex_to_references(raw)

        assert len(refs) == 1
        assert "&" in refs[0].title

    def test_supported_entry_types(self):
        types = [
            "article", "inproceedings", "book", "incollection",
            "phdthesis", "mastersthesis", "techreport", "misc",
            "dataset", "software",
        ]

        for entry_type in types:
            raw = f"@{entry_type}{{k1, title={{Test}}}}"
            refs = _parse_bibtex_to_references(raw)

            assert len(refs) == 1, entry_type

    def test_ignores_string_comment_preamble(self):
        raw = """
        @string{acl = "ACL"}
        @comment{Ignore me}
        @preamble{"Preamble"}
        @article{k1, title={Real Article}}
        """
        refs = _parse_bibtex_to_references(raw)

        assert len(refs) == 1
        assert refs[0].title == "Real Article"

    def test_parentheses_entry(self):
        raw = "@article(k1, title={Test Article})"
        refs = _parse_bibtex_to_references(raw)

        assert len(refs) == 1
        assert refs[0].title == "Test Article"

    def test_arxiv_extraction(self):
        raw = "@article{k1, title={Test}, eprint={2401.12345}}"
        refs = _parse_bibtex_to_references(raw)

        assert len(refs) == 1
        assert refs[0].arxiv_id == "2401.12345"

    def test_markdown_multiple_entries(self):
        raw = """Here are the references:
            ```bibtex
            @article{k1, title={First}}
            @article{k2, title={Second}}
            ```
        """
        refs = _parse_bibtex_to_references(raw)

        assert len(refs) == 2
        assert [r.title for r in refs] == ["First", "Second"]

    def test_empty_input(self):
        assert _parse_bibtex_to_references("") == []

    def test_invalid_input(self):
        assert _parse_bibtex_to_references("No references found") == []

    def test_missing_title(self):
        raw = "@article{k1, author={John Dark Souls}}"
        assert _parse_bibtex_to_references(raw) == []

    def test_missing_doi(self):
        raw = "@article{k1, title={Test}, author={John Dark Souls}}"
        refs = _parse_bibtex_to_references(raw)

        assert refs[0].doi is None

    def test_missing_author(self):
        raw = "@article{k1, title={Test}}"
        refs = _parse_bibtex_to_references(raw)

        assert len(refs) == 1
        assert refs[0].authors == []