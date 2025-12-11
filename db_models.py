# models.py
from database import db 

class leaderboard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.now())

    def __repr__(self):
        return f'<Leaderboard {self.username}: {self.score}>'