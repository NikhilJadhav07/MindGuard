"""
Neural Network Training Script for MindGuard Mental Health Detection.

This script trains the SimpleMLP model using synthetic clinical data
derived from the question weights in questions.json.

Run from project root directory:
    python scripts/train_neural_model.py
"""

import sys
import os
import json
import numpy as np

# --- Path Setup ---
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from logic.neural_network import SimpleMLP

# --- Config ---
QUESTIONS_PATH = os.path.join(ROOT, "data", "questions.json")
OUTPUT_PATH = os.path.join(ROOT, "data", "neural_weights.json")
EPOCHS = 3000
LEARNING_RATE = 0.005
HIDDEN_SIZE = 64

CATEGORIES = [
    "Anxiety", "Depression", "Burnout",
    "Social Anxiety", "Panic Disorder", "Sleep Issues", "Stress"
]

# ─────────────────────────────────────────────────────────────────────────────
# Load question database
# ─────────────────────────────────────────────────────────────────────────────
with open(QUESTIONS_PATH, 'r', encoding='utf-8') as f:
    question_db = json.load(f)

questions = question_db["questions"]
question_ids = sorted(questions.keys())
INPUT_SIZE = len(question_ids)
OUTPUT_SIZE = len(CATEGORIES)

print(f"Questions loaded: {INPUT_SIZE} features | {OUTPUT_SIZE} output categories")

# ─────────────────────────────────────────────────────────────────────────────
# Build clinical weight matrix from questions.json
# Maps each question → category score contribution (0.0–1.0)
# ─────────────────────────────────────────────────────────────────────────────
# For each (question, category) pair, compute max possible weight
def get_max_weights():
    max_w = {cat: 0.0 for cat in CATEGORIES}
    for q_id, q_def in questions.items():
        q_weights = q_def.get("weight", {})
        for cat, w in q_weights.items():
            if cat in max_w and w > 0:
                max_w[cat] += w
        # Also account for option-level weights
        for opt in q_def.get("options", []):
            for cat, w in opt.get("weight", {}).items():
                if cat in max_w and w > 0:
                    max_w[cat] += w
    return max_w

max_weights = get_max_weights()
# Ensure no zero division
for cat in CATEGORIES:
    if max_weights[cat] == 0:
        max_weights[cat] = 1.0

# ─────────────────────────────────────────────────────────────────────────────
# Build feature vector from an "answer pattern"
# ─────────────────────────────────────────────────────────────────────────────
def answers_to_feature(answer_dict):
    features = np.zeros(INPUT_SIZE)
    for i, q_id in enumerate(question_ids):
        if q_id in answer_dict:
            val = answer_dict[q_id]
            q_def = questions[q_id]
            q_type = q_def.get("type", "")
            if q_type == "statement":
                if val == "yes":
                    features[i] = 1.0
                elif val == "dk":
                    features[i] = 0.3
                else:
                    features[i] = 0.0
            elif q_type == "group_single":
                options = q_def.get("options", [])
                for opt_idx, opt in enumerate(options):
                    if opt.get("value") == val:
                        features[i] = (opt_idx + 1) / max(len(options), 1)
                        break
            else:
                features[i] = 0.5
    return features

# ─────────────────────────────────────────────────────────────────────────────
# Compute ground-truth label from answer dict (rule-based, normalized)
# ─────────────────────────────────────────────────────────────────────────────
def answers_to_label(answer_dict):
    raw = {cat: 0.0 for cat in CATEGORIES}
    for q_id, val in answer_dict.items():
        q_def = questions.get(q_id, {})
        q_type = q_def.get("type", "")

        multiplier = 0.0
        if q_type == "statement":
            if val == "yes":
                multiplier = 1.0
            elif val == "dk":
                multiplier = 0.4

        if q_type == "group_single":
            for opt in q_def.get("options", []):
                if opt.get("value") == val:
                    for cat, w in opt.get("weight", {}).items():
                        if cat in raw:
                            raw[cat] += w
                    multiplier = None
                    break

        if multiplier is not None:
            for cat, w in q_def.get("weight", {}).items():
                if cat in raw:
                    raw[cat] += w * multiplier

    # Normalize
    label = np.array([min(1.0, max(0.0, raw[cat] / max_weights[cat])) for cat in CATEGORIES])
    return label

