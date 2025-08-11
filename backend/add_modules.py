from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./sapguidepro.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Module(Base):
    __tablename__ = "modules"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)

Base.metadata.create_all(bind=engine)

db = SessionLocal()
db.add(Module(name="SAP FI - Financial Accounting"))
db.add(Module(name="SAP MM - Materials Management"))
db.add(Module(name="SAP SD - Sales and Distribution"))
db.commit()
db.close()

print("SAP modules added.")
