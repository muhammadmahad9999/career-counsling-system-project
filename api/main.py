"""
=============================================================================
FuturePath — FastAPI Backend  (api/main.py)
=============================================================================
Endpoints:
  GET  /health          — liveness probe
  GET  /options         — dropdown values for the Wizard
  POST /predict         — career prediction (XGBoost / Stacking / Hybrid)
  GET  /roadmap?career= — roadmap data from Excel Reference Roadmaps sheet
  POST /chat            — AI counselor using Groq (llama-3.3-70b-versatile)
  POST /shap            — SHAP explanations for XGBoost model
  POST /save_session    — persist prediction to SQLite
  POST /export_pdf      — generate and return PDF report
=============================================================================
"""

import os, re, json, sqlite3, io, datetime, traceback
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", ".env"))

import numpy as np
import pandas as pd
import joblib
import shap


from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List

# ── Integrated modules ────────────────────────────────────────────────────────
from system_prompt import build_system_prompt
from memory import save_memory, search_memory, get_all_memories
from voice import transcribe_audio_bytes
from auth import register_student, login_student, get_google_login_url, get_current_user
from student_db import get_student_profile, update_student_profile, get_student_context_for_llm
from chat_db import (create_conversation, save_message,
                     get_conversation_history, get_student_conversations,
                     get_conversation_for_student, save_resource)
from audio_storage import upload_voice_audio

# Sentence Transformer for live embedding generation
from sentence_transformers import SentenceTransformer

# PDF generation
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm

# ── paths ─────────────────────────────────────────────────────────────────────
ROOT       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR  = os.path.join(ROOT, "models")
DATA_DIR   = os.path.join(ROOT, "data")
DB_PATH    = os.path.join(DATA_DIR, "career_counseling.db")
EXCEL_PATH = os.path.join(DATA_DIR, "career_counseling_full_dataset.xlsx")

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(title="FuturePath Career Counseling API", version="2.0")

