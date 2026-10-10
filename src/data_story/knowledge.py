"""Knowledge base for RAG (stage 07): editable rule documents, fragments and local search.

Documents live in SQLite, seeded once from the repository defaults in ``knowledge/``; a future
editor changes the rows, never the defaults. Each ``##`` section is one fragment with its
document, section, source and priority. Search is fully local: TF-IDF over character n-grams
(scikit-learn), which tolerates Ukrainian word endings without model weights or network.
The retriever sits behind ``search`` so embeddings can replace it later.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from .storage import connect, ensure_schema

DEFAULTS = Path(__file__).parent / "knowledge"
METHOD = "tfidf-char_wb-3-5"
MIN_SCORE = 0.08
MAX_QUERY = 500


class KnowledgeError(ValueError):
    """The knowledge base cannot answer this request."""


@dataclass(frozen=True)
class Fragment:
    id: str
    document_id: str
    title: str
    section: str
    source: str
    priority: int
    text: str


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse(document_id: str, text: str) -> tuple[dict, list[Fragment]]:
    """Header ``# title``, ``Джерело:``, ``Пріоритет:``; every ``## section`` is a fragment."""
    lines = text.strip().splitlines()
    if not lines or not lines[0].startswith("# "):
        raise KnowledgeError("Документ бази знань має починатися із заголовка «# Назва».")
    title = lines[0][2:].strip()
    source, priority = "", 3
    for line in lines[1:4]:
        if line.startswith("Джерело:"):
            source = line.split(":", 1)[1].strip()
        if line.startswith("Пріоритет:"):
            priority = int(line.split(":", 1)[1].strip() or 3)
    fragments = []
    for number, block in enumerate(re.split(r"^## ", text, flags=re.M)[1:], 1):
        heading, _, body = block.partition("\n")
        body = " ".join(body.split())
        if body:
            fragments.append(
                Fragment(
                    f"{document_id}#{number}",
                    document_id,
                    title,
                    heading.strip(),
                    source,
                    priority,
                    body,
                )
            )
    if not fragments:
        raise KnowledgeError("Документ бази знань не містить розділів «## …».")
    meta = {"id": document_id, "title": title, "source": source, "priority": priority}
    return meta, fragments


class KnowledgeStore:
    def __init__(self, database: Path, defaults: Path = DEFAULTS):
        self.database = ensure_schema(database)
        self.defaults = defaults
        self._index: tuple[str, TfidfVectorizer, np.ndarray, list[Fragment]] | None = None

    def _seed(self, connection) -> None:
        if connection.execute("SELECT 1 FROM knowledge_documents LIMIT 1").fetchone():
            return
        for path in sorted(self.defaults.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            meta, _ = parse(path.stem, text)
            connection.execute(
                "INSERT INTO knowledge_documents VALUES (?, ?, ?, ?, ?, 1, ?)",
                (path.stem, meta["title"], meta["source"], meta["priority"], text, _now()),
            )

    def documents(self) -> list[dict]:
        with connect(self.database) as connection:
            self._seed(connection)
            rows = connection.execute(
                "SELECT * FROM knowledge_documents ORDER BY priority, id"
            ).fetchall()
        return [
            {
                "id": r["id"],
                "title": r["title"],
                "source": r["source"],
                "priority": r["priority"],
                "text": r["text"],
                "is_default": bool(r["is_default"]),
                "updated_at": r["updated_at"],
                "fragments": len(parse(r["id"], r["text"])[1]),
            }
            for r in rows
        ]

    def fragments(self) -> list[Fragment]:
        result: list[Fragment] = []
        for document in self.documents():
            result.extend(parse(document["id"], document["text"])[1])
        return result

    def _ensure_index(self) -> tuple[str, TfidfVectorizer, np.ndarray, list[Fragment]]:
        fragments = self.fragments()
        fingerprint = hashlib.sha256(
            json.dumps([(f.id, f.section, f.text) for f in fragments], ensure_ascii=False).encode()
        ).hexdigest()
        if self._index is None or self._index[0] != fingerprint:
            vectorizer = TfidfVectorizer(
                analyzer="char_wb", ngram_range=(3, 5), lowercase=True, sublinear_tf=True
            )
            matrix = vectorizer.fit_transform(
                [f"{f.title}. {f.section}. {f.section}. {f.text}" for f in fragments]
            )
            self._index = (fingerprint, vectorizer, matrix, fragments)
        return self._index

    def search(self, query: str, limit: int = 3) -> dict:
        query = " ".join(str(query).split())
        if not query:
            raise KnowledgeError("Введіть запитання для пошуку в базі знань.")
        if len(query) > MAX_QUERY:
            raise KnowledgeError(f"Запитання задовге: до {MAX_QUERY} символів.")
        started = perf_counter()
        fingerprint, vectorizer, matrix, fragments = self._ensure_index()
        scores = (matrix @ vectorizer.transform([query.lower()]).T).toarray().ravel()
        order = sorted(range(len(fragments)), key=lambda i: (-scores[i], fragments[i].priority, i))
        hits = [
            {
                "id": fragments[i].id,
                "document_id": fragments[i].document_id,
                "title": fragments[i].title,
                "section": fragments[i].section,
                "source": fragments[i].source,
                "priority": fragments[i].priority,
                "text": fragments[i].text,
                "score": round(float(scores[i]), 4),
            }
            for i in order[:limit]
            if scores[i] >= MIN_SCORE
        ]
        result = {
            "query": query,
            "method": METHOD,
            "index": fingerprint[:12],
            "fragment_count": len(fragments),
            "hits": hits,
            "reason": None if hits else "У базі знань не знайдено достатньо схожих правил.",
        }
        with connect(self.database) as connection:
            connection.execute(
                "INSERT INTO config_events VALUES (?, ?, ?, ?, ?)",
                (
                    str(uuid4()),
                    "knowledge",
                    "knowledge.searched",
                    _now(),
                    json.dumps(
                        {
                            "query": query,
                            "limit": limit,
                            "method": METHOD,
                            "index": fingerprint[:12],
                            "hits": [{"id": h["id"], "score": h["score"]} for h in hits],
                            "duration_ms": (perf_counter() - started) * 1000,
                        },
                        ensure_ascii=False,
                    ),
                ),
            )
        return result

    def events(self, limit: int = 20) -> list[dict]:
        with connect(self.database) as connection:
            rows = connection.execute(
                "SELECT operation, occurred_at, payload FROM config_events "
                "WHERE subject = 'knowledge' ORDER BY occurred_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {
                "operation": r["operation"],
                "occurred_at": r["occurred_at"],
                **json.loads(r["payload"]),
            }
            for r in rows
        ]
