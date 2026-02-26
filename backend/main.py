"""
FastAPI backend for Health Dashboard
"""
from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

app = FastAPI(title="健康数据管理系统")

# Models
class HealthData(BaseModel):
    date: str
    weight: float
    steps: int
    calories: int
    heart_rate: int
    sleep_duration: int
    
class UserProfile(BaseModel):
    user_id: str
    name: str
    preferences: dict
    targets: dict
    health_data: List[HealthData] = []

class MealRecord(BaseModel):
    id: str
    user_id: str
    meal_type: str  # breakfast, lunch, dinner, snack
    image_url: str
    timestamp: datetime = datetime.utcnow()

class ActivityRecord(BaseModel):
    id: str
    user_id: str
    activity_type: str  # steps, exercise, sleep
    value: int
    timestamp: datetime = datetime.utcnow()

# Database simulation
users_db = {
    "user123": UserProfile(
        user_id="user123",
        name="程永强",
        preferences={"theme": "light", "notifications": "daily"},
        targets={"daily_calories": 2000, "daily_steps": 10000, "weight_target": 70.0},
        health_data=[]
    )
}

@app.get("/")
def read_root():
    return {
        "message": "健康数据管理系统 API",
        "version": "1.0.0",
        "endpoints": [
            "/health/data",
            "/users/{user_id}/profile",
            "/users/{user_id}/health-data",
            "/users/{user_id}/meals",
            "/users/{user_id}/activities"
        ]
    }

@app.post("/health/data")
def add_health_data(user_id: str, data: dict):
    if user_id not in users_db:
        return {"error": "User not found"}
    
    user = users_db[user_id]
    user.health_data.append(HealthData(**data))
    return {"message": "Health data added", "data": user.health_data}

@app.get("/users/{user_id}/profile")
def get_user_profile(user_id: str):
    if user_id not in users_db:
        return {"error": "User not found"}
    
    user = users_db[user_id]
    return {"message": "User profile", "profile": user}

@app.get("/users/{user_id}/health-data")
def get_user_health_data(user_id: str):
    if user_id not in users_db:
        return {"error": "User not found"}
    
    user = users_db[user_id]
    return {"message": "User health data", "health_data": user.health_data}

@app.post("/users/{user_id}/meal-image")
def process_meal_image(user_id: str, image_url: str):
    # TODO: Implement image processing
    return {"message": "Meal image processing not implemented yet", "image_url": image_url}

# CORS Middleware
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware(
        allow_origins=["https://your-app.com", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
