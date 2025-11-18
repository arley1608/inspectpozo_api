from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Date,
    Time,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from .database import Base


class Usuario(Base):
    __tablename__ = "usuario"

    id = Column(Integer, primary_key=True, index=True)
    usuario = Column(String, unique=True, index=True, nullable=False)
    contrasenia = Column(String, nullable=False)
    nombre = Column(Text, nullable=False)


class Proyecto(Base):
    __tablename__ = "proyecto"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(Text, nullable=False)
    contrato = Column(String, nullable=True)
    contratante = Column(Text, nullable=True)
    contratista = Column(Text, nullable=True)
    encargado = Column(Text, nullable=True)

    id_usuario = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    usuario = relationship("Usuario", backref="proyectos")


class EstructuraHidraulica(Base):
    """
    Modelo ORM simplificado para la tabla estructura_hidraulica.
    Solo usamos algunos campos clave por ahora; el resto pueden
    quedar como NULL en la base (o con sus valores por defecto).
    """

    __tablename__ = "estructura_hidraulica"

    # En tu tabla el id es character varying (PK)
    id = Column(String, primary_key=True, index=True)

    tipo = Column(String, nullable=True)

    fecha_inspeccion = Column(Date, nullable=True)
    hora_inspeccion = Column(Time, nullable=True)

    clima_inspeccion = Column(Text, nullable=True)
    tipo_via = Column(Text, nullable=True)
    tipo_sistema = Column(Text, nullable=True)
    material = Column(Text, nullable=True)
    observaciones = Column(Text, nullable=True)

    id_proyecto = Column(Integer, ForeignKey("proyecto.id"), nullable=False)
    proyecto = relationship("Proyecto", backref="estructuras_hidraulicas")
