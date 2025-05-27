from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Message, Shelter
from app.telegram_parser import fetch_messages
import uvicorn
from sqlalchemy.sql import text
import pandas as pd
from sklearn.cluster import DBSCAN
from tensorflow.keras.models import load_model
from sqlalchemy import func

app = FastAPI(title="Emergency System API")
model = load_model('strike_predictor.keras')

@app.get("/")
async def root():
    return {"message": "Welcome to Emergency System API"}

@app.get("/parse/{channel}", response_model=dict)
async def parse_channel(channel: str, db: Session = Depends(get_db)):
    try:
        messages = await fetch_messages(channel, limit=10)
        if not messages:
            raise HTTPException(status_code=404, detail="Сообщения не найдены")
        for msg in messages:
            db_message = Message(
                text=msg["text"],
                channel=msg["channel"],
                created_at=msg["created_at"],
                location=msg["location"],
                event_type=msg["event_type"]
            )
            db.merge(db_message)
        db.commit()
        return {"status": "success", "messages": messages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")

@app.get("/messages", response_model=list[dict])
async def get_messages(db: Session = Depends(get_db)):
    messages = db.query(
        Message.id,
        Message.text,
        Message.channel,
        Message.created_at,
        Message.event_type,
        func.ST_X(Message.location).label('lon'),
        func.ST_Y(Message.location).label('lat')
    ).order_by(Message.created_at.desc()).limit(100).all()
    return [
        {
            "id": m.id,
            "text": m.text,
            "channel": m.channel,
            "created_at": m.created_at.isoformat(),
            "location": (
                {"latitude": float(m.lat), "longitude": float(m.lon)}
                if m.lat and m.lon
                else None
            ),
            "event_type": m.event_type
        }
        for m in messages
    ]

@app.get("/shelters", response_model=list[dict])
async def get_shelters(db: Session = Depends(get_db)):
    shelters = db.query(
        Shelter.id,
        Shelter.name,
        Shelter.capacity,
        func.ST_X(Shelter.coordinates).label('lon'),
        func.ST_Y(Shelter.coordinates).label('lat')
    ).all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "location": (
                {"latitude": float(s.lat), "longitude": float(s.lon)}
                if s.lat and s.lon
                else None
            ),
            "capacity": s.capacity
        }
        for s in shelters
    ]

@app.get("/strike-zones", response_model=list[dict])
async def get_strike_zones(db: Session = Depends(get_db)):
    query = db.execute(text("SELECT ST_Y(location) as lat, ST_X(location) as lon FROM messages WHERE location IS NOT NULL"))
    coords = [(row[0], row[1]) for row in query]
    if not coords:
        return []
    coords_array = pd.DataFrame(coords, columns=['lat', 'lon']).values
    if len(coords_array) < 2:
        return []
    dbscan = DBSCAN(eps=0.05, min_samples=2).fit(coords_array)
    labels = dbscan.labels_
    hot_zones = coords_array[labels != -1]
    if len(hot_zones) == 0:
        return []
    return [
        {
            "center": {"latitude": float(hot_zones[0][0]), "longitude": float(hot_zones[0][1])},
            "radius_km": 5,
            "probability": 0.65
        }
    ]

@app.post("/route", response_model=dict)
async def get_route(data: dict, db: Session = Depends(get_db)):
    user_lat = data.get("user_lat")
    user_lon = data.get("user_lon")
    if not user_lat or not user_lon:
        raise HTTPException(status_code=400, detail="Координаты пользователя не указаны")
    query = db.execute(
        text("""
        SELECT id, name, capacity, ST_X(coordinates) as lon, ST_Y(coordinates) as lat
        FROM shelters
        ORDER BY ST_Distance(coordinates, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))
        LIMIT 1
        """),
        {"lon": user_lon, "lat": user_lat}
    )
    shelter = query.fetchone()
    if not shelter:
        raise HTTPException(status_code=404, detail="Укрытие не найдено")
    route = {
        "coordinates": [
            {"latitude": user_lat, "longitude": user_lon},
            {"latitude": user_lat + 0.01, "longitude": user_lon},
            {"latitude": shelter['lat'], "longitude": shelter['lon']}
        ]
    }
    return {
        "shelter": {
            "id": shelter['id'],
            "name": shelter['name'],
            "capacity": shelter['capacity'],
            "location": {"latitude": shelter['lat'], "longitude": shelter['lon']}
        },
        "route": route
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)