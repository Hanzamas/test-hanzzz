# api/index.py

import json
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, Column, Integer, String, Text, or_
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from pydantic import BaseModel, ValidationError
from typing import List, Optional
from pydantic_settings import BaseSettings

# --- 1. Konfigurasi ---
# Mengambil variabel dari Environment Variables di Vercel
class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./test.db"  # Default fallback
    SEED_SECRET: str = "default_secret"  # Default fallback

    class Config:
        env_file = ".env"

try:
    settings = Settings()
except Exception as e:
    print(f"Warning: Could not load settings properly: {e}")
    settings = Settings()

# --- 2. Setup Database (SQLAlchemy) ---
try:
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
except Exception as e:
    print(f"Database connection error: {e}")
    raise

# Dependency untuk mendapatkan sesi database per request
def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise
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

class Location(BaseModel):
    id: int
    name: str
    loca: str
    img: str
    desc: str
    facilities: Optional[str] = None
    layout_info: Optional[str] = None
    
    class Config:
        from_attributes = True

# Response models untuk error handling
class ErrorResponse(BaseModel):
    detail: str
    status_code: int
    timestamp: str
    path: str

class SuccessResponse(BaseModel):
    message: str
    data: Optional[dict] = None

# --- 4. Lifecycle Management ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting up...")
    try:
        Base.metadata.create_all(bind=engine)
        print("Database tables created successfully!")
    except Exception as e:
        print(f"Error creating database tables: {e}")
    yield
    # Shutdown
    print("Shutting down...")

# --- 5. Aplikasi FastAPI & Error Handlers ---

app = FastAPI(
    title="TPN Locations API (Full Feature)",
    description="API dengan CRUD dan filter canggih berdasarkan db.json.",
    version="FINAL",
    lifespan=lifespan
)

# Global Exception Handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code,
            "timestamp": "2025-07-20T00:00:00Z",
            "path": str(request.url.path)
        }
    )

@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "status_code": 422,
            "timestamp": "2025-07-20T00:00:00Z",
            "path": str(request.url.path),
            "errors": exc.errors()
        }
    )

@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Database error occurred",
            "status_code": 500,
            "timestamp": "2025-07-20T00:00:00Z",
            "path": str(request.url.path)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "status_code": 500,
            "timestamp": "2025-07-20T00:00:00Z",
            "path": str(request.url.path)
        }
    )

# --- 6. Root Endpoint ---
@app.get("/", tags=["Root"])
def read_root():
    """Root endpoint dengan informasi API."""
    return {
        "message": "Welcome to TPN Locations API",
        "version": "FINAL",
        "documentation": "/docs",
        "endpoints": {
            "locations": "/locations",
            "seed": "/api/seed",
            "health": "/health"
        },
        "status": "running"
    }

