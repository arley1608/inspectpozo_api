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
    description="Backend para app InspectPozo (usuarios, proyectos y estructuras hidráulicas).",
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
def get_me(
    token: str,
    db: Session = Depends(get_db),
):
    user = get_user_by_token(db, token)
    return schemas.MeResponse(
        id=user.id,
        usuario=user.usuario,
        nombre=user.nombre,
    )


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

    Formato:
    - Pozo     -> pz0001, pz0002, ...
    - Sumidero -> sm0001, sm0002, ...
    - Otros    -> es0001, es0002, ...
    """

    user = get_user_by_token(db, token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o usuario no encontrado",
        )

    tipo_norm = tipo.strip().lower()
    if tipo_norm == "pozo":
        prefix = "pz"
    elif tipo_norm == "sumidero":
        prefix = "sm"
    else:
        prefix = "es"

    rows = (
        db.query(models.EstructuraHidraulica.id)
        .filter(models.EstructuraHidraulica.id.ilike(f"{prefix}%"))
        .all()
    )

    max_num = 0
    for (sid,) in rows:
        try:
            num_part = sid[len(prefix):]
            num = int(num_part)
            if num > max_num:
                max_num = num
        except (IndexError, ValueError):
            continue

    next_num = max_num + 1
    new_id = f"{prefix}{next_num:04d}"

    return {"id": new_id}


@app.post("/estructuras/", response_model=schemas.EstructuraHidraulicaOut)
def crear_estructura_hidraulica(
    data: schemas.EstructuraHidraulicaCreate,
    token: str,
    db: Session = Depends(get_db),
):
    """
    Crea una estructura hidráulica asociada a un proyecto del usuario,
    usando TODOS los campos definidos en la tabla estructura_hidraulica.
    """

    user = get_user_by_token(db, token)

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
        geometria=data.geometria,
        fecha_inspeccion=data.fecha_inspeccion,
        hora_inspeccion=data.hora_inspeccion,
        clima_inspeccion=data.clima_inspeccion,
        tipo_via=data.tipo_via,
        tipo_sistema=data.tipo_sistema,
        material=data.material,
        cono_reduccion=data.cono_reduccion,
        altura_cono=data.altura_cono,
        profundidad_pozo=data.profundidad_pozo,
        diametro_camara=data.diametro_camara,
        sedimentacion=data.sedimentacion,
        cobertura_tuberia_salida=data.cobertura_tuberia_salida,
        deposito_predomina=data.deposito_predomina,
        flujo_represado=data.flujo_represado,
        nivel_cubre_cotasalida=data.nivel_cubre_cotasalida,
        cota_estructura=data.cota_estructura,
        condiciones_investiga=data.condiciones_investiga,
        observaciones=data.observaciones,
        tipo_sumidero=data.tipo_sumidero,
        ancho_sumidero=data.ancho_sumidero,
        largo_sumidero=data.largo_sumidero,
        altura_sumidero=data.altura_sumidero,
        ancho_rejilla=data.ancho_rejilla,
        largo_rejilla=data.largo_rejilla,
        altura_rejilla=data.altura_rejilla,
        material_rejilla=data.material_rejilla,
        id_proyecto=data.id_proyecto,
        material_sumidero=data.material_sumidero,
    )

    db.add(estructura)
    db.commit()
    db.refresh(estructura)

    return estructura


@app.get(
    "/estructuras/",
    response_model=list[schemas.EstructuraHidraulicaOut],
)
def listar_estructuras_por_proyecto(
    token: str,
    id_proyecto: int,
    db: Session = Depends(get_db),
):
    """
    Lista las estructuras hidráulicas de un proyecto del usuario.
    """

    user = get_user_by_token(db, token)

    proyecto = (
        db.query(models.Proyecto)
        .filter(
            models.Proyecto.id == id_proyecto,
            models.Proyecto.id_usuario == user.id,
        )
        .first()
    )

    if not proyecto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado o no pertenece al usuario",
        )

    estructuras = (
        db.query(models.EstructuraHidraulica)
        .filter(models.EstructuraHidraulica.id_proyecto == id_proyecto)
        .all()
    )

    return estructuras
