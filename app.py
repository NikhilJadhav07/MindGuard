from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from logic.interview_engine import InterviewEngine
from logic.chatbot_engine import ChatbotEngine
from logic.profile_engine import ProfileEngine
from models import db, User, Feedback, UserMentalProfile, SymptomResponse

app = Flask(__name__)
app.secret_key = 'your_secret_key_here' # In production use os.environ
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

interview_engine = InterviewEngine()
chatbot_engine = ChatbotEngine()
profile_engine = ProfileEngine()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    return render_template('index.html')

# --- Authentication Routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    next_page = request.args.get('next') or url_for('home')

    if request.method == 'POST':
        action = request.form.get('action')
        email = request.form.get('email')
        password = request.form.get('password')

        if action == 'register':
            name = request.form.get('name')
            age = request.form.get('age')
            gender = request.form.get('gender')
            
            user = User.query.filter_by(email=email).first()
            if user:
                flash('Email already exists')
                return redirect(url_for('login', next=request.args.get('next')))
            
            hashed_password = generate_password_hash(password, method='scrypt')
            new_user = User(email=email, password=hashed_password, name=name, age=age, gender=gender)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            session.pop('is_guest', None)
            return redirect(next_page)

        elif action == 'login':
            user = User.query.filter_by(email=email).first()
            if user and check_password_hash(user.password, password):
                login_user(user)
                session.pop('is_guest', None)
                # Log history
                try:
                    from models import LoginHistory
                    history = LoginHistory(user_id=user.id, ip_address=request.remote_addr)
                    db.session.add(history)
                    db.session.commit()
                except:
                    pass
                return redirect(next_page)

            else:
                flash('Login Unsuccessful. Please check email and password')
                return redirect(url_for('login', next=request.args.get('next')))
    
    return render_template('modern_login.html')

@app.route('/guest_login')
def guest_login():
    # Create a temporary guest session
    session.clear()
    session['user_id'] = None # Explicitly None for guest
    session['is_guest'] = True
    session['name'] = "Guest User"
    next_page = request.args.get('next') or url_for('home')
    return redirect(next_page)


@app.route('/logout')
def logout():
    if current_user.is_authenticated:
        logout_user()
    session.clear()
    return redirect(url_for('home'))

# --- Feature Routes ---
@app.route('/feedback', methods=['GET', 'POST'])
@login_required
def feedback():
    if request.method == 'POST':
        assessment_id = request.form.get('assessment_id')
        accuracy_rating = int(request.form.get('accuracy_rating', 3))
        emotional_relevance_score = int(request.form.get('emotional_relevance_score', 3))
        user_confidence_before = int(request.form.get('user_confidence_before', 5))
        user_confidence_after = int(request.form.get('user_confidence_after', 5))
        missed_symptoms = request.form.get('missed_symptoms')
        free_text_feedback = request.form.get('content')
        
        feedback = Feedback(
            user_id=current_user.id, 
            assessment_id=assessment_id,
            accuracy_rating=accuracy_rating,
            emotional_relevance_score=emotional_relevance_score,
            user_confidence_before=user_confidence_before,
            user_confidence_after=user_confidence_after,
            missed_symptoms=missed_symptoms,
            free_text_feedback=free_text_feedback
        )
        db.session.add(feedback)
        
        # --- ACTIVE LEARNING LOGIC ---
        from models import UserLearningProfile, AssessmentResult
        
        # 1. Adjust weights based on accuracy rating
        if accuracy_rating <= 2: # System was inaccurate (e.g. over-diagnosed)
            assessment = AssessmentResult.query.get(assessment_id)
            if assessment:
                for p in assessment.data.get('predictions', []):
                    cond = p['condition']
                    profile = UserLearningProfile.query.filter_by(user_id=current_user.id, condition=cond).first()
                    if not profile:
                        profile = UserLearningProfile(user_id=current_user.id, condition=cond, weight_adjustment=0.9)
                        db.session.add(profile)
                    else:
                        profile.weight_adjustment *= 0.9 # Dampen weights for this condition
        
        elif accuracy_rating >= 4: # System was accurate
            assessment = AssessmentResult.query.get(assessment_id)
            if assessment:
                for p in assessment.data.get('predictions', []):
                    cond = p['condition']
                    profile = UserLearningProfile.query.filter_by(user_id=current_user.id, condition=cond).first()
                    if profile:
                        # Slightly move back towards 1.0 or amplify if very low
                        profile.weight_adjustment = min(1.2, profile.weight_adjustment * 1.05)

        # 2. Log personalization notes for missed symptoms
        if missed_symptoms:
            gen_profile = UserLearningProfile.query.filter_by(user_id=current_user.id, condition='General').first()
            if not gen_profile:
                gen_profile = UserLearningProfile(user_id=current_user.id, condition='General', personalization_notes={"missed": [missed_symptoms]})
                db.session.add(gen_profile)
            else:
                notes = gen_profile.personalization_notes or {"missed": []}
                notes["missed"].append(missed_symptoms)
                gen_profile.personalization_notes = notes

        db.session.commit()
        flash('Thank you for helping MindGuard learn and improve!')
        return redirect(url_for('feedback'))

    
    # Show previous feedback
    feedbacks = Feedback.query.filter_by(user_id=current_user.id).order_by(Feedback.created_at.desc()).all()
    # Also get assessments to link to feedback in the UI
    from models import AssessmentResult
    assessments = AssessmentResult.query.filter_by(user_id=current_user.id).order_by(AssessmentResult.created_at.desc()).all()
    return render_template('feedback.html', feedbacks=feedbacks, assessments=assessments)

