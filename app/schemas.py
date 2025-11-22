from datetime import date, time
from typing import Optional, List
from pydantic import BaseModel

# ==========================
#         AUTH / USERS
# ==========================

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    id: int
    usuario: str
    nombre: str


class UserBase(BaseModel):
    usuario: str
    nombre: str


class UserCreate(UserBase):
    contrasenia: str


class UserOut(UserBase):
    id: int

    class Config:
        from_attributes = True


# ==========================
#         PROYECTOS
# ==========================

class ProjectBase(BaseModel):
    nombre: str
    contrato: Optional[str] = None
    contratante: Optional[str] = None
    contratista: Optional[str] = None
    encargado: Optional[str] = None


class ProjectCreate(ProjectBase):
    """Datos que envía la app para crear proyecto."""
    pass


class ProjectOut(ProjectBase):
    id: int
    id_usuario: int

    class Config:
        from_attributes = True


class ProjectDetailOut(ProjectOut):
    """Por si luego necesitas más info diferenciada."""
    pass


class ProjectUpdate(BaseModel):
    """Campos opcionales para actualización parcial."""
    nombre: Optional[str] = None
    contrato: Optional[str] = None
    contratante: Optional[str] = None
    contratista: Optional[str] = None
    encargado: Optional[str] = None


# ==========================
#   ESTRUCTURAS HIDRÁULICAS
# ==========================

class EstructuraHidraulicaBase(BaseModel):
    id: str
    tipo: str  # "Pozo" o "Sumidero"

    geometria: Optional[str] = None
    fecha_inspeccion: Optional[date] = None
    hora_inspeccion: Optional[time] = None
    clima_inspeccion: Optional[str] = None
    tipo_via: Optional[str] = None

    tipo_sistema: str
    material: Optional[str] = None

    cono_reduccion: Optional[bool] = None
    altura_cono: Optional[float] = None
    profundidad_pozo: Optional[float] = None
    diametro_camara: Optional[float] = None

    sedimentacion: Optional[bool] = None
    cobertura_tuberia_salida: Optional[bool] = None
    deposito_predomina: Optional[str] = None
    flujo_represado: Optional[bool] = None
    nivel_cubre_cotasalida: Optional[bool] = None
    cota_estructura: Optional[float] = None
    condiciones_investiga: Optional[str] = None
    observaciones: Optional[str] = None

    tipo_sumidero: Optional[str] = None
    ancho_sumidero: Optional[float] = None
    largo_sumidero: Optional[float] = None
    altura_sumidero: Optional[float] = None
    material_sumidero: Optional[str] = None

    ancho_rejilla: Optional[float] = None
    largo_rejilla: Optional[float] = None
    altura_rejilla: Optional[float] = None
    material_rejilla: Optional[str] = None

    id_proyecto: int


class EstructuraHidraulicaCreate(EstructuraHidraulicaBase):
    pass


class EstructuraHidraulicaOut(EstructuraHidraulicaBase):
    class Config:
        from_attributes = True


class EstructuraHidraulicaUpdate(BaseModel):
    """
    Campos opcionales para actualización parcial de una estructura
    hidráulica (usado en PUT /estructuras/{id}).

    Aquí se permiten TODOS los campos de la tabla, excepto el ID.
    """
    tipo: Optional[str] = None

    geometria: Optional[str] = None
    fecha_inspeccion: Optional[date] = None
    hora_inspeccion: Optional[time] = None
    clima_inspeccion: Optional[str] = None
    tipo_via: Optional[str] = None

    tipo_sistema: Optional[str] = None
    material: Optional[str] = None

    cono_reduccion: Optional[bool] = None
    altura_cono: Optional[float] = None
    profundidad_pozo: Optional[float] = None
    diametro_camara: Optional[float] = None

    sedimentacion: Optional[bool] = None
    cobertura_tuberia_salida: Optional[bool] = None
    deposito_predomina: Optional[str] = None
    flujo_represado: Optional[bool] = None
    nivel_cubre_cotasalida: Optional[bool] = None
    cota_estructura: Optional[float] = None
    condiciones_investiga: Optional[str] = None
    observaciones: Optional[str] = None

    tipo_sumidero: Optional[str] = None
    ancho_sumidero: Optional[float] = None
    largo_sumidero: Optional[float] = None
    altura_sumidero: Optional[float] = None
    material_sumidero: Optional[str] = None

    ancho_rejilla: Optional[float] = None
    largo_rejilla: Optional[float] = None
    altura_rejilla: Optional[float] = None
    material_rejilla: Optional[str] = None

    id_proyecto: Optional[int] = None
