from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()


def _utcnow():
    return datetime.now(timezone.utc)


class HealthRecord(db.Model):
    """Apple Watch health metrics record."""
    __tablename__ = "health_records"

    id = db.Column(db.Integer, primary_key=True)
    recorded_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    steps = db.Column(db.Integer, default=0)
    heart_rate = db.Column(db.Float)
    calories_burned = db.Column(db.Integer, default=0)
    active_minutes = db.Column(db.Integer, default=0)
    sleep_hours = db.Column(db.Float)
    blood_oxygen = db.Column(db.Float)
    workout_type = db.Column(db.String(64))
    workout_duration = db.Column(db.Integer, default=0)
    source = db.Column(db.String(32), default="apple_watch")
    created_at = db.Column(db.DateTime, default=_utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "recorded_at": self.recorded_at.isoformat(),
            "steps": self.steps,
            "heart_rate": self.heart_rate,
            "calories_burned": self.calories_burned,
            "active_minutes": self.active_minutes,
            "sleep_hours": self.sleep_hours,
            "blood_oxygen": self.blood_oxygen,
            "workout_type": self.workout_type,
            "workout_duration": self.workout_duration,
            "source": self.source,
        }


class FoodEntry(db.Model):
    """Food and nutrition log entry."""
    __tablename__ = "food_entries"

    id = db.Column(db.Integer, primary_key=True)
    logged_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    meal_type = db.Column(db.String(16), nullable=False)  # breakfast/lunch/dinner/snack
    food_name = db.Column(db.String(128), nullable=False)
    amount_g = db.Column(db.Float, default=100.0)
    calories = db.Column(db.Float, default=0.0)
    protein_g = db.Column(db.Float, default=0.0)
    carbs_g = db.Column(db.Float, default=0.0)
    fat_g = db.Column(db.Float, default=0.0)
    fiber_g = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=_utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "logged_at": self.logged_at.isoformat(),
            "meal_type": self.meal_type,
            "food_name": self.food_name,
            "amount_g": self.amount_g,
            "calories": self.calories,
            "protein_g": self.protein_g,
            "carbs_g": self.carbs_g,
            "fat_g": self.fat_g,
            "fiber_g": self.fiber_g,
        }


class UserGoals(db.Model):
    """User health goals configuration."""
    __tablename__ = "user_goals"

    id = db.Column(db.Integer, primary_key=True)
    daily_steps = db.Column(db.Integer, default=10000)
    daily_calories_intake = db.Column(db.Integer, default=2000)
    daily_calories_burn = db.Column(db.Integer, default=500)
    sleep_hours = db.Column(db.Float, default=8.0)
    active_minutes = db.Column(db.Integer, default=30)
    updated_at = db.Column(db.DateTime, default=_utcnow, onupdate=_utcnow)

    def to_dict(self):
        return {
            "daily_steps": self.daily_steps,
            "daily_calories_intake": self.daily_calories_intake,
            "daily_calories_burn": self.daily_calories_burn,
            "sleep_hours": self.sleep_hours,
            "active_minutes": self.active_minutes,
        }