@app.route('/helpline')
def helpline():
    return render_template('helpline.html')

@app.route('/admin/users')
@login_required # In real app, add admin check
def admin_users():
    users = User.query.all()
    return render_template('admin_users.html', users=users)

# --- Existing Logic Routes ---
@app.route('/interview')
def interview():
    # Require login or guest mode
    if not current_user.is_authenticated and not session.get('is_guest'):
        # Redirect to login with next param
        return redirect(url_for('login', next=url_for('interview')))

    # Render template with optional profile context for intelligent defaults
    profile_context = None
    try:
        if current_user.is_authenticated:
            profile_context = profile_engine.get_profile_context(current_user.id)
    except Exception as e:
        profile_context = None
        print(f"Profile context error: {e}")
    return render_template('interview.html', profile_context=profile_context)

@app.route('/api/get_followups', methods=['POST'])
def get_followups():
    # Deprecated by new flow, but keeping for safety if needed
    return jsonify({'followups': []})


@app.route('/api/interview_submit', methods=['POST'])
def interview_submit():
    data = request.json
    answers = data.get('answers', {})
    symptoms = data.get('symptoms', []) # List of selected symptoms from phase 1
    demographics = data.get('demographics', {})

    # Update User Profile if data is missing and user is logged in
    if current_user.is_authenticated:
        changed = False
        if not current_user.age and demographics.get('age'):
            current_user.age = demographics.get('age')
            changed = True
        if not current_user.gender and demographics.get('gender'):
            current_user.gender = demographics.get('gender')
            changed = True
        
        if changed:
            db.session.commit()

    # Use new calculate_results with user context
    results = interview_engine.calculate_results(answers, user=current_user, symptoms=symptoms)
    
    # Merge symptoms into results for completeness
    results['symptoms'] = symptoms

    session['results'] = results
    
    # Save to DB if logged in
    if current_user.is_authenticated:
        try:
            from models import AssessmentResult
            
            # 1. Create AssessmentResult
            assessment = AssessmentResult(
                user_id=current_user.id, 
                result_type='interview',
                data=results
            )
            db.session.add(assessment)
            db.session.flush() # Flush to get assessment.id
            
            # 2. Save Symptom Responses
            for s in symptoms:
                # Basic symptom check
                sr = SymptomResponse(
                    assessment_id=assessment.id,
                    symptom_name=s,
                    response_value="Checked"
                )
                db.session.add(sr)
            
            for q_id, val in answers.items():
                # Detailed answers
                sr = SymptomResponse(
                    assessment_id=assessment.id,
                    symptom_name=q_id, # Using Question ID as symptom name reference
                    response_value=str(val)
                )
                db.session.add(sr)

            # 3. Update User Mental Profile
            profile_engine.update_profile(current_user.id, results)

            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            print(f"Error saving result: {e}")

    return jsonify({'status': 'success', 'redirect': '/result'})



