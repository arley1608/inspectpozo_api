from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Form,
)
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Tuple, List, Dict, Any
import hashlib
import json

from .database import SessionLocal, engine, Base
from . import models, schemas
from .auth_utils import create_token_for_user, get_user_by_token

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="InspectPozo API",
    version="2.2.0",
    description="Backend para app InspectPozo (usuarios, proyectos, estructuras hidráulicas y tuberías).",
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
#   HELPER WKT PARA TUBERÍAS
# ==========================

def _parse_point_wkt(wkt: str) -> Tuple[float, float]:
    """
    Parsea un WKT tipo 'POINT(x y)' y devuelve (x, y).
    Lanza ValueError si el formato no es válido.
    """
    if not wkt:
        raise ValueError("WKT vacío")

    txt = wkt.strip()
    if not txt.lower().startswith("point(") or not txt.endswith(")"):
        raise ValueError(f"Formato WKT no soportado: {txt}")

    # contenido entre paréntesis
    inner = txt[txt.find("(") + 1: -1].strip()
    # Admitimos separador coma o espacio
    parts = inner.replace(",", " ").split()
    if len(parts) != 2:
        raise ValueError(f"POINT debe tener 2 coordenadas: {inner}")

    x = float(parts[0])
    y = float(parts[1])
    return x, y


def _parse_linestring_wkt(wkt: str) -> List[List[float]]:
    """
    Parsea un WKT tipo 'LINESTRING(x1 y1, x2 y2, ...)' y devuelve
    [[x1, y1], [x2, y2], ...].
    """
    if not wkt:
        return []

    txt = wkt.strip()
    if not txt.lower().startswith("linestring(") or not txt.endswith(")"):
        return []

    inner = txt[txt.find("(") + 1: -1].strip()
    parts = inner.split(",")

    coords: List[List[float]] = []
    for part in parts:
        tokens = part.strip().split()
        if len(tokens) != 2:
            continue
        x = float(tokens[0])
        y = float(tokens[1])
        coords.append([x, y])

    return coords


def _get_point_from_structure(db: Session, estructura_id: str) -> Tuple[float, float]:
    """
    Obtiene la geometría de una estructura como WKT usando ST_AsText
    (soporta columnas geometry/WKB) y devuelve (x, y) del POINT.
    """
    wkt = db.execute(
        text("SELECT ST_AsText(geometria) FROM estructura_hidraulica WHERE id = :id"),
        {"id": estructura_id},
    ).scalar()

    if not wkt:
        raise ValueError(f"Estructura {estructura_id} sin geometría o no existe")

    return _parse_point_wkt(wkt)


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


@app.put("/proyectos/{proyecto_id}", response_model=schemas.ProjectOut)
def actualizar_proyecto(
    proyecto_id: int,
    token: str,
    data: schemas.ProjectUpdate,
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
            detail="Proyecto no encontrado o no pertenece al usuario",
        )

    if data.nombre is not None:
        proyecto.nombre = data.nombre
    if data.contrato is not None:
        proyecto.contrato = data.contrato
    if data.contratante is not None:
        proyecto.contratante = data.contratante
    if data.contratista is not None:
        proyecto.contratista = data.contratista
    if data.encargado is not None:
        proyecto.encargado = data.encargado

    db.commit()
    db.refresh(proyecto)

    return proyecto


# ==========================
#   ESTRUCTURAS HIDRÁULICAS
# ==========================

@app.get("/estructuras/next-id")
def get_next_estructura_id(
    tipo: str,
    token: str,
    db: Session = Depends(get_db),
):
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


@app.delete("/estructuras/{estructura_id}")
def eliminar_estructura_hidraulica(
    estructura_id: str,
    token: str,
    db: Session = Depends(get_db),
):
    user = get_user_by_token(db, token)

    estructura = (
        db.query(models.EstructuraHidraulica)
        .filter(models.EstructuraHidraulica.id == estructura_id)
        .first()
    )

    if not estructura:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estructura no encontrada",
        )

    db.delete(estructura)
    db.commit()

    return {"ok": True}


