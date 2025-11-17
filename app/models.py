from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base


class Usuario(Base):
    __tablename__ = "usuario"

    id = Column(Integer, primary_key=True, index=True)
    usuario = Column(String, unique=True, nullable=False, index=True)
    contrasenia = Column(String, nullable=False)
    nombre = Column(String, nullable=False)

    # relación uno-a-muchos con proyectos
    proyectos = relationship("Proyecto", back_populates="usuario")


class Proyecto(Base):
    __tablename__ = "proyecto"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    contrato = Column(String, nullable=True)
    contratante = Column(String, nullable=True)
    contratista = Column(String, nullable=True)
    encargado = Column(String, nullable=True)

    # debe coincidir con tu columna id_usuario bigint en PostgreSQL
    id_usuario = Column(Integer, ForeignKey("usuario.id"), nullable=True)

    usuario = relationship("Usuario", back_populates="proyectos")
