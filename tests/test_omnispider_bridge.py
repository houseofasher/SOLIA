"""OmniSpider bridge and RAG live-crawl tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from brain.omnispider_bridge import CrawledDocument, crawl_for_question, omnispider_enabled
from brain.vector_rag import RagHit, VectorRAGIndex, retrieve_with_citations


def test_omnispider_disabled_returns_empty(monkeypatch):
    monkeypatch.setenv("OMNISPIDER_ENABLED", "0")
    assert crawl_for_question("quantum mechanics", "physics") == []


@patch("brain.omnispider_bridge.requests.post")
def test_crawl_for_question_parses_documents(mock_post, monkeypatch):
    monkeypatch.setenv("OMNISPIDER_ENABLED", "1")
    mock_post.return_value = MagicMock(
        status_code=200,
        json=lambda: {
            "jobId": "job-1",
            "documents": [
                {
                    "text": (
                        "Quantum mechanics describes the behavior of matter and energy "
                        "at atomic and subatomic scales with probabilistic outcomes."
                    ),
                    "url": "https://arxiv.org/abs/1234",
                    "title": "Quantum overview",
                    "source": "omnispider",
                }
            ],
        },
    )
    mock_post.return_value.raise_for_status = MagicMock()

    docs = crawl_for_question("what is quantum mechanics", "physics")
    assert len(docs) == 1
    assert docs[0].url.startswith("https://arxiv.org")
    assert "Quantum mechanics" in docs[0].text


def test_retrieve_triggers_live_crawl_when_corpus_thin(monkeypatch):
    monkeypatch.setenv("AUREON_RAG_CONFIDENCE_THRESHOLD", "0.5")
    monkeypatch.setenv("OMNISPIDER_ENABLED", "1")

    def fake_rebuild(self):
        self._hits = [
            RagHit(1, "h1", "Weak", "Unrelated corpus text.", "test", 0.0),
        ]
        self._matrix = self._vectorizer.fit_transform([h.snippet() for h in self._hits])
        self._built_at = 1.0
        return 1

    monkeypatch.setattr(VectorRAGIndex, "rebuild", fake_rebuild)

    crawled = [
        CrawledDocument(
            text="The Roman Empire fell due to political instability and economic strain over centuries.",
            url="https://www.worldhistory.org/Roman_Empire/",
            title="Roman Empire",
        )
    ]

    with patch("brain.vector_rag._merge_live_crawl") as mock_merge:
        mock_merge.return_value = [
            RagHit(
                -10000,
                "live",
                "Roman Empire",
                crawled[0].text,
                "omnispider:https://www.worldhistory.org/Roman_Empire/",
                0.5,
            )
        ]
        from brain import vector_rag as vr

        monkeypatch.setattr(vr, "_index", None)
        _ctx, hits, _citations = retrieve_with_citations(
            "why did the roman empire fall",
            domain="humanities.history",
            top_k=3,
        )
        mock_merge.assert_called_once()
        assert hits
        assert "Roman Empire" in hits[0].title