@app.put("/estructuras/{estructura_id}", response_model=schemas.EstructuraHidraulicaOut)
def actualizar_estructura_hidraulica(
    estructura_id: str,
    token: str,
    data: schemas.EstructuraHidraulicaUpdate,
    db: Session = Depends(get_db),
):
    user = get_user_by_token(db, token)

    # Buscar la estructura y verificar que su proyecto pertenezca al usuario
    estructura = (
        db.query(models.EstructuraHidraulica)
        .join(models.Proyecto, models.EstructuraHidraulica.id_proyecto == models.Proyecto.id)
        .filter(
            models.EstructuraHidraulica.id == estructura_id,
            models.Proyecto.id_usuario == user.id,
        )
        .first()
    )

    if not estructura:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estructura no encontrada o no pertenece al usuario",
        )

    # ---- Actualizar TODOS los campos excepto el id ----

    if data.tipo is not None:
        estructura.tipo = data.tipo

    if data.geometria is not None:
        estructura.geometria = data.geometria
    if data.fecha_inspeccion is not None:
        estructura.fecha_inspeccion = data.fecha_inspeccion
    if data.hora_inspeccion is not None:
        estructura.hora_inspeccion = data.hora_inspeccion
    if data.clima_inspeccion is not None:
        estructura.clima_inspeccion = data.clima_inspeccion
    if data.tipo_via is not None:
        estructura.tipo_via = data.tipo_via

    if data.tipo_sistema is not None:
        estructura.tipo_sistema = data.tipo_sistema
    if data.material is not None:
        estructura.material = data.material

    if data.cono_reduccion is not None:
        estructura.cono_reduccion = data.cono_reduccion
    if data.altura_cono is not None:
        estructura.altura_cono = data.altura_cono
    if data.profundidad_pozo is not None:
        estructura.profundidad_pozo = data.profundidad_pozo
    if data.diametro_camara is not None:
        estructura.diametro_camara = data.diametro_camara

    if data.sedimentacion is not None:
        estructura.sedimentacion = data.sedimentacion
    if data.cobertura_tuberia_salida is not None:
        estructura.cobertura_tuberia_salida = data.cobertura_tuberia_salida
    if data.deposito_predomina is not None:
        estructura.deposito_predomina = data.deposito_predomina
    if data.flujo_represado is not None:
        estructura.flujo_represado = data.flujo_represado
    if data.nivel_cubre_cotasalida is not None:
        estructura.nivel_cubre_cotasalida = data.nivel_cubre_cotasalida
    if data.cota_estructura is not None:
        estructura.cota_estructura = data.cota_estructura
    if data.condiciones_investiga is not None:
        estructura.condiciones_investiga = data.condiciones_investiga
    if data.observaciones is not None:
        estructura.observaciones = data.observaciones

    if data.tipo_sumidero is not None:
        estructura.tipo_sumidero = data.tipo_sumidero
    if data.ancho_sumidero is not None:
        estructura.ancho_sumidero = data.ancho_sumidero
    if data.largo_sumidero is not None:
        estructura.largo_sumidero = data.largo_sumidero
    if data.altura_sumidero is not None:
        estructura.altura_sumidero = data.altura_sumidero
    if data.material_sumidero is not None:
        estructura.material_sumidero = data.material_sumidero

    if data.ancho_rejilla is not None:
        estructura.ancho_rejilla = data.ancho_rejilla
    if data.largo_rejilla is not None:
        estructura.largo_rejilla = data.largo_rejilla
    if data.altura_rejilla is not None:
        estructura.altura_rejilla = data.altura_rejilla
    if data.material_rejilla is not None:
        estructura.material_rejilla = data.material_rejilla

    if data.id_proyecto is not None:
        # Validar que el nuevo proyecto también sea del mismo usuario
        proyecto_nuevo = (
            db.query(models.Proyecto)
            .filter(
                models.Proyecto.id == data.id_proyecto,
                models.Proyecto.id_usuario == user.id,
            )
            .first()
        )
        if not proyecto_nuevo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proyecto destino no encontrado o no pertenece al usuario",
            )
        estructura.id_proyecto = data.id_proyecto

    db.commit()
    db.refresh(estructura)

    return estructura


# ==========================
#         TUBERÍAS
# ==========================

