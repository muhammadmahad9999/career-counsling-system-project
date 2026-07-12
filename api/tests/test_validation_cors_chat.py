import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import sys
import os

# Ensure the api directory is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from auth import get_current_user

client = TestClient(app)

class TestBackendImprovements(unittest.TestCase):
    
    # ── 1. INPUT VALIDATION TESTS ─────────────────────────────────────────────
    def test_validation_invalid_age(self):
        """Test that out-of-range age (e.g. 10) returns 422 Unprocessable Entity."""
        payload = {
            "name": "Test Student",
            "Gender": "Male",
            "Age": 10,  # Invalid: ge=14, le=25
            "City": "Lahore",
            "Stream": "Pre-Engineering",
            "Matric_Marks": 950,
            "FSc_Marks": 850,
            "Marks_Math": 70,
            "Marks_Physics": 70,
            "Marks_Chemistry": 70,
            "Marks_Computer": 70,
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
        response = client.post("/predict", json=payload)
        self.assertEqual(response.status_code, 422)
        errors = response.json().get("detail", [])
        self.assertTrue(any("Age" in str(err) for err in errors), "Expected Age error in validation details")
        print("Success: Predict endpoint correctly rejected out-of-range Age (10).")

    def test_validation_invalid_fsc_marks(self):
        """Test that out-of-range FSc marks (e.g. 1200) returns 422."""
        payload = {
            "name": "Test Student",
            "Gender": "Male",
            "Age": 18,
            "City": "Lahore",
            "Stream": "Pre-Engineering",
            "Matric_Marks": 950,
            "FSc_Marks": 1200,  # Invalid: ge=0, le=1100
            "Marks_Math": 70,
            "Marks_Physics": 70,
            "Marks_Chemistry": 70,
            "Marks_Computer": 70,
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
        response = client.post("/predict", json=payload)
        self.assertEqual(response.status_code, 422)
        errors = response.json().get("detail", [])
        self.assertTrue(any("FSc_Marks" in str(err) for err in errors), "Expected FSc_Marks error in validation details")
        print("Success: Predict endpoint correctly rejected out-of-range FSc_Marks (1200).")

    def test_validation_invalid_subject_marks(self):
        """Test that out-of-range subject marks (e.g. -5, 105) return 422."""
        payload = {
            "name": "Test Student",
            "Gender": "Male",
            "Age": 18,
            "City": "Lahore",
            "Stream": "Pre-Engineering",
            "Matric_Marks": 950,
            "FSc_Marks": 850,
            "Marks_Math": 105,  # Invalid: ge=-1, le=100
            "Marks_Physics": -5,  # Invalid: ge=-1, le=100
            "Marks_Chemistry": 70,
            "Marks_Computer": 70,
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
        response = client.post("/predict", json=payload)
        self.assertEqual(response.status_code, 422)
        errors = response.json().get("detail", [])
        self.assertTrue(any("Marks_Math" in str(err) or "Marks_Physics" in str(err) for err in errors))
        print("Success: Predict endpoint correctly rejected invalid subject marks (105, -5).")

    def test_validation_valid_payload(self):
        """Test that a valid payload succeeds with 200 OK."""
        payload = {
            "name": "Test Student",
            "Gender": "Male",
            "Age": 18,
            "City": "Lahore",
            "Stream": "Pre-Engineering",
            "Matric_Marks": 950,
            "FSc_Marks": 850,
            "Marks_Math": 70,
            "Marks_Physics": 70,
            "Marks_Chemistry": 70,
            "Marks_Computer": 70,
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
        response = client.post("/predict", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertIn("primary_recommendation", response.json())
        print("Success: Predict endpoint accepted valid payload.")

    # ── 2. CORS ORIGIN RESTRICTION TESTS ──────────────────────────────────────
    def test_cors_trusted_origin(self):
        """Test that trusted origins (localhost:5173) are allowed by CORS."""
        headers = {"Origin": "http://localhost:5173"}
        response = client.options("/health", headers=headers)
        self.assertEqual(response.headers.get("access-control-allow-origin"), "http://localhost:5173")
        print("Success: CORS correctly allowed trusted origin (http://localhost:5173).")

    def test_cors_untrusted_origin(self):
        """Test that untrusted origins (untrusted.com) are rejected/not allowed by CORS."""
        headers = {"Origin": "http://untrusted.com"}
        response = client.options("/health", headers=headers)
        self.assertNotEqual(response.headers.get("access-control-allow-origin"), "http://untrusted.com")
        print("Success: CORS correctly blocked untrusted origin (http://untrusted.com).")

    # ── 3. CHAT PERSISTENCE VERIFICATION ──────────────────────────────────────
    @patch("main.get_student_conversations")
    @patch("main.create_conversation")
    @patch("main.save_message")
    @patch("main.search_memory")
    @patch("main.save_memory")
    def test_chat_persistence_authenticated(
        self, mock_save_mem, mock_search_mem, mock_save_msg, mock_create_conv, mock_get_convs
    ):
        """Verify /chat saves message & response to Supabase when user is authenticated."""
        # Setup mocks
        mock_user = MagicMock()
        mock_user.id = "test-student-123"
        app.dependency_overrides[get_current_user] = lambda: mock_user

        mock_get_convs.return_value = []
        mock_create_conv.return_value = "new-conv-uuid"
        mock_search_mem.return_value = "Mocked memory"

        payload = {
            "message": "Can I do Software Engineering?",
            "recommended_career": "Software Engineer",
            "city": "Lahore"
        }
        
        response = client.post("/chat", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["conversation_id"], "new-conv-uuid")

        # Verify database calls
        # 1. create_conversation was called because no active conversation existed
        mock_create_conv.assert_called_once_with("test-student-123", payload["message"])
        
        # 2. save_message called for BOTH user message and assistant reply
        self.assertEqual(mock_save_msg.call_count, 2)
        
        # Check user message arguments
        first_call_args = mock_save_msg.call_args_list[0][1]
        self.assertEqual(first_call_args["conversation_id"], "new-conv-uuid")
        self.assertEqual(first_call_args["student_id"], "test-student-123")
        self.assertEqual(first_call_args["role"], "user")
        self.assertEqual(first_call_args["content"], payload["message"])

        # Check assistant reply arguments
        second_call_args = mock_save_msg.call_args_list[1][1]
        self.assertEqual(second_call_args["conversation_id"], "new-conv-uuid")
        self.assertEqual(second_call_args["student_id"], "test-student-123")
        self.assertEqual(second_call_args["role"], "assistant")
        self.assertIsNotNone(second_call_args["content"])

        # Reset overrides
        app.dependency_overrides.clear()
        print("Success: Authenticated /chat correctly created a conversation and saved both messages.")

if __name__ == "__main__":
    unittest.main()