@app.get("/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint untuk memastikan API dan database berjalan."""
    try:
        # Test database connection
        db.execute("SELECT 1")
        
        # Get locations count
        location_count = db.query(DBLocation).count()
        
        return {
            "status": "healthy",
            "database": "connected",
            "locations_count": location_count,
            "timestamp": "2025-07-20T00:00:00Z"
        }
    except Exception as e:
        raise HTTPException(
            status_code=503, 
            detail=f"Service unavailable - Database error: {str(e)}"
        )
# --- 7. Endpoint Seeding Rahasia (Jalankan Sekali) ---
@app.post("/api/seed", response_model=SuccessResponse, tags=["Admin (Jalankan Sekali Saja)"])
def seed_database(secret: str = Query(..., description="Kunci rahasia untuk seeding."), db: Session = Depends(get_db)):
    """Mengisi database dengan data awal dari db.json. Membutuhkan kunci rahasia."""
    try:
        if secret != settings.SEED_SECRET:
            raise HTTPException(status_code=403, detail="Kunci rahasia tidak valid.")

        if db.query(DBLocation).count() > 0:
            raise HTTPException(status_code=400, detail="Database sudah terisi.")

        # File db.json harus ada di folder root proyek
        try:
            with open('db.json', 'r', encoding='utf-8') as f:
                locations_data = json.load(f)["locations"]
        except FileNotFoundError:
            raise HTTPException(status_code=500, detail="File db.json tidak ditemukan di root proyek.")
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="File db.json tidak valid (JSON error).")

        for loc_data in locations_data:
            if 'Layout' in loc_data:
                loc_data['layout_info'] = loc_data.pop('Layout')
            try:
                db.add(DBLocation(**loc_data))
            except Exception as e:
                db.rollback()
                raise HTTPException(status_code=500, detail=f"Error adding location data: {str(e)}")
        
        db.commit()
        return SuccessResponse(
            message=f"SUKSES! {len(locations_data)} data berhasil dimasukkan.",
            data={"count": len(locations_data)}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected error during seeding: {str(e)}")

# --- 8. Endpoint CRUD & Filter ---

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
    try:
        query = db.query(DBLocation)
        
        if loca:
            query = query.filter(DBLocation.loca.ilike(f"%{loca}%"))
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(or_(DBLocation.name.ilike(search_term), DBLocation.desc.ilike(search_term)))

        if sort_by in ["id", "name"]:
            column_to_sort = getattr(DBLocation, sort_by)
            query = query.order_by(column_to_sort.desc() if order.lower() == "desc" else column_to_sort.asc())
        
        results = query.limit(limit).all()
        return results
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving locations: {str(e)}")

@app.post("/locations", response_model=Location, status_code=201, tags=["Locations"])
def create_location(location: LocationCreate, db: Session = Depends(get_db)):
    """CREATE: Menambahkan lokasi baru."""
    try:
        new_location = DBLocation(**location.model_dump())
        db.add(new_location)
        db.commit()
        db.refresh(new_location)
        return new_location
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Data lokasi tidak valid atau sudah ada.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating location: {str(e)}")

@app.get("/locations/{location_id}", response_model=Location, tags=["Locations"])
def read_location(location_id: int, db: Session = Depends(get_db)):
    """READ: Mengambil satu lokasi berdasarkan ID."""
    try:
        if location_id <= 0:
            raise HTTPException(status_code=400, detail="ID lokasi harus berupa angka positif.")
        
        location = db.query(DBLocation).filter(DBLocation.id == location_id).first()
        if not location:
            raise HTTPException(
                status_code=404, 
                detail=f"Lokasi dengan ID {location_id} tidak ditemukan."
            )
        return location
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving location: {str(e)}")

@app.patch("/locations/{location_id}", response_model=Location, tags=["Locations"])
def update_location(location_id: int, location_update: LocationUpdate, db: Session = Depends(get_db)):
    """UPDATE: Memperbarui data lokasi yang ada."""
    try:
        if location_id <= 0:
            raise HTTPException(status_code=400, detail="ID lokasi harus berupa angka positif.")
        
        db_location = db.query(DBLocation).filter(DBLocation.id == location_id).first()
        if not db_location:
            raise HTTPException(
                status_code=404, 
                detail=f"Lokasi dengan ID {location_id} tidak ditemukan."
            )
        
        update_data = location_update.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="Tidak ada data untuk diperbarui.")
        
        for key, value in update_data.items():
            setattr(db_location, key, value)
        
        db.commit()
        db.refresh(db_location)
        return db_location
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating location: {str(e)}")

@app.delete("/locations/{location_id}", status_code=204, tags=["Locations"])
def delete_location(location_id: int, db: Session = Depends(get_db)):
    """DELETE: Menghapus lokasi berdasarkan ID."""
    try:
        if location_id <= 0:
            raise HTTPException(status_code=400, detail="ID lokasi harus berupa angka positif.")
        
        db_location = db.query(DBLocation).filter(DBLocation.id == location_id).first()
        if not db_location:
            raise HTTPException(
                status_code=404, 
                detail=f"Lokasi dengan ID {location_id} tidak ditemukan."
            )
        
        db.delete(db_location)
        db.commit()
        return None
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting location: {str(e)}")