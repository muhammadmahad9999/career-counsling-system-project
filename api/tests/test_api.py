"""
=============================================================================
FuturePath — Backend Unit Tests
=============================================================================
Tests all major FastAPI endpoints using pytest + httpx TestClient.

Run from: d:\\career c fyp\\futurepath\\api\\
Command:  pytest tests/ -v
=============================================================================
"""

import pytest
from fastapi.testclient import TestClient

# We import the app — models load at import time, so make sure
# the models/ folder exists and has the .pkl files.
from main import app

client = TestClient(app)


# ─────────────────────────────────────────────────────────────────────────────
# 1. HEALTH CHECK
# ─────────────────────────────────────────────────────────────────────────────

class TestHealth:
    def test_health_returns_ok(self):
        """GET /health should return status ok."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_models_loaded(self):
        """GET /health should confirm models are loaded."""
        data = response = client.get("/health").json()
        assert data["status"] == "ok"
        assert data["models_loaded"] is True
        assert data["careers"] > 0


# ─────────────────────────────────────────────────────────────────────────────
# 2. OPTIONS
# ─────────────────────────────────────────────────────────────────────────────

class TestOptions:
    def test_options_returns_all_fields(self):
        """GET /options should return all dropdown fields."""
        response = client.get("/options")
        assert response.status_code == 200
        data = response.json()
        assert "genders" in data
        assert "cities" in data
        assert "streams" in data
        assert "activities" in data
        assert "models" in data

    def test_options_genders(self):
        """Genders should be Male and Female."""
        data = client.get("/options").json()
        assert "Male" in data["genders"]
        assert "Female" in data["genders"]

    def test_options_streams(self):
        """Streams should include all FSc streams."""
        data = client.get("/options").json()
        assert "Pre-Engineering" in data["streams"]
        assert "Pre-Medical" in data["streams"]

    def test_options_cities_not_empty(self):
        """Cities list should not be empty."""
        data = client.get("/options").json()
        assert len(data["cities"]) > 0


# ─────────────────────────────────────────────────────────────────────────────
# 3. PREDICT
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_STUDENT = {
    "name": "Test Student",
    "Gender": "Male",
    "Age": 18,
    "City": "Lahore",
    "Stream": "Pre-Engineering",
    "Matric_Marks": 950,
    "FSc_Marks": 480,
    "Marks_Math": 90,
    "Marks_Physics": 85,
    "Marks_Computer": 88,
    "Marks_Biology": 50,
    "Aptitude_Logic": 75,
    "Aptitude_Verbal": 60,
    "Aptitude_Spatial": 70,
    "Aptitude_Math": 80,
    "Psych_Openness": 7.0,
    "Psych_Conscientiousness": 8.0,
    "Psych_Extraversion": 5.0,
    "Psych_Agreeableness": 6.0,
    "Psych_Neuroticism": 3.0,
    "Extracurricular_Activity": "Robotics Club",
    "Interest_Text": "I love computers and programming",
    "Sentiment_Label": "Positive",
    "Model_Name": "Hybrid",
}


class TestPredict:
    def test_predict_returns_200(self):
        """POST /predict should return 200 with a valid payload."""
        response = client.post("/predict", json=SAMPLE_STUDENT)
        assert response.status_code == 200

    def test_predict_returns_primary_recommendation(self):
        """POST /predict should return a primary career recommendation."""
        data = client.post("/predict", json=SAMPLE_STUDENT).json()
        assert "primary_recommendation" in data
        assert "career" in data["primary_recommendation"]
        assert len(data["primary_recommendation"]["career"]) > 0

    def test_predict_returns_three_recommendations(self):
        """POST /predict should return exactly 3 ranked recommendations."""
        data = client.post("/predict", json=SAMPLE_STUDENT).json()
        assert len(data["recommendations"]) == 3

    def test_predict_probability_is_valid(self):
        """Probability values should be between 0 and 1."""
        data = client.post("/predict", json=SAMPLE_STUDENT).json()
        for rec in data["recommendations"]:
            assert 0.0 <= rec["probability"] <= 1.0

    def test_predict_ranking_is_sorted(self):
        """Recommendations should be sorted by rank 1, 2, 3."""
        data = client.post("/predict", json=SAMPLE_STUDENT).json()
        ranks = [r["rank"] for r in data["recommendations"]]
        assert ranks == [1, 2, 3]

    def test_predict_stacking_model(self):
        """POST /predict with Stacking model should work."""
        payload = {**SAMPLE_STUDENT, "Model_Name": "Stacking"}
        response = client.post("/predict", json=payload)
        assert response.status_code == 200

    def test_predict_ensemble_model(self):
        """POST /predict with Ensemble model should work."""
        payload = {**SAMPLE_STUDENT, "Model_Name": "Ensemble"}
        response = client.post("/predict", json=payload)
        assert response.status_code == 200

    def test_predict_female_student(self):
        """POST /predict should work for female students too."""
        payload = {**SAMPLE_STUDENT, "Gender": "Female", "Stream": "Pre-Medical"}
        response = client.post("/predict", json=payload)
        assert response.status_code == 200

    def test_predict_karachi_city(self):
        """POST /predict should handle different cities."""
        payload = {**SAMPLE_STUDENT, "City": "Karachi"}
        response = client.post("/predict", json=payload)
        assert response.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# 4. ROADMAP
# ─────────────────────────────────────────────────────────────────────────────

class TestRoadmap:
    def test_roadmap_valid_career(self):
        """GET /roadmap?career=... should return roadmap data for a valid career."""
        # First get a predicted career, then test its roadmap
        data = client.post("/predict", json=SAMPLE_STUDENT).json()
        career = data["primary_recommendation"]["career"]
        response = client.get(f"/roadmap?career={career}")
        assert response.status_code == 200

    def test_roadmap_invalid_career_returns_404(self):
        """GET /roadmap for a non-existent career should return 404."""
        response = client.get("/roadmap?career=XYZ_Fake_Career_12345")
        assert response.status_code == 404

    def test_roadmap_has_required_fields(self):
        """Roadmap response should have description, steps, and skills."""
        data = client.post("/predict", json=SAMPLE_STUDENT).json()
        career = data["primary_recommendation"]["career"]
        roadmap = client.get(f"/roadmap?career={career}").json()
        assert "career" in roadmap
        assert "description" in roadmap


# ─────────────────────────────────────────────────────────────────────────────
# 5. SHAP EXPLAINABILITY
# ─────────────────────────────────────────────────────────────────────────────

class TestShap:
    def test_shap_returns_top_features(self):
        """POST /shap should return top 6 grouped feature importances."""
        response = client.post("/shap", json=SAMPLE_STUDENT)
        assert response.status_code == 200
        data = response.json()
        assert "top_features" in data
        assert len(data["top_features"]) == 6

    def test_shap_feature_has_name_and_value(self):
        """Each SHAP feature should have 'feature' and 'value' keys."""
        data = client.post("/shap", json=SAMPLE_STUDENT).json()
        for feature in data["top_features"]:
            assert "feature" in feature
            assert "value" in feature

    def test_shap_predicted_class_is_int(self):
        """SHAP predicted class should be an integer."""
        data = client.post("/shap", json=SAMPLE_STUDENT).json()
        assert isinstance(data["predicted_class"], int)


# ─────────────────────────────────────────────────────────────────────────────
# 6. CHAT (Rule-based fallback, no GROQ key needed)
# ─────────────────────────────────────────────────────────────────────────────

class TestChat:
    def test_chat_returns_response(self):
        """POST /chat should always return a response string."""
        payload = {
            "message": "What skills do I need for Software Engineering?",
            "recommended_career": "Software Engineer",
            "city": "Lahore",
        }
        response = client.post("/chat", json=payload)
        assert response.status_code == 200
        assert "response" in response.json()
        assert len(response.json()["response"]) > 0

    def test_chat_roadmap_question(self):
        """Chat should answer roadmap questions."""
        payload = {
            "message": "Give me a roadmap",
            "recommended_career": "Software Engineer",
        }
        response = client.post("/chat", json=payload)
        assert response.status_code == 200

    def test_chat_scholarship_question(self):
        """Chat should handle scholarship questions."""
        payload = {
            "message": "What scholarships are available?",
            "recommended_career": "Software Engineer",
        }
        response = client.post("/chat", json=payload)
        assert response.status_code == 200

    def test_chat_university_question(self):
        """Chat should handle university questions."""
        payload = {
            "message": "Which universities should I apply to?",
            "recommended_career": "Software Engineer",
        }
        response = client.post("/chat", json=payload)
        assert response.status_code == 200

    def test_chat_no_career_context(self):
        """Chat should work even without a recommended_career."""
        payload = {"message": "How do I choose a career?"}
        response = client.post("/chat", json=payload)
        assert response.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# 7. SAVE SESSION
# ─────────────────────────────────────────────────────────────────────────────

class TestSaveSession:
    def test_save_session_returns_saved(self):
        """POST /save_session should return status: saved."""
        # First get a prediction to save
        pred_data = client.post("/predict", json=SAMPLE_STUDENT).json()
        payload = {
            "student": SAMPLE_STUDENT,
            "prediction": pred_data,
        }
        response = client.post("/save_session", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "saved"


# ─────────────────────────────────────────────────────────────────────────────
# 8. PDF EXPORT
# ─────────────────────────────────────────────────────────────────────────────

class TestExportPdf:
    def test_export_pdf_returns_pdf(self):
        """POST /export_pdf should return a PDF binary file."""
        pred_data = client.post("/predict", json=SAMPLE_STUDENT).json()
        payload = {
            "student": SAMPLE_STUDENT,
            "prediction": pred_data,
        }
        response = client.post("/export_pdf", json=payload)
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        # A valid PDF starts with the %PDF magic bytes
        assert response.content[:4] == b"%PDF"


# ─────────────────────────────────────────────────────────────────────────────
# 9. PROFILE & CHAT INTEGRATION
# ─────────────────────────────────────────────────────────────────────────────

from unittest.mock import patch, MagicMock

class DummyUser:
    id = "dummy-student-id-12345"

class TestProfileIntegration:
    @patch("main.update_student_profile")
    @patch("main.save_memory")
    @patch("main.get_student_context_for_llm")
    def test_predict_and_chat_with_auth(self, mock_get_context, mock_save_memory, mock_update_profile):
        """Verify that prediction updates profile/memory and chat injects context when authenticated."""
        from auth import get_current_user
        
        # 1. Setup mock returns
        mock_get_context.return_value = "FSc stream: Pre-Engineering\nCity: Lahore"
        
        # Override dependency
        app.dependency_overrides[get_current_user] = lambda: DummyUser()
        
        try:
            # 2. Call /predict
            response = client.post("/predict", json=SAMPLE_STUDENT)
            assert response.status_code == 200
            
            # Assert update_student_profile was called with converted percentages
            mock_update_profile.assert_called_once()
            args, kwargs = mock_update_profile.call_args
            assert args[0] == "dummy-student-id-12345"
            assert args[1]["fsc_stream"] == "Pre-Engineering"
            assert "target_career" in args[1]
            
            # Assert save_memory was called to store assessment results
            mock_save_memory.assert_called_once()
            mem_args, mem_kwargs = mock_save_memory.call_args
            assert mem_args[0] == "dummy-student-id-12345"
            assert "Aptitude Scores" in mem_args[1][0]["content"]
            
            # 3. Call /chat
            chat_payload = {
                "message": "Tell me more about the roadmap",
                "recommended_career": "Software Engineer",
                "city": "Lahore"
            }
            # We mock the Groq API call inside main.py if needed, or let it fallback
            chat_resp = client.post("/chat", json=chat_payload)
            assert chat_resp.status_code == 200
            
            # Assert get_student_context_for_llm was called to pull profile context
            mock_get_context.assert_called_once_with("dummy-student-id-12345")
            
        finally:
            # Clean up override
            app.dependency_overrides.pop(get_current_user, None)


# ─────────────────────────────────────────────────────────────────────────────
# 10. WEB SEARCH & SCRAPING TOOLS
# ─────────────────────────────────────────────────────────────────────────────

class TestWebSearchTools:
    @patch("scrapers.web_tools.httpx.get")
    def test_search_duckduckgo(self, mock_get):
        """Verify search_duckduckgo correctly parses result__a links."""
        from scrapers.web_tools import search_duckduckgo
        
        # Mock DuckDuckGo HTML response
        mock_html = """
        <html>
        <body>
            <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fstudy&rut=123">Study Guide</a>
            <div class="result__snippet">Get the best study guide for exams.</div>
            
            <a class="result__a" href="https://test.com/notes">Subject Notes</a>
            <div class="result__snippet">Free notes for matric.</div>
        </body>
        </html>
        """
        mock_get.return_value = MagicMock(status_code=200, text=mock_html)
        
        res = search_duckduckgo("FSc study material")
        assert len(res) == 2
        assert res[0]["title"] == "Study Guide"
        assert res[0]["url"] == "https://example.com/study"
        assert res[0]["snippet"] == "Get the best study guide for exams."
        assert res[1]["title"] == "Subject Notes"
        assert res[1]["url"] == "https://test.com/notes"
        assert res[1]["snippet"] == "Free notes for matric."

    @patch("scrapers.web_tools.httpx.get")
    def test_web_scrape_paragraphs(self, mock_get):
        """Verify web_scrape extracts headers and long paragraph blocks."""
        from scrapers.web_tools import web_scrape
        
        mock_html = """
        <html>
        <body>
            <h1>Engineering Syllabuses</h1>
            <p>This is a long syllabus paragraph detailing the courses needed for engineering.</p>
            <p>Short</p> <!-- skipped (< 20 chars) -->
            <li>Core Math 1: Calculus and analytical geometry.</li>
        </body>
        </html>
        """
        mock_get.return_value = MagicMock(status_code=200, text=mock_html)
        
        scraped = web_scrape("https://example.com/syllabus")
        assert "H1: Engineering Syllabuses" in scraped
        assert "P: This is a long syllabus paragraph" in scraped
        assert "LI: Core Math 1" in scraped
        assert "Short" not in scraped

    @patch("main._execute_tool")
    def test_chat_with_tool_calling(self, mock_execute):
        """Verify `/chat` handles tool calls from Groq and performs second pass."""
        from main import app
        
        mock_execute.return_value = {"results": [{"title": "Course Link", "url": "https://coursera.org"}]}
        
        # Mock Groq client and responses
        with patch("groq.Groq") as mock_groq_class:
            mock_client = MagicMock()
            mock_groq_class.return_value = mock_client
            
            # First pass returns a tool call
            mock_tool_call = MagicMock()
            mock_tool_call.id = "call_abc123"
            mock_tool_call.function.name = "google_search"
            mock_tool_call.function.arguments = '{"query": "study courses"}'
            
            mock_first_msg = MagicMock()
            mock_first_msg.tool_calls = [mock_tool_call]
            mock_first_msg.content = None
            
            # Second pass returns final textual answer
            mock_second_msg = MagicMock()
            mock_second_msg.tool_calls = None
            mock_second_msg.content = "Here is the course link: https://coursera.org"
            
            # Mock the completions.create behavior
            mock_first_choice = MagicMock()
            mock_first_choice.message = mock_first_msg
            mock_first_completion = MagicMock(choices=[mock_first_choice])
            
            mock_second_choice = MagicMock()
            mock_second_choice.message = mock_second_msg
            mock_second_completion = MagicMock(choices=[mock_second_choice])
            
            mock_client.chat.completions.create.side_effect = [
                mock_first_completion,
                mock_second_completion
            ]
            
            # Inject key so Groq block triggers
            with patch.dict("os.environ", {"GROQ_API_KEY": "dummy-key"}):
                response = client.post("/chat", json={
                    "message": "Find me courses online",
                    "recommended_career": "Software Engineer"
                })
                
                assert response.status_code == 200
                assert response.json()["response"] == "Here is the course link: https://coursera.org"
                mock_execute.assert_called_once_with("google_search", {"query": "study courses"})


# ─────────────────────────────────────────────────────────────────────────────
# 11. LOCAL WHISPER VOICE TRANSCRIPTION
# ─────────────────────────────────────────────────────────────────────────────

class TestVoiceTranscribe:
    @patch("main.transcribe_audio_bytes")
    def test_voice_transcribe_success(self, mock_transcribe):
        """POST /voice should return transcribed text and language."""
        mock_transcribe.return_value = {
            "text": "Hello, how are you?",
            "language": "en",
            "segments": [{"start": 0.0, "end": 2.0, "text": "Hello, how are you?"}]
        }
        
        response = client.post(
            "/voice",
            files={"audio": ("voice.wav", b"dummy-audio-bytes", "audio/wav")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "Hello, how are you?"
        assert data["language"] == "en"
        assert len(data["segments"]) == 1
        mock_transcribe.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# 12. FSC STREAM PREDICTION MASK CONSTRAINTS
# ─────────────────────────────────────────────────────────────────────────────

class TestPredictionStreamConstraint:
    def test_predict_arts_constrained(self):
        """Arts student should only receive Arts recommendations (e.g. Design, Psychology, etc.)."""
        payload = {**SAMPLE_STUDENT, "Stream": "Arts"}
        data = client.post("/predict", json=payload).json()
        allowed_arts = [
            "BBA (Business Admin)", "BS Accounting & Finance", "BS Animation & VFX",
            "BS English Literature", "BS Fashion Design", "BS Graphic Design",
            "BS International Relations", "BS Marketing", "BS Psychology",
            "Digital Marketing (BBA / BS Marketing)", "LLB (Lawyer)"
        ]
        for rec in data["recommendations"]:
            assert rec["career"] in allowed_arts

    def test_predict_ics_constrained(self):
        """ICS student should only receive ICS recommendations (CS, AI, Ethical Hacking, Software Eng, etc.)."""
        payload = {**SAMPLE_STUDENT, "Stream": "ICS"}
        data = client.post("/predict", json=payload).json()
        allowed_ics = [
            "BS Artificial Intelligence", "BS Computer Science", "BS Cyber Security",
            "BS Data Science", "BS Game Development",
            "Ethical Hacking (BS Cyber Security / Computer Science)",
            "Software Engineering",
            "Web Development (BS Computer Science / Software Engineering)"
        ]
        for rec in data["recommendations"]:
            assert rec["career"] in allowed_ics

    def test_predict_display_name_mapping(self):
        """Verify display career name mapping for roles (e.g. Web Development -> Web Development (BS CS / SE))."""
        # Set interests to guide toward Web Dev / CS
        payload = {**SAMPLE_STUDENT, "Stream": "ICS", "Interest_Text": "web development website development HTML CSS"}
        data = client.post("/predict", json=payload).json()
        careers = [rec["career"] for rec in data["recommendations"]]
        
        # Check that if Web Development is suggested, it uses the mapped name
        for c in careers:
            if "Web Development" in c:
                assert c == "Web Development (BS Computer Science / Software Engineering)"



