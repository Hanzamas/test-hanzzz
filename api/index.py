# api/index.py

import json
import os
from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy import create_engine, Column, Integer, String, Text, or_
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from pydantic import BaseModel
from typing import List, Optional
from pydantic_settings import BaseSettings

# --- 1. Konfigurasi ---
# Mengambil variabel dari Environment Variables di Vercel
class Settings(BaseSettings):
    DATABASE_URL: str
    SEED_SECRET: str

    class Config:
        env_file = ".env"

settings = Settings()

# --- 2. Setup Database (SQLAlchemy) ---
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency untuk mendapatkan sesi database per request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- 3. Model Database & Skema Pydantic ---

# Model Tabel untuk SQLAlchemy
class DBLocation(Base):
    __tablename__ = "locations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    loca = Column(String, index=True)
    img = Column(Text)
    desc = Column(Text)
    facilities = Column(Text, nullable=True)
    layout = Column(Text, name="layout_info", nullable=True) # Mapping 'layout' ke 'layout_info'

# Skema Pydantic untuk validasi data
class LocationBase(BaseModel):
    name: str
    loca: str
    img: str
    desc: str
    facilities: Optional[str] = None
    layout_info: Optional[str] = None

class LocationCreate(LocationBase):
    pass

class LocationUpdate(BaseModel):
    name: Optional[str] = None
    loca: Optional[str] = None
    img: Optional[str] = None
    desc: Optional[str] = None
    facilities: Optional[str] = None
    layout_info: Optional[str] = None

class Location(LocationBase):
    id: int
    class Config:
        from_attributes = True

# --- 4. Aplikasi FastAPI & Endpoint ---

app = FastAPI(
    title="TPN Locations API (Full Feature)",
    description="API dengan CRUD dan filter canggih berdasarkan db.json.",
    version="FINAL",
)

# --- Endpoint Seeding Rahasia (Jalankan Sekali) ---
@app.post("/api/seed", tags=["Admin (Jalankan Sekali Saja)"])
def seed_database(secret: str = Query(..., description="Kunci rahasia untuk seeding."), db: Session = Depends(get_db)):
    """Mengisi database dengan data awal dari db.json. Membutuhkan kunci rahasia."""
    if secret != settings.SEED_SECRET:
        raise HTTPException(status_code=403, detail="Kunci rahasia tidak valid.")

    if db.query(DBLocation).count() > 0:
        raise HTTPException(status_code=400, detail="Database sudah terisi.")

    try:
        # File db.json harus ada di folder root proyek
        with open('db.json', 'r', encoding='utf-8') as f:
            locations_data = json.load(f)["locations"]
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="File db.json tidak ditemukan di root proyek.")

    for loc_data in locations_data:
        if 'Layout' in loc_data:
            loc_data['layout_info'] = loc_data.pop('Layout')
        db.add(DBLocation(**loc_data))
    
    db.commit()
    return {"message": f"SUKSES! {len(locations_data)} data berhasil dimasukkan."}

# --- Endpoint CRUD & Filter ---

@app.get("/locations", response_model=List[Location], tags=["Locations"])
def read_locations(
    db: Session = Depends(get_db),
    search: Optional[str] = Query(None, description="Cari teks di kolom 'name' dan 'desc' (case-insensitive)."),
    loca: Optional[str] = Query(None, description="Filter berdasarkan dunia lokasi (case-insensitive)."),
    sort_by: Optional[str] = Query("id", description="Urutkan berdasarkan: 'id' atau 'name'."),
    order: str = Query("asc", description="Urutan: 'asc' atau 'desc'."),
    limit: int = Query(100, ge=1, le=100, description="Batasi jumlah hasil.")
):
    """READ (Lengkap): Mengambil daftar lokasi dengan filter dan urutan."""
    query = db.query(DBLocation)
    if loca:
        query = query.filter(DBLocation.loca.ilike(f"%{loca}%"))
    if search:
        search_term = f"%{search}%"
        query = query.filter(or_(DBLocation.name.ilike(search_term), DBLocation.desc.ilike(search_term)))

    if sort_by in ["id", "name"]:
        column_to_sort = getattr(DBLocation, sort_by)
        query = query.order_by(column_to_sort.desc() if order.lower() == "desc" else column_to_sort.asc())
    
    return query.limit(limit).all()

@app.post("/locations", response_model=Location, status_code=201, tags=["Locations"])
def create_location(location: LocationCreate, db: Session = Depends(get_db)):
    """CREATE: Menambahkan lokasi baru."""
    new_location = DBLocation(**location.model_dump())
    db.add(new_location)
    db.commit()
    db.refresh(new_location)
    return new_location

@app.get("/locations/{location_id}", response_model=Location, tags=["Locations"])
def read_location(location_id: int, db: Session = Depends(get_db)):
    """READ: Mengambil satu lokasi berdasarkan ID."""
    location = db.query(DBLocation).filter(DBLocation.id == location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Lokasi tidak ditemukan")
    return location

@app.patch("/locations/{location_id}", response_model=Location, tags=["Locations"])
def update_location(location_id: int, location_update: LocationUpdate, db: Session = Depends(get_db)):
    """UPDATE: Memperbarui data lokasi yang ada."""
    db_location = db.query(DBLocation).filter(DBLocation.id == location_id).first()
    if not db_location:
        raise HTTPException(status_code=404, detail="Lokasi tidak ditemukan")
    
    update_data = location_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_location, key, value)
    
    db.commit()
    db.refresh(db_location)
    return db_location

@app.delete("/locations/{location_id}", status_code=204, tags=["Locations"])
def delete_location(location_id: int, db: Session = Depends(get_db)):
    """DELETE: Menghapus lokasi berdasarkan ID."""
    db_location = db.query(DBLocation).filter(DBLocation.id == location_id).first()
    if not db_location:
        raise HTTPException(status_code=404, detail="Lokasi tidak ditemukan")
    
    db.delete(db_location)
    db.commit()
    return None

@app.on_event("startup")
def on_startup():
    # Membuat tabel di database jika belum ada saat aplikasi pertama kali dijalankan
    Base.metadata.create_all(bind=engine)