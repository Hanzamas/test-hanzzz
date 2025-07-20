# seed.py

import json
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import sessionmaker, declarative_base

# --- GANTI DENGAN URL DATABASE NEON ANDA ---
DATABASE_URL = "postgresql://user:password@ep-host-name.region.aws.neon.tech/dbname"

# Setup koneksi dan model database
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class DBLocation(Base):
    __tablename__ = "locations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    loca = Column(String, index=True)
    img = Column(Text)
    desc = Column(Text)
    facilities = Column(Text, nullable=True)
    layout = Column(Text, name="layout_info", nullable=True)

# Fungsi utama
def seed_database():
    print("Membuat tabel jika belum ada...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    if db.query(DBLocation).count() > 0:
        print("Database sudah terisi. Seeding dibatalkan.")
        db.close()
        return

    print("Membaca db.json...")
    try:
        with open('db.json', 'r', encoding='utf-8') as f:
            locations_data = json.load(f)["locations"]
    except FileNotFoundError:
        print("Error: Pastikan 'db.json' ada di folder yang sama dengan script ini.")
        db.close()
        return

    print(f"Memasukkan {len(locations_data)} data...")
    for loc_data in locations_data:
        if 'Layout' in loc_data:
            loc_data['layout_info'] = loc_data.pop('Layout')
        db.add(DBLocation(**loc_data))
    
    try:
        db.commit()
        print("SUKSES! Data berhasil dimasukkan.")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()