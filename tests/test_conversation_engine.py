"""Conversational intelligence — continuation routing and human search replies."""

from __future__ import annotations

from app.chat_service import chat, is_search_question
from app.session_memory import append_turn
from brain.conversation_engine import is_continuation_message, resolve_message, update_stack_from_turn


def test_is_continuation_message():
    assert is_continuation_message("dive deeper")
    assert is_continuation_message("go deeper")
    assert is_continuation_message("tell me more")
    assert is_continuation_message("keep going")
    assert not is_continuation_message("What happened in the tech world today?")


def test_resolve_message_continuation():
    resolved = resolve_message("dive deeper", "conv-stack-1")
    assert not resolved.is_continuation  # no history yet

    append_turn("conv-stack-1", user="What happened in tech today?", assistant="Some news.")
    update_stack_from_turn(
        "conv-stack-1",
        user="What happened in tech today?",
        payload={"kind": "search_opinion", "sources": ["reuters.com"]},
    )
    resolved = resolve_message("dive deeper", "conv-stack-1")
    assert resolved.is_continuation
    assert "tech today" in resolved.resolved_text.lower()


def test_search_reply_is_human_not_robotic(monkeypatch):
    monkeypatch.setenv("AUREON_WEB_SEARCH_ENABLED", "1")
    monkeypatch.setattr(
        "brain.web_search.search",
        lambda q, **kw: [
            {
                "text": "TechNewsWorld - Google's AI Search Revamp Fuels DuckDuckGo Install Surge.",
                "source": "technewsworld.com",
            },
            {
                "text": "Reuters - SpaceX lands Google AI compute deal ahead of IPO.",
                "source": "reuters.com",
            },
        ],
    )

    result = chat("What happened in the tech world today?", session_id="human-news-1")
    assert result["kind"] == "search_opinion"
    reply = result["reply"].lower()
    assert "based on" not in reply
    assert "zophiel lens" not in reply
    assert "sources:" not in reply
    assert "wikipedia:" not in reply
    assert result.get("sources")
    assert "google" in reply or "spacex" in reply or "duckduckgo" in reply


def test_dive_deeper_continues_thread_not_taxonomy(monkeypatch):
    monkeypatch.setenv("AUREON_WEB_SEARCH_ENABLED", "1")

    calls: list[str] = []

    def mock_search(q, **kw):
        calls.append(q)
        if len(calls) == 1:
            return [
                {
                    "text": "Nvidia raises AI PC stakes with new chips.",
                    "source": "cnbc.com",
                }
            ]
        return [
            {
                "text": "Analysts say the AI PC market will double by 2027.",
                "source": "wired.com",
            }
        ]

    monkeypatch.setattr("brain.web_search.search", mock_search)

    sid = "dive-deeper-1"
    first = chat("What happened in the tech world today?", session_id=sid)
    assert first["kind"] == "search_opinion"

    second = chat("dive deeper", session_id=sid)
    assert second.get("continuation") is True
    assert "biodiversity" not in second["reply"].lower()
    assert ".environmental_science" not in second["reply"].lower()
    assert " → " not in second["reply"]
    assert second["kind"] == "search_opinion"
    assert len(calls) >= 2


def test_religion_spirituality_choice_is_reflection(monkeypatch):
    monkeypatch.setenv("AUREON_WEB_SEARCH_ENABLED", "0")
    q = (
        "if you had to choose religion or spirituality which one would you choose and what domain"
    )
    result = chat(q, session_id="belief-choice-1")
    assert result["kind"] == "reflection"
    reply = result["reply"].lower()
    assert "spiritual" in reply
    assert "religion" in reply
    assert "philosophy" in reply or "ethics" in reply
    assert "biodiversity" not in reply
    assert ".metaphysics" not in result["reply"]


def test_is_search_question_live_news():
    assert is_search_question("What happened in the tech world today?")


def test_rewrite_live_news_query_tech_today():
    from brain.web_search import is_live_news_query, rewrite_live_news_query

    q = "What happened in the tech world today?"
    assert is_live_news_query(q)
    rewritten = rewrite_live_news_query(q)
    assert "technology" in rewritten
    assert "today" in rewritten


def test_anchor_term_passes_parthenon_style_answer():
    from brain.response_quality import audit_response

    q = "Why is the Parthenon historically significant?"
    reply = "Parthenon | Definition, History, Architecture, Columns ...The Parthenon: A Deep Dive."
    assert audit_response(q, reply, {"kind": "predict"}).adequate is True


def test_rejects_forum_date_headlines():
    from brain.opinion_brain import form_human_brief

    junk = [
        {
            "title": "How To Organise Cables: Mar 17, 2026 · Any suggestions on hiding cords?: Mar 26, 2022",
            "text": "How To Organise Cables: Mar 17, 2026 · Any suggestions",
            "source": "forum",
        }
    ]
    brief = form_human_brief("organize cables behind desk", junk)
    assert brief.get("opinion") is None or "2022" not in brief.get("opinion", "")


def test_stargate_project_inquiry(monkeypatch):
    monkeypatch.setenv("AUREON_WEB_SEARCH_ENABLED", "1")
    monkeypatch.setattr(
        "brain.web_search.search",
        lambda q, **kw: [
            {
                "type": "news",
                "title": "Stargate Project was a secret US Army unit for remote viewing research",
                "text": "Stargate Project was a secret US Army unit for remote viewing research",
                "source": "wikipedia.org",
            }
        ],
    )
    q = "Can you tell me about history about the CIA STARGATE PROJECT"
    result = chat(q, session_id="stargate-test-1")
    reply = result["reply"].lower()
    assert "stargate" in reply
    assert "main kinds of history" not in reply
    assert "ancient egyptian history" not in reply


def test_religion_choice_is_reflection(monkeypatch):
    monkeypatch.setenv("AUREON_WEB_SEARCH_ENABLED", "0")
    q = "if you had to choose a religion, what religion would you choose"
    result = chat(q, session_id="religion-pick-1")
    assert result["kind"] == "reflection"
    reply = result["reply"].lower()
    assert "buddhism" in reply or "quaker" in reply
    assert "facebook" not in reply
    assert "may 20, 2022" not in reply
    assert "computer_science" not in str(result.get("classification", "")).lower()


def test_rejects_evergreen_junk_headlines():
    from brain.opinion_brain import form_human_brief

    junk_results = [
        {
            "type": "abstract",
            "text": "What Happened to Tech? The New York Times: Tech history is poorly documented.",
            "source": "nytimes.com",
        },
        {
            "type": "news",
            "title": "Marvell Technology and Flex to join S&P 500 index",
            "text": "Marvell Technology and Flex to join S&P 500 index",
            "source": "CNBC",
        },
        {
            "type": "news",
            "title": "Why a leading AI company wants the world to slow down on the technology",
            "text": "Why a leading AI company wants the world to slow down on the technology",
            "source": "CNN",
        },
    ]
    brief = form_human_brief("What happened in the tech world today?", junk_results)
    reply = brief["opinion"].lower()
    assert "what happened to tech" not in reply
    assert "poorly documented" not in reply
    assert "marvell" in reply or "s&p" in reply
    assert "ai company" in reply or "slow down" in reply
