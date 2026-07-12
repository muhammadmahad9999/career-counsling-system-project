import requests
import sys

SAMPLE_STUDENT = {
    "name": "E2E Test Student",
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

def main():
    print("Sending /predict request to FastAPI server...")
    url = "http://127.0.0.1:8000/predict"
    
    try:
        response = requests.post(url, json=SAMPLE_STUDENT)
        print(f"Response status code: {response.status_code}")
        
        if response.status_code != 200:
            print("ERROR: Response was not 200 OK")
            print(response.text)
            sys.exit(1)
            
        data = response.json()
        print("\n--- Prediction Output ---")
        print(f"Primary Recommendation: {data.get('primary_recommendation')}")
        print("\nAll Recommendations:")
        for rec in data.get("recommendations", []):
            print(f"  Rank {rec['rank']}: {rec['career']} (Prob: {rec['probability']:.4f})")
            
        # Verify fields
        assert "primary_recommendation" in data, "Missing primary_recommendation"
        assert "recommendations" in data, "Missing recommendations list"
        assert len(data["recommendations"]) == 3, "Expected exactly 3 recommendations"
        
        print("\nSUCCESS: E2E prediction endpoint verified successfully!")
        
    except Exception as e:
        print(f"E2E Test Failed with Exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
