"""
=============================================================================
FuturePath — ML Pipeline Integration Tests
=============================================================================
Tests the ML models directly (without the API layer).
=============================================================================
"""

import os
import pytest
import pandas as pd
import joblib
from main import app, _build_feature_df, xgb_model, stacking_model, voting_model, career_map, feature_names

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_DIR = os.path.join(ROOT, "models")

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
    "Marks_Chemistry": 75,
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
    "Interest_R": 80.0,
    "Interest_I": 70.0,
    "Interest_A": 40.0,
    "Interest_S": 60.0,
    "Interest_E": 75.0,
    "Interest_C": 50.0,
    "Extracurricular_Activity": "Robotics Club",
    "Interest_Text": "I love computers and programming",
    "Sentiment_Label": "Positive",
    "Model_Name": "Hybrid",
}

class TestModelFiles:
    def test_xgboost_model_exists(self):
        assert os.path.exists(os.path.join(MODEL_DIR, "xgboost_model.pkl"))

    def test_stacking_model_exists(self):
        assert os.path.exists(os.path.join(MODEL_DIR, "stacking_model.pkl"))

    def test_voting_model_exists(self):
        assert os.path.exists(os.path.join(MODEL_DIR, "voting_model.pkl"))

    def test_scaler_exists(self):
        assert os.path.exists(os.path.join(MODEL_DIR, "scaler.pkl"))

    def test_career_label_map_exists(self):
        assert os.path.exists(os.path.join(MODEL_DIR, "career_label_map.pkl"))

    def test_feature_names_exists(self):
        assert os.path.exists(os.path.join(MODEL_DIR, "feature_names.pkl"))

class TestFeatureDimensions:
    def test_feature_names_count(self):
        assert len(feature_names) == 27

class TestPredictionOutput:
    def test_xgb_predict_proba(self):
        df = _build_feature_df(SAMPLE_STUDENT)
        proba = xgb_model.predict_proba(df)
        assert proba.shape[1] == len(career_map)

    def test_stacking_predict_proba(self):
        df = _build_feature_df(SAMPLE_STUDENT)
        proba = stacking_model.predict_proba(df)
        assert proba.shape[1] == len(career_map)

    def test_voting_predict_proba(self):
        df = _build_feature_df(SAMPLE_STUDENT)
        proba = voting_model.predict_proba(df)
        assert proba.shape[1] == len(career_map)

    def test_probabilities_sum_to_one(self):
        df = _build_feature_df(SAMPLE_STUDENT)
        proba = xgb_model.predict_proba(df)[0]
        assert abs(proba.sum() - 1.0) < 1e-5
