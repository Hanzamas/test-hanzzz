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

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting up...")
    try:
        # Test database connection first
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        
        # Create tables
        Base.metadata.create_all(bind=engine)
        print("Database tables created successfully!")
    except Exception as e:
        print(f"Error during startup: {e}")
        # Don't fail startup, but log the issue
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
    """Handler untuk HTTP exceptions dengan response yang konsisten."""
    from datetime import datetime
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "path": str(request.url.path),
            "method": request.method
        }
    )

@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handler untuk validation errors dari Pydantic."""
    from datetime import datetime
    
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Data validation failed",
            "status_code": 422,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "path": str(request.url.path),
            "method": request.method,
            "validation_errors": exc.errors()
        }
    )

@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handler untuk database errors."""
    from datetime import datetime
    
    error_detail = "Database operation failed"
    
    # Provide more specific error messages for common issues
    error_str = str(exc)
    if "relation" in error_str and "does not exist" in error_str:
        error_detail = "Database table does not exist. Please run the seeding endpoint first."
    elif "duplicate key" in error_str:
        error_detail = "Duplicate data - record already exists"
    elif "connection" in error_str.lower():
        error_detail = "Database connection failed"
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": error_detail,
            "status_code": 500,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "path": str(request.url.path),
            "method": request.method,
            "error_type": "database_error"
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handler untuk general exceptions."""
    from datetime import datetime
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error occurred",
            "status_code": 500,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "path": str(request.url.path),
            "method": request.method,
            "error_type": "internal_error"
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
        
        # Try to get locations count (create table if not exists)
        try:
            location_count = db.query(DBLocation).count()
        except Exception as e:
            # Jika tabel belum ada, coba buat
            try:
                Base.metadata.create_all(bind=engine)
                location_count = db.query(DBLocation).count()
            except Exception as create_error:
                location_count = "unknown"
                print(f"Could not determine location count: {create_error}")
        
        return {
            "status": "healthy",
            "database": "connected",
            "locations_count": location_count,
            "timestamp": "2025-07-20T00:00:00Z",
            "version": "FINAL",
            "endpoints": {
                "root": "/",
                "docs": "/docs",
                "locations": "/locations",
                "seed": "/api/seed",
                "health": "/health"
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=503, 
            detail=f"Service unavailable - Database error: {str(e)}"
        )

@app.get("/api/debug", tags=["Debug"])
def debug_info():
    """Debug endpoint untuk melihat informasi sistem."""
    import sys
    import platform
    
    try:
        # Test database connection
        test_db = SessionLocal()
        test_db.execute("SELECT 1")
        db_status = "connected"
        test_db.close()
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    # Check file paths
    current_dir = os.getcwd()
    file_exists = {}
    possible_paths = [
        'db.json',
        '../db.json', 
        '/app/db.json',
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db.json')
    ]
    
    for path in possible_paths:
        file_exists[path] = os.path.exists(path)
    
    return {
        "python_version": sys.version,
        "platform": platform.platform(),
        "current_directory": current_dir,
        "database_url_set": bool(settings.DATABASE_URL != "sqlite:///./test.db"),
        "seed_secret_set": bool(settings.SEED_SECRET != "default_secret"),
        "database_status": db_status,
        "file_paths": file_exists,
        "environment_variables": {
            "DATABASE_URL": "***SET***" if settings.DATABASE_URL != "sqlite:///./test.db" else "NOT SET",
            "SEED_SECRET": "***SET***" if settings.SEED_SECRET != "default_secret" else "NOT SET"
        }
    }
# --- 7. Endpoint Seeding Rahasia (Jalankan Sekali) ---
@app.post("/api/seed", response_model=SuccessResponse, tags=["Admin (Jalankan Sekali Saja)"])
def seed_database(secret: str = Query(..., description="Kunci rahasia untuk seeding."), db: Session = Depends(get_db)):
    """Mengisi database dengan data awal dari db.json. Membutuhkan kunci rahasia."""
    try:
        # Validasi secret
        if secret != settings.SEED_SECRET:
            raise HTTPException(status_code=403, detail="Kunci rahasia tidak valid.")

        # Pastikan tabel ada terlebih dahulu
        try:
            Base.metadata.create_all(bind=engine)
        except Exception as e:
            print(f"Warning: Error creating tables: {e}")

        # Cek apakah database sudah terisi
        try:
            existing_count = db.query(DBLocation).count()
            if existing_count > 0:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Database sudah terisi dengan {existing_count} data. Gunakan endpoint DELETE jika ingin mengosongkan terlebih dahulu."
                )
        except Exception as e:
            # Jika query gagal, mungkin tabel belum ada, coba buat ulang
            print(f"Database query failed, attempting to recreate tables: {e}")
            try:
                Base.metadata.drop_all(bind=engine)
                Base.metadata.create_all(bind=engine)
            except Exception as create_error:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Failed to create database tables: {str(create_error)}"
                )

        # Baca file db.json - coba beberapa lokasi
        locations_data = None
        possible_paths = [
            'db.json',
            '../db.json', 
            '/app/db.json',
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db.json')
        ]
        
        for path in possible_paths:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    locations_data = data.get("locations", [])
                    print(f"Successfully loaded db.json from: {path}")
                    break
            except FileNotFoundError:
                continue
            except json.JSONDecodeError as je:
                raise HTTPException(status_code=500, detail=f"File db.json tidak valid (JSON error): {str(je)}")
        
        if not locations_data:
            raise HTTPException(status_code=500, detail="File db.json tidak ditemukan di semua lokasi yang dicoba.")

        # Proses data dan masukkan ke database
        successful_inserts = 0
        for i, loc_data in enumerate(locations_data):
            try:
                # Perbaiki mapping field dari db.json ke model database
                processed_data = {}
                
                # Mapping field yang benar
                field_mapping = {
                    'id': 'id',
                    'name': 'name', 
                    'locations': 'loca',  # Mapping field 'locations' ke 'loca'
                    'loca': 'loca',       # Jika sudah ada field 'loca'
                    'img': 'img',
                    'desc': 'desc',
                    'facilities': 'facilities',
                    'Layout': 'layout',
                    'layout_info': 'layout'
                }
                
                for json_field, db_field in field_mapping.items():
                    if json_field in loc_data:
                        # Jangan tambahkan id jika auto-increment
                        if json_field == 'id':
                            continue
                        processed_data[db_field] = loc_data[json_field]
                
                # Validasi data yang diperlukan
                required_fields = ['name', 'loca', 'img', 'desc']
                for field in required_fields:
                    if field not in processed_data or not processed_data[field]:
                        raise ValueError(f"Missing required field: {field}")
                
                # Buat instance DBLocation
                new_location = DBLocation(**processed_data)
                db.add(new_location)
                successful_inserts += 1
                
            except Exception as e:
                print(f"Error processing location {i+1}: {str(e)}")
                continue
        
        if successful_inserts == 0:
            db.rollback()
            raise HTTPException(
                status_code=500, 
                detail="Tidak ada data yang berhasil diproses. Periksa format data di db.json."
            )
        
        # Commit semua perubahan
        db.commit()
        
        return SuccessResponse(
            message=f"SUKSES! {successful_inserts} dari {len(locations_data)} data berhasil dimasukkan.",
            data={"inserted_count": successful_inserts, "total_data": len(locations_data)}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected error during seeding: {str(e)}")

@app.delete("/api/reset", response_model=SuccessResponse, tags=["Admin (Berbahaya)"])
def reset_database(secret: str = Query(..., description="Kunci rahasia untuk reset database."), db: Session = Depends(get_db)):
    """BERBAHAYA: Mengosongkan seluruh database. Membutuhkan kunci rahasia."""
    try:
        if secret != settings.SEED_SECRET:
            raise HTTPException(status_code=403, detail="Kunci rahasia tidak valid.")
        
        # Hapus semua data
        deleted_count = db.query(DBLocation).count()
        db.query(DBLocation).delete()
        db.commit()
        
        return SuccessResponse(
            message=f"Database berhasil dikosongkan. {deleted_count} record dihapus.",
            data={"deleted_count": deleted_count}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error during database reset: {str(e)}")

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
        # Coba buat tabel jika belum ada
        try:
            query = db.query(DBLocation)
        except Exception as table_error:
            # Jika tabel belum ada, coba buat
            try:
                Base.metadata.create_all(bind=engine)
                query = db.query(DBLocation)
            except Exception as create_error:
                raise HTTPException(
                    status_code=503, 
                    detail="Database tidak siap. Jalankan endpoint /api/seed terlebih dahulu untuk membuat tabel."
                )
        
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
    
    except HTTPException:
        raise
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