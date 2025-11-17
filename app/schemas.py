from typing import Optional
from pydantic import BaseModel


# ==========================
#        USUARIOS
# ==========================

class UserCreate(BaseModel):
    usuario: str
    nombre: str
    contrasenia: str


class UserOut(BaseModel):
    id: int
    usuario: str
    nombre: str

    class Config:
        orm_mode = True


# ==========================
#        AUTH
# ==========================

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
#        PROYECTOS
# ==========================

class ProjectCreate(BaseModel):
    nombre: str
    contrato: Optional[str] = None
    contratante: Optional[str] = None
    contratista: Optional[str] = None
    encargado: Optional[str] = None


class ProjectOut(BaseModel):
    """
    Respuesta mínima para creación de proyecto (sync del outbox):
    Flutter solo necesita el id y el nombre para actualizar serverId.
    """
    id: int
    nombre: str

    class Config:
        orm_mode = True


class ProjectDetailOut(BaseModel):
    """
    Respuesta completa para listar proyectos en la app.
    """
    id: int
    nombre: str
    contrato: Optional[str] = None
    contratante: Optional[str] = None
    contratista: Optional[str] = None
    encargado: Optional[str] = None

    class Config:
        orm_mode = True
