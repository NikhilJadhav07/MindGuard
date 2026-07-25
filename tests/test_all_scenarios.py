import unittest
import json
import sys
import os

# Make sure root project directory is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db

class TestMentalHealthApp(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        # Push an application context and create tables
        self.ctx = app.app_context()
        self.ctx.push()
        db.create_all()

    def tearDown(self):
        self.ctx.pop()

    def test_home_page(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Mental Health', response.data)

    def test_interview_page_as_guest(self):
        """Interview page requires login or guest session.
        Inject a guest session so the route returns 200 instead of 302."""
        with self.app.session_transaction() as sess:
            sess['is_guest'] = True
        response = self.app.get('/interview')
        self.assertEqual(response.status_code, 200)

    def test_interview_submit(self):
        """Simulate an interview submission via the JSON API."""
        with self.app.session_transaction() as sess:
            sess['is_guest'] = True
        data = {
            "symptoms": ["anxious", "stressed"],
            "answers": {
                "start": "yes",
                "mood_q1": "no",
                "burnout_q1": "no"
            },
            "demographics": {"age": "25", "gender": "Other"}
        }
        response = self.app.post(
            '/api/interview_submit',
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.data)
        self.assertIn('redirect', body)

    def test_chatbot_analyze(self):
        """Chatbot analysis endpoint should return a redirect."""
        history = [
            {"role": "user",      "content": "I feel sad"},
            {"role": "assistant", "content": "I understand"}
        ]
        response = self.app.post(
            '/api/chat_analyze',
            data=json.dumps({"history": history}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.data)
        self.assertIn('redirect', body)

if __name__ == '__main__':
    unittest.main()