# 🔹 NUEVO: obtener siguiente ID global para tubería
@app.get("/tuberias/next-id")
def get_next_tuberia_id(
    token: str,
    db: Session = Depends(get_db),
):
    """
    Genera el siguiente ID global de tubería con prefijo 'tub' y
    sufijo numérico incremental (ej: tub0001, tub0002, ...).
    """
    user = get_user_by_token(db, token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o usuario no encontrado",
        )

    prefix = "tub"
    rows = db.query(models.Tuberia.id).all()

    max_num = 0
    for (tid,) in rows:
        if not tid:
            continue
        tid_lower = tid.lower()
        if not tid_lower.startswith(prefix):
            continue
        try:
            num_part = tid[len(prefix):]
            num = int(num_part)
            if num > max_num:
                max_num = num
        except (IndexError, ValueError):
            continue

    next_num = max_num + 1
    new_id = f"{prefix}{next_num:04d}"

    return {"id": new_id}


@app.post("/tuberias/", response_model=schemas.PipeOut)
def crear_tuberia(
    data: schemas.PipeCreate,  # id se ignora, se genera en el backend
    token: str,
    db: Session = Depends(get_db),
):
    """
    Crea una tubería entre dos estructuras hidráulicas.
    La geometría se construye automáticamente como LINESTRING
    entre los POINT de inicio y destino usando ST_AsText(geometria)
    para soportar columnas geometry/WKB.

    Además:
      - El ID de la tubería se genera automáticamente como 'tubXXXX'
        de forma incremental global.
      - La cota clave de inicio y destino se calcula como:
          cota_clave = cota_estructura - profundidad_clave
    """
    user = get_user_by_token(db, token)

    # 1) Generar ID automático para la tubería (ignora data.id)
    prefix = "tub"
    rows = db.query(models.Tuberia.id).all()
    max_num = 0
    for (tid,) in rows:
        if not tid:
            continue
        tid_lower = tid.lower()
        if not tid_lower.startswith(prefix):
            continue
        try:
            num_part = tid[len(prefix):]
            num = int(num_part)
            if num > max_num:
                max_num = num
        except (IndexError, ValueError):
            continue
    next_num = max_num + 1
    new_pipe_id = f"{prefix}{next_num:04d}"

    # 2) Obtener estructuras de inicio y destino
    est_inicio = db.query(models.EstructuraHidraulica).get(
        data.id_estructura_inicio
    )
    est_dest = db.query(models.EstructuraHidraulica).get(
        data.id_estructura_destino
    )

    if not est_inicio or not est_dest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estructura de inicio o destino no encontrada",
        )

    # 3) Verificar que ambas estructuras pertenezcan a proyectos del usuario
    proyectos_ids_usuario = {
        p.id
        for p in db.query(models.Proyecto)
        .filter(models.Proyecto.id_usuario == user.id)
        .all()
    }

    if (
        est_inicio.id_proyecto not in proyectos_ids_usuario
        or est_dest.id_proyecto not in proyectos_ids_usuario
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Las estructuras no pertenecen a proyectos del usuario",
        )

    # 4) Construir geometría de la tubería (LINESTRING) a partir de las geometrías de las estructuras
    try:
        x1, y1 = _get_point_from_structure(db, est_inicio.id)
        x2, y2 = _get_point_from_structure(db, est_dest.id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "No se pudo construir la geometría de la tubería. "
                "Verifica que las estructuras tengan geometría POINT válida."
            ),
        )

    geom = f"LINESTRING({x1} {y1}, {x2} {y2})"

    # 5) Calcular cota clave inicio/destino usando:
    #    cota_clave = cota_estructura - profundidad_clave
    cota_clave_inicio_calc = data.cota_clave_inicio
    if est_inicio.cota_estructura is not None and data.profundidad_clave_inicio is not None:
        cota_clave_inicio_calc = (
            est_inicio.cota_estructura - data.profundidad_clave_inicio
        )

    cota_clave_destino_calc = data.cota_clave_destino
    if est_dest.cota_estructura is not None and data.profundidad_clave_destino is not None:
        cota_clave_destino_calc = (
            est_dest.cota_estructura - data.profundidad_clave_destino
        )

    # 6) Crear instancia ORM con geometría, cotas calculadas e ID generado
    tuberia = models.Tuberia(
        id=new_pipe_id,  # 👈 usamos el ID generado
        diametro=data.diametro,
        material=data.material,
        flujo=data.flujo,
        estado=data.estado,
        sedimento=data.sedimento,
        cota_clave_inicio=cota_clave_inicio_calc,
        cota_batea_inicio=data.cota_batea_inicio,
        profundidad_clave_inicio=data.profundidad_clave_inicio,
        profundidad_batea_inicio=data.profundidad_batea_inicio,
        cota_clave_destino=cota_clave_destino_calc,
        cota_batea_destino=data.cota_batea_destino,
        profundidad_clave_destino=data.profundidad_clave_destino,
        profundidad_batea_destino=data.profundidad_batea_destino,
        grados=data.grados,
        observaciones=data.observaciones,
        geometria=geom,
        id_estructura_inicio=data.id_estructura_inicio,
        id_estructura_destino=data.id_estructura_destino,
    )

    db.add(tuberia)
    db.commit()
    db.refresh(tuberia)

    return tuberia