@app.route('/chatbot')
def chatbot():
    return render_template('chatbot.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    import uuid
    data = request.json
    message = data.get('message', '')
    if 'chat_session_id' not in session:
        session['chat_session_id'] = str(uuid.uuid4())
    user_id = current_user.id if current_user.is_authenticated else None
    response_text, meta = chatbot_engine.chat(user_id, session['chat_session_id'], message)
    return jsonify({'response': response_text, 'scores': meta})

@app.route('/dashboard')
@login_required
def dashboard():
    from models import AssessmentResult
    import json
    
    # Fetch all assessments for user
    assessments = AssessmentResult.query.filter_by(user_id=current_user.id).order_by(AssessmentResult.created_at.asc()).all()
    
    # Prepare chart data
    dates = []
    # Dataset structure for Chart.js: [{label: 'Anxiety', data: []}, ...]
    metrics = ["Anxiety", "Depression", "Burnout"]
    chart_data = {m: [] for m in metrics}
    
    latest_result = None
    
    for a in assessments:
        # Check if data is string or dict (SQLite JSON quirk)
        res_data = a.data
        if isinstance(res_data, str):
            try:
                res_data = json.loads(res_data)
            except:
                continue
                
        # Handle new format vs legacy
        # New format has "predictions": [{condition, probability, ...}]
        # Legacy might have just {"predictions": { "Anxiety": 10 }} or similar
        
        preds = res_data.get('predictions', [])
        
        # Extract scores for chart
        current_scores = {m: 0 for m in metrics}
        
        if isinstance(preds, list): # New format
            for p in preds:
                if p['condition'] in current_scores:
                    current_scores[p['condition']] = p['probability']
        elif isinstance(preds, dict): # Old format
            for k, v in preds.items():
                if k in current_scores:
                    current_scores[k] = v
                    
        dates.append(a.created_at.strftime('%Y-%m-%d'))
        for m in metrics:
            chart_data[m].append(current_scores[m])
            
        latest_result = {
            "date": a.created_at,
            "data": res_data
        }

    # Format dataset for Chart.js
    dataset = []
    colors = {'Anxiety': 'red', 'Depression': 'blue', 'Burnout': 'orange'}
    for m in metrics:
        dataset.append({
            "label": m,
            "data": chart_data[m],
            "borderColor": colors.get(m, 'gray'),
            "fill": False
        })
        
    return render_template('dashboard.html', latest_result=latest_result, dates=dates, dataset=dataset)

@app.route('/api/chat_analyze', methods=['POST'])
def chat_analyze():
    data = request.json
    history = data.get('history', [])
    results = chatbot_engine.get_final_prediction(history)
    session['results'] = results


    # Save to DB if logged in
    if current_user.is_authenticated:
        try:
            from models import AssessmentResult
            assessment = AssessmentResult(
                user_id=current_user.id, 
                result_type='chatbot',
                data=results
            )
            db.session.add(assessment)
            db.session.commit()
        except Exception as e:
            print(f"Error saving result: {e}")

    return jsonify({'status': 'success', 'redirect': '/result'})


@app.route('/api/interview/next', methods=['POST'])
def interview_next():
    data = request.json
    current_answers = data.get('current_answers', {})
    regions = data.get('regions', [])
    
    # Get Profile Context if logged in
    profile_context = None
    if current_user.is_authenticated:
        profile_context = profile_engine.get_profile_context(current_user.id)

    # Get next question with user context
    next_question = interview_engine.get_next_question(
        current_answers, 
        selected_regions=regions, 
        user=current_user if current_user.is_authenticated else None,
        profile_context=profile_context
    )
    
    if next_question:
        return jsonify({'status': 'continue', 'question': next_question})
    else:
        return jsonify({'status': 'finished'})

@app.route('/result')
def result():
    results = session.get('results', {})
    
    # --- EMPATHETIC UI PRE-PROCESSING ---
    # We need to map clinical conditions to user-friendly "Insight Cards"
    # 1. Mood (Depression, Anxiety, Stress, Panic)
    # 2. Energy (Burnout, Sleep Issues)
    # 3. Calmness (Inverse of Anxiety/Stress) or Focus? User asked for "Mood, Interest, Energy"
    
    raw_scores = results.get('raw_scores', {})
    preds = results.get('predictions', [])
    def get_score(name):
        val = raw_scores.get(name)
        if val is not None:
            return val
        for p in preds or []:
            if p.get('condition') == name:
                return p.get('probability', 0)
        return 0

    mood_score = max(get_score('Depression'), get_score('Anxiety'), get_score('Stress'), get_score('Panic Disorder'))
    energy_score = max(get_score('Burnout'), get_score('Sleep Issues'))
    interest_score = get_score('Depression') 

    # Determine Top Severity for Hero Section
    top_severity = "Low"
    if results.get('predictions'):
        top_severity = results['predictions'][0].get('severity', 'Low')

    return render_template('result.html', 
                           results=results, 
                           mood_pred=mood_score,
                           energy_pred=energy_score,
                           interest_pred=interest_score,
                           top_severity=top_severity)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
