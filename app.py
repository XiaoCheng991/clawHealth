from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from datetime import datetime, timedelta, date, timezone
from sqlalchemy import func

from database import db, HealthRecord, FoodEntry, UserGoals

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///clawhealth.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
CORS(app)

db.init_app(app)


def _seed_goals():
    """Create default user goals if none exist."""
    if UserGoals.query.count() == 0:
        db.session.add(UserGoals())
        db.session.commit()


# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# Apple Watch / Health Data API
# ---------------------------------------------------------------------------

@app.route("/api/health/sync", methods=["POST"])
def sync_health_data():
    """Receive Apple Watch health metrics (bulk or single)."""
    payload = request.get_json(force=True, silent=True)
    if not payload:
        return jsonify({"error": "Invalid JSON payload"}), 400

    records = payload if isinstance(payload, list) else [payload]
    created = []
    for item in records:
        try:
            recorded_at = (
                datetime.fromisoformat(item["recorded_at"])
                if "recorded_at" in item
                else datetime.now(timezone.utc)
            )
        except ValueError:
            return jsonify({"error": f"Invalid recorded_at: {item.get('recorded_at')}"}), 400

        record = HealthRecord(
            recorded_at=recorded_at,
            steps=int(item.get("steps", 0)),
            heart_rate=item.get("heart_rate"),
            calories_burned=int(item.get("calories_burned", 0)),
            active_minutes=int(item.get("active_minutes", 0)),
            sleep_hours=item.get("sleep_hours"),
            blood_oxygen=item.get("blood_oxygen"),
            workout_type=item.get("workout_type"),
            workout_duration=int(item.get("workout_duration", 0)),
            source=item.get("source", "apple_watch"),
        )
        db.session.add(record)
        created.append(record)

    db.session.commit()
    return jsonify({"synced": len(created), "records": [r.to_dict() for r in created]}), 201


@app.route("/api/health/data", methods=["GET"])
def get_health_data():
    """Return health records filtered by optional date range."""
    start = request.args.get("start")
    end = request.args.get("end")
    limit = min(int(request.args.get("limit", 30)), 365)

    query = HealthRecord.query.order_by(HealthRecord.recorded_at.desc())
    if start:
        query = query.filter(HealthRecord.recorded_at >= datetime.fromisoformat(start))
    if end:
        query = query.filter(HealthRecord.recorded_at <= datetime.fromisoformat(end))

    records = query.limit(limit).all()
    return jsonify([r.to_dict() for r in records])


@app.route("/api/health/summary", methods=["GET"])
def health_summary():
    """Return aggregated summary for the last N days (default 7)."""
    days = int(request.args.get("days", 7))
    since = datetime.now(timezone.utc) - timedelta(days=days)

    records = HealthRecord.query.filter(HealthRecord.recorded_at >= since).all()

    if not records:
        return jsonify({
            "days": days,
            "total_records": 0,
            "avg_steps": 0,
            "avg_heart_rate": None,
            "avg_calories_burned": 0,
            "avg_sleep_hours": None,
            "avg_blood_oxygen": None,
            "avg_active_minutes": 0,
        })

    steps_list = [r.steps for r in records]
    hr_list = [r.heart_rate for r in records if r.heart_rate is not None]
    cal_list = [r.calories_burned for r in records]
    sleep_list = [r.sleep_hours for r in records if r.sleep_hours is not None]
    spo2_list = [r.blood_oxygen for r in records if r.blood_oxygen is not None]
    active_list = [r.active_minutes for r in records]

    def avg(lst):
        return round(sum(lst) / len(lst), 1) if lst else None

    return jsonify({
        "days": days,
        "total_records": len(records),
        "avg_steps": avg(steps_list),
        "avg_heart_rate": avg(hr_list),
        "avg_calories_burned": avg(cal_list),
        "avg_sleep_hours": avg(sleep_list),
        "avg_blood_oxygen": avg(spo2_list),
        "avg_active_minutes": avg(active_list),
    })


