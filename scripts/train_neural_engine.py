import numpy as np
import json
import os
import sys

# Add project root to path to import logic
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic.neural_network import SimpleMLP
from logic.scoring_config import SCORING_CONFIG

def generate_synthetic_data(num_samples, question_db, categories):
    """
    Generate synthetic training data based on existing rules + non-linear interactions.
    """
    questions = question_db["questions"]
    q_ids = sorted(questions.keys())
    input_size = len(q_ids)
    output_size = len(categories)
    
    X = np.zeros((num_samples, input_size))
    y = np.zeros((num_samples, output_size))
    
    for s in range(num_samples):
        # 1. Randomly answer questions (weighted towards 'no' to represent general population)
        answers = {}
        for i, q_id in enumerate(q_ids):
            q_def = questions[q_id]
            prob_yes = 0.3 # 30% chance of a symptom
            
            if np.random.random() < prob_yes:
                if q_def["type"] == "statement":
                    X[s, i] = 1.0
                    answers[q_id] = "yes"
                elif q_def["type"] == "group_single":
                    opts = q_def.get("options", [])
                    idx = np.random.randint(len(opts))
                    X[s, i] = (idx + 1) / len(opts)
                    answers[q_id] = opts[idx]["value"]
            else:
                if q_def["type"] == "statement":
                    X[s, i] = 0.0
                    answers[q_id] = "no"
                else:
                    X[s, i] = 0.1 # Minimal signal for 'good' options
                    
        # 2. Calculate "Target" scores using rules + INTERACTION EFFECTS
        raw_scores = {cat: 0.0 for cat in categories}
        
        # Base Linear Weighting
        for i, q_id in enumerate(q_ids):
            if X[s, i] > 0.3:
                weights = questions[q_id].get("weight", {})
                for cat, w in weights.items():
                    if cat in raw_scores:
                        raw_scores[cat] += w * X[s, i]

        # NON-LINEAR INTERACTIONS (The "Accuracy" secret sauce)
        # 1. Depression + Sleep Issues -> Higher Risk for both
        if answers.get("mood_q1") == "yes" and "insomnia" in str(answers.get("sleep_q1")):
            raw_scores["Depression"] *= 1.3
            raw_scores["Sleep Issues"] *= 1.2
            
        # 2. Anxiety + Panic Trigger -> Much higher Panic Risk
        if answers.get("start") == "yes" and answers.get("anxiety_triggers") == "yes":
            raw_scores["Panic Disorder"] *= 1.5
            
        # 3. Burnout + Stress -> Rapid decline
        # (Assuming Stress is a category)
        if raw_scores.get("Burnout", 0) > 10 and raw_scores.get("Anxiety", 0) > 10:
             raw_scores["Burnout"] *= 1.4

        # 4. Crisis/Suicide check -> Absolute priority
        if answers.get("mood_suicide_check") == "yes":
            raw_scores["Depression"] = max(raw_scores["Depression"], 40.0) # Ensure high score

        # Normalize y to 0-1 range for sigmoid output
        # Use a "max possible" estimate to scale
        for i, cat in enumerate(categories):
            # Sigmoid-ish scaling to target output space
            midpoint = 20.0 # Approximate "Moderate" raw score
            val = raw_scores[cat]
            y[s, i] = 1.0 / (1.0 + np.exp(-0.15 * (val - midpoint)))
            
    return X, y

def main():
    print("Starting Neural Model Training...")
    
    # 1. Load data
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    questions_path = os.path.join(base_dir, "data", "questions.json")
    with open(questions_path, 'r', encoding='utf-8') as f:
        question_db = json.load(f)
        
    categories = [
        "Anxiety", "Depression", "Burnout", 
        "Social Anxiety", "Panic Disorder", "Sleep Issues", "Stress"
    ]
    
    # 2. Generate Data
    print("Generating synthetic dataset (5000 samples)...")
    X, y = generate_synthetic_data(5000, question_db, categories)
    
    # 3. Initialize Model
    input_size = X.shape[1]
    output_size = len(categories)
    model = SimpleMLP(input_size, 64, output_size)
    
    # 4. Train
    epochs = 100
    batch_size = 32
    print(f"Training for {epochs} epochs...")
    
    for epoch in range(epochs):
        indices = np.arange(X.shape[0])
        np.random.shuffle(indices)
        X = X[indices]
        y = y[indices]
        
        total_loss = 0
        for i in range(0, X.shape[0], batch_size):
            X_batch = X[i:i+batch_size]
            y_batch = y[i:i+batch_size]
            
            loss = model.train_step(X_batch, y_batch, learning_rate=0.05)
            total_loss += loss
            
        if (epoch + 1) % 10 == 0:
            print(f"Epoch {epoch+1}/100, Loss: {total_loss/(X.shape[0]/batch_size):.6f}")
            
    # 5. Save Model
    weights_path = os.path.join(base_dir, "data", "neural_weights.json")
    model.save_weights(weights_path)
    print(f"Model saved to {weights_path}")
    print("Training Complete!")

if __name__ == "__main__":
    main()
