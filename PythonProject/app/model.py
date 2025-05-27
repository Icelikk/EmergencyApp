import pandas as pd
from sklearn.cluster import DBSCAN
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Input, LSTM, Dense
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os
import numpy as np

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

# Load data
data = pd.read_sql("SELECT ST_X(location) as lon, ST_Y(location) as lat, created_at FROM messages WHERE location IS NOT NULL", engine)

# Clustering
coords = data[['lat', 'lon']].values
if len(coords) > 1:  # DBSCAN требует минимум 2 точки
    dbscan = DBSCAN(eps=0.01, min_samples=2).fit(coords)
    data['cluster'] = dbscan.labels_
else:
    data['cluster'] = [-1] * len(data)

# Prepare LSTM data
sequences = []
for cluster in data[data['cluster'] != -1]['cluster'].unique():
    cluster_data = data[data['cluster'] == cluster][['lat', 'lon']].values
    if len(cluster_data) >= 10:
        # Добавить фиктивный event_type (0)
        cluster_data = np.pad(cluster_data, ((0, 0), (0, 1)), mode='constant')
        sequences.append(cluster_data[-10:])

# Mock training
if sequences:
    model = Sequential([
        Input(shape=(10, 3)),  # Используем Input вместо input_shape
        LSTM(50),
        Dense(2)
    ])
    model.compile(optimizer='adam', loss='mse')
    model.save('strike_predictor.keras')  # Сохраняем в .keras
else:
    print("Недостаточно данных для обучения. Создаём пустую модель.")
    model = Sequential([
        Input(shape=(10, 3)),
        LSTM(50),
        Dense(2)
    ])
    model.compile(optimizer='adam', loss='mse')
    model.save('strike_predictor.keras')