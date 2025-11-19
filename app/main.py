from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .database import SessionLocal, engine, Base
from . import models, schemas
from .auth_utils import create_token_for_user, get_user_by_token

# Crear tablas si no existen
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="InspectPozo API",
    version="2.0.0",
    description="Backend para app Flutter con usuarios, proyectos y estructuras hidráulicas",
)


# ==========================
#       DEPENDENCIA DB
# ==========================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==========================
#        RUTAS BASE
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
    user = get_user_by_token(db, token)

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

    return proyecto


@app.get("/proyectos/", response_model=list[schemas.ProjectDetailOut])
def listar_proyectos(
    token: str,
    db: Session = Depends(get_db),
):
    user = get_user_by_token(db, token)

    proyectos = (
        db.query(models.Proyecto)
        .filter(models.Proyecto.id_usuario == user.id)
        .order_by(models.Proyecto.id.desc())
        .all()
    )

    return proyectos


@app.delete("/proyectos/{proyecto_id}")
def eliminar_proyecto(
    proyecto_id: int,
    token: str,
    db: Session = Depends(get_db),
):
    user = get_user_by_token(db, token)

    proyecto = (
        db.query(models.Proyecto)
        .filter(
            models.Proyecto.id == proyecto_id,
            models.Proyecto.id_usuario == user.id,
        )
        .first()
    )

    if not proyecto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado",
        )

    db.delete(proyecto)
    db.commit()

    return {"ok": True}


# ==========================
#   ESTRUCTURAS HIDRÁULICAS
# ==========================

@app.get("/estructuras/next-id")
def get_next_estructura_id(
    tipo: str,
    token: str,
    db: Session = Depends(get_db),
):
    """
    Genera el siguiente ID disponible para una estructura hidráulica.

    El ID se basa en el tipo de estructura:

    - Pozo     -> PZ-001, PZ-002, ...
    - Sumidero -> SM-001, SM-002, ...
    - Otros    -> ES-001, ES-002, ...
    """

    # Validar el token y obtener usuario
    user = get_user_by_token(db, token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o usuario no encontrado",
        )

    # Prefijos según tipo
    prefix_map = {
        "Pozo": "PZ",
        "Sumidero": "SM",
    }
    prefix = prefix_map.get(tipo, "ES")

    # Buscar IDs existentes con ese prefijo
    rows = (
        db.query(models.EstructuraHidraulica.id)
        .filter(models.EstructuraHidraulica.id.like(f"{prefix}-%"))
        .all()
    )

    max_num = 0
    for (sid,) in rows:
        try:
            # asumimos formato PREFIX-###, ej: PZ-001
            num_part = sid.split("-", 1)[1]
            num = int(num_part)
            if num > max_num:
                max_num = num
        except (IndexError, ValueError):
            # Si algún ID no cumple el patrón, lo ignoramos
            continue

    next_num = max_num + 1
    new_id = f"{prefix}-{next_num:03d}"

    return {"id": new_id}


@app.post("/estructuras/", response_model=schemas.EstructuraHidraulicaOut)
def crear_estructura_hidraulica(
    data: schemas.EstructuraHidraulicaCreate,
    token: str,
    db: Session = Depends(get_db),
):
    """
    Crea una estructura hidráulica asociada a un proyecto del usuario.
    """

    user = get_user_by_token(db, token)

    # Validar que el proyecto exista y sea del usuario
    proyecto = (
        db.query(models.Proyecto)
        .filter(
            models.Proyecto.id == data.id_proyecto,
            models.Proyecto.id_usuario == user.id,
        )
        .first()
    )

    if not proyecto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado o no pertenece al usuario",
        )

    estructura = models.EstructuraHidraulica(
        id=data.id,
        tipo=data.tipo,
        fecha_inspeccion=data.fecha_inspeccion,
        hora_inspeccion=data.hora_inspeccion,
        clima_inspeccion=data.clima_inspeccion,
        tipo_via=data.tipo_via,
        tipo_sistema=data.tipo_sistema,
        material=data.material,
        observaciones=data.observaciones,
        id_proyecto=data.id_proyecto,
    )

    db.add(estructura)
    db.commit()
    db.refresh(estructura)

    return estructura