# ─────────────────────────────────────────────────────────────────────────────
# Generate Synthetic Training Data
# Strategy: Create diverse response patterns with known clinical profiles
# ─────────────────────────────────────────────────────────────────────────────
def generate_synthetic_dataset(n_samples=4000):
    """
    Generate training samples by creating varied answer patterns and
    deriving labels from the clinical weight system.
    """
    X = []
    y = []
    np.random.seed(42)

    # Possible values per question type
    statement_vals = ["yes", "no", "dk"]
    
    # Group single maps: question_id → list of option values
    group_options_map = {}
    for q_id, q_def in questions.items():
        if q_def.get("type") == "group_single":
            group_options_map[q_id] = [opt.get("value") for opt in q_def.get("options", [])]

    # ── Profile-driven sampling ──────────────────────────────────────────────
    # Clinical "archetypes": each archetype defines a bias toward certain answers
    profiles = [
        # (name, yes-bias questions, no-bias questions)
        {
            "name": "High Anxiety",
            "yes": ["start", "anxiety_triggers", "panic_symptoms"],
            "no": ["mood_q1", "burnout_q1", "social_anxiety_q1"]
        },
        {
            "name": "Depression",
            "yes": ["mood_q1", "mood_interest", "energy_q1"],
            "no": ["start", "social_anxiety_q1", "burnout_q1"]
        },
        {
            "name": "Burnout",
            "yes": ["burnout_q1", "burnout_cynicism", "burnout_efficacy"],
            "no": ["start", "mood_q1", "social_anxiety_q1"]
        },
        {
            "name": "Social Anxiety",
            "yes": ["social_anxiety_q1", "social_physical"],
            "no": ["start", "mood_q1", "burnout_q1"]
        },
        {
            "name": "Panic Disorder",
            "yes": ["anxiety_triggers", "panic_symptoms", "start"],
            "no": ["mood_q1", "burnout_q1", "social_anxiety_q1"]
        },
        {
            "name": "Sleep Issues",
            "yes": ["energy_q1", "sleep_hygiene"],
            "no": ["start", "mood_q1", "burnout_q1"]
        },
        {
            "name": "High Stress",
            "yes": ["start", "cognitive_q1", "burnout_q1"],
            "no": ["mood_q1", "social_anxiety_q1", "panic_symptoms"]
        },
        {
            "name": "Comorbid Anxiety+Depression",
            "yes": ["start", "mood_q1", "mood_interest", "anxiety_triggers"],
            "no": ["burnout_q1"]
        },
        {
            "name": "Healthy / Low Risk",
            "yes": [],
            "no": ["start", "mood_q1", "burnout_q1", "social_anxiety_q1",
                   "anxiety_triggers", "panic_symptoms", "cognitive_q1"]
        },
        {
            "name": "Moderate Mixed",
            "yes": ["start", "burnout_q1"],
            "no": ["panic_symptoms", "social_anxiety_q1"]
        }
    ]

    samples_per_profile = n_samples // len(profiles)
    extra = n_samples - samples_per_profile * len(profiles)

    for pidx, profile in enumerate(profiles):
        count = samples_per_profile + (1 if pidx < extra else 0)

        for _ in range(count):
            answer_dict = {}
            for q_id in question_ids:
                q_def = questions[q_id]
                q_type = q_def.get("type", "")

                if q_type == "statement":
                    if q_id in profile.get("yes", []):
                        # Strong yes-bias with some noise
                        probs = [0.85, 0.05, 0.10]  # yes, no, dk
                    elif q_id in profile.get("no", []):
                        probs = [0.05, 0.88, 0.07]
                    else:
                        probs = [0.35, 0.50, 0.15]  # neutral
                    val = np.random.choice(statement_vals, p=probs)
                    answer_dict[q_id] = val

                elif q_type == "group_single":
                    opts = group_options_map.get(q_id, [])
                    if opts:
                        n_opts = len(opts)
                        # Distribute probability based on profile bias
                        if q_id in profile.get("yes", []):
                            # Bias toward higher-index (more severe) options
                            w = np.arange(1, n_opts + 1, dtype=float)
                        elif q_id in profile.get("no", []):
                            # Bias toward lower-index (milder/good) options
                            w = np.arange(n_opts, 0, -1, dtype=float)
                        else:
                            w = np.ones(n_opts, dtype=float)
                        w = w / w.sum()
                        val = np.random.choice(opts, p=w)
                        answer_dict[q_id] = val

            # Add some fully random samples (10%) to prevent overfitting
            if np.random.random() < 0.1:
                answer_dict = {}
                for q_id in question_ids:
                    q_def = questions[q_id]
                    q_type = q_def.get("type", "")
                    if q_type == "statement":
                        answer_dict[q_id] = np.random.choice(statement_vals)
                    elif q_type == "group_single":
                        opts = group_options_map.get(q_id, [])
                        if opts:
                            answer_dict[q_id] = np.random.choice(opts)

            feat = answers_to_feature(answer_dict)
            lbl = answers_to_label(answer_dict)
            X.append(feat)
            y.append(lbl)

    X = np.array(X)  # (N, INPUT_SIZE)
    y = np.array(y)  # (N, OUTPUT_SIZE)
    return X, y

