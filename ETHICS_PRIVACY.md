# Ethics & Privacy - MindGuard Learning System

The MindGuard platform handles sensitive mental health data. Our learning system is designed with "Privacy by Design" principles to ensure user safety and ethical AI behavior.

## 1. Data Anonymization
All free-text feedback is stored strictly for system improvement. We recommend users avoid using names or specific identifying details in their text feedback.

## 2. Active Learning Consent
- **Transparency**: Users are informed that their feedback "Updates their Learning Profile".
- **Opt-out**: Personalization can be reset by users at any time (Future Implementation), effectively clearing the `UserLearningProfile` and `ConfidenceScore` tables.

## 3. Algorithm Fairness
- **Dampening vs Amplification**: Our system primarily uses feedback to "Dampen" false positives (e.g., if we consistently over-diagnose Anxiety). This reduces "Alarm Fatigue" and prevents unnecessary user distress.
- **Human-in-the-Loop**: While the system adjusts weights automatically, significant deviations (Weights < 0.5 or > 1.5) trigger a flag for review (Future Implementation) to ensure clinical validity isn't compromised.

## 4. Secure Storage
- Data is stored in a locally managed SQLite database (`site.db`).
- Access to the database is restricted to the application service.

## 5. Ethical Follow-ups
Dynamic follow-up questions prioritized by the system are selected from a pre-vetted, clinically-aligned question bank. The AI does not "generate" medical advice; it only "orchestrates" validated sequences.
## 6. Neural Network Inference
- **Transparency**: The assessment scoring is conducted via a lightweight Neural Network (Multi-Layer Perceptron).
- **Deterministic Training**: The model is pre-trained on a synthesized dataset derived from clinical scoring rules to ensure it remains within safe, predictable bounds.
- **Accuracy over Diagnostic Labeling**: The network is optimized to prioritize capturing complex symptom interactions rather than providing definitive medical diagnoses.
