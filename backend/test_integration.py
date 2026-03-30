#!/usr/bin/env python3
"""Integration test: Simulate frontend's predict + audit flow."""

import httpx
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def test_simulator_flow():
    """Test the complete simulator flow: predict + fetch contributions."""
    
    print("=" * 70)
    print("INTEGRATION TEST: Simulator Flow (Predict + Audit)")
    print("=" * 70)
    
    payload = {
        "scenario": "hiring",
        "features": {
            "experience": 4,
            "education_level": "bachelors",
            "college_tier": "other",
            "skills_score": 72,
            "expected_salary": 90000,
            "gender": "female",
            "caste": "general",
            "religion": "hindu"
        }
    }
    
    print(f"\n1. Calling /predict...")
    print(f"   Payload: {json.dumps(payload, indent=2)}")
    
    try:
        start_time = time.time()
        response1 = requests.post(f"{BASE_URL}/predict", json=payload, timeout=10)
        elapsed1 = time.time() - start_time
        
        print(f"   Status: {response1.status_code}")
        print(f"   Time: {elapsed1:.2f}s")
        
        if response1.status_code != 200:
            print(f"   ERROR: {response1.text}")
            return False
        
        data1 = response1.json()
        print(f"   Response: {json.dumps(data1, indent=2)}")
        
    except Exception as e:
        print(f"   FAILED: {e}")
        return False
    
    print(f"\n2. Calling /audit/current...")
    print(f"   Using same payload features")
    
    audit_payload = {
        "scenario": "hiring",
        "features": payload["features"]
    }
    
    try:
        start_time = time.time()
        response2 = requests.post(f"{BASE_URL}/audit/current", json=audit_payload, timeout=10)
        elapsed2 = time.time() - start_time
        
        print(f"   Status: {response2.status_code}")
        print(f"   Time: {elapsed2:.2f}s")
        
        if response2.status_code != 200:
            print(f"   ERROR: {response2.text}")
            return False
        
        data2 = response2.json()
        print(f"\n   Contributions: {json.dumps(data2.get('contributions', {}), indent=2)}")
        
    except Exception as e:
        print(f"   FAILED: {e}")
        return False
    
    print(f"\n3. Comparing predictions...")
    
    if data1["biased_prediction"] == data2["biased_prediction"]:
        print(f"   ✓ Biased predictions match: {data1['biased_prediction']}")
    else:
        print(f"   ✗ Biased predictions differ: {data1['biased_prediction']} vs {data2['biased_prediction']}")
        return False
    
    if data1["fair_prediction"] == data2["fair_prediction"]:
        print(f"   ✓ Fair predictions match: {data1['fair_prediction']}")
    else:
        print(f"   ✗ Fair predictions differ: {data1['fair_prediction']} vs {data2['fair_prediction']}")
        return False
    
    if abs(data1["fair_probability"] - data2["fair_probability"]) < 0.0001:
        print(f"   ✓ Fair probabilities match: {data1['fair_probability']:.4f}")
    else:
        print(f"   ✗ Fair probabilities differ: {data1['fair_probability']:.4f} vs {data2['fair_probability']:.4f}")
        return False
    
    if abs(data1["bias_gap"] - data2["bias_gap"]) < 0.0001:
        print(f"   ✓ Bias gaps match: {data1['bias_gap']:.4f}")
    else:
        print(f"   ✗ Bias gaps differ: {data1['bias_gap']:.4f} vs {data2['bias_gap']:.4f}")
        return False
    
    print(f"\n4. Testing with different scenarios...")
    
    for scenario in ["loan_approval", "college_admission"]:
        print(f"\n   Testing {scenario}...")
        
        scenarios = {
            "loan_approval": {
                "loan_amount": 800000,
                "interest_rate": 10.5,
                "monthly_income": 70000,
                "profession": "salaried",
                "gender": "female",
                "caste": "general",
                "religion": "hindu"
            },
            "college_admission": {
                "entrance_score": 78,
                "family_income": 550000,
                "parents_education": "graduate",
                "previous_academic_score": 82,
                "gender": "female",
                "caste": "general",
                "religion": "hindu"
            }
        }
        
        test_payload = {
            "scenario": scenario,
            "features": scenarios[scenario]
        }
        
        try:
            r1 = requests.post(f"{BASE_URL}/predict", json=test_payload, timeout=10)
            r2 = requests.post(f"{BASE_URL}/audit/current", json={
                "scenario": scenario,
                "features": scenarios[scenario]
            }, timeout=10)
            
            if r1.status_code == 200 and r2.status_code == 200:
                print(f"      ✓ Both API calls succeeded")
            else:
                print(f"      ✗ API call failed: predict={r1.status_code}, audit={r2.status_code}")
                return False
        except Exception as e:
            print(f"      ✗ Error: {e}")
            return False
    
    print(f"\n{'=' * 70}")
    print("✓ ALL TESTS PASSED")
    print("=" * 70)
    return True

if __name__ == "__main__":
    success = test_simulator_flow()
    exit(0 if success else 1)
