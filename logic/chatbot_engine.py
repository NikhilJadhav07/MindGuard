from textblob import TextBlob
import random
import os
import requests
import json
from uuid import uuid4
from datetime import datetime
from models import db, ChatMessage

class ChatbotEngine:
    def __init__(self):
        # Ollama local endpoint
        self.ollama_url = "http://localhost:11434/api/generate"
        self.tags_url = "http://localhost:11434/api/tags"

        # Preferred models in order
        self.preferred_models = ["llama3", "phi3", "mistral", "gemma"]
        # Defer model detection to first chat call (avoids blocking startup)
        self._model = None

        self.system_prompt = (
            "You are MindGuard, a calm, empathetic mental health support companion. "
            "Offer supportive, natural responses. Avoid medical diagnoses. "
            "Encourage self-care, grounding, and reaching out to trusted people. "
            "If user expresses self-harm intent, advise immediate professional help and crisis resources."
        )

    @property
    def model(self):
        """Lazily detect the best available Ollama model on first use."""
        if self._model is None:
            self._model = self._get_best_available_model()
        return self._model

    @model.setter
    def model(self, value):
        self._model = value

    def _get_best_available_model(self):
        try:
            response = requests.get(self.tags_url, timeout=2)
            if response.status_code == 200:
                data = response.json()
                models = [m['name'].split(':')[0] for m in data.get('models', [])]
                full_names = [m['name'] for m in data.get('models', [])]
                
                # Check for exact preferred matches
                for pref in self.preferred_models:
                    for name in full_names:
                        if pref in name:
                            return name
                
                # Fallback to any available
                if full_names:
                    return full_names[0]
            return "llama3" # Default fallback if API fails
        except:
            return "llama3"

    def moderate(self, text):
        # Local keyword-based moderation to define safety without external API
        flagged_keywords = ["suicide", "kill myself", "die", "end it all", "self-harm", "hurt myself"]
        flagged = any(k in text.lower() for k in flagged_keywords)
        return flagged, {"flagged": flagged}

    def analyze_sentiment(self, text):
        try:
            return TextBlob(text).sentiment.polarity
        except Exception:
            return 0.0

    def _load_messages(self, user_id, session_id):
        return ChatMessage.query.filter_by(session_id=session_id).order_by(ChatMessage.created_at.asc()).all()

    def _store(self, user_id, session_id, role, content, sentiment=None, flagged=False):
        m = ChatMessage(
            user_id=user_id,
            session_id=session_id,
            role=role,
            content=content,
            sentiment=sentiment,
            flagged=flagged,
            created_at=datetime.utcnow()
        )
        db.session.add(m)

    def _format_prompt(self, history, system_prompt):
        # Format based on model family
        if "llama3" in self.model:
            prompt = f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{system_prompt}<|eot_id|>"
            for msg in history:
                prompt += f"<|start_header_id|>{msg.role}<|end_header_id|>\n\n{msg.content}<|eot_id|>"
            prompt += "<|start_header_id|>assistant<|end_header_id|>\n\n"
            return prompt, ["<|eot_id|>"]
            
        elif "gemma" in self.model:
            # Gemma formatting: <start_of_turn>user ... <end_of_turn>
            # System prompt is usually just prepended or treated as user instruction involved in first turn
            prompt = f"<start_of_turn>user\n{system_prompt}\n\n"
            for i, msg in enumerate(history):
                if i == 0 and msg.role == "user":
                    # Combine system with first user message if needed, or just append
                    prompt += f"{msg.content}<end_of_turn>\n"
                else:
                    role = "model" if msg.role == "assistant" else "user"
                    prompt += f"<start_of_turn>{role}\n{msg.content}<end_of_turn>\n"
            prompt += "<start_of_turn>model\n"
            return prompt, ["<end_of_turn>"]
            
        elif "phi3" in self.model:
            # Phi-3: <|user|> ... <|end|>\n<|assistant|> ...
            prompt = f"<|system|>\n{system_prompt}<|end|>\n"
            for msg in history:
                prompt += f"<|{msg.role}|>\n{msg.content}<|end|>\n"
            prompt += "<|assistant|>\n"
            return prompt, ["<|end|>"]
            
        else:
            # Generic/Mistral: [INST] ... [/INST]
            prompt = f"[INST] {system_prompt} [/INST]\n"
            for msg in history:
                if msg.role == "user":
                    prompt += f"[INST] {msg.content} [/INST]"
                else:
                    prompt += f"{msg.content}\n"
            return prompt, []

    def chat(self, user_id, session_id, message):
        if not session_id:
            session_id = str(uuid4())
            
        sentiment = self.analyze_sentiment(message)
        flagged, _ = self.moderate(message)

        self._store(user_id, session_id, "user", message, sentiment=sentiment, flagged=flagged)
        db.session.commit()

        if flagged:
            reply = ("Your message may include sensitive content. "
                     "If you're in immediate danger or considering self-harm, please seek help now. "
                     "Would you like me to open the helpline page?")
            self._store(user_id, session_id, "assistant", reply, flagged=True)
            db.session.commit()
            return reply, {"sentiment": sentiment, "flagged": True}

        try:
            requests.get(self.ollama_url.replace("/api/generate", ""), timeout=2)
        except requests.exceptions.RequestException:
            reply = "I'm currently having trouble connecting to my local engine. Please ensure Ollama is running."
            self._store(user_id, session_id, "assistant", reply)
            db.session.commit()
            return reply, {"sentiment": sentiment, "flagged": False}

        # Dynamically evaluate the best available model before formatting prompt
        self.model = self._get_best_available_model()

        # Load history and format
        history = self._load_messages(user_id, session_id)
        # Append current message to history object list for formatting logic (temporary)
        # Actually easier to just append to prompt generation or create temp object
        # Let's just pass the stored objects which now INCLUDE the new message
        
        full_prompt, stop_tokens = self._format_prompt(history, self.system_prompt)

        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "num_predict": 800, 
                "temperature": 0.7,
                "stop": stop_tokens
            }
        }

        try:
            response = requests.post(self.ollama_url, json=payload, timeout=45)
            if response.status_code == 200:
                data = response.json()
                reply = data.get("response", "").strip()
            else:
                print(f"Ollama Error: {response.status_code} - {response.text}")
                reply = f"I'm encountering an issue with the AI model ({self.model}). Please ensure it is installed."
        except Exception as e:
            print(f"Ollama Exception: {e}")
            reply = "I'm having trouble processing that request."

        if not reply:
            reply = "..."

        self._store(user_id, session_id, "assistant", reply)
        db.session.commit()
        return reply, {"sentiment": sentiment, "flagged": False}

    def get_final_prediction(self, conversation_history):
        total = 0.0
        n = 0
        for msg in conversation_history:
            content = ""
            if isinstance(msg, dict):
                if msg.get("role") == "user":
                    content = msg.get("content", "")
            elif hasattr(msg, "role"):
                if msg.role == "user":
                    content = msg.content
            
            if content:
                n += 1
                total += self.analyze_sentiment(content)
                
        avg = (total / n) if n else 0.0
        status = "Green"
        if avg < -0.4:
            status = "Red"
        elif avg < -0.2:
            status = "Orange"
        elif avg < 0.0:
            status = "Yellow"
        return {"predictions": [], "status": status, "raw_scores": {"Sentiment": avg}}
