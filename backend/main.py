from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from typing import List, Optional
from pydantic import BaseModel
import os

app = FastAPI()

# --- FRONTEND ACCESS (CORS) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # ok for local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- SIMPLE ADMIN AUTH (change these!) ---
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme")
ADMIN_TOKEN    = os.getenv("ADMIN_TOKEN",    "super-secret-token")

def require_admin(authorization: Optional[str] = Header(None)):
    # Expect "Authorization: Bearer <token>"
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing/invalid token")
    token = authorization.split(" ", 1)[1].strip()
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")


# --- DATABASE (SQLite file in this folder) ---
DATABASE_URL = "sqlite:///./sapguidepro.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

class Module(Base):
    __tablename__ = "modules"
    id   = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)

class Guide(Base):
    __tablename__ = "guides"
    id        = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("modules.id"))
    title     = Column(String)
    content   = Column(String)

Base.metadata.create_all(bind=engine)

# --- SCHEMAS ---
class ModuleOut(BaseModel):
    id: int
    name: str
    class Config:
        orm_mode = True

class LoginIn(BaseModel):
    username: str
    password: str

class LoginOut(BaseModel):
    token: str

class GuideCreate(BaseModel):
    module_id: int
    title: str
    content: str

class GuideOut(BaseModel):
    id: int
    module_id: int
    title: str
    content: str
    class Config:
        orm_mode = True


# --- DB SESSION DEP ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- ROUTES ---

@app.get("/api/modules", response_model=List[ModuleOut])
def read_modules(db: Session = Depends(get_db)):
    return db.query(Module).all()

@app.post("/api/login", response_model=LoginOut)
def login(body: LoginIn):
    if body.username == ADMIN_USERNAME and body.password == ADMIN_PASSWORD:
        return {"token": ADMIN_TOKEN}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/api/guides", response_model=GuideOut)
def create_guide(guide: GuideCreate, db: Session = Depends(get_db), _admin = Depends(require_admin)):
    # Ensure module exists
    if not db.query(Module).filter(Module.id == guide.module_id).first():
        raise HTTPException(status_code=404, detail="Module not found")
    db_guide = Guide(**guide.dict())
    db.add(db_guide)
    db.commit()
    db.refresh(db_guide)
    return db_guide

@app.get("/api/guides/{module_id}", response_model=List[GuideOut])
def get_guides(module_id: int, db: Session = Depends(get_db)):
    return db.query(Guide).filter(Guide.module_id == module_id).all()

@app.put("/api/guides/{guide_id}")
def update_guide(guide_id: int, payload: dict, db: Session = Depends(get_db), _admin = Depends(require_admin)):
    guide = db.query(Guide).filter(Guide.id == guide_id).first()
    if not guide:
        raise HTTPException(status_code=404, detail="Guide not found")
    title = payload.get("title")
    content = payload.get("content")
    if title is not None:
        guide.title = title
    if content is not None:
        guide.content = content
    db.commit()
    db.refresh(guide)
    return {"ok": True, "id": guide.id}

@app.delete("/api/guides/{guide_id}")
def delete_guide(guide_id: int, db: Session = Depends(get_db), _admin = Depends(require_admin)):
    guide = db.query(Guide).filter(Guide.id == guide_id).first()
    if not guide:
        raise HTTPException(status_code=404, detail="Guide not found")
    db.delete(guide)
    db.commit()
    return {"ok": True}


# --- OPTIONAL: quick seed endpoint to create some modules ---
@app.post("/api/seed-modules")
def seed_modules(_admin = Depends(require_admin), db: Session = Depends(get_db)):
    names = [
        "SAP FI - Financial Accounting",
        "SAP MM - Materials Management",
        "SAP SD - Sales and Distribution"
    ]
    for n in names:
        if not db.query(Module).filter(Module.name == n).first():
            db.add(Module(name=n))
    db.commit()
    return {"ok": True, "created": True}
