
class Persona:
    def __init__(self, data):
        self.id = data['id']
        self.name = data['name'] 
        self.profile = data['profile']
        self.mood = data['mood']
        self.status = data['status']
        self.plans = data['plans']
        self.goals = data['goals']
        self.characteristics = data['characteristics']
        self.schedule = []

    def __call__(self):
        """Makes the Persona class callable"""
        return {
            'id': self.id,
            'name': self.name,
            'profile': self.profile,
            'mood': self.mood,
            'status': self.status,
            'plans': self.plans,
            'goals': self.goals,
            'characteristics': self.characteristics,
            'schedule': self.schedule
        }