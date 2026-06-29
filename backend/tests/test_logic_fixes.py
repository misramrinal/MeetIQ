import unittest
from datetime import date
from unittest.mock import Mock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import ActionItem, Decision, Meeting
from app.routers.meetings import _parse_range_header
from app.database import Base
from app.services import rag_service


class SearchLogicTests(unittest.TestCase):
    def test_greeting_does_not_enter_rag(self):
        with patch.object(rag_service, "chat") as chat:
            result = rag_service.search_and_answer("hi", db=Mock())

        chat.assert_not_called()
        self.assertEqual(result["sources"], [])
        self.assertEqual(result["status"], rag_service.STATUS_NON_SEARCH)
        self.assertEqual(result["confidence"], 0.0)
        self.assertIn("specific question", result["answer"])

    def test_low_evidence_does_not_enter_llm(self):
        weak_hit = [{
            "segment_id": "seg-1",
            "meeting_id": "m-1",
            "meeting_title": "Unrelated",
            "speaker": "Speaker",
            "text": "All right.",
            "start_time": 1.0,
            "end_time": 2.0,
            "score": 0.61,
            "retrieval": "vector",
        }]

        with patch.object(rag_service, "structured_search", return_value=[]), \
             patch.object(rag_service, "hybrid_search_transcripts", return_value=weak_hit), \
             patch.object(rag_service, "chat") as chat:
            result = rag_service.search_and_answer("architecture decision", db=Mock())

        chat.assert_not_called()
        self.assertEqual(result["answer"], rag_service.NO_RELEVANT_ANSWER)
        self.assertEqual(result["status"], rag_service.STATUS_NO_EVIDENCE)
        self.assertEqual(result["sources"], [])

    def test_rrf_dedupes_qdrant_segment_id_with_sql_id(self):
        fused = rag_service.reciprocal_rank_fusion([
            [{"segment_id": "seg-1", "text": "Use PostgreSQL", "score": 0.7}],
            [{"id": "seg-1", "text": "Use PostgreSQL", "score": 0.9}],
        ])

        self.assertEqual(len(fused), 1)
        self.assertEqual(fused[0]["id"], "seg-1")
        self.assertEqual(fused[0]["score"], 0.9)

    def test_structured_decisions_and_actions_are_search_sources(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        db = Session()
        try:
            meeting = Meeting(
                id="m-1",
                title="Planning",
                recording_path="recording.mp4",
                status="done",
            )
            db.add(meeting)
            db.add(Decision(
                id="d-1",
                meeting_id="m-1",
                text="Use PostgreSQL as the primary database.",
                made_by="Alice",
                timestamp=12.0,
                confidence=0.9,
            ))
            db.add(ActionItem(
                id="a-1",
                meeting_id="m-1",
                text="Prepare database migration plan.",
                owner="Bob",
                due_date=date(2026, 6, 30),
                timestamp=18.0,
                status="open",
            ))
            db.commit()

            with patch.object(rag_service, "hybrid_search_transcripts", return_value=[]), \
                 patch.object(rag_service, "chat", return_value="PostgreSQL was selected. [1]"):
                result = rag_service.search_and_answer("database decision action", db=db)

            self.assertEqual(result["status"], rag_service.STATUS_ANSWERED)
            self.assertGreater(result["confidence"], 0.0)
            self.assertEqual({source["type"] for source in result["sources"]}, {"decision", "action_item"})

            with patch.object(rag_service, "hybrid_search_transcripts", return_value=[]), \
                 patch.object(rag_service, "chat", return_value="The decision was PostgreSQL. [1]"):
                decision_result = rag_service.search_and_answer("what decisions were made", db=db)

            self.assertEqual(decision_result["status"], rag_service.STATUS_ANSWERED)
            self.assertEqual(decision_result["sources"][0]["type"], "decision")
        finally:
            db.close()


    def test_single_term_intent_query_returns_no_evidence(self):
        """R4 fix: bare intent word ("action") with <2 terms must not produce evidence."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        db = Session()
        try:
            meeting = Meeting(
                id="m-r4", title="Sprint Planning", recording_path="r.mp4", status="done"
            )
            db.add(meeting)
            db.add(ActionItem(
                id="a-r4", meeting_id="m-r4",
                text="Update the deployment scripts", owner="Alice",
                timestamp=5.0, status="open",
            ))
            db.commit()

            with patch.object(rag_service, "hybrid_search_transcripts", return_value=[]), \
                 patch.object(rag_service, "chat") as chat:
                result = rag_service.search_and_answer("action", db=db)

            chat.assert_not_called()
            self.assertIn(result["status"], {
                rag_service.STATUS_NO_EVIDENCE,
                rag_service.STATUS_NON_SEARCH,
            })
        finally:
            db.close()

    def test_partial_keyword_match_scores_low_and_fails_gate(self):
        """R2 fix: a vector-only result scoring 0.17 must not pass the evidence gate
        when the text contains none of the query terms (no direct term evidence)."""
        # Query has 5 meaningful terms; result text contains none of them.
        # score = 0.85 * (1/5) = 0.17 — below 0.72 threshold.
        # retrieval="vector" so has_keyword_hit=False, has_direct_terms=False → gate rejects.
        weak_vector_hit = [{
            "segment_id": "seg-partial",
            "meeting_id": "m-2",
            "meeting_title": "Design Review",
            "speaker": "Bob",
            "text": "Okay, let us move on to the next topic.",
            "start_time": 3.0,
            "end_time": 4.0,
            "score": round(0.85 * (1 / 5), 4),  # 0.17 — simulates 1-of-5 coverage
            "retrieval": "vector",
        }]
        with patch.object(rag_service, "structured_search", return_value=[]), \
             patch.object(rag_service, "hybrid_search_transcripts", return_value=weak_vector_hit), \
             patch.object(rag_service, "chat") as chat:
            result = rag_service.search_and_answer(
                "architecture scalability performance latency caching", db=Mock()
            )

        chat.assert_not_called()
        self.assertEqual(result["status"], rag_service.STATUS_NO_EVIDENCE)

    def test_full_coverage_keyword_match_passes_gate(self):
        """R2 fix: a 5-of-5-term keyword hit must still pass the evidence gate."""
        full_hit = [{
            "segment_id": "seg-full",
            "meeting_id": "m-3",
            "meeting_title": "Architecture Review",
            "speaker": "Carol",
            "text": "We chose PostgreSQL for the database schema migration plan.",
            "start_time": 10.0,
            "end_time": 12.0,
            "score": 0.85,  # full coverage → min(0.85, 0.85 * 1.0)
            "retrieval": "keyword",
        }]
        with patch.object(rag_service, "structured_search", return_value=[]), \
             patch.object(rag_service, "hybrid_search_transcripts", return_value=full_hit), \
             patch.object(rag_service, "chat", return_value="PostgreSQL was chosen. [1]"):
            result = rag_service.search_and_answer(
                "PostgreSQL database schema migration plan", db=Mock()
            )

        self.assertEqual(result["status"], rag_service.STATUS_ANSWERED)
        self.assertGreater(result["confidence"], 0.0)

    def test_rrf_dedup_handles_structured_id_prefix(self):
        """R3 fix: 'decision:<uuid>' and source_id='<uuid>' are the same record — one result."""
        uuid = "aaaaaaaa-0000-0000-0000-000000000001"
        list_a = [{"id": f"decision:{uuid}", "text": "Use PostgreSQL", "score": 0.9,
                   "type": "decision", "retrieval": "structured"}]
        list_b = [{"source_id": uuid, "id": f"decision:{uuid}",
                   "text": "Use PostgreSQL", "score": 0.85,
                   "type": "decision", "retrieval": "structured"}]

        fused = rag_service.reciprocal_rank_fusion([list_a, list_b])

        self.assertEqual(len(fused), 1, "Same decision must appear only once after RRF dedup")
        self.assertEqual(fused[0]["score"], 0.9, "Highest original score should be kept")
    def test_standard_range(self):
        self.assertEqual(_parse_range_header("bytes=10-19", 100), (10, 19))

    def test_suffix_range(self):
        self.assertEqual(_parse_range_header("bytes=-10", 100), (90, 99))

    def test_open_ended_range(self):
        self.assertEqual(_parse_range_header("bytes=95-", 100), (95, 99))

    def test_invalid_range(self):
        self.assertIsNone(_parse_range_header("bytes=150-200", 100))
        self.assertIsNone(_parse_range_header("bytes=20-10", 100))


if __name__ == "__main__":
    unittest.main()
