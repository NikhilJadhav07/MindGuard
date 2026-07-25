from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessment_result.id'), nullable=True)
    
    # Active Metrics
    accuracy_rating = db.Column(db.Integer) # 1-5
    emotional_relevance_score = db.Column(db.Integer) # 1-5
    user_confidence_before = db.Column(db.Integer) # 1-10
    user_confidence_after = db.Column(db.Integer) # 1-10
    
    missed_symptoms = db.Column(db.Text) # Text or comma-separated symptoms
    free_text_feedback = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('feedbacks', lazy=True))
    assessment = db.relationship('AssessmentResult', backref=db.backref('feedback_data', uselist=False))

class UserMentalProfile(db.Model):
    """
    Stores long-term mental health profile for the user.
    Updated after every assessment.
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Core Profile Data
    dominant_condition = db.Column(db.String(50)) # e.g., 'Anxiety'
    risk_level = db.Column(db.String(20)) # 'Low', 'Moderate', 'High'
    average_confidence = db.Column(db.Float) # Average confidence of past assessments
    
    # Trends (stored as JSON)
    symptom_frequency = db.Column(db.JSON) # e.g., {"insomnia": 5, "fatigue": 2}
    severity_trend = db.Column(db.JSON) # e.g., [{"date": "2023-10-01", "score": 0.8}, ...]
    
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('mental_profile', uselist=False, lazy=True))

class SymptomResponse(db.Model):
    """
    Stores individual symptom responses linked to an assessment.
    """
    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessment_result.id'), nullable=False)
    symptom_name = db.Column(db.String(100), nullable=False)
    severity_level = db.Column(db.Integer) # 1-10 or similar scale
    response_value = db.Column(db.String(200)) # The actual answer text/value
    
    assessment = db.relationship('AssessmentResult', backref=db.backref('symptom_responses', lazy=True))

class UserLearningProfile(db.Model):
    """
    Stores system adjustments based on feedback to improve personalization.
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    condition = db.Column(db.String(50)) # e.g. 'Anxiety'
    weight_adjustment = db.Column(db.Float, default=1.0) # Multiplier for symptom weights
    personalization_notes = db.Column(db.JSON) # e.g. {"prioritize_symptoms": ["insomnia"]}
    
    user = db.relationship('User', backref=db.backref('learning_profile', lazy=True))

class ConfidenceScore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    condition = db.Column(db.String(50), nullable=False)
    score = db.Column(db.Float, default=0.5) # 0.0 to 1.0 (System's confidence in its own diagnosis)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('confidence_scores', lazy=True))


class AssessmentResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    result_type = db.Column(db.String(50), nullable=False) # 'interview' or 'chatbot'
    data = db.Column(db.JSON, nullable=False) # Store full result JSON
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('assessments', lazy=True))


class LoginHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    login_time = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(50), nullable=True)

    user = db.relationship('User', backref=db.backref('logins', lazy=True))

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    session_id = db.Column(db.String(64), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'user' | 'assistant' | 'system'
    content = db.Column(db.Text, nullable=False)
    sentiment = db.Column(db.Float, nullable=True)
    flagged = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('chat_messages', lazy=True))