# ─────────────────────────────────────────────────────────────────────────────
# Train
# ─────────────────────────────────────────────────────────────────────────────
print("Generating synthetic training data...")
X_train, y_train = generate_synthetic_dataset(n_samples=5000)
print(f"Dataset size: X={X_train.shape}, y={y_train.shape}")

# Shuffle
idx = np.random.permutation(len(X_train))
X_train, y_train = X_train[idx], y_train[idx]

# Train/val split (80/20)
split = int(0.8 * len(X_train))
X_val, y_val = X_train[split:], y_train[split:]
X_train, y_train = X_train[:split], y_train[:split]

print(f"Train: {len(X_train)} | Val: {len(X_val)}")

model = SimpleMLP(INPUT_SIZE, HIDDEN_SIZE, OUTPUT_SIZE)

best_val_loss = float('inf')
best_W1, best_b1, best_W2, best_b2 = None, None, None, None

print(f"\nTraining for {EPOCHS} epochs...")
for epoch in range(1, EPOCHS + 1):
    # Mini-batch SGD
    batch_size = 64
    total_loss = 0.0
    n_batches = 0
    for start in range(0, len(X_train), batch_size):
        Xb = X_train[start:start + batch_size]
        yb = y_train[start:start + batch_size]
        loss = model.train_step(Xb, yb, learning_rate=LEARNING_RATE)
        total_loss += loss
        n_batches += 1

    if epoch % 200 == 0 or epoch == 1:
        # Validation loss
        val_pred = model.forward(X_val)
        val_loss = np.mean(np.square(val_pred - y_val))
        train_loss = total_loss / max(n_batches, 1)
        print(f"  Epoch {epoch:4d} | Train Loss: {train_loss:.5f} | Val Loss: {val_loss:.5f}")

        # Save best
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_W1 = model.W1.copy()
            best_b1 = model.b1.copy()
            best_W2 = model.W2.copy()
            best_b2 = model.b2.copy()

# Restore best weights
if best_W1 is not None:
    model.W1, model.b1 = best_W1, best_b1
    model.W2, model.b2 = best_W2, best_b2
    print(f"\n[OK] Best model restored (val_loss={best_val_loss:.5f})")

# ─────────────────────────────────────────────────────────────────────────────
# Validation: quick sanity check
# ─────────────────────────────────────────────────────────────────────────────
print("\n--- Sanity Check ---")
test_cases = [
    {
        "label": "Anxious Person",
        "answers": {"start": "yes", "anxiety_triggers": "yes", "panic_symptoms": "yes",
                    "mood_q1": "no", "burnout_q1": "no", "social_anxiety_q1": "no"}
    },
    {
        "label": "Depressed Person",
        "answers": {"mood_q1": "yes", "mood_interest": "yes", "energy_q1": "yes",
                    "start": "no", "burnout_q1": "no", "social_anxiety_q1": "no"}
    },
    {
        "label": "Burned Out",
        "answers": {"burnout_q1": "yes", "burnout_cynicism": "yes", "burnout_efficacy": "yes",
                    "start": "no", "mood_q1": "no"}
    },
    {
        "label": "Healthy",
        "answers": {"start": "no", "mood_q1": "no", "burnout_q1": "no",
                    "social_anxiety_q1": "no", "anxiety_triggers": "no"}
    }
]

for tc in test_cases:
    feat = answers_to_feature(tc["answers"]).reshape(1, -1)
    out = model.forward(feat)[0]
    scores = {cat: round(float(out[i]) * 100, 1) for i, cat in enumerate(CATEGORIES)}
    top_cat = max(scores, key=scores.get)
    print(f"  [{tc['label']}] -> Top: {top_cat} ({scores[top_cat]:.1f}%)")
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    for cat, s in sorted_scores[:3]:
        print(f"      {cat}: {s:.1f}%")

# ─────────────────────────────────────────────────────────────────────────────
# Save
# ─────────────────────────────────────────────────────────────────────────────
model.save_weights(OUTPUT_PATH)
print(f"\n[SAVED] Model saved to: {OUTPUT_PATH}")
print(f"   Input size: {INPUT_SIZE} | Hidden: {HIDDEN_SIZE} | Output: {OUTPUT_SIZE}")