@app.route("/api/health/trend", methods=["GET"])
def health_trend():
    """Return day-by-day trend for charts (last N days)."""
    days = int(request.args.get("days", 7))
    since = datetime.now(timezone.utc).date() - timedelta(days=days - 1)

    records = HealthRecord.query.filter(
        HealthRecord.recorded_at >= datetime.combine(since, datetime.min.time())
    ).order_by(HealthRecord.recorded_at).all()

    # Group by date
    by_date: dict = {}
    for r in records:
        key = r.recorded_at.date().isoformat()
        by_date.setdefault(key, []).append(r)

    trend = []
    for i in range(days):
        d = (since + timedelta(days=i)).isoformat()
        day_records = by_date.get(d, [])
        if day_records:
            steps = max(r.steps for r in day_records)
            hr_vals = [r.heart_rate for r in day_records if r.heart_rate]
            cal = max(r.calories_burned for r in day_records)
            sleep_vals = [r.sleep_hours for r in day_records if r.sleep_hours]
            active = max(r.active_minutes for r in day_records)
            trend.append({
                "date": d,
                "steps": steps,
                "heart_rate": round(sum(hr_vals) / len(hr_vals), 1) if hr_vals else None,
                "calories_burned": cal,
                "sleep_hours": round(sum(sleep_vals) / len(sleep_vals), 1) if sleep_vals else None,
                "active_minutes": active,
            })
        else:
            trend.append({
                "date": d,
                "steps": None,
                "heart_rate": None,
                "calories_burned": None,
                "sleep_hours": None,
                "active_minutes": None,
            })

    return jsonify(trend)


# ---------------------------------------------------------------------------
# Food Analysis API
# ---------------------------------------------------------------------------

@app.route("/api/food/entries", methods=["GET"])
def get_food_entries():
    """Return food entries for a given date (defaults to today)."""
    date_str = request.args.get("date", date.today().isoformat())
    try:
        target = date.fromisoformat(date_str)
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    start_dt = datetime.combine(target, datetime.min.time())
    end_dt = datetime.combine(target, datetime.max.time())

    entries = (
        FoodEntry.query
        .filter(FoodEntry.logged_at >= start_dt, FoodEntry.logged_at <= end_dt)
        .order_by(FoodEntry.logged_at)
        .all()
    )
    return jsonify([e.to_dict() for e in entries])


@app.route("/api/food/entries", methods=["POST"])
def add_food_entry():
    """Log a new food entry."""
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    meal_type = data.get("meal_type", "").strip().lower()
    food_name = data.get("food_name", "").strip()

    if meal_type not in ("breakfast", "lunch", "dinner", "snack"):
        return jsonify({"error": "meal_type must be breakfast, lunch, dinner, or snack"}), 400
    if not food_name:
        return jsonify({"error": "food_name is required"}), 400

    try:
        logged_at = (
            datetime.fromisoformat(data["logged_at"])
            if "logged_at" in data
            else datetime.now(timezone.utc)
        )
    except ValueError:
        return jsonify({"error": f"Invalid logged_at: {data.get('logged_at')}"}), 400

    entry = FoodEntry(
        logged_at=logged_at,
        meal_type=meal_type,
        food_name=food_name,
        amount_g=float(data.get("amount_g", 100.0)),
        calories=float(data.get("calories", 0.0)),
        protein_g=float(data.get("protein_g", 0.0)),
        carbs_g=float(data.get("carbs_g", 0.0)),
        fat_g=float(data.get("fat_g", 0.0)),
        fiber_g=float(data.get("fiber_g", 0.0)),
    )
    db.session.add(entry)
    db.session.commit()
    return jsonify(entry.to_dict()), 201