@app.get("/tuberias/{estructura_id}", response_model=list[schemas.PipeOut])
def listar_tuberias_por_estructura(
    estructura_id: str,
    token: str,
    db: Session = Depends(get_db),
):
    """
    Lista las tuberías donde la estructura participa como inicio o destino.
    Solo se devuelven tuberías asociadas a proyectos del usuario.
    """
    user = get_user_by_token(db, token)

    # Verificar que la estructura pertenezca a un proyecto del usuario
    estructura = (
        db.query(models.EstructuraHidraulica)
        .join(models.Proyecto, models.EstructuraHidraulica.id_proyecto == models.Proyecto.id)
        .filter(
            models.EstructuraHidraulica.id == estructura_id,
            models.Proyecto.id_usuario == user.id,
        )
        .first()
    )
    if not estructura:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estructura no encontrada o no pertenece a proyectos del usuario",
        )

    proyectos_ids_usuario = {
        p.id
        for p in db.query(models.Proyecto)
        .filter(models.Proyecto.id_usuario == user.id)
        .all()
    }

    q = (
        db.query(models.Tuberia)
        .join(
            models.EstructuraHidraulica,
            models.Tuberia.id_estructura_inicio == models.EstructuraHidraulica.id,
        )
        .filter(
            models.EstructuraHidraulica.id_proyecto.in_(proyectos_ids_usuario),
            (
                (models.Tuberia.id_estructura_inicio == estructura_id)
                | (models.Tuberia.id_estructura_destino == estructura_id)
            ),
        )
    )

    tuberias = q.all()

    return tuberias


@app.put("/tuberias/{tuberia_id}", response_model=schemas.PipeOut)
def actualizar_tuberia(
    tuberia_id: str,
    token: str,
    data: schemas.PipeUpdate,
    db: Session = Depends(get_db),
):
    """
    Actualiza una tubería existente. No permite cambiar:
    - id
    - id_estructura_inicio
    - id_estructura_destino
    - geometría
    """
    user = get_user_by_token(db, token)

    tuberia = (
        db.query(models.Tuberia)
        .join(
            models.EstructuraHidraulica,
            models.Tuberia.id_estructura_inicio == models.EstructuraHidraulica.id,
        )
        .join(
            models.Proyecto,
            models.EstructuraHidraulica.id_proyecto == models.Proyecto.id,
        )
        .filter(
            models.Tuberia.id == tuberia_id,
            models.Proyecto.id_usuario == user.id,
        )
        .first()
    )

    if not tuberia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tubería no encontrada o no pertenece a proyectos del usuario",
        )

    # Actualizar campos permitidos
    if data.diametro is not None:
        tuberia.diametro = data.diametro
    if data.material is not None:
        tuberia.material = data.material
    if data.flujo is not None:
        tuberia.flujo = data.flujo
    if data.estado is not None:
        tuberia.estado = data.estado
    if data.sedimento is not None:
        tuberia.sedimento = data.sedimento

    if data.cota_clave_inicio is not None:
        tuberia.cota_clave_inicio = data.cota_clave_inicio
    if data.cota_batea_inicio is not None:
        tuberia.cota_batea_inicio = data.cota_batea_inicio
    if data.profundidad_clave_inicio is not None:
        tuberia.profundidad_clave_inicio = data.profundidad_clave_inicio
    if data.profundidad_batea_inicio is not None:
        tuberia.profundidad_batea_inicio = data.profundidad_batea_inicio

    if data.cota_clave_destino is not None:
        tuberia.cota_clave_destino = data.cota_clave_destino
    if data.cota_batea_destino is not None:
        tuberia.cota_batea_destino = data.cota_batea_destino
    if data.profundidad_clave_destino is not None:
        tuberia.profundidad_clave_destino = data.profundidad_clave_destino
    if data.profundidad_batea_destino is not None:
        tuberia.profundidad_batea_destino = data.profundidad_batea_destino

    if data.grados is not None:
        tuberia.grados = data.grados
    if data.observaciones is not None:
        tuberia.observaciones = data.observaciones

    db.commit()
    db.refresh(tuberia)

    return tuberia


