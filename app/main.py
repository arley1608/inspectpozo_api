from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .database import SessionLocal, engine, Base
from . import models, schemas
from .auth_utils import create_token_for_user, get_user_by_token

# Crear tablas si no existen (NO borra datos existentes)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="InspectPozo API",
    version="2.0.0",
    description="Backend para app Flutter con usuarios y proyectos",
)


# ==========================
#       DEPENDENCIAS
# ==========================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==========================
#         RUTAS BASE
# ==========================

@app.get("/")
def root():
    return {"message": "InspectPozo API conectada a PostgreSQL"}


@app.get("/ping")
def ping():
    return {"ping": "pong"}


# ==========================
#          AUTH
# ==========================

@app.post("/auth/login", response_model=schemas.TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Flutter envía:
      Content-Type: application/x-www-form-urlencoded
      username=<usuario>
      password=<contrasenia>
    """

    user = (
        db.query(models.Usuario)
        .filter(
            models.Usuario.usuario == form_data.username,
            models.Usuario.contrasenia == form_data.password,
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario o contraseña incorrectos",
        )

    token = create_token_for_user(user)
    return schemas.TokenResponse(access_token=token)


@app.get("/auth/me", response_model=schemas.MeResponse)
def me(token: str, db: Session = Depends(get_db)):
    """
    Flutter llama:
      GET /auth/me?token=<TOKEN>
    """
    user = get_user_by_token(db, token)
    return schemas.MeResponse(id=user.id, usuario=user.usuario, nombre=user.nombre)


# ==========================
#        USUARIOS
# ==========================

@app.post("/auth/register", response_model=schemas.UserOut)
def register_user(
    data: schemas.UserCreate,
    db: Session = Depends(get_db),
):
    """
    Flutter (sync de usuarios) envía JSON:
      {
        "usuario": "...",
        "nombre": "...",
        "contrasenia": "..."
      }
    """

    existing = (
        db.query(models.Usuario)
        .filter(models.Usuario.usuario == data.usuario)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario ya existe",
        )

    nuevo = models.Usuario(
        usuario=data.usuario,
        contrasenia=data.contrasenia,
        nombre=data.nombre,
    )

    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    return nuevo


@app.get("/usuarios", response_model=list[schemas.UserOut])
def listar_usuarios(db: Session = Depends(get_db)):
    return db.query(models.Usuario).all()


# ==========================
#        PROYECTOS
# ==========================

@app.post("/proyectos/", response_model=schemas.ProjectOut)
def crear_proyecto(
    token: str,
    data: schemas.ProjectCreate,
    db: Session = Depends(get_db),
):
    """
    Flutter llama:
      POST /proyectos/?token=<TOKEN>
      body JSON:
      {
        "nombre": "...",
        "contrato": "...",
        "contratante": "...",
        "contratista": "...",
        "encargado": "..."
      }
    """

    # 1) Validar token y obtener usuario dueño
    user = get_user_by_token(db, token)

    # 2) Crear proyecto asociado al usuario
    proyecto = models.Proyecto(
        nombre=data.nombre,
        contrato=data.contrato,
        contratante=data.contratante,
        contratista=data.contratista,
        encargado=data.encargado,
        id_usuario=user.id,
    )

    db.add(proyecto)
    db.commit()
    db.refresh(proyecto)

    # 3) Respuesta: al menos {id, nombre} para sync en Flutter
    return proyecto


@app.get("/proyectos/", response_model=list[schemas.ProjectDetailOut])
def listar_proyectos(
    token: str,
    db: Session = Depends(get_db),
):
    """
    Devuelve todos los proyectos del usuario dueño del token.

    Flutter podrá llamar:
      GET /proyectos/?token=<TOKEN>
    """

    user = get_user_by_token(db, token)

    proyectos = (
        db.query(models.Proyecto)
        .filter(models.Proyecto.id_usuario == user.id)
        .order_by(models.Proyecto.id.desc())
        .all()
    )

    return proyectos
