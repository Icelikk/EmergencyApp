from app.database import Base, engine
from app.models import Message, Shelter
from sqlalchemy import inspect

Base.metadata.create_all(bind=engine)
inspector = inspect(engine)
tables = inspector.get_table_names()
print("Tables in database:", tables)

# Insert initial shelters
from sqlalchemy.orm import Session
from app.database import SessionLocal

db = SessionLocal()
shelters = [
    Shelter(name="Укрытие на ул. Ленина", location="POINT(36.1871 51.7373)", capacity=50),
    Shelter(name="Укрытие на ул. Советская", location="POINT(36.1850 51.7350)", capacity=30),
]
for shelter in shelters:
    db.merge(shelter)
db.commit()
db.close()