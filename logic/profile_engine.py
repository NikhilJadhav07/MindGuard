from models import db, UserMentalProfile, AssessmentResult
import json
from datetime import datetime

class ProfileEngine:
    def __init__(self):
        pass

    def update_profile(self, user_id, assessment_data):
        """
        Updates the UserMentalProfile based on a new assessment result.
        """
        profile = UserMentalProfile.query.filter_by(user_id=user_id).first()
        if not profile:
            profile = UserMentalProfile(
                user_id=user_id,
                symptom_frequency={},
                severity_trend=[]
            )
            db.session.add(profile)
        
        # 1. Update Symptom Frequency
        # assessment_data['symptoms'] is a list of strings
        current_freq = profile.symptom_frequency or {}
        new_symptoms = assessment_data.get('symptoms', [])
        
        for symptom in new_symptoms:
            if symptom in current_freq:
                current_freq[symptom] += 1
            else:
                current_freq[symptom] = 1
        
        profile.symptom_frequency = current_freq
        
        # 2. Update Severity Trend & Dominant Condition
        # assessment_data['predictions'] contains probabilities
        predictions = assessment_data.get('predictions', [])
        if predictions:
            # Find max probability condition
            top_prediction = max(predictions, key=lambda x: x['probability'])
            profile.dominant_condition = top_prediction['condition']
            
            # Estimate risk level based on probability
            prob = top_prediction['probability']
            if prob > 75:
                profile.risk_level = 'High'
            elif prob > 50:
                profile.risk_level = 'Moderate'
            else:
                profile.risk_level = 'Low'
            
            # Update trend
            current_trend = profile.severity_trend or []
            current_trend.append({
                "date": datetime.utcnow().strftime('%Y-%m-%d'),
                "condition": top_prediction['condition'],
                "score": prob
            })
            # Keep last 20 entries to avoid bloat
            profile.severity_trend = current_trend[-20:]
            
            # Update average confidence
            profile.average_confidence = prob # For now just set to latest, or average it properly
        
        profile.last_updated = datetime.utcnow()
        db.session.commit()
        return profile

    def get_profile_context(self, user_id):
        """
        Returns a context dictionary for the interview engine.
        """
        profile = UserMentalProfile.query.filter_by(user_id=user_id).first()
        if not profile:
            return None
            
        return {
            "dominant_condition": profile.dominant_condition,
            "risk_level": profile.risk_level,
            "frequent_symptoms": sorted(
                profile.symptom_frequency.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:3] if profile.symptom_frequency else []
        }
