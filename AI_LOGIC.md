# AI Logic & Data-Driven Improvement

The Mental Health Detection system uses a hybrid AI approach that evolves with user data.

## 1. Hybrid Detection Engine
The system combines three layers of analysis:
- **Rule-Based Keywords**: Detects specific triggers (e.g., "panic", "hopeless") for immediate weighting.
- **Sentiment Analysis (TextBlob)**: Gauge the emotional tone (positive/negative) to adjust severity.
- **Zero-Shot Classification (Transformers)**: Uses a pre-trained NLP model to classify input into categories: *Anxiety, Depression, Overthinking, Stress*.

## 2. Adaptive History (Data-Driven)
The system stores every assessment result in the database (`AssessmentResult` table).

### How Past Data improves Accuracy:
1. **Baseline Establishment**:
   - If a user consistently scores high on "Anxiety", the system learns this is their baseline.
   - Future slight deviations might be treated differently than a sudden spike in a previously calm user.
   
2. **Contextual Awareness**:
   - When a user logs in, the engine pulls their last 5 sessions.
   - If the trend is "Worsening" (scores increasing), the system flags "Red" status earlier, even if the single session score is "Yellow".
   
3. **Personalized Follow-ups**:
   - (Future Implementation) The chatbot will reference past topics: *"You mentioned feeling overwhelmed last week, is that still bothering you?"*

## 3. Privacy & Security
- All personal data is stored locally in `site.db`.
- Passwords are hashed using `scrypt`.
- "Guest Mode" sessions are not saved, ensuring privacy for temporary users.
