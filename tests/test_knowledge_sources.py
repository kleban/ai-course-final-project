"""Book library: fragments next to the database, indexing with progress, search by meaning."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from data_story import embeddings
from data_story.knowledge import KnowledgeStore
from data_story.knowledge_sources import BOOK_MIN, SourceLibrary, index

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from build_sources import heading, useful  # noqa: E402

CHUNKS = [
    {"id": "b-0000", "book": "b", "chapter": "Regression", "section": "Multiple Regression",
     "pages": [10, 11], "text": "Each coefficient is the change holding other variables fixed."},
    {"id": "b-0001", "book": "b", "chapter": "Regression", "section": "Residuals",
     "pages": [12, 12], "text": "A funnel shape of residuals suggests heteroscedasticity."},
]  # fmt: skip


class Fake:
    calls = 0

    def encode(self, texts, kind):
        Fake.calls += 1
        if kind == "query":
            return np.array([[1.0, 0.0]], dtype=np.float32)
        return np.array([[0.9, 0.1] if "coefficient" in t else [0.1, 0.9] for t in texts])


class SourceTests(unittest.TestCase):
    def setUp(self):
        folder = ROOT / "tmp" / "tests"
        folder.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=folder)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.library = self.root / "knowledge-sources"

    def write(self):
        self.library.mkdir()
        (self.library / "chunks.jsonl").write_text(
            "".join(json.dumps(c) + "\n" for c in CHUNKS), encoding="utf-8"
        )
        (self.library / "books.json").write_text(
            json.dumps({"books": [{"id": "b", "title": "Stats Book", "authors": "A. Author",
                                   "year": 2024, "why": "Регресія.", "chunks": 2}]}),
            encoding="utf-8",
        )  # fmt: skip

    def test_no_library_means_no_hits_and_no_error(self):
        store = KnowledgeStore(self.root / "k.sqlite3")
        result = store.search("що таке вільний член")
        self.assertEqual(result["book_hits"], [])
        self.assertIsNone(result["books_reason"])

    def test_unindexed_library_explains_how_to_index(self):
        self.write()
        status = SourceLibrary(self.library).status()
        self.assertEqual(status["fragments"], 2)
        self.assertFalse(status["indexed"])
        self.assertIn("index_sources", status["reason"])

    def test_index_then_search_returns_cited_book_fragment(self):
        self.write()
        messages = []
        with patch.object(embeddings, "embedder", return_value=Fake()):
            path = index(self.library, messages.append)
            again = index(self.library, messages.append)
            hits, reason = SourceLibrary(self.library).search(np.array([1.0, 0.0]), 2)
        self.assertEqual(path, again)
        self.assertTrue(path.is_file())
        self.assertTrue(any("100%" in m for m in messages))
        self.assertTrue(any("Already indexed" in m for m in messages))
        self.assertIsNone(reason)
        self.assertEqual(hits[0]["id"], "b-0000")
        self.assertEqual(hits[0]["kind"], "book")
        self.assertIn("с. 10–11", hits[0]["source"])
        self.assertTrue(all(h["score"] >= BOOK_MIN for h in hits))
        self.assertEqual(len(hits), 1)  # the residuals fragment is below the threshold

    def test_cleaning_drops_code_and_detects_headings(self):
        self.assertFalse(useful("In[12]: lasso = Lasso(alpha=0.01).fit(X_train, y_train)"))
        self.assertFalse(useful("M12 Research Methods for Business Students 02727.indd 636"))
        self.assertTrue(useful("The coefficient of determination shows the explained variance."))
        self.assertTrue(heading("12.11 Assessing the strength of relationships", "x " * 10))
        self.assertFalse(heading("Figure 2-13. Learning curves", "x " * 10))
