"""
Student Profile CRUD — read/update student data from Supabase.
"""

from supabase_client import get_supabase_admin as get_supabase


def get_student_profile(user_id: str) -> dict:
    """Get full student profile from Supabase."""
    sb = get_supabase()
    if not sb:
        return {}
    try:
        result = sb.table("students") \
            .select("*") \
            .eq("id", user_id) \
            .single() \
            .execute()
        return result.data or {}
    except Exception as e:
        print(f"[StudentDB] Get profile failed: {e}")
        return {}


def update_student_profile(user_id: str, updates: dict) -> dict:
    """Update student profile — only safe fields allowed."""
    sb = get_supabase()
    if not sb:
        return {}

    allowed = [
        "full_name", "phone", "city", "fsc_stream",
        "fsc_percentage", "matric_percentage", "target_career",
        "target_university", "entry_test_planned", "preferred_language",
        "matric_marks", "fsc_marks", "marks_math", "marks_physics", "marks_chemistry", "marks_computer", "marks_biology",
        "aptitude_logic", "aptitude_verbal", "aptitude_spatial", "aptitude_math",
        "psych_openness", "psych_conscientiousness", "psych_extraversion", "psych_agreeableness", "psych_neuroticism",
        "interest_r", "interest_i", "interest_a", "interest_s", "interest_e", "interest_c", "interest_text",
        "extracurricular_activity", "sentiment_label", "model_name", "prediction_recommendations", "prediction_explanation", "last_prediction_result", "shap_explanation"
    ]
    clean = {k: v for k, v in updates.items() if k in allowed}
    clean["updated_at"] = "now()"

    try:
        result = sb.table("students") \
            .update(clean) \
            .eq("id", user_id) \
            .execute()
        return result.data[0] if result.data else {}
    except Exception as e:
        print(f"[StudentDB] Update failed: {e}")
        return {}


def get_student_context_for_llm(user_id: str) -> str:
    """Build a context string from the student profile to inject into system prompt."""
    profile = get_student_profile(user_id)
    if not profile:
        return ""

    lines = []
    if profile.get("fsc_stream"):
        lines.append(f"FSc stream: {profile['fsc_stream']}")
    if profile.get("fsc_percentage"):
        lines.append(f"FSc percentage: {profile['fsc_percentage']}%")
    if profile.get("matric_percentage"):
        lines.append(f"Matric percentage: {profile['matric_percentage']}%")
    if profile.get("target_career"):
        lines.append(f"Target career: {profile['target_career']}")
    if profile.get("target_university"):
        lines.append(f"Target university: {profile['target_university']}")
    if profile.get("city"):
        lines.append(f"City: {profile['city']}")
    if profile.get("entry_test_planned"):
        lines.append(f"Entry test: {profile['entry_test_planned']}")

    return "\n".join(lines) if lines else ""