frontend_origins = [
    os.environ.get("FRONTEND_URL", "http://localhost:5173").rstrip("/"),
    "http://127.0.0.1:5173"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Custom wrapper classes for deserialized dict-based models ─────────────────
class CustomStackingPredictor:
    def __init__(self, model_dict):
        self.base_estimators = model_dict["base_estimators"]
        self.meta_learner = model_dict["meta_learner"]
        
    def predict_proba(self, X):
        lgbm_proba = self.base_estimators["lgbm"].predict_proba(X)
        xgb_proba = self.base_estimators["xgb"].predict_proba(X)
        cat_proba = self.base_estimators["cat"].predict_proba(X)
        combined = np.hstack([lgbm_proba, xgb_proba, cat_proba])
        return self.meta_learner.predict_proba(combined)

class CustomVotingPredictor:
    def __init__(self, model_dict):
        self.models = model_dict
        
    def predict_proba(self, X):
        lgbm_proba = self.models["lgbm"].predict_proba(X)
        xgb_proba = self.models["xgb"].predict_proba(X)
        cat_proba = self.models["cat"].predict_proba(X)
        return (lgbm_proba + xgb_proba + cat_proba) / 3.0

# ── load models at startup ────────────────────────────────────────────────────
print("[STARTUP] Loading ML models …")
xgb_model      = joblib.load(os.path.join(MODEL_DIR, "xgboost_model.pkl"))
stacking_model = CustomStackingPredictor(joblib.load(os.path.join(MODEL_DIR, "stacking_model.pkl")))
voting_model   = CustomVotingPredictor(joblib.load(os.path.join(MODEL_DIR, "voting_model.pkl")))
scaler         = joblib.load(os.path.join(MODEL_DIR, "scaler.pkl"))
career_map     = joblib.load(os.path.join(MODEL_DIR, "career_label_map.pkl"))  # int -> name
feature_names  = joblib.load(os.path.join(MODEL_DIR, "feature_names.pkl"))
split_info     = joblib.load(os.path.join(MODEL_DIR, "split_info.pkl"))
categorical_mappings = joblib.load(os.path.join(MODEL_DIR, "categorical_mappings.pkl"))

# Invert career_map: name -> int (for reference)
career_name_to_id = {v: k for k, v in career_map.items()}
career_names_list = sorted(career_map.values())
print(f"[STARTUP] Loaded {len(career_map)} career classes")

print("[STARTUP] Loading SentenceTransformer …")
embedder = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
print("[STARTUP] Embedder ready")

# ── load reference data from Excel ────────────────────────────────────────────
print("[STARTUP] Loading Excel reference data …")
xl = pd.ExcelFile(EXCEL_PATH)

def _parse_sheet(sheet_name: str) -> pd.DataFrame:
    """Parse a sheet that has a title row 0, metadata row 1, and header row 2."""
    df = xl.parse(sheet_name, header=2)
    df = df.dropna(how="all")
    return df

salary_df      = _parse_sheet("Salary Market Data")
scholarship_df = _parse_sheet("Scholarships")
skills_df      = _parse_sheet("Skill Requirements")
courses_df     = _parse_sheet("Online Courses")
uni_df         = _parse_sheet("Universities")
roadmap_df     = _parse_sheet("Reference Roadmaps")

# Standardize roadmap column names
roadmap_df.columns = [c.strip() for c in roadmap_df.columns]
print(f"[STARTUP] Roadmap sheet cols: {list(roadmap_df.columns)}")
print(f"[STARTUP] Roadmap rows: {len(roadmap_df)}")

# ── SHAP explainer (XGBoost only — fast TreeExplainer) ────────────────────────
print("[STARTUP] Building SHAP explainer …")
try:
    shap_explainer = shap.TreeExplainer(xgb_model)
except Exception as e:
    print(f"[STARTUP] Warning: Could not initialize SHAP explainer: {e}")
    shap_explainer = None
print("[STARTUP] All startup complete")

# ── init market trends cache table in SQLite ──────────────────────────────────
try:
    with sqlite3.connect(DB_PATH) as _db:
        _db.execute("""
            CREATE TABLE IF NOT EXISTS market_trends_cache (
                career       TEXT PRIMARY KEY,
                data_json    TEXT NOT NULL,
                fetched_at   TEXT NOT NULL
            )
        """)
        _db.commit()
    print("[STARTUP] market_trends_cache table ready")
except Exception as _e:
    print(f"[STARTUP] Warning: Could not create market_trends_cache table: {_e}")

# ── helpers ───────────────────────────────────────────────────────────────────
NUMERIC_COLS = [
    "Age", "Matric_Marks", "FSc_Marks",
    "Marks_Math", "Marks_Physics", "Marks_Computer", "Marks_Biology",
    "Aptitude_Logic", "Aptitude_Verbal", "Aptitude_Spatial", "Aptitude_Math",
    "Psych_Openness", "Psych_Conscientiousness", "Psych_Extraversion",
    "Psych_Agreeableness", "Psych_Neuroticism",
]

# Encoding maps (must match training preprocessing)
GENDER_MAP  = {"Male": 0, "Female": 1}
CITY_MAP    = {"Faisalabad": 0, "Gujranwala": 1, "Hyderabad": 2, "Islamabad": 3,
               "Karachi": 4, "Lahore": 5, "Multan": 6, "Peshawar": 7,
               "Quetta": 8, "Rawalpindi": 9, "Sialkot": 10, "Sukkur": 11}
STREAM_MAP  = {"Arts": 0, "ICS": 1, "Pre-Engineering": 2, "Pre-Medical": 3}
ACTIVITY_MAP= {"Debate": 0, "None": 1, "Quran Hifz": 2, "Robotics Club": 3,
               "Scouting": 4, "Social Work": 5, "Sports": 6,
               "Student Council": 7, "Tutor": 8}
SENTIMENT_MAP = {"Demotivated": 0, "Neutral": 1, "Positive": 2}

def _get_roadmap_data(career_name: str) -> dict:
    """Fetch roadmap from Excel sheet for a given career."""
    df = roadmap_df.copy()
    career_col = "Career Name"
    if career_col not in df.columns:
        career_col = df.columns[0]

    # Pre-process the query using standard synonyms
    synonyms = {
        "pakistan army/navy/paf": "Pakistan Army (Officer)",
        "pilot (aviation)": "Pakistan Air Force (GD Pilot)",
        "dpt (physical therapy)": "DPT (Physical Therapist)",
        "dvm (veterinary)": "DVM (Veterinary Doctor)",
        "llb (lawyer)": "LLB (Law)",
        "bs english literature": "BS English",
        "bs psychology": "BS Psychology (Clinical)",
        "bs medical lab tech": "BS Medical Lab Technology (MLT)",
        "aerospace engineering": "BE / BS Aerospace Engineering",
        "chemical engineering": "BE / BS Chemical Engineering",
        "civil engineering": "BE / BS Civil Engineering",
        "electrical engineering": "BE / BS Electrical Engineering",
        "mechanical engineering": "BE / BS Mechanical Engineering",
        "software engineering": "BE / BS Software Engineering",
        "bs computer science": "BS Computer Science (CS)",
    }
    
    clean_query = career_name.strip().lower()
    mapped_query = synonyms.get(clean_query, career_name)
    
    # Try exact match with mapped name first
    row = df[df[career_col].str.strip().str.lower() == mapped_query.strip().lower()]
    
    if row.empty:
        # Fallback 1: Try exact match with original query
        row = df[df[career_col].str.strip().str.lower() == clean_query]
        
    if row.empty:
        # Fallback 2: Try fuzzy search with split mapped query
        row = df[df[career_col].str.contains(mapped_query.split("(")[0].strip(), case=False, na=False)]
        
    if row.empty:
        # Fallback 3: Try fuzzy search with original query split
        row = df[df[career_col].str.contains(career_name.split("(")[0].strip(), case=False, na=False)]
        
    if row.empty:
        return {}

    r = row.iloc[0]
    steps_raw = str(r.get("Roadmap Steps", ""))
    steps = [s.strip() for s in re.split(r"\s*\|\s*", steps_raw) if s.strip()]
    skills_raw = str(r.get("Skills Required", ""))
    skills = [s.strip() for s in skills_raw.split(",") if s.strip()]
    unis_raw = str(r.get("Top Universities PK", ""))
    unis = [u.strip() for u in unis_raw.split(",") if u.strip()]

    return {
        "career": career_name,
        "description": str(r.get("Description", "")).strip(),
        "roadmap_steps": steps,
        "skills_required": skills,
        "top_universities": unis,
        "sector": str(r.get("Sector", "")).strip(),
        "typical_duration": str(r.get("Typical Duration", "")).strip(),
        "avg_entry_salary": str(r.get("Avg Entry Salary PKR", "")).strip(),
    }

def _coerce_json(value, fallback=None):
    """Return a dict/list from Supabase JSONB or JSON text."""
    if fallback is None:
        fallback = {}
    if value is None:
        return fallback
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return fallback
    return fallback


def _pct(value) -> str:
    try:
        return f"{float(value) * 100:.1f}%" if float(value) <= 1 else f"{float(value):.1f}%"
    except Exception:
        return "N/A"


def _compute_shap_explanation(payload: dict, top_career: str = "") -> dict:
    """Compute grouped SHAP factors for the latest prediction payload."""
    if shap_explainer is None:
        return {"career": top_career, "top_features": [], "warning": "SHAP explainer is unavailable"}

    X = _build_feature_df(payload)
    shap_vals = shap_explainer.shap_values(X)
    pred_class = int(xgb_model.predict(X)[0])

    if isinstance(shap_vals, list):
        sv = shap_vals[pred_class][0]
    elif len(shap_vals.shape) == 3:
        sv = shap_vals[0, :, pred_class]
    else:
        sv = shap_vals[0]

    groups = {
        "Academic Stream": 0.0,
        "Academic Marks": 0.0,
        "Aptitude Test": 0.0,
        "Personality Profile": 0.0,
        "RIASEC Interests": 0.0,
        "Activity and Engineered Fit": 0.0,
        "Other Factors": 0.0,
    }

    for i, col in enumerate(feature_names):
        val = float(sv[i])
        if col == "Stream":
            groups["Academic Stream"] += val
        elif col in ["FSc_Marks", "Marks_Biology", "Marks_Physics", "Marks_Chemistry", "Marks_Math", "Marks_Computer", "FSc_Percentage", "Avg_Subject_Marks"]:
            groups["Academic Marks"] += val
        elif col in ["Aptitude_Logic", "Aptitude_Verbal", "Aptitude_Spatial", "Aptitude_Math", "Aptitude_Avg"]:
            groups["Aptitude Test"] += val
        elif col in ["Psych_Openness", "Psych_Conscientiousness", "Psych_Extraversion", "Psych_Agreeableness", "Psych_Neuroticism"]:
            groups["Personality Profile"] += val
        elif col in ["Interest_R", "Interest_I", "Interest_A", "Interest_S", "Interest_E", "Interest_C", "Top_RIASEC_Score"]:
            groups["RIASEC Interests"] += val
        elif col in ["Extracurricular_Activity"]:
            groups["Activity and Engineered Fit"] += val
        else:
            groups["Other Factors"] += val

    top_features = [
        {"feature": key, "value": round(value, 4), "direction": "supports" if value >= 0 else "reduces"}
        for key, value in groups.items()
    ]
    top_features = sorted(top_features, key=lambda item: abs(item["value"]), reverse=True)
    return {"career": top_career, "predicted_class": pred_class, "top_features": top_features}


def _build_structured_student_context(student_id: str, fallback_career: str = "") -> str:
    """Build the complete direct context packet injected into every chat turn."""
    profile = get_student_profile(student_id)
    if not profile:
        return ""

    latest_scores = []
    try:
        from supabase_client import get_supabase_admin
        sb_admin = get_supabase_admin()
        if sb_admin:
            score_res = sb_admin.table("entry_test_scores") \
                .select("*") \
                .eq("student_id", student_id) \
                .order("taken_at", desc=True) \
                .limit(12) \
                .execute()
            latest_scores = score_res.data or []
    except Exception as score_err:
        print(f"[StructuredContext] Entry-test score lookup failed: {score_err}")

    recommendations = _coerce_json(profile.get("prediction_recommendations"), [])
    last_prediction = _coerce_json(profile.get("last_prediction_result"), {})
    if not recommendations and isinstance(last_prediction, dict):
        recommendations = last_prediction.get("recommendations", []) or []

    explanation = _coerce_json(profile.get("prediction_explanation"), {})
    if not explanation and isinstance(last_prediction, dict):
        explanation = last_prediction.get("shap_explanation", {}) or {}

    top_career = fallback_career or profile.get("target_career") or ""
    if recommendations:
        top_career = recommendations[0].get("career") or top_career

    roadmap = _get_roadmap_data(top_career) if top_career else {}

    profile_fields = [
        "full_name", "phone", "city", "fsc_stream", "matric_marks", "fsc_marks",
        "matric_percentage", "fsc_percentage", "marks_math", "marks_physics",
        "marks_chemistry", "marks_computer", "marks_biology", "aptitude_logic",
        "aptitude_verbal", "aptitude_spatial", "aptitude_math", "psych_openness",
        "psych_conscientiousness", "psych_extraversion", "psych_agreeableness",
        "psych_neuroticism", "interest_r", "interest_i", "interest_a", "interest_s",
        "interest_e", "interest_c", "interest_text", "extracurricular_activity",
        "target_career", "target_university", "entry_test_planned", "model_name",
    ]
    profile_lines = [f"- {field}: {profile.get(field)}" for field in profile_fields if profile.get(field) is not None]

    score_lines = []
    for score in latest_scores:
        score_lines.append(
            f"- {score.get('test_type') or 'Test'} / {score.get('subject') or 'Overall'}: "
            f"{score.get('score')} out of {score.get('total')} (taken_at: {score.get('taken_at')})"
        )

    recommendation_lines = []
    for rec in recommendations[:3]:
        recommendation_lines.append(
            f"- Rank {rec.get('rank')}: {rec.get('career')} ({_pct(rec.get('probability', 0))})"
        )

    shap_lines = []
    for factor in (explanation.get("top_features") or [])[:7]:
        shap_lines.append(
            f"- {factor.get('feature')}: {factor.get('direction', '')} recommendation (impact {factor.get('value')})"
        )

    roadmap_lines = []
    if roadmap:
        roadmap_lines.extend([
            f"- Career: {top_career}",
            f"- Description: {roadmap.get('description', '')}",
            f"- Steps: {' | '.join(roadmap.get('roadmap_steps', []))}",
            f"- Universities: {', '.join(roadmap.get('top_universities', []))}",
            f"- Skills: {', '.join(roadmap.get('skills_required', []))}",
            f"- Salary: {roadmap.get('avg_entry_salary', '')}",
            f"- Duration: {roadmap.get('typical_duration', '')}",
        ])

    sections = [
        "FULL STUDENT PROFILE\n" + ("\n".join(profile_lines) if profile_lines else "- No profile fields available"),
        "LATEST ENTRY TEST / ASSESSMENT SCORES\n" + ("\n".join(score_lines) if score_lines else "- No entry-test rows found"),
        "LATEST TOP 3 RECOMMENDATIONS\n" + ("\n".join(recommendation_lines) if recommendation_lines else "- No persisted recommendations found"),
        "SHAP / EXPLANATION FACTORS FOR TOP RECOMMENDATION\n" + ("\n".join(shap_lines) if shap_lines else "- No persisted SHAP explanation found"),
        "ROADMAP FOR TOP RECOMMENDATION\n" + ("\n".join(roadmap_lines) if roadmap_lines else "- No roadmap found"),
    ]
    context = "\n\n".join(sections)
    print(f"[StructuredContext] Built context for student_id={student_id}, top_career={top_career}, chars={len(context)}")
    print(f"[StructuredContext] Preview:\n{context[:1200]}")
    return context

def _build_feature_df(payload: dict) -> pd.DataFrame:
    """Build the 27-feature DataFrame matching the new model's input format."""
    def get_mark(val):
        if val is None or val == -1:
            return np.nan
        try:
            return int(val)
        except (ValueError, TypeError):
            return np.nan

    # 1. Build dictionary of raw features from payload
    raw_data = {
        "Stream": payload.get("Stream", "Pre-Engineering"),
        "FSc_Marks": int(payload.get("FSc_Marks", 425)),
        "Marks_Biology": get_mark(payload.get("Marks_Biology")),
        "Marks_Physics": get_mark(payload.get("Marks_Physics")),
        "Marks_Chemistry": get_mark(payload.get("Marks_Chemistry")),
        "Marks_Math": get_mark(payload.get("Marks_Math")),
        "Marks_Computer": get_mark(payload.get("Marks_Computer")),
        "Aptitude_Logic": int(payload.get("Aptitude_Logic", 50)),
        "Aptitude_Verbal": int(payload.get("Aptitude_Verbal", 50)),
        "Aptitude_Spatial": int(payload.get("Aptitude_Spatial", 50)),
        "Aptitude_Math": int(payload.get("Aptitude_Math", 50)),
        "Psych_Openness": float(payload.get("Psych_Openness", 5.0)),
        "Psych_Conscientiousness": float(payload.get("Psych_Conscientiousness", 5.0)),
        "Psych_Extraversion": float(payload.get("Psych_Extraversion", 5.0)),
        "Psych_Agreeableness": float(payload.get("Psych_Agreeableness", 5.0)),
        "Psych_Neuroticism": float(payload.get("Psych_Neuroticism", 5.0)),
        "Interest_R": float(payload.get("Interest_R", 50.0)),
        "Interest_I": float(payload.get("Interest_I", 50.0)),
        "Interest_A": float(payload.get("Interest_A", 50.0)),
        "Interest_S": float(payload.get("Interest_S", 50.0)),
        "Interest_E": float(payload.get("Interest_E", 50.0)),
        "Interest_C": float(payload.get("Interest_C", 50.0)),
        "Extracurricular_Activity": payload.get("Extracurricular_Activity", "None"),
    }
    
    # Create DataFrame
    df = pd.DataFrame([raw_data])
    
    # 2. Add engineered features (exactly matching train_new_model.py)
    df["FSc_Percentage"] = df["FSc_Marks"] / 1100.0 * 100.0
    
    mark_cols = ["Marks_Biology", "Marks_Physics", "Marks_Chemistry", "Marks_Math", "Marks_Computer"]
    df["Avg_Subject_Marks"] = df[mark_cols].mean(axis=1)
    
    apt_cols = ["Aptitude_Logic", "Aptitude_Verbal", "Aptitude_Spatial", "Aptitude_Math"]
    df["Aptitude_Avg"] = df[apt_cols].mean(axis=1)
    
    riasec_cols = ["Interest_R", "Interest_I", "Interest_A", "Interest_S", "Interest_E", "Interest_C"]
    df["Top_RIASEC_Score"] = df[riasec_cols].max(axis=1)
    
    # 3. Cast categoricals using categorical_mappings
    for col in ["Stream", "Extracurricular_Activity"]:
        cats = list(categorical_mappings[col])
        val = str(df[col].iloc[0])
        if val not in cats:
            cats.append(val)
        df[col] = pd.Categorical(df[col], categories=cats)
        
    # 4. Reorder columns to match feature_names exactly
    df = df[feature_names]
    
    return df


def _execute_tool(name: str, arguments: dict) -> dict:
    """Execute the corresponding web search or scraper tool and return JSON result."""
    from scrapers.web_tools import search_duckduckgo, web_scrape
    from scrapers.youtube_api import search_youtube_videos
    from scrapers.playwright_scraper import scrape_udemy_courses
    import asyncio

    try:
        if name == "google_search":
            q = arguments.get("query", "")
            return {"results": search_duckduckgo(q)}
        elif name == "web_scrape":
            u = arguments.get("url", "")
            return {"text": web_scrape(u)}
        elif name == "get_youtube_videos":
            q = arguments.get("query", "")
            return {"videos": search_youtube_videos(q)}
        elif name == "get_online_courses":
            q = arguments.get("query", "")
            # scrape_udemy_courses is async; run in event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            try:
                courses = asyncio.run(scrape_udemy_courses(q))
            except RuntimeError:
                import nest_asyncio
                nest_asyncio.apply()
                courses = asyncio.get_event_loop().run_until_complete(scrape_udemy_courses(q))
            return {"courses": courses}
        else:
            return {"error": f"Tool '{name}' not found."}
    except Exception as e:
        return {"error": str(e)}


def _is_youtube_request(message: str) -> bool:
    """Detect whether the student is explicitly asking for YouTube content."""
    text = (message or "").lower()
    keywords = ["youtube", "video", "videos", "channel", "channels", "playlist", "watch"]
    return any(keyword in text for keyword in keywords)


def _format_youtube_results(videos: list) -> str:
    """Format YouTube results in the response style expected by the prompt."""
    if not videos:
        return ""

    lines = ["Here are some YouTube recommendations:"]
    for index, video in enumerate(videos[:5], start=1):
        title = video.get("title", "Untitled video")
        channel = video.get("channel", "Unknown channel")
        url = video.get("url", "")
        description = video.get("description", "")
        why = description or "Relevant learning content for your query."
        lines.append(
            f"{index}. {title}\n"
            f"Channel: {channel}\n"
            f"Link: {url}\n"
            f"Why watch: {why}"
        )
    return "\n\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# Schemas
# ═══════════════════════════════════════════════════════════════════════════════
class PredictRequest(BaseModel):
    name: Optional[str] = "Student"
    Gender: str = "Male"
    Age: int = Field(default=18, ge=14, le=25)
    City: str = "Lahore"
    Stream: str = "Pre-Engineering"
    Matric_Marks: int = 850
    FSc_Marks: int = Field(default=850, ge=0, le=1100)
    Marks_Math: int = Field(default=70, ge=-1, le=100)
    Marks_Physics: int = Field(default=70, ge=-1, le=100)
    Marks_Chemistry: int = Field(default=70, ge=-1, le=100)
    Marks_Computer: int = Field(default=70, ge=-1, le=100)
    Marks_Biology: int = Field(default=50, ge=-1, le=100)
    Aptitude_Logic: int = 50
    Aptitude_Verbal: int = 50
    Aptitude_Spatial: int = 50
    Aptitude_Math: int = 50
    Psych_Openness: float = 6.0
    Psych_Conscientiousness: float = 7.0
    Psych_Extraversion: float = 5.0
    Psych_Agreeableness: float = 6.0
    Psych_Neuroticism: float = 4.0
    Interest_R: float = 50.0
    Interest_I: float = 50.0
    Interest_A: float = 50.0
    Interest_S: float = 50.0
    Interest_E: float = 50.0
    Interest_C: float = 50.0
    Extracurricular_Activity: str = "None"
    Interest_Text: str = "general"
    Sentiment_Label: str = "Neutral"
    Model_Name: str = "Hybrid"   # "Ensemble" | "Stacking" | "Hybrid"


class ChatRequest(BaseModel):
    message: str
    city: Optional[str] = ""
    recommended_career: Optional[str] = ""
    history: Optional[List[dict]] = []
    user_id: Optional[str] = "anonymous"    # for Mem0 memory
    voice_mode: Optional[bool] = False       # for voice-friendly responses
    conversation_id: Optional[str] = ""      # optional conversation ID



class SearchRequest(BaseModel):
    query: str
    resource_type: str = "all"  # 'videos' | 'scholarships' | 'courses' | 'all'


class AuthRequest(BaseModel):
    email: str
    password: str
    full_name: str = ""


class OtpRequest(BaseModel):
    phone: str
    token: str = ""


class ProfileUpdateRequest(BaseModel):
    updates: dict


class SaveSessionRequest(BaseModel):
    student: dict
    prediction: dict


class ExportPdfRequest(BaseModel):
    student: dict
    prediction: dict


class MindMapRequest(BaseModel):
    notes: str


class AptitudeDiagnosticRequest(BaseModel):
    Aptitude_Logic: int
    Aptitude_Verbal: int
    Aptitude_Spatial: int
    Aptitude_Math: int


# ═══════════════════════════════════════════════════════════════════════════════
# Routes
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/health")
def health():
    return {"status": "ok", "models_loaded": True, "careers": len(career_map)}


@app.get("/options")
def options():
    return {
        "genders": ["Male", "Female"],
        "cities": sorted(CITY_MAP.keys()),
        "streams": sorted(categorical_mappings["Stream"]),
        "activities": sorted(categorical_mappings["Extracurricular_Activity"]),
        "models": ["Ensemble", "Stacking", "Hybrid"],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Auth & Profile Routes (Supabase)
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/auth/register")
async def register(req: AuthRequest):
    return await register_student(req.email, req.password, req.full_name)

@app.post("/auth/login")
async def login(req: AuthRequest):
    return await login_student(req.email, req.password)

# OTP routes disabled — requires Supabase phone auth provider setup, see auth.py for implementation
# from auth import send_otp, verify_otp
# @app.post("/auth/send-otp")
# async def send_otp_route(req: OtpRequest):
#     return await send_otp(req.phone)
# 
# @app.post("/auth/verify-otp")
# async def verify_otp_route(req: OtpRequest):
#     return await verify_otp(req.phone, req.token)

@app.get("/auth/google")
async def google_login():
    return await get_google_login_url()

@app.get("/profile")
async def get_profile(user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return get_student_profile(user.id)

@app.patch("/profile")
async def patch_profile(req: ProfileUpdateRequest, user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return update_student_profile(user.id, req.updates)

@app.get("/conversations")
async def list_conversations(user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return get_student_conversations(user.id)

@app.get("/conversations/{conv_id}/messages")
async def list_messages(conv_id: str, user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return get_conversation_history(conv_id, student_id=user.id, limit=50)


@app.post("/predict")
def predict(req: PredictRequest, user=Depends(get_current_user)):
    try:
        payload = req.model_dump()
        X = _build_feature_df(payload)

        # Choose model
        model_name = req.Model_Name.lower()
        if model_name == "stacking":
            model = stacking_model
            used = "Stacking Ensemble"
        elif model_name == "ensemble":
            model = voting_model
            used = "Voting Ensemble"
        else:
            # Hybrid: use stacking for final but annotate
            model = stacking_model
            used = "Hybrid (Stacking + XGBoost)"

        proba = model.predict_proba(X)[0]

        # Apply neuro-symbolic stream eligibility constraints based on actual Pakistani university admission criteria
        # (FAST, NUST, UET, COMSATS, Air University, and private medical colleges). This allows the ML model's learned 
        # cross-stream predictions (e.g. Pre-Engineering -> BS Computer Science) to surface instead of being arbitrarily discarded.
        stream_careers = {
            "Arts": [
                "BBA (Business Admin)", "BS Accounting & Finance", "BS Animation & VFX",
                "BS English Literature", "BS Fashion Design", "BS Graphic Design",
                "BS International Relations", "BS Marketing", "BS Psychology",
                "Digital Marketing", "LLB (Lawyer)", "Pakistan Army/Navy/PAF"
            ],
            "ICS": [
                "BS Artificial Intelligence", "BS Computer Science", "BS Cyber Security",
                "BS Data Science", "BS Game Development", "Ethical Hacking",
                "Software Engineering", "Web Development", "BS Mathematics", "BS Physics",
                "BBA (Business Admin)", "BS Accounting & Finance", "BS Marketing",
                "Digital Marketing", "BS Psychology", "LLB (Lawyer)",
                "Pakistan Army/Navy/PAF", "Pilot (Aviation)"
            ],
            "Pre-Engineering": [
                "Aerospace Engineering", "BS Mathematics", "BS Physics",
                "Chemical Engineering", "Civil Engineering", "Electrical Engineering",
                "Mechanical Engineering", "Pakistan Army/Navy/PAF", "Pilot (Aviation)",
                "BS Artificial Intelligence", "BS Computer Science", "BS Cyber Security",
                "BS Data Science", "BS Game Development", "Ethical Hacking",
                "Software Engineering", "Web Development",
                "BBA (Business Admin)", "BS Accounting & Finance", "LLB (Lawyer)"
            ],
            "Pre-Medical": [
                "BDS (Dentist)", "BS Agriculture", "BS Food Science",
                "BS Medical Lab Tech", "BS Nursing", "BS Nutrition & Dietetics",
                "DPT (Physical Therapy)", "DVM (Veterinary)", "MBBS (Doctor)",
                "Pharm-D (Pharmacist)", "BS Psychology",
                "BBA (Business Admin)", "BS Accounting & Finance", "LLB (Lawyer)",
                "Pakistan Army/Navy/PAF",
                "BS Computer Science", "Software Engineering",
                "BS Artificial Intelligence", "BS Cyber Security", "BS Data Science",
                "BS Game Development", "Ethical Hacking", "Web Development"
                # Note: Computing disciplines require additional/deficiency Math courses under HEC criteria
            ]
        }
        allowed = stream_careers.get(req.Stream, [])
        if allowed:
            mask = np.zeros_like(proba)
            for idx, name in career_map.items():
                if name in allowed:
                    mask[idx] = 1.0
            proba = proba * mask
            p_sum = proba.sum()
            if p_sum > 0:
                proba = proba / p_sum

        # Calculate suitability score based on student's actual profile (RIASEC + Aptitude)
        career_profiles = {
            "BS Artificial Intelligence": {"riasec": ["I", "R"], "aptitude": ["Logic", "Math"]},
            "BS Computer Science": {"riasec": ["I", "R"], "aptitude": ["Logic", "Math"]},
            "BS Cyber Security": {"riasec": ["I", "R"], "aptitude": ["Logic", "Math"]},
            "BS Data Science": {"riasec": ["I", "C"], "aptitude": ["Logic", "Math"]},
            "BS Game Development": {"riasec": ["A", "I"], "aptitude": ["Logic", "Spatial"]},
            "Ethical Hacking": {"riasec": ["I", "R"], "aptitude": ["Logic", "Verbal"]},
            "Software Engineering": {"riasec": ["I", "R"], "aptitude": ["Logic", "Math"]},
            "Web Development": {"riasec": ["I", "A"], "aptitude": ["Logic", "Spatial"]},
            
            "Aerospace Engineering": {"riasec": ["R", "I"], "aptitude": ["Spatial", "Math"]},
            "Chemical Engineering": {"riasec": ["R", "I"], "aptitude": ["Math", "Logic"]},
            "Civil Engineering": {"riasec": ["R", "C"], "aptitude": ["Spatial", "Math"]},
            "Electrical Engineering": {"riasec": ["R", "I"], "aptitude": ["Spatial", "Math"]},
            "Mechanical Engineering": {"riasec": ["R", "I"], "aptitude": ["Spatial", "Math"]},
            
            "BDS (Dentist)": {"riasec": ["I", "S"], "aptitude": ["Spatial", "Verbal"]},
            "BS Medical Lab Tech": {"riasec": ["I", "R"], "aptitude": ["Logic", "Verbal"]},
            "BS Nursing": {"riasec": ["S", "I"], "aptitude": ["Verbal", "Logic"]},
            "BS Nutrition & Dietetics": {"riasec": ["I", "S"], "aptitude": ["Verbal", "Logic"]},
            "DPT (Physical Therapy)": {"riasec": ["S", "R"], "aptitude": ["Spatial", "Verbal"]},
            "DVM (Veterinary)": {"riasec": ["I", "R"], "aptitude": ["Logic", "Verbal"]},
            "MBBS (Doctor)": {"riasec": ["I", "S"], "aptitude": ["Logic", "Verbal"]},
            "Pharm-D (Pharmacist)": {"riasec": ["I", "C"], "aptitude": ["Logic", "Verbal"]},
            
            "BBA (Business Admin)": {"riasec": ["E", "S"], "aptitude": ["Verbal", "Logic"]},
            "BS Accounting & Finance": {"riasec": ["C", "E"], "aptitude": ["Math", "Logic"]},
            "BS Marketing": {"riasec": ["E", "A"], "aptitude": ["Verbal", "Logic"]},
            "Digital Marketing": {"riasec": ["E", "A"], "aptitude": ["Verbal", "Spatial"]},
            
            "BS Mathematics": {"riasec": ["I", "C"], "aptitude": ["Math", "Logic"]},
            "BS Physics": {"riasec": ["I", "R"], "aptitude": ["Math", "Logic"]},
            "BS English Literature": {"riasec": ["A", "S"], "aptitude": ["Verbal", "Logic"]},
            "BS Fashion Design": {"riasec": ["A", "R"], "aptitude": ["Spatial", "Verbal"]},
            "BS Graphic Design": {"riasec": ["A", "I"], "aptitude": ["Spatial", "Verbal"]},
            "BS Animation & VFX": {"riasec": ["A", "I"], "aptitude": ["Spatial", "Logic"]},
            "BS International Relations": {"riasec": ["E", "I"], "aptitude": ["Verbal", "Logic"]},
            "BS Psychology": {"riasec": ["S", "I"], "aptitude": ["Verbal", "Logic"]},
            "BS Agriculture": {"riasec": ["R", "I"], "aptitude": ["Logic", "Verbal"]},
            "BS Food Science": {"riasec": ["I", "R"], "aptitude": ["Logic", "Verbal"]},
            "LLB (Lawyer)": {"riasec": ["E", "I"], "aptitude": ["Verbal", "Logic"]},
            
            "Pakistan Army/Navy/PAF": {"riasec": ["R", "E"], "aptitude": ["Spatial", "Logic"]},
            "Pilot (Aviation)": {"riasec": ["R", "I"], "aptitude": ["Spatial", "Logic"]}
        }
        
        suitability_scores = {}
        for career_name, profile_info in career_profiles.items():
            r_scores = [payload.get(f"Interest_{x}", 50.0) for x in profile_info["riasec"]]
            r_fit = sum(r_scores) / len(r_scores) / 100.0 if r_scores else 0.5
            
            a_scores = [payload.get(f"Aptitude_{y}", 50.0) for y in profile_info["aptitude"]]
            a_fit = sum(a_scores) / len(a_scores) / 100.0 if a_scores else 0.5
            
            suitability_scores[career_name] = 0.5 * r_fit + 0.5 * a_fit

        # Adjust probabilities using suitability scores
        for idx, name in career_map.items():
            factor = suitability_scores.get(name, 0.5)
            # Additive suitability boost (using factor^3 * 0.3) to allow strong interest alignment to surface cross-stream predictions
            proba[idx] = proba[idx] * (0.5 + factor) + (factor ** 3) * 0.3

        p_sum = proba.sum()
        if p_sum > 0:
            proba = proba / p_sum

        # Categorize careers for diversity checking
        career_categories = {
            "Aerospace Engineering": "Traditional Engineering",
            "Chemical Engineering": "Traditional Engineering",
            "Civil Engineering": "Traditional Engineering",
            "Electrical Engineering": "Traditional Engineering",
            "Mechanical Engineering": "Traditional Engineering",
            
            "BS Artificial Intelligence": "Computer Science / IT",
            "BS Computer Science": "Computer Science / IT",
            "BS Cyber Security": "Computer Science / IT",
            "BS Data Science": "Computer Science / IT",
            "BS Game Development": "Computer Science / IT",
            "Ethical Hacking": "Computer Science / IT",
            "Software Engineering": "Computer Science / IT",
            "Web Development": "Computer Science / IT",
            
            "BDS (Dentist)": "Medical & Health Sciences",
            "BS Medical Lab Tech": "Medical & Health Sciences",
            "BS Nursing": "Medical & Health Sciences",
            "BS Nutrition & Dietetics": "Medical & Health Sciences",
            "DPT (Physical Therapy)": "Medical & Health Sciences",
            "DVM (Veterinary)": "Medical & Health Sciences",
            "MBBS (Doctor)": "Medical & Health Sciences",
            "Pharm-D (Pharmacist)": "Medical & Health Sciences",
            
            "BBA (Business Admin)": "Business & Finance",
            "BS Accounting & Finance": "Business & Finance",
            "BS Marketing": "Business & Finance",
            "Digital Marketing": "Business & Finance",
            
            "BS Mathematics": "Sciences & Arts",
            "BS Physics": "Sciences & Arts",
            "BS English Literature": "Sciences & Arts",
            "BS Fashion Design": "Sciences & Arts",
            "BS Graphic Design": "Sciences & Arts",
            "BS Animation & VFX": "Sciences & Arts",
            "BS International Relations": "Sciences & Arts",
            "BS Psychology": "Sciences & Arts",
            "BS Agriculture": "Sciences & Arts",
            "BS Food Science": "Sciences & Arts",
            "LLB (Lawyer)": "Sciences & Arts",
            
            "Pakistan Army/Navy/PAF": "Military & Aviation",
            "Pilot (Aviation)": "Military & Aviation"
        }

        # Select top 3 with category diversity
        sorted_indices = np.argsort(proba)[::-1]
        top3_idx = []
        category_counts = {}
        for idx in sorted_indices:
            career_name = career_map.get(idx, "")
            category = career_categories.get(career_name, "Other")
            if category_counts.get(category, 0) >= 2:
                continue
            top3_idx.append(idx)
            category_counts[category] = category_counts.get(category, 0) + 1
            if len(top3_idx) == 3:
                break

        def get_display_name(cname: str) -> str:
            mapping = {
                "Web Development": "Web Development (BS Computer Science / Software Engineering)",
                "Ethical Hacking": "Ethical Hacking (BS Cyber Security / Computer Science)",
                "Digital Marketing": "Digital Marketing (BBA / BS Marketing)"
            }
            return mapping.get(cname, cname)

        recommendations = []
        for rank, idx in enumerate(top3_idx, 1):
            career_name = career_map.get(idx, f"Career {idx}")
            prob = float(proba[idx])
            roadmap = _get_roadmap_data(career_name)
            recommendations.append({
                "rank": rank,
                "career": get_display_name(career_name),
                "probability": round(prob, 4),
                "description": roadmap.get("description", ""),
                "roadmap_steps": roadmap.get("roadmap_steps", []),
                "skills_required": roadmap.get("skills_required", []),
                "top_universities": roadmap.get("top_universities", []),
                "sector": roadmap.get("sector", ""),
                "avg_entry_salary": roadmap.get("avg_entry_salary", ""),
            })

        prediction_explanation = _compute_shap_explanation(payload, recommendations[0]["career"])
        prediction_result = {
            "used_model": used,
            "primary_recommendation": recommendations[0],
            "recommendations": recommendations,
            "shap_explanation": prediction_explanation,
        }
        # Save profile to Supabase and Mem0 if authenticated
        if user:
            try:
                # Convert raw marks to percentages
                matric_pct = (req.Matric_Marks / 1100.0) * 100.0 if req.Matric_Marks > 100 else float(req.Matric_Marks)
                fsc_pct = (req.FSc_Marks / 1100.0) * 100.0 if req.FSc_Marks > 100 else float(req.FSc_Marks)
                
                # Update persistent profile in Supabase
                updates = {
                    "full_name": req.name,
                    "city": req.City,
                    "fsc_stream": req.Stream,
                    "matric_percentage": matric_pct,
                    "fsc_percentage": fsc_pct,
                    "target_career": recommendations[0]["career"],
                    "matric_marks": req.Matric_Marks,
                    "fsc_marks": req.FSc_Marks,
                    "marks_math": req.Marks_Math,
                    "marks_physics": req.Marks_Physics,
                    "marks_chemistry": req.Marks_Chemistry,
                    "marks_computer": req.Marks_Computer,
                    "marks_biology": req.Marks_Biology,
                    "aptitude_logic": req.Aptitude_Logic,
                    "aptitude_verbal": req.Aptitude_Verbal,
                    "aptitude_spatial": req.Aptitude_Spatial,
                    "aptitude_math": req.Aptitude_Math,
                    "psych_openness": req.Psych_Openness,
                    "psych_conscientiousness": req.Psych_Conscientiousness,
                    "psych_extraversion": req.Psych_Extraversion,
                    "psych_agreeableness": req.Psych_Agreeableness,
                    "psych_neuroticism": req.Psych_Neuroticism,
                    "interest_r": req.Interest_R,
                    "interest_i": req.Interest_I,
                    "interest_a": req.Interest_A,
                    "interest_s": req.Interest_S,
                    "interest_e": req.Interest_E,
                    "interest_c": req.Interest_C,
                    "interest_text": req.Interest_Text,
                    "extracurricular_activity": req.Extracurricular_Activity,
                    "sentiment_label": req.Sentiment_Label,
                    "model_name": req.Model_Name,
                    "prediction_recommendations": recommendations,
                    "prediction_explanation": prediction_explanation,
                    "last_prediction_result": prediction_result
                }
                update_student_profile(user.id, updates)
                
                # Save aptitude test scores to entry_test_scores table in Supabase
                try:
                    from supabase_client import get_supabase_admin
                    sb_admin = get_supabase_admin()
                    if sb_admin:
                        # Clear existing Aptitude scores to avoid duplicates on re-taking the assessment
                        try:
                            sb_admin.table("entry_test_scores").delete().eq("student_id", user.id).eq("test_type", "Aptitude").execute()
                        except Exception:
                            pass
                        
                        scores_to_insert = [
                            {"student_id": user.id, "test_type": "Aptitude", "subject": "Logic", "score": float(req.Aptitude_Logic), "total": 100.0},
                            {"student_id": user.id, "test_type": "Aptitude", "subject": "Math", "score": float(req.Aptitude_Math), "total": 100.0},
                            {"student_id": user.id, "test_type": "Aptitude", "subject": "Verbal", "score": float(req.Aptitude_Verbal), "total": 100.0},
                            {"student_id": user.id, "test_type": "Aptitude", "subject": "Spatial", "score": float(req.Aptitude_Spatial), "total": 100.0},
                        ]
                        
                        # Add a row for the planned admission test if not already present
                        test_planned = "ECAT"
                        if req.Stream == "Pre-Medical":
                            test_planned = "MDCAT"
                        elif req.Stream == "ICS":
                            test_planned = "ECAT / FAST / NUST"
                        elif req.Stream == "Arts":
                            test_planned = "LAT / General"
                            
                        # Check if this admission test is already present
                        existing_tests = sb_admin.table("entry_test_scores").select("*").eq("student_id", user.id).eq("test_type", "Admission Test").eq("subject", test_planned).execute()
                        if not existing_tests.data:
                            scores_to_insert.append({
                                "student_id": user.id,
                                "test_type": "Admission Test",
                                "subject": test_planned,
                                "score": None, # Null score indicates planned but not taken
                                "total": 400.0 if "ECAT" in test_planned or "FAST" in test_planned else 200.0
                            })
                        
                        sb_admin.table("entry_test_scores").insert(scores_to_insert).execute()
                        print("[Predict] Saved aptitude scores and planned test to Supabase successfully.")
                except Exception as db_err:
                    print(f"[Predict] Failed to save entry_test_scores to Supabase: {db_err}")
                
                # Save structured assessment memory in Mem0
                profile_summary = (
                    f"Student Profile & Aptitude Test Details:\n"
                    f"- Name: {req.name}\n"
                    f"- Stream: {req.Stream}\n"
                    f"- City: {req.City}\n"
                    f"- Matric Marks: {req.Matric_Marks} ({matric_pct:.1f}%)\n"
                    f"- FSc Marks: {req.FSc_Marks} ({fsc_pct:.1f}%)\n"
                    f"- Aptitude Scores: Math {req.Aptitude_Math}%, Logic {req.Aptitude_Logic}%, Verbal {req.Aptitude_Verbal}%, Spatial {req.Aptitude_Spatial}%\n"
                    f"- Personality Traits: Openness {req.Psych_Openness}, Conscientiousness {req.Psych_Conscientiousness}, Extraversion {req.Psych_Extraversion}, Agreeableness {req.Psych_Agreeableness}, Neuroticism {req.Psych_Neuroticism}\n"
                    f"- Interests: {req.Interest_Text}\n"
                    f"- Primary Recommended Career: {recommendations[0]['career']}\n"
                    f"- Alternative Recommendations: {recommendations[1]['career']}, {recommendations[2]['career']}"
                )
                save_memory(user.id, [{"role": "system", "content": profile_summary}])
            except Exception as prof_err:
                print(f"[Predict] Save user profile / memory context failed: {prof_err}")

        return prediction_result

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/roadmap")
def roadmap(career: str):
    data = _get_roadmap_data(career)
    if not data:
        raise HTTPException(status_code=404, detail=f"Roadmap not found for: {career}")
    return data


# ── Market Trends: Dynamic AI-Powered Search + Groq LLM + SQLite Cache ────────

def _fetch_market_trends_live(career_name: str) -> dict:
    """
    Use DuckDuckGo search + Groq LLM to fetch real-time Pakistan job market data.
    Covers all 38 careers the ML model can predict.
    """
    from scrapers.web_tools import search_duckduckgo
    from groq import Groq

    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY", ""))

    # Strip degree qualifiers for a cleaner search (e.g. "Web Development (BS CS)" -> "Web Development")
    clean_name = career_name.split("(")[0].strip()

    # Two targeted search queries for Pakistan-specific market data
    queries = [
        f"{clean_name} salary Pakistan 2024 2025 monthly PKR jobs",
        f"{clean_name} top companies hiring Pakistan job market growth",
    ]

    snippets = []
    for q in queries:
        results = search_duckduckgo(q, max_results=4)
        for r in results:
            if r.get("snippet"):
                snippets.append(r["snippet"])

    context = "\n".join(snippets[:10]) if snippets else f"No search results found for {clean_name} in Pakistan."

    prompt = f"""You are a Pakistan career market analyst. Based on the web search snippets below, extract real Pakistani job market data for the career: "{clean_name}"

Search snippets:
{context}

Return ONLY a valid JSON object with these exact keys (use realistic Pakistani estimates if data is missing):
{{
  "entry_salary_pkr": "e.g. 60,000 - 80,000",
  "mid_salary_pkr": "e.g. 120,000 - 180,000",
  "senior_salary_pkr": "e.g. 250,000 - 400,000",
  "growth_rate": "e.g. High (15% annually)",
  "job_market_trend": "e.g. Growing rapidly",
  "remote_friendly": "Yes / Partial / No",
  "competition_level": "Low / Medium / High / Very High",
  "top_employers": ["Company 1", "Company 2", "Company 3", "Company 4", "Company 5"],
  "key_cities": ["Lahore", "Karachi", "Islamabad"],
  "skills_in_demand": ["Skill 1", "Skill 2", "Skill 3", "Skill 4"],
  "certifications": ["Cert 1", "Cert 2"],
  "freelance_potential": "High / Medium / Low",
  "summary": "2-3 sentence overview of this career in Pakistan's job market",
  "gov_vs_private": {{
    "gov_salary_pkr": "e.g. 70,000 (BPS-17 scale)",
    "gov_job_security": "Very High / High / Medium / Low",
    "gov_pension_benefits": "Yes / No / Partial",
    "gov_typical_grade": "e.g. BPS-17",
    "private_salary_pkr": "e.g. 80,000 - 120,000 starting",
    "private_bonuses": "High / Medium / Low",
    "private_growth_speed": "Fast / Moderate / Slow",
    "private_remote_work": "Yes / Partial / No"
  }},
  "overseas_opportunities": {{
    "score": 8,
    "accepted_countries": ["UAE", "Saudi Arabia", "UK", "Germany"],
    "overseas_salary_usd": "e.g. $3,000 - $6,000/mo",
    "needs_equivalency": "e.g. Yes (Requires PLAB/USMLE) / No"
  }},
  "gender_representation": {{
    "male_percentage": 65,
    "female_percentage": 35
  }}
}}
Return ONLY the JSON. No markdown. No explanation."""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1000,
        )
        raw = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw.strip())
        data["career"] = career_name
        data["data_source"] = "Live AI Web Search"
        return data
    except Exception as e:
        print(f"[MarketTrends] LLM parse error: {e}")
        # Fallback: return a template with clear indication data is estimated
        return {
            "career": career_name,
            "entry_salary_pkr": "50,000 - 80,000",
            "mid_salary_pkr": "100,000 - 160,000",
            "senior_salary_pkr": "200,000 - 350,000",
            "growth_rate": "Moderate",
            "job_market_trend": "Stable",
            "remote_friendly": "Partial",
            "competition_level": "Medium",
            "top_employers": ["Various Pakistani Companies"],
            "key_cities": ["Lahore", "Karachi", "Islamabad"],
            "skills_in_demand": ["Domain Knowledge", "Communication", "Problem Solving"],
            "certifications": ["Relevant Professional Certifications"],
            "freelance_potential": "Medium",
            "summary": f"{clean_name} is a growing career in Pakistan with opportunities across major cities.",
            "data_source": "Estimated (Live search unavailable)",
            "gov_vs_private": {
                "gov_salary_pkr": "65,000 (BPS-17)",
                "gov_job_security": "High",
                "gov_pension_benefits": "Yes",
                "gov_typical_grade": "BPS-17",
                "private_salary_pkr": "75,000 starting",
                "private_bonuses": "Medium",
                "private_growth_speed": "Moderate",
                "private_remote_work": "Partial"
            },
            "overseas_opportunities": {
                "score": 6,
                "accepted_countries": ["Gulf Countries", "UK"],
                "overseas_salary_usd": "$2,500 - $4,500/mo",
                "needs_equivalency": "Depends on destination country"
            },
            "gender_representation": {
                "male_percentage": 50,
                "female_percentage": 50
              }
        }


@app.get("/market-trends")
def market_trends(career: str, refresh: bool = False):
    """
    GET /market-trends?career=Software+Engineering
    Returns dynamic, AI-powered Pakistan job market data with 7-day SQLite caching.
    Supports all 38 career paths predicted by the ML model.
    Pass refresh=true to force a live re-fetch regardless of cache age.
    """
    CACHE_DAYS = 7
    now = datetime.datetime.utcnow()

    if not refresh:
        # Check cache
        try:
            with sqlite3.connect(DB_PATH) as db:
                row = db.execute(
                    "SELECT data_json, fetched_at FROM market_trends_cache WHERE career = ?",
                    (career,)
                ).fetchone()
            if row:
                fetched_at = datetime.datetime.fromisoformat(row[1])
                age_days = (now - fetched_at).days
                if age_days < CACHE_DAYS:
                    cached = json.loads(row[0])
                    cached["cache_status"] = "cached"
                    cached["cache_age_days"] = age_days
                    return cached
        except Exception as ce:
            print(f"[MarketTrends] Cache read error: {ce}")

    # Fetch live data
    try:
        data = _fetch_market_trends_live(career)
        data["cache_status"] = "live"
        data["cache_age_days"] = 0

        # Save to cache
        try:
            with sqlite3.connect(DB_PATH) as db:
                db.execute(
                    "INSERT OR REPLACE INTO market_trends_cache (career, data_json, fetched_at) VALUES (?, ?, ?)",
                    (career, json.dumps(data), now.isoformat())
                )
                db.commit()
        except Exception as se:
            print(f"[MarketTrends] Cache write error: {se}")

        return data
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch market trends: {str(e)}")


@app.post("/shap")
def shap_explain(req: dict):
    try:
        X = _build_feature_df(req)
        
        # TreeExplainer requires the exact same shape for shap_values
        shap_vals = shap_explainer.shap_values(X)

        # For multi-class, pick class with highest probability
        pred_class = int(xgb_model.predict(X)[0])
        
        if isinstance(shap_vals, list):
            sv = shap_vals[pred_class][0]
        else:
            if len(shap_vals.shape) == 3:
                sv = shap_vals[0, :, pred_class]
            else:
                sv = shap_vals[0]

        # Group SHAP values into 6 logical categories
        groups = {
            "Academic Stream": 0.0,
            "Academic Marks": 0.0,
            "Aptitude Test": 0.0,
            "Personality Profile": 0.0,
            "Interest Statement": 0.0,
            "Other Factors": 0.0
        }
        
        for i, col in enumerate(feature_names):
            val = float(sv[i])
            if col == "Stream":
                groups["Academic Stream"] += val
            elif col in ["FSc_Marks", "Marks_Biology", "Marks_Physics", "Marks_Chemistry", "Marks_Math", "Marks_Computer", "FSc_Percentage", "Avg_Subject_Marks"]:
                groups["Academic Marks"] += val
            elif col in ["Aptitude_Logic", "Aptitude_Verbal", "Aptitude_Spatial", "Aptitude_Math", "Aptitude_Avg"]:
                groups["Aptitude Test"] += val
            elif col in ["Psych_Openness", "Psych_Conscientiousness", "Psych_Extraversion", "Psych_Agreeableness", "Psych_Neuroticism"]:
                groups["Personality Profile"] += val
            elif col in ["Interest_R", "Interest_I", "Interest_A", "Interest_S", "Interest_E", "Interest_C", "Top_RIASEC_Score"]:
                groups["Interest Statement"] += val
            else:
                groups["Other Factors"] += val

        # Convert groups to list of dicts
        top_features = [
            {"feature": k, "value": round(v, 4)}
            for k, v in groups.items()
        ]
        
        # Sort by absolute SHAP impact
        top_features = sorted(top_features, key=lambda x: abs(x["value"]), reverse=True)
        return {"top_features": top_features, "predicted_class": pred_class}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


def _generate_mindmap_from_text(text: str) -> dict:
    import os, json
    from groq import Groq

    groq_key2 = os.environ.get("GROQ_API_KEY2", "")
    if not groq_key2:
        groq_key2 = os.environ.get("GROQ_API_KEY", "")

    if not groq_key2:
        raise Exception("Groq API key is not configured on the backend.")

    client = Groq(api_key=groq_key2.strip())
    system_prompt = (
        "You are an expert educational assistant specializing in visual conceptual learning. "
        "Analyze the provided study notes and extract all key concepts, their definitions, and how they relate.\n\n"
        "Return a clean JSON object with an 'elements' field containing 'nodes' and 'edges'. "
        "Strictly follow this schema:\n"
        "{\n"
        "  \"elements\": {\n"
        "    \"nodes\": [\n"
        "      { \"data\": { \"id\": \"unique_alphanumeric_id\", \"label\": \"Short Concept Name\", "
        "\"description\": \"Clear 1-2 sentence definition of this concept.\", "
        "\"type\": \"central\" } }\n"
        "    ],\n"
        "    \"edges\": [\n"
        "      { \"data\": { \"id\": \"unique_edge_id\", \"source\": \"source_node_id\", "
        "\"target\": \"target_node_id\", \"label\": \"relationship verb\" } }\n"
        "    ]\n"
        "  }\n"
        "}\n\n"
        "STRICT RULES:\n"
        "1. Node 'label' must be SHORT: max 4 words.\n"
        "2. Node 'description' must be an educational 1-2 sentence explanation.\n"
        "3. Node 'type' MUST be exactly ONE of these four values:\n"
        "   - 'central'    -> The single main topic of the notes (only 1 central node)\n"
        "   - 'subconcept' -> Direct major subtopics or components of the central concept\n"
        "   - 'detail'     -> Specific facts, properties, or methods of a subconcept\n"
        "   - 'example'    -> A concrete real-world example or instance\n"
        "4. Edge 'label' must be a short verb phrase: 'uses', 'contains', 'defines', 'is a type of', etc.\n"
        "5. All 'source' and 'target' values MUST exactly match an existing node 'id'.\n"
        "6. All 'id' fields must be unique, clean alphanumeric strings (no spaces or special chars).\n"
        "7. Output ONLY the raw JSON starting with { and ending with }. No markdown, no extra text."
    )

    response = client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Notes:\n{text}"}
        ],
        model="llama-3.3-70b-versatile",
        temperature=0.2,
        response_format={"type": "json_object"}
    )

    raw_content = response.choices[0].message.content.strip()
    parsed = json.loads(raw_content)
    return parsed


@app.post("/generate-mindmap")
def generate_mindmap(req: MindMapRequest):
    """
    Generate an interactive concept mind-map from study notes using GROQ_API_KEY2.
    """
    try:
        return _generate_mindmap_from_text(req.notes)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate mind-map: {str(e)}")


@app.post("/generate-mindmap/file")
async def generate_mindmap_file(file: UploadFile = File(...)):
    """
    Extract text from PDF or TXT files, and generate an interactive mind-map.
    """
    import io
    from pypdf import PdfReader

    filename = file.filename.lower()
    text = ""

    try:
        content = await file.read()
        if filename.endswith(".pdf"):
            pdf_file = io.BytesIO(content)
            reader = PdfReader(pdf_file)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        elif filename.endswith(".txt"):
            text = content.decode("utf-8", errors="ignore")
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Only PDF and TXT are supported.")

        if not text.strip():
            raise HTTPException(status_code=400, detail="Could not extract any readable text from the uploaded file.")

        # Truncate text if it's too long to prevent LLM token limit issues
        if len(text) > 8000:
            text = text[:8000] + "\n... [truncated]"

        return _generate_mindmap_from_text(text)

    except HTTPException as he:
        raise he
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")


@app.post("/diagnose-aptitude")
def diagnose_aptitude(req: AptitudeDiagnosticRequest):
    """
    Diagnose student aptitude performance, highlight the weakest category,
    and return AI-generated analysis, improvement tips, and practice questions.
    """
    import os, json
    from groq import Groq

    # 1. Identify weakest category
    scores = {
        "Logic": req.Aptitude_Logic,
        "Math": req.Aptitude_Math,
        "Verbal": req.Aptitude_Verbal,
        "Spatial": req.Aptitude_Spatial,
    }
    weakest_cat = min(scores, key=scores.get)
    weakest_val = scores[weakest_cat]

    # Pre-designed fallback packages in case of API failure or missing keys
    fallback_data = {
        "Logic": {
            "weakest_category": "Logic",
            "weakest_score": weakest_val,
            "analysis": "Your logic and reasoning score indicates that you may sometimes find it challenging to parse complex conditional statements, identify non-verbal patterns, or build step-by-step deductive structures. Developing logic skills is highly beneficial for computer programming, troubleshooting, law, and engineering.",
            "improvement_tips": [
                "Solve daily logical puzzles like Sudoku, nonograms, or cryptograms.",
                "Review basic logical operators (AND, OR, NOT) and truth tables.",
                "Practice deconstructing complex arguments into simple premises and conclusions."
            ],
            "practice_questions": [
                {
                    "id": 1,
                    "question": "All cats are mammals. Some mammals are carnivores. Based on this, is it true that some cats are definitely carnivores?",
                    "options": ["Yes, definitely", "No, not necessarily", "Mammals cannot be carnivores", "Cats are not mammals"],
                    "correct_answer": "No, not necessarily",
                    "explanation": "Just because all cats are mammals and some mammals are carnivores, it doesn't mean the carnivore mammals and the cat mammals overlap. Therefore, we cannot deduce that some cats are definitely carnivores."
                },
                {
                    "id": 2,
                    "question": "Look at this series: 2, 6, 18, 54, ... What number should come next?",
                    "options": ["108", "148", "162", "216"],
                    "correct_answer": "162",
                    "explanation": "This is a geometric progression where each term is multiplied by 3 to get the next term. 2 * 3 = 6; 6 * 3 = 18; 18 * 3 = 54; 54 * 3 = 162."
                },
                {
                    "id": 3,
                    "question": "A, B, C, and D are sitting in a row. A is to the immediate right of B. C is between B and D. Who is sitting on the far left?",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": "D",
                    "explanation": "If C is between B and D, they sit as D-C-B or B-C-D. Since A is to the immediate right of B, we must have D-C-B-A. Thus, D sits on the far left."
                }
            ]
        },
        "Math": {
            "weakest_category": "Math",
            "weakest_score": weakest_val,
            "analysis": "Your math and numerical reasoning score suggests that quantitative concepts, rate calculations, or statistics might take you more time to process. Strengthening math skills improves confidence in data science, finance, engineering, and business analytics.",
            "improvement_tips": [
                "Practice mental arithmetic and estimation in daily tasks.",
                "Use interactive math learning tools to review algebra, ratios, and percentages.",
                "Break word problems down by writing out what is given and what needs to be solved."
            ],
            "practice_questions": [
                {
                    "id": 1,
                    "question": "A product is originally priced at $80. It is discounted by 20%, and then that discounted price is increased by 10%. What is the final price?",
                    "options": ["$72.00", "$70.40", "$64.00", "$68.80"],
                    "correct_answer": "$70.40",
                    "explanation": "A 20% discount on $80 reduces it by $16, resulting in a price of $64. Increasing $64 by 10% adds $6.40, which equals $70.40."
                },
                {
                    "id": 2,
                    "question": "If a car travels at 60 mph for 45 minutes, how many miles does it travel?",
                    "options": ["45 miles", "40 miles", "50 miles", "30 miles"],
                    "correct_answer": "45 miles",
                    "explanation": "45 minutes is 3/4 (or 0.75) of an hour. Distance = Speed * Time = 60 * 0.75 = 45 miles."
                },
                {
                    "id": 3,
                    "question": "A bag contains 3 red balls and 7 blue balls. If you draw one ball at random, what is the probability that it is red?",
                    "options": ["30%", "70%", "3%", "10%"],
                    "correct_answer": "30%",
                    "explanation": "The probability is the number of red balls (3) divided by the total number of balls (3 + 7 = 10), which is 3/10 = 0.3 or 30%."
                }
            ]
        },
        "Verbal": {
            "weakest_category": "Verbal",
            "weakest_score": weakest_val,
            "analysis": "Your verbal and communication score suggests you might benefit from enriching your vocabulary, refining reading comprehension speed, or identifying structural relationships in texts. Verbal competence is key for law, humanities, marketing, and leadership roles.",
            "improvement_tips": [
                "Read diverse articles (science, history, editorial) and look up unfamiliar words immediately.",
                "Practice summarize-in-a-sentence exercises for paragraphs you read.",
                "Study word roots, prefixes, and suffixes to decode complex vocabulary."
            ],
            "practice_questions": [
                {
                    "id": 1,
                    "question": "Find the word that is closest in meaning to 'Ephemeral':",
                    "options": ["Eternal", "Short-lived", "Beautiful", "Deliberate"],
                    "correct_answer": "Short-lived",
                    "explanation": "'Ephemeral' means lasting for a very short time; transient or fleeting. 'Short-lived' is the closest synonym."
                },
                {
                    "id": 2,
                    "question": "Complete the analogy: Light is to Blind as Sound is to ___.",
                    "options": ["Deaf", "Noise", "Quiet", "Silence"],
                    "correct_answer": "Deaf",
                    "explanation": "Light is the sensory input that a blind person cannot perceive. Similarly, sound is the sensory input that a deaf person cannot perceive."
                },
                {
                    "id": 3,
                    "question": "Choose the word that best fits the blank: 'Although she spoke with great conviction, the audience remained ___.'",
                    "options": ["Skeptical", "Enthusiastic", "Convinced", "Attentive"],
                    "correct_answer": "Skeptical",
                    "explanation": "The word 'Although' signals a contrast. If she spoke with great conviction, the contrast is that the audience did not believe her, making 'skeptical' the best choice."
                }
            ]
        },
        "Spatial": {
            "weakest_category": "Spatial",
            "weakest_score": weakest_val,
            "analysis": "Your spatial and visual thinking score indicates that mental rotation of shapes, 3D visualization, or map navigation might be less intuitive for you. Spatial skills are essential for design, architecture, dentistry, chemistry, and structural engineering.",
            "improvement_tips": [
                "Spend time sketching, modeling, or playing 3D video games that require mapping.",
                "Practice folding paper, solving origami puzzles, or assembling tangram patterns.",
                "Examine blueprints, maps, and diagrams, translating them into physical models."
            ],
            "practice_questions": [
                {
                    "id": 1,
                    "question": "If you look at a standard clock at 3:15, what is the approximate angle between the hour hand and the minute hand?",
                    "options": ["0 degrees", "7.5 degrees", "15 degrees", "90 degrees"],
                    "correct_answer": "7.5 degrees",
                    "explanation": "At 3:15, the minute hand is pointing exactly at 3. However, the hour hand has moved forward by 15 minutes, which is 1/4 of an hour. Since the hour hand moves 30 degrees per hour, it will have moved 30 * 0.25 = 7.5 degrees away from 3."
                },
                {
                    "id": 2,
                    "question": "Imagine a paper is folded in half, and a single diamond shape is cut out from the center of the fold. When the paper is unfolded, what does it show?",
                    "options": ["Two diamonds", "One diamond", "One circle", "Two circles"],
                    "correct_answer": "One diamond",
                    "explanation": "Since the diamond was cut directly out of the fold itself, unfolding it will open the half-cuts into a single, complete diamond shape at the center."
                },
                {
                    "id": 3,
                    "question": "Which of these objects has the most faces?",
                    "options": ["Cube", "Triangular Pyramid", "Pentagonal Prism", "Square Pyramid"],
                    "correct_answer": "Pentagonal Prism",
                    "explanation": "A Cube has 6 faces. A Triangular Pyramid has 4 faces. A Pentagonal Prism has 7 faces (2 pentagonal bases + 5 rectangular sides). A Square Pyramid has 5 faces. Thus, Pentagonal Prism has the most."
                }
            ]
        }
    }

    # 2. Check for Groq API keys and try dynamic generation
    groq_key = os.environ.get("GROQ_API_KEY2", "")
    if not groq_key:
        groq_key = os.environ.get("GROQ_API_KEY", "")

    if not groq_key:
        # Return fallback data
        return fallback_data[weakest_cat]

    try:
        client = Groq(api_key=groq_key.strip())
        system_prompt = (
            "You are an expert cognitive psychologist and educational assessor.\n"
            f"Analyze the student's weakest aptitude category: '{weakest_cat}' (Score: {weakest_val}%).\n"
            "Generate a structured diagnostic assessment in JSON format. Follow this schema exactly:\n"
            "{\n"
            "  \"weakest_category\": \"CategoryName\",\n"
            "  \"weakest_score\": 40,\n"
            "  \"analysis\": \"A detailed 2-3 sentence critique explaining what this cognitive weakness means for their learning/career.\",\n"
            "  \"improvement_tips\": [\n"
            "    \"Tip 1\",\n"
            "    \"Tip 2\",\n"
            "    \"Tip 3\"\n"
            "  ],\n"
            "  \"practice_questions\": [\n"
            "    {\n"
            "      \"id\": 1,\n"
            "      \"question\": \"Medium difficulty question text?\",\n"
            "      \"options\": [\"Option A\", \"Option B\", \"Option C\", \"Option D\"],\n"
            "      \"correct_answer\": \"Option A\",\n"
            "      \"explanation\": \"Detailed logic explanation of why this answer is correct.\"\n"
            "    }\n"
            "  ]\n"
            "}\n"
            "Rules:\n"
            "1. Output ONLY the raw JSON. Do not include markdown blocks like ```json or any other text.\n"
            "2. Generate exactly 3 highly relevant and educational multiple-choice practice questions.\n"
            "3. The correct_answer string MUST exactly match one of the items in the options array."
        )

        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Please diagnose the weakness in '{weakest_cat}' with score {weakest_val}%."}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        raw_content = response.choices[0].message.content.strip()
        parsed = json.loads(raw_content)
        # Ensure we have all required fields
        if all(k in parsed for k in ["weakest_category", "analysis", "improvement_tips", "practice_questions"]):
            return parsed
        else:
            raise Exception("JSON missing required fields.")
    except Exception as e:
        traceback.print_exc()
        # Fallback to local data
        return fallback_data[weakest_cat]


@app.post("/chat")
def chat(req: ChatRequest, user=Depends(get_current_user)):
    """Roshni AI Counselor — with Mem0 memory + Groq LLM + Supabase Persistence."""
    import os

    print(f"\n[DEBUG /chat] Incoming request message: '{req.message}'")
    print(f"[DEBUG /chat] Authorization/User resolved: {user}")
    if user:
        print(f"[DEBUG /chat] Resolved User ID: {user.id}")

    career = req.recommended_career
    user_id = req.user_id or "anonymous"
    conversation_history = []

    # Supabase chat persistence setup. No conversation_id means start a new thread.
    conversation_id = req.conversation_id or ""
    student_id = None
    if user:
        student_id = user.id
        user_id = user.id
        print(f"[DEBUG /chat] student_id={student_id} message={req.message!r} requested_conversation_id={conversation_id!r}")
        try:
            if conversation_id:
                existing = get_conversation_for_student(conversation_id, student_id)
                if not existing:
                    raise HTTPException(status_code=404, detail="Conversation not found for this student")
                conversation_history = get_conversation_history(conversation_id, student_id=student_id, limit=20, for_llm=True)
                print(f"[DEBUG /chat] Continuing conversation {conversation_id}; prior messages={len(conversation_history)}")
            else:
                conversation_id = create_conversation(student_id, req.message)
                print(f"[DEBUG /chat] Created new conversation ID: {conversation_id}")

            if conversation_id:
                save_res = save_message(
                    conversation_id=conversation_id,
                    student_id=student_id,
                    role="user",
                    content=req.message,
                    is_voice=req.voice_mode,
                )
                print(f"[DEBUG /chat] User message save result: {save_res}")
            else:
                print("[DEBUG /chat] Warning: conversation_id is empty; user message not saved.")
        except HTTPException:
            raise
        except Exception as e:
            print(f"[Chat] Supabase save user message error: {e}")
            traceback.print_exc()

    # Retrieve Mem0 memory for this student.
    # [MEM0 LOG] Incoming chat message logging
    print(f"[MEM0 LOG] Incoming chat message. student_id: {user_id}, message: {req.message}")
    
    # Retrieve Mem0 memory for this student.
    print(f"[MEM0 LOG] Retrieving memories for query: {req.message}")
    memory_context = search_memory(user_id, req.message)
    print(f"[MEM0 LOG] Retrieved memories context: {memory_context}")

    # ── 2. Build reference context from Excel data ────────────────────────────
    context_parts = []
    if user:
        try:
            structured_context = _build_structured_student_context(user.id, fallback_career=career)
            if structured_context:
                context_parts.append(structured_context)
        except Exception as prof_err:
            print(f"[Chat] Load structured context failed: {prof_err}")
            traceback.print_exc()

    if not career and user:
        profile = get_student_profile(user.id)
        career = profile.get("target_career", "") if profile else ""

    youtube_videos = []
    if _is_youtube_request(req.message):
        try:
            from scrapers.youtube_api import search_youtube_videos

            youtube_query = req.message.strip()
            if career:
                youtube_query = f"{career} {youtube_query}"
            youtube_videos = search_youtube_videos(youtube_query)
            if youtube_videos:
                context_parts.append(_format_youtube_results(youtube_videos))
        except Exception as yt_err:
            print(f"[Chat] YouTube lookup failed: {yt_err}")
            traceback.print_exc()

    if "scholarship" in req.message.lower():
        try:
            sch = scholarship_df.dropna(subset=[scholarship_df.columns[0]])
            sch_info = sch[[scholarship_df.columns[0], scholarship_df.columns[3], scholarship_df.columns[4]]].head(5)
            context_parts.append("Available Scholarships:\n" + sch_info.to_string(index=False))
        except Exception:
            pass

    if req.city:
        try:
            city_unis = uni_df[uni_df.iloc[:, 0].str.contains(req.city, case=False, na=False)].head(5)
            if not city_unis.empty:
                context_parts.append(f"Universities in {req.city}:\n" + city_unis.to_string(index=False))
        except Exception:
            pass

    context = "\n\n".join(context_parts)

    # ── 3. Build Roshni system prompt with memory + context ───────────────────
    sys_prompt = build_system_prompt(
        context=context,
        memory_context=memory_context,
        voice_mode=req.voice_mode
    )

    # ── 4. Try Groq API with Tool Calling ────────────────────────────────────
    groq_key = os.environ.get("GROQ_API_KEY", "")
    ai_response = None
    search_used = False
    
    if groq_key:
        try:
            from groq import Groq
            client = Groq(api_key=groq_key)
            messages = [{"role": "system", "content": sys_prompt}]
            history_for_prompt = conversation_history[-8:] if conversation_history else (req.history or [])[-6:]
            for h in history_for_prompt:
                messages.append(h)
            messages.append({"role": "user", "content": req.message})

            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "google_search",
                        "description": (
                            "Search the web using DuckDuckGo for study guides, past papers, date sheets, "
                            "syllabus documents, admission details, or general educational resources in Pakistan."
                        ),
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "The search query (e.g. 'BISE Lahore 12th class Chemistry past papers 2024')"
                                }
                            },
                            "required": ["query"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "web_scrape",
                        "description": "Scrape/read the text content of a specific web page URL to get detailed notes, eligibility steps, or schedules.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "url": {
                                    "type": "string",
                                    "description": "The target website URL to scrape (must start with http:// or https://)"
                                }
                            },
                            "required": ["url"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_youtube_videos",
                        "description": "Search YouTube for learning tutorials, career introduction videos, or university preparation playlists.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "The search query for YouTube (e.g. 'React JS course for beginners in Urdu')"
                                }
                            },
                            "required": ["query"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_online_courses",
                        "description": "Search online learning platforms (Udemy, Coursera) for courses on a specific subject.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "Topic or keyword to find courses (e.g. 'Ethical hacking course')"
                                }
                            },
                            "required": ["query"]
                        }
                    }
                }
            ]

            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                max_tokens=800,
                temperature=0.4,
                tools=tools,
                tool_choice="auto"
            )
            
            response_msg = resp.choices[0].message
            
            if response_msg.tool_calls:
                # LLM requested tool execution
                messages.append(response_msg)
                
                for tool_call in response_msg.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    
                    # Execute tool
                    tool_result = _execute_tool(tool_name, tool_args)
                    search_used = True
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": json.dumps(tool_result)
                    })
                
                # Second pass to get final answer
                final_resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages,
                    max_tokens=800,
                    temperature=0.4
                )
                ai_response = final_resp.choices[0].message.content
            else:
                ai_response = response_msg.content
                
        except Exception as e:
            print(f"[Chat] Groq tool-calling flow error: {e}")

    # ── 5. Fallback to rule-based if no LLM response ─────────────────────────
    if not ai_response:
        msg_lower = req.message.lower()
        rm = _get_roadmap_data(career) if career else {}
        if youtube_videos:
            ai_response = _format_youtube_results(youtube_videos)
        if "roadmap" in msg_lower or "steps" in msg_lower:
            steps = rm.get("roadmap_steps", [])
            ai_response = f"Here is the roadmap for {career}:\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps)) if steps else f"Please visit /roadmap for {career} details."
        elif "universit" in msg_lower:
            unis = rm.get("top_universities", [])
            ai_response = f"Top universities for {career} in Pakistan: {', '.join(unis)}" if unis else "Check HEC website for university rankings."
        elif "skill" in msg_lower:
            skills = rm.get("skills_required", [])
            ai_response = f"Key skills for {career}: {', '.join(skills)}" if skills else "Focus on core subject skills and communication."
        elif "scholarship" in msg_lower:
            ai_response = "Key scholarships: HEC Need-Based (merit + need), Ehsaas Undergraduate, Punjab Educational Endowment Fund (PEEF), Aga Khan Foundation. Apply after FSc result."
        elif "salary" in msg_lower:
            ai_response = f"Entry-level salary for {career} in Pakistan: {rm.get('avg_entry_salary', 'varies by employer and location')}."
        else:
            ai_response = f"As your AI career counselor, I'm here to help you with questions about {career or 'your career path'}. Ask me about roadmaps, universities, scholarships, or skills!"

    # ── 6. Save assistant message to Supabase ─────────────────────────────────
    if user and conversation_id:
        try:
            print(f"[DEBUG /chat] Calling save_message for assistant message in conversation {conversation_id}...")
            save_res = save_message(
                conversation_id=conversation_id,
                student_id=student_id,
                role="assistant",
                content=ai_response,
                search_used=search_used
            )
            print(f"[DEBUG /chat] Assistant message save result: {save_res}")
        except Exception as e:
            print(f"[Chat] Supabase save assistant message error: {e}")

    # ── 7. Save this conversation turn to Mem0 ────────────────────────────────
    try:
        save_memory(user_id, [
            {"role": "user", "content": req.message},
            {"role": "assistant", "content": ai_response}
        ])
    except Exception as e:
        print(f"[Chat] Memory save error: {e}")

    return {"response": ai_response, "conversation_id": conversation_id}



