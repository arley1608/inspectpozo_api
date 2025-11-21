from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 👇 AJUSTA ESTOS DATOS A TU ENTORNO REAL
DB_USER = "postgres"
DB_PASS = "postgres"
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "inspectpozo_2"

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Motor de conexión
engine = create_engine(DATABASE_URL, future=True)

# Sesiones
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# Base ORM
Base = declarative_base()