@app.route("/api/food/entries/<int:entry_id>", methods=["DELETE"])
def delete_food_entry(entry_id):
    """Delete a food log entry."""
    entry = db.session.get(FoodEntry, entry_id)
    if not entry:
        return jsonify({"error": "Entry not found"}), 404
    db.session.delete(entry)
    db.session.commit()
    return jsonify({"deleted": entry_id})


@app.route("/api/food/analysis", methods=["GET"])
def food_analysis():
    """Return nutritional breakdown for a date or date range."""
    date_str = request.args.get("date", date.today().isoformat())
    try:
        target = date.fromisoformat(date_str)
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    start_dt = datetime.combine(target, datetime.min.time())
    end_dt = datetime.combine(target, datetime.max.time())

    entries = FoodEntry.query.filter(
        FoodEntry.logged_at >= start_dt, FoodEntry.logged_at <= end_dt
    ).all()

    goals = UserGoals.query.first()
    calorie_goal = goals.daily_calories_intake if goals else 2000

    total_cal = sum(e.calories for e in entries)
    total_protein = round(sum(e.protein_g for e in entries), 1)
    total_carbs = round(sum(e.carbs_g for e in entries), 1)
    total_fat = round(sum(e.fat_g for e in entries), 1)
    total_fiber = round(sum(e.fiber_g for e in entries), 1)

    by_meal: dict = {}
    for e in entries:
        by_meal.setdefault(e.meal_type, []).append(e.to_dict())

    return jsonify({
        "date": date_str,
        "calorie_goal": calorie_goal,
        "total_calories": round(total_cal, 1),
        "total_protein_g": total_protein,
        "total_carbs_g": total_carbs,
        "total_fat_g": total_fat,
        "total_fiber_g": total_fiber,
        "entries_by_meal": by_meal,
    })


@app.route("/api/food/trend", methods=["GET"])
def food_trend():
    """Return day-by-day calorie trend for the last N days."""
    days = int(request.args.get("days", 7))
    since = datetime.now(timezone.utc).date() - timedelta(days=days - 1)

    entries = FoodEntry.query.filter(
        FoodEntry.logged_at >= datetime.combine(since, datetime.min.time())
    ).all()

    by_date: dict = {}
    for e in entries:
        key = e.logged_at.date().isoformat()
        by_date.setdefault(key, []).append(e)

    trend = []
    for i in range(days):
        d = (since + timedelta(days=i)).isoformat()
        day_entries = by_date.get(d, [])
        trend.append({
            "date": d,
            "calories": round(sum(e.calories for e in day_entries), 1),
            "protein_g": round(sum(e.protein_g for e in day_entries), 1),
            "carbs_g": round(sum(e.carbs_g for e in day_entries), 1),
            "fat_g": round(sum(e.fat_g for e in day_entries), 1),
        })
    return jsonify(trend)


# ---------------------------------------------------------------------------
# Goals API
# ---------------------------------------------------------------------------

@app.route("/api/goals", methods=["GET"])
def get_goals():
    goals = UserGoals.query.first()
    if not goals:
        goals = UserGoals()
        db.session.add(goals)
        db.session.commit()
    return jsonify(goals.to_dict())


@app.route("/api/goals", methods=["PUT"])
def update_goals():
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    goals = UserGoals.query.first()
    if not goals:
        goals = UserGoals()
        db.session.add(goals)

    if "daily_steps" in data:
        goals.daily_steps = int(data["daily_steps"])
    if "daily_calories_intake" in data:
        goals.daily_calories_intake = int(data["daily_calories_intake"])
    if "daily_calories_burn" in data:
        goals.daily_calories_burn = int(data["daily_calories_burn"])
    if "sleep_hours" in data:
        goals.sleep_hours = float(data["sleep_hours"])
    if "active_minutes" in data:
        goals.active_minutes = int(data["active_minutes"])

    goals.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(goals.to_dict())


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

with app.app_context():
    db.create_all()
    _seed_goals()


if __name__ == "__main__":
    import os
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug, port=5000)
