class RecommendationEngine:
    def __init__(self):
        self.strategies = {
            "Anxiety": [
                {"title": "4-7-8 Breathing", "desc": "Inhale for 4s, hold for 7s, exhale for 8s to calm your nervous system.", "time": "5 mins", "reason": "Effective for acute anxiety spikes."},
                {"title": "Grounding Technique", "desc": "Identify 5 things you see, 4 you feel, 3 you hear, 2 you smell, 1 you taste.", "time": "2 mins", "reason": "Helps detach from racing thoughts."},
                {"title": "Limit Stimulants", "desc": "Try to reduce caffeine and sugar intake which can trigger anxiety spikes.", "time": "Ongoing", "reason": "Dietary triggers often mimic anxiety symptoms."}
            ],
            "Depression": [
                {"title": "Behavioral Activation", "desc": "Do one small task today, even if you don't feel like it (e.g., make bed).", "time": "10 mins", "reason": "Action often precedes motivation."},
                {"title": "Sunlight Exposure", "desc": "Try to get 15 minutes of natural sunlight in the morning.", "time": "15 mins", "reason": "Regulates circadian rhythm and mood."},
                {"title": "Connect", "desc": "Reach out to one friend or family member via text or call.", "time": "5 mins", "reason": "Social connection combats isolation."}
            ],
            "Burnout": [
                {"title": "Digital Detox", "desc": "Set strict boundaries for no-screen time at least 1 hour before bed.", "time": "1 hour", "reason": "Reduces cognitive load and improves sleep."},
                {"title": "Micro-Breaks", "desc": "Take a 5-minute break every hour to stretch and disconnect.", "time": "5 mins", "reason": "Prevents cumulative fatigue."},
                {"title": "Delegation", "desc": "Identify one task you can delay or ask someone else to help with.", "time": "15 mins", "reason": "Restores sense of control."}
            ],
            "Sleep Issues": [
                {"title": "Sleep Schedule", "desc": "Go to bed and wake up at the same time every day.", "time": "Ongoing", "reason": "Stabilizes internal body clock."},
                {"title": "Blue Light Filter", "desc": "Use night mode on devices after sunset.", "time": "Evening", "reason": "Blue light suppresses melatonin production."},
                {"title": "Bedroom Environment", "desc": "Keep your room cool, dark, and quiet.", "time": "Ongoing", "reason": "Optimizes physical conditions for rest."}
            ],
            "Social Anxiety": [
                {"title": "Small Exposure", "desc": "Make brief eye contact with a cashier or stranger today.", "time": "1 min", "reason": "Gradual exposure builds confidence."},
                {"title": "Challenge Thoughts", "desc": "Ask yourself: 'What is the worst that could actually happen?'", "time": "5 mins", "reason": "Cognitive restructuring reduces fear."}
            ],
            "Panic Disorder": [
                {"title": "Ice Cube Trick", "desc": "Hold an ice cube in your hand to shock your system out of a panic loop.", "time": "1 min", "reason": "Strong sensory input overrides panic signals."},
                {"title": "Acceptance", "desc": "Remind yourself: 'This is uncomfortable, but it is not dangerous.'", "time": "Instant", "reason": "Reduces the fear-of-fear cycle."}
            ]
        }
        
    def get_recommendations(self, results):
        """
        Generates personalized advice based on assessment results.
        """
        advice = []
        
        # Collect top strategies for top conditions
        # Only consider conditions with probability > 20 (Mild+)
        
        seen_strategies = set()
        
        for condition in results:
            if condition['probability'] > 20:
                cat = condition['condition']
                if cat in self.strategies:
                    for strat in self.strategies[cat]:
                        if strat['title'] not in seen_strategies:
                            advice.append({
                                "category": cat,
                                "title": strat['title'],
                                "desc": strat['desc'],
                                "time": strat.get('time', '5 mins'),
                                "reason": strat.get('reason', f"Helps with {cat}")
                            })
                            seen_strategies.add(strat['title'])
                            
                            # Limit to 2 strategies per category to avoid overwhelm
                            if len([x for x in advice if x['category'] == cat]) >= 2:
                                break
        
        # If no significant issues, return general wellness
        if not advice:
            advice.append({"category": "General", "title": "Hydration", "desc": "Drink plenty of water to maintain physical and mental energy.", "time": "Ongoing", "reason": "Dehydration affects mood and focus."})
            advice.append({"category": "General", "title": "Mindfulness", "desc": "Take 5 minutes to just sit and breathe without distraction.", "time": "5 mins", "reason": "Reduces baseline stress levels."})
            
        return advice[:6] # consistent limit
