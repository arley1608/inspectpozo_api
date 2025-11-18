from datetime import date, time
from pydantic import BaseModel
from typing import Optional, List


# ==========================
#         USUARIOS
# ==========================

class UserBase(BaseModel):
    usuario: str
    nombre: str


class UserCreate(UserBase):
    contrasenia: str


class UserOut(UserBase):
    id: int

    class Config:
        orm_mode = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    id: int
    usuario: str
    nombre: str

    class Config:
        orm_mode = True


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
    pass


class ProjectOut(ProjectBase):
    id: int

    class Config:
        orm_mode = True


class ProjectDetailOut(ProjectOut):
    # Por ahora es igual, pero aquí podrías agregar más campos luego
    pass


# ==========================
#  ESTRUCTURAS HIDRÁULICAS
# ==========================

class EstructuraHidraulicaBase(BaseModel):
    id: str
    tipo: Optional[str] = None
    fecha_inspeccion: Optional[date] = None
    hora_inspeccion: Optional[time] = None
    clima_inspeccion: Optional[str] = None
    tipo_via: Optional[str] = None
    tipo_sistema: Optional[str] = None
    material: Optional[str] = None
    observaciones: Optional[str] = None
    id_proyecto: int


class EstructuraHidraulicaCreate(EstructuraHidraulicaBase):
    pass


class EstructuraHidraulicaOut(EstructuraHidraulicaBase):
    class Config:
        orm_mode = True