@app.post("/voice")
async def voice_transcribe(audio: UploadFile = File(...)):
    """Transcribe voice input (Urdu/English) using local Whisper model."""
    try:
        audio_bytes = await audio.read()
        suffix = "." + (audio.filename.split(".")[-1] if audio.filename else "wav")
        result = transcribe_audio_bytes(audio_bytes, suffix=suffix)
        return {
            "text": result["text"],
            "language": result["language"],
            "segments": result["segments"]
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search")
async def search_resources(req: SearchRequest):
    """Search YouTube, scholarships, and courses via web scrapers."""
    try:
        from scrapers.master_scraper import get_resources_for_query
        results = await get_resources_for_query(req.query, req.resource_type)
        return results
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memory/{user_id}")
def get_student_memory(user_id: str):
    """Retrieve all stored memories for a student."""
    memories = get_all_memories(user_id)
    return {"user_id": user_id, "memories": memories}


@app.post("/save_session")
def save_session(req: SaveSessionRequest):
    """Persist prediction session to SQLite."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            INSERT INTO sessions
                (student_name, city, stream, marks_matric, marks_fsc,
                 primary_recommendation, full_prediction_json, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            req.student.get("name", ""),
            req.student.get("City", ""),
            req.student.get("Stream", ""),
            req.student.get("Matric_Marks", 0),
            req.student.get("FSc_Marks", 0),
            req.prediction.get("primary_recommendation", {}).get("career", ""),
            json.dumps(req.prediction),
            datetime.datetime.now().isoformat(),
        ))
        conn.commit()
        conn.close()
        return {"status": "saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/export_pdf")
def export_pdf(req: ExportPdfRequest):
    """Generate a personalized PDF career report."""
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                leftMargin=2*cm, rightMargin=2*cm,
                                topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        story = []

        title_style = ParagraphStyle("title", parent=styles["Title"],
                                     fontSize=22, textColor=colors.HexColor("#00e5ff"),
                                     spaceAfter=12)
        h2_style = ParagraphStyle("h2", parent=styles["Heading2"],
                                  fontSize=14, textColor=colors.HexColor("#0d9488"),
                                  spaceAfter=6)
        body_style = ParagraphStyle("body", parent=styles["Normal"],
                                    fontSize=11, leading=16, spaceAfter=4)

        student = req.student
        pred = req.prediction
        primary = pred.get("primary_recommendation", {})
        recommendations = pred.get("recommendations", [])

        # Header
        story.append(Paragraph("FuturePath AI Career Report", title_style))
        story.append(Paragraph(f"Student: {student.get('name', 'N/A')}", h2_style))
        story.append(Paragraph(f"Generated: {datetime.datetime.now().strftime('%d %B %Y, %I:%M %p')}", body_style))
        story.append(Spacer(1, 0.5*cm))

        # Profile table
        story.append(Paragraph("Student Profile", h2_style))
        profile_data = [
            ["City", student.get("City",""), "Stream", student.get("Stream","")],
            ["Matric Marks", str(student.get("Matric_Marks","")), "FSc Marks", str(student.get("FSc_Marks",""))],
            ["Activity", student.get("Extracurricular_Activity",""), "Model Used", pred.get("used_model","")],
        ]
        t = Table(profile_data, colWidths=[4*cm, 5*cm, 4*cm, 4.5*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#0d1117")),
            ("TEXTCOLOR", (0,0), (-1,-1), colors.white),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#30363d")),
            ("FONTSIZE", (0,0), (-1,-1), 10),
            ("PADDING", (0,0), (-1,-1), 6),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.5*cm))

        # Primary recommendation
        story.append(Paragraph("Primary Career Recommendation", h2_style))
        story.append(Paragraph(
            f"<b>{primary.get('career','N/A')}</b> — {round(primary.get('probability',0)*100,1)}% match confidence",
            body_style
        ))
        story.append(Paragraph(primary.get("description",""), body_style))
        story.append(Spacer(1, 0.3*cm))

        # Roadmap steps
        steps = primary.get("roadmap_steps", [])
        if steps:
            story.append(Paragraph("Career Roadmap", h2_style))
            for i, step in enumerate(steps, 1):
                story.append(Paragraph(f"{i}. {step}", body_style))
            story.append(Spacer(1, 0.3*cm))

        # Skills
        skills = primary.get("skills_required", [])
        if skills:
            story.append(Paragraph("Skills to Develop", h2_style))
            story.append(Paragraph(", ".join(skills), body_style))
            story.append(Spacer(1, 0.3*cm))

        # Universities
        unis = primary.get("top_universities", [])
        if unis:
            story.append(Paragraph("Recommended Universities in Pakistan", h2_style))
            story.append(Paragraph(", ".join(unis), body_style))
            story.append(Spacer(1, 0.3*cm))

        # Other recommendations
        if len(recommendations) > 1:
            story.append(Paragraph("Other Top Career Matches", h2_style))
            for r in recommendations[1:]:
                story.append(Paragraph(
                    f"• <b>{r['career']}</b> ({round(r['probability']*100,1)}% match)",
                    body_style
                ))

        story.append(Spacer(1, 1*cm))
        story.append(Paragraph(
            "Powered by FuturePath AI — Dissertation Project | All recommendations are AI-generated and should be verified with a professional counselor.",
            ParagraphStyle("footer", parent=styles["Normal"], fontSize=8, textColor=colors.grey)
        ))

        doc.build(story)
        buffer.seek(0)
        return StreamingResponse(buffer, media_type="application/pdf",
                                 headers={"Content-Disposition": "attachment; filename=AI_Career_Report.pdf"})
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# New Schemas for Saved Resources & Entry Test Scores
class SavedResourceRequest(BaseModel):
    title: str
    url: str
    resource_type: str = "other"
    notes: Optional[str] = ""

class EntryTestScoreRequest(BaseModel):
    test_type: str
    subject: str
    score: Optional[float] = None
    total: float
    weak_topics: Optional[List[str]] = []

@app.post("/save_resource")
def api_save_resource(req: SavedResourceRequest, user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    from supabase_client import get_supabase_admin
    sb_admin = get_supabase_admin()
    if not sb_admin:
        raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        res = sb_admin.table("saved_resources").insert({
            "student_id": user.id,
            "title": req.title,
            "url": req.url,
            "resource_type": req.resource_type,
            "notes": req.notes
        }).execute()
        return {"status": "saved", "data": res.data[0] if res.data else {}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/saved_resources")
def api_get_saved_resources(user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    from supabase_client import get_supabase_admin
    sb_admin = get_supabase_admin()
    if not sb_admin:
        return []
    try:
        res = sb_admin.table("saved_resources").select("*").eq("student_id", user.id).order("saved_at", desc=True).execute()
        return res.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/save_entry_test_score")
def api_save_entry_test_score(req: EntryTestScoreRequest, user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    from supabase_client import get_supabase_admin
    sb_admin = get_supabase_admin()
    if not sb_admin:
        raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        res = sb_admin.table("entry_test_scores").insert({
            "student_id": user.id,
            "test_type": req.test_type,
            "subject": req.subject,
            "score": req.score,
            "total": req.total,
            "weak_topics": req.weak_topics
        }).execute()
        return {"status": "saved", "data": res.data[0] if res.data else {}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/entry_test_scores")
def api_get_entry_test_scores(user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    from supabase_client import get_supabase_admin
    sb_admin = get_supabase_admin()
    if not sb_admin:
        return []
    try:
        res = sb_admin.table("entry_test_scores").select("*").eq("student_id", user.id).order("taken_at", desc=True).execute()
        return res.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
