document.addEventListener('DOMContentLoaded', function () {
    const stages = ['intro', 'patient', 'symptoms', 'regions', 'interview', 'results'];
    let curStageIdx = 0;

    // State
    let userData = {
        age: '',
        gender: '',
        symptom: '',
        regions: [],
        answers: {}
    };

    // Load User Context
    const userContext = document.getElementById('user-context');
    const isAuth = userContext.dataset.auth === 'true';
    if (isAuth) {
        if (userContext.dataset.age) userData.age = parseInt(userContext.dataset.age);
        if (userContext.dataset.gender) userData.gender = userContext.dataset.gender;
    }

    // DOM Elements
    const btnNextIntro = document.getElementById('btn-next');
    const btnNextMain = document.getElementById('btn-next-main');
    const btnBackMain = document.getElementById('btn-back-main');
    const globalActionBar = document.getElementById('global-action-bar');
    const questionContainer = document.getElementById('question-container');
    const inputAge = document.getElementById('input-age');
    const inputSymptom = document.getElementById('input-symptom');
    const ageError = document.getElementById('age-error');
    const regionContainer = document.getElementById('region-grid');

    // Region Data
    const regions = [
        { id: "stress", title: "Stress & Anxiety", icon: "⚡", desc: "Feeling overwhelmed, restless, or constantly worried" },
        { id: "mood", title: "Mood & Emotions", icon: "❤️", desc: "Low mood, loss of interest, sadness or irritability" },
        { id: "sleep", title: "Sleep & Energy", icon: "💤", desc: "Trouble sleeping, waking tired, or daytime fatigue" },
        { id: "cognitive", title: "Focus & Cognition", icon: "🧠", desc: "Difficulty concentrating, forgetfulness, mental fog" },
        { id: "social", title: "Social Interaction", icon: "👥", desc: "Withdrawal, isolation, or anxiety in social settings" },
        { id: "lifestyle", title: "Lifestyle & Habits", icon: "🌱", desc: "Diet, activity, or routines affecting daily wellbeing" }
    ];

    // Initialization
    const progressInline = document.getElementById('progress-inline');
    const historyNote = document.getElementById('history-note');
    const dominant = userContext.dataset.dominant || '';
    let freq = [];
    try {
        freq = JSON.parse(userContext.dataset.freq || '[]');
    } catch (e) { freq = []; }

    // Map common symptoms to regions
    function mapSymptomToRegion(sym) {
        const s = (sym || '').toLowerCase();
        if (s.includes('anxiety') || s.includes('stress') || s.includes('panic')) return 'stress';
        if (s.includes('sleep') || s.includes('insomnia') || s.includes('tired')) return 'sleep';
        if (s.includes('focus') || s.includes('concentration') || s.includes('memory')) return 'cognitive';
        if (s.includes('social')) return 'social';
        if (s.includes('mood') || s.includes('sad') || s.includes('depress')) return 'mood';
        return 'lifestyle';
    }

    // Preselect logic
    const preselect = new Set();
    if (dominant) {
        const d = dominant.toLowerCase();
        if (d.includes('anxiety') || d.includes('panic') || d.includes('stress')) preselect.add('stress');
        if (d.includes('depress') || d.includes('mood')) preselect.add('mood');
        if (d.includes('sleep')) preselect.add('sleep');
    }
    if (freq && Array.isArray(freq)) {
        freq.slice(0, 2).forEach(item => {
            const sym = Array.isArray(item) ? item[0] : item;
            preselect.add(mapSymptomToRegion(sym));
        });
    }
    if (preselect.size > 0) {
        historyNote && (historyNote.style.display = 'inline-block');
    }

    renderRegions(preselect);
    updateView();

    // Events
    btnNextIntro.addEventListener('click', handleNext);
    btnNextMain.addEventListener('click', handleNext);
    btnBackMain.addEventListener('click', handleBack);

    // Global helper for chips
    window.selectSymptom = function (val) {
        inputSymptom.value = val;
        userData.symptom = val;
        document.querySelectorAll('.symptom-chip').forEach(c => c.classList.remove('active'));
        event.target.classList.add('active');
        setTimeout(() => handleNext(), 300);
    };

    function handleNext() {
        const stage = stages[curStageIdx];

        if (stage === 'patient') {
            const age = parseInt(inputAge.value);
            const gender = document.querySelector('input[name="gender"]:checked');
            if (!age || age < 18 || age > 130) {
                ageError.style.display = 'block';
                return;
            }
            ageError.style.display = 'none';
            if (!gender) {
                alert("Please select a gender.");
                return;
            }
            userData.age = age;
            userData.gender = gender.value;
        }

        if (stage === 'symptoms') {
            if (!inputSymptom.value.trim()) {
                inputSymptom.style.borderColor = '#ef4444';
                inputSymptom.focus();
                setTimeout(() => inputSymptom.style.borderColor = '', 1500);
                return;
            }
            userData.symptom = inputSymptom.value.trim();
        }

        if (stage === 'regions') {
            const selected = document.querySelectorAll('.region-card.selected');
            userData.regions = Array.from(selected).map(el => el.dataset.id);
            // regions are optional — allow proceeding without selecting any
        }

        if (stage === 'interview') {
            // Interview answers are auto-submitted on selection.
            // Manual Next only appears for multi-select questions.
            fetchNextQuestion();
            return;
        }

        // Standard step advance
        if (curStageIdx < stages.length - 1) {
            curStageIdx++;

            // Auto-skip Patient step if data is pre-loaded from profile
            if (stages[curStageIdx] === 'patient' && userData.age && userData.gender) {
                curStageIdx++;
            }

            updateView();
        }
    }

    function handleBack() {
        if (curStageIdx > 0) {
            curStageIdx--;
            updateView();
        }
    }

    function updateView() {
        const stage = stages[curStageIdx];

        // Sidebar Update
        document.querySelectorAll('.nav-step').forEach((el, idx) => {
            el.classList.remove('active', 'completed');
            if (idx === curStageIdx) el.classList.add('active');
            if (idx < curStageIdx) el.classList.add('completed');
        });

        // Content Sections Update
        document.querySelectorAll('.view-section').forEach(el => {
            el.style.display = 'none';
            el.classList.remove('fade-in-up');
        });
        const activeView = document.getElementById(`view-${stage}`);
        activeView.style.display = 'flex';
        void activeView.offsetWidth; // Trigger reflow
        activeView.classList.add('fade-in-up');

        // Navigation Visibility
        if (stage === 'intro') {
            globalActionBar.style.display = 'none';
        } else if (stage === 'interview') {
            // Hide global nav in interview by default (handled by question type)
            globalActionBar.style.display = 'none';
        } else {
            globalActionBar.style.display = 'flex';
        }

        if (progressInline) {
            const total = stages.length;
            const stepNum = curStageIdx + 1;
            progressInline.textContent = `Step ${stepNum} of ${total} • This helps us ask better questions`;
        }

        if (stage === 'interview' && !questionContainer.dataset.initialized) {
            fetchNextQuestion();
        }
    }

    function fetchNextQuestion() {
        // Show loading state
        questionContainer.style.opacity = '0.5';
        questionContainer.style.pointerEvents = 'none';

        fetch('/api/interview/next', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                current_answers: userData.answers,
                regions: userData.regions
            })
        })
            .then(r => {
                if (!r.ok) throw new Error('Network error: ' + r.status);
                return r.json();
            })
            .then(data => {
                questionContainer.style.opacity = '1';
                questionContainer.style.pointerEvents = '';
                if (data.status === 'finished') {
                    submitFinal();
                } else if (data.question) {
                    renderQuestion(data.question);
                    // Make sure we are on the interview stage
                    if (stages[curStageIdx] !== 'interview') {
                        curStageIdx = stages.indexOf('interview');
                        updateView();
                    }
                } else {
                    throw new Error('Malformed data from server');
                }
            })
            .catch(err => {
                questionContainer.style.opacity = '1';
                questionContainer.style.pointerEvents = '';
                console.error('fetchNextQuestion error:', err);
                questionContainer.innerHTML = `
                    <div style="text-align:center; padding: 40px; color: #ef4444;">
                        <p style="font-size:18px; font-weight:600;">Connection error</p>
                        <p style="color:#A0AEC0;">Could not load the next question. Please check your connection.</p>
                        <button class="btn-next" onclick="fetchNextQuestion()" style="margin-top:20px;">Try Again</button>
                    </div>`;
            });
    }

    // SVG Checkmark
    const checkmarkSvg = `<svg class="checkmark-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`;

    // Feedback messages
    const feedbacks = ["Got it", "Thanks for sharing", "Understood", "Noted", "Okay"];

    function renderQuestion(q) {
        questionContainer.dataset.qid = q.id;
        questionContainer.dataset.initialized = "true";
        questionContainer.dataset.type = q.type;

        // Reset Animation classes
        questionContainer.className = '';
        void questionContainer.offsetWidth; // trigger reflow
        questionContainer.className = 'slide-in-right';

        // Calculate progress (Approximate)
        const answeredCount = Object.keys(userData.answers).length;
        const estimatedTotal = 10 + (userData.regions.length * 2); // Heuristic
        const progressPct = Math.min((answeredCount / estimatedTotal) * 100, 95);

        let optionsHtml = '';
        // Standardize options
        let options = q.options || [];
        if (q.type === 'statement' || (!q.options || q.options.length === 0)) {
            options = [
                { value: 'yes', text: 'Yes' },
                { value: 'no', text: 'No' },
                { value: 'dk', text: "I'm not sure" }
            ];
        }

        optionsHtml = options.map(opt => `
            <div class="option-card" onclick="selectAnswer('${q.id}', '${opt.value || opt.val}', this)">
                <span class="option-text">${opt.text}</span>
                ${checkmarkSvg}
            </div>
        `).join('');

        const empathyHtml = q.empathy_prefix ? `<div class="empathy-block">${q.empathy_prefix}</div>` : '';
        const pastRefHtml = q.is_past_reference ? `<div class="past-ref-badge">Context: Past Session</div>` : '';

        // Determine if we show "Next" button (Multi-select only)
        const showNext = (q.type === 'group_multiple');
        if (showNext) {
            globalActionBar.style.display = 'flex';
            btnNextMain.style.display = 'block';
            btnBackMain.style.display = 'none'; // No back in interview flow for now to keep it simple
        } else {
            globalActionBar.style.display = 'none';
        }

        // Determine doctor presence and size
        const isEarly = answeredCount < 5;
        const doctorClass = isEarly ? 'doctor-img breathing' : 'doctor-img doctor-mini breathing';
        const doctorContainerClass = answeredCount > 10 ? 'doctor-container doctor-hidden' : 'doctor-container';
        const doctorImg = '/static/img/question.png';

        questionContainer.innerHTML = `
            <div class="${doctorContainerClass}">
                <img src="${doctorImg}" class="${doctorClass}" alt="Guide">
            </div>
            <div class="progress-container">
                <div class="progress-bar" style="width: ${progressPct}%"></div>
            </div>
            <div class="question-counter">Question ${answeredCount + 1}</div>
            ${empathyHtml}
            ${pastRefHtml}
            <div class="statement-block" style="font-size: 22px; margin-bottom: 24px;">${q.text}</div>
            <div class="options-container">${optionsHtml}</div>
            ${q.tooltip ? `<div style="margin-top: 24px; color: #7b8084; font-size: 14px;">ℹ️ ${q.tooltip}</div>` : ''}
            <div id="feedback-toast" class="feedback-toast"></div>
        `;
    }

    window.selectAnswer = function (qid, val, cardEl) {
        // Prevent double clicks
        if (cardEl.classList.contains('selected')) return;

        // If single choice, remove other selections
        const type = questionContainer.dataset.type;
        const isMulti = (type === 'group_multiple');

        if (!isMulti) {
            document.querySelectorAll('.option-card').forEach(c => c.classList.remove('selected'));
        }

        cardEl.classList.add('selected');

        // Logic
        if (isMulti) {
            // Toggle logic if needed, but for now we just add it
            // Implementation detail: for multi, we might need to store array
            // But current backend expects single value usually, unless modified.
            // Let's assume for this specific UX request we treat 'group_multiple' carefully.
            // Actually, for multi, we wait for "Next" button.
            // But if we want to support it:
            let current = userData.answers[qid];
            if (!Array.isArray(current)) current = [];
            if (current.includes(val)) {
                current = current.filter(v => v !== val);
                cardEl.classList.remove('selected');
            } else {
                current.push(val);
            }
            userData.answers[qid] = current;
            return; // Wait for manual Next
        }

        // Single Choice Logic
        userData.answers[qid] = val;

        // Micro-feedback
        showFeedback();

        // Auto-advance
        setTimeout(() => {
            questionContainer.classList.add('fade-out-left');
            setTimeout(() => {
                fetchNextQuestion();
            }, 300); // Wait for animation
        }, 500); // Wait for user to see selection
    };

    function showFeedback() {
        const toast = document.getElementById('feedback-toast');
        if (toast) {
            toast.textContent = feedbacks[Math.floor(Math.random() * feedbacks.length)];
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 1500);
        }
    }

    function submitFinal() {
        const container = document.querySelector('.card-container');
        container.innerHTML = `
            <h1 class="page-title">Analysis Complete</h1>
            <p class="page-subtitle">Generating your personalized report...</p>
            <div class="loading-spinner"></div>
        `;

        const payload = {
            answers: userData.answers,
            symptoms: userData.symptom ? [userData.symptom] : [],
            regions: userData.regions,
            demographics: {
                age: userData.age,
                gender: userData.gender
            }
        };

        fetch('/api/interview_submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
            .then(r => r.json())
            .then(data => {
                window.location.href = data.redirect;
            })
            .catch(err => {
                console.error(err);
                alert("Error submitting assessment. Please try again.");
                window.location.reload();
            });
    }

    function renderRegions(preselect = new Set()) {
        if (!regionContainer) return;
        const primaryIds = ['stress', 'mood'];
        regionContainer.innerHTML = regions.map(r => {
            const isPrimary = primaryIds.includes(r.id);
            const classes = ['region-card', isPrimary ? 'region-card--primary' : 'region-card--secondary'];
            const selectedClass = preselect.has(r.id) ? ' selected' : '';
            return `
            <div class="${classes.join(' ')}${selectedClass}" data-id="${r.id}" onclick="this.classList.toggle('selected')">
                <div class="region-title">${r.icon} ${r.title}</div>
                <div class="region-desc">${r.desc}</div>
            </div>`;
        }).join('');
    }
});