@app.delete("/tuberias/{tuberia_id}")
def eliminar_tuberia(
    tuberia_id: str,
    token: str,
    db: Session = Depends(get_db),
):
    """
    Elimina una tubería si pertenece a algún proyecto del usuario.
    """
    user = get_user_by_token(db, token)

    tuberia = (
        db.query(models.Tuberia)
        .join(
            models.EstructuraHidraulica,
            models.Tuberia.id_estructura_inicio == models.EstructuraHidraulica.id,
        )
        .join(
            models.Proyecto,
            models.EstructuraHidraulica.id_proyecto == models.Proyecto.id,
        )
        .filter(
            models.Tuberia.id == tuberia_id,
            models.Proyecto.id_usuario == user.id,
        )
        .first()
    )

    if not tuberia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tubería no encontrada o no pertenece a proyectos del usuario",
        )

    db.delete(tuberia)
    db.commit()

    return {"ok": True}


# ==========================
#      MAPA / CONEXIONES
# ==========================

@app.get("/proyectos/{proyecto_id}/map-data")
def get_project_map_data(
    proyecto_id: int,
    token: str,
    db: Session = Depends(get_db),
):
    """
    Devuelve la información necesaria para pintar el mapa:
    - structures: lista de {id, tipo, lat, lon}
    - pipes: lista de {id, id_estructura_inicio, id_estructura_destino, coords}
      donde coords = [[lon, lat], ...]
    Usando geometría almacenada en PostGIS.
    Se asume que geometria ya está en coordenadas WGS84 (lon, lat).
    """
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
            detail="Proyecto no encontrado o no pertenece al usuario",
        )

    # ----- Estructuras: POINT -> lat/lon -----
    estructuras_rows = db.execute(
        text(
            """
            SELECT
              id,
              tipo,
              ST_Y(geometria) AS lat,
              ST_X(geometria) AS lon
            FROM estructura_hidraulica
            WHERE id_proyecto = :pid
              AND geometria IS NOT NULL
            """
        ),
        {"pid": proyecto_id},
    ).mappings().all()

    structures: List[Dict[str, Any]] = [dict(r) for r in estructuras_rows]

    # ----- Tuberías: LINESTRING -> coords [[lon, lat], ...] -----
    pipes_rows = db.execute(
        text(
            """
            SELECT
              t.id,
              t.id_estructura_inicio,
              t.id_estructura_destino,
              ST_AsText(t.geometria) AS wkt
            FROM tuberia t
            JOIN estructura_hidraulica e1
              ON t.id_estructura_inicio = e1.id
            WHERE e1.id_proyecto = :pid
              AND t.geometria IS NOT NULL
            """
        ),
        {"pid": proyecto_id},
    ).mappings().all()

    pipes: List[Dict[str, Any]] = []
    for row in pipes_rows:
        coords = _parse_linestring_wkt(row["wkt"])
        if not coords:
            continue
        pipes.append(
            {
                "id": row["id"],
                "id_estructura_inicio": row["id_estructura_inicio"],
                "id_estructura_destino": row["id_estructura_destino"],
                "coords": coords,  # [[lon, lat], ...]
            }
        )

    return {
        "structures": structures,
        "pipes": pipes,
    }
