#!/usr/bin/env python3
"""Test prediction consistency across multiple calls."""

from app.main import _bootstrap_models, state, _normalize_features
from app.core.model import predict_single

def test_determinism():
    _bootstrap_models()
    
    profiles = {
        'hiring_strong': ('hiring', {
            'experience': 8,
            'education_level': 'masters',
            'college_tier': 'iit',
            'skills_score': 90,
            'expected_salary': 120000,
            'gender': 'male',
            'caste': 'general',
            'religion': 'hindu'
        }),
        'hiring_weak': ('hiring', {
            'experience': 0.5,
            'education_level': 'high_school',
            'college_tier': 'other',
            'skills_score': 35,
            'expected_salary': 180000,
            'gender': 'female',
            'caste': 'sc',
            'religion': 'muslim'
        }),
    }
    
    print("=" * 70)
    print("DETERMINISM TEST: Multiple predictions with same input")
    print("=" * 70)
    
    for profile_name, (scenario, features) in profiles.items():
        bundle = state.scenario_bundles[scenario]
        normalized = _normalize_features(features, scenario)
        fair_features = {k: v for k, v in normalized.items() if k not in ['gender', 'caste', 'religion']}
        
        # Test multiple times
        results = []
        for trial in range(3):
            _, biased_prob = predict_single(bundle.biased_model, normalized)
            _, fair_prob = predict_single(bundle.fair_model, fair_features)
            results.append({
                'biased': round(biased_prob, 4),
                'fair': round(fair_prob, 4),
                'gap': round(abs(biased_prob - fair_prob), 4)
            })
        
        # Check consistency
        consistent = all(r == results[0] for r in results)
        
        print(f"\n{profile_name}:")
        print(f"  Trial 1: biased={results[0]['biased']:6.4f}, fair={results[0]['fair']:6.4f}, gap={results[0]['gap']:6.4f}")
        print(f"  Consistent across 3 trials: {'✓ YES' if consistent else '✗ NO'}")
        
        if not consistent:
            for i, r in enumerate(results, 1):
                print(f"    Trial {i}: biased={r['biased']:6.4f}, fair={r['fair']:6.4f}, gap={r['gap']:6.4f}")

if __name__ == '__main__':
    test_determinism()
