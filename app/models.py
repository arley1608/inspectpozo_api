from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Date,
    Time,
    Boolean,
    Float,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from .database import Base


class Usuario(Base):
    __tablename__ = "usuario"

    id = Column(Integer, primary_key=True, index=True)
    usuario = Column(String, unique=True, nullable=False, index=True)
    contrasenia = Column(String, nullable=False)
    nombre = Column(String, nullable=False)

    proyectos = relationship(
        "Proyecto",
        back_populates="usuario",
        cascade="all, delete-orphan",
    )


class Proyecto(Base):
    __tablename__ = "proyecto"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(Text, nullable=False)
    contrato = Column(String, nullable=True)
    contratante = Column(Text, nullable=True)
    contratista = Column(Text, nullable=True)
    encargado = Column(Text, nullable=True)

    id_usuario = Column(
        Integer,
        ForeignKey("usuario.id", ondelete="CASCADE"),
        nullable=False,
    )

    usuario = relationship("Usuario", back_populates="proyectos")

    estructuras_hidraulicas = relationship(
        "EstructuraHidraulica",
        back_populates="proyecto",
        cascade="all, delete-orphan",
    )


class EstructuraHidraulica(Base):
    __tablename__ = "estructura_hidraulica"

    # --- claves y datos básicos ---
    id = Column(String, primary_key=True, index=True)
    tipo = Column(String, nullable=False)  # Pozo / Sumidero

    # geometry en PostGIS; aquí lo manejamos como texto (WKT / GeoJSON) por simplicidad
    geometria = Column(Text, nullable=True)

    fecha_inspeccion = Column(Date, nullable=True)
    hora_inspeccion = Column(Time, nullable=True)
    clima_inspeccion = Column(Text, nullable=True)
    tipo_via = Column(Text, nullable=True)

    tipo_sistema = Column(Text, nullable=False)
    material = Column(Text, nullable=True)

    # Pozo
    cono_reduccion = Column(Boolean, nullable=True)
    altura_cono = Column(Float, nullable=True)
    profundidad_pozo = Column(Float, nullable=True)
    diametro_camara = Column(Float, nullable=True)

    # Compartidos
    sedimentacion = Column(Boolean, nullable=True)
    cobertura_tuberia_salida = Column(Boolean, nullable=True)
    deposito_predomina = Column(Text, nullable=True)
    flujo_represado = Column(Boolean, nullable=True)
    nivel_cubre_cotasalida = Column(Boolean, nullable=True)
    cota_estructura = Column(Float, nullable=True)
    condiciones_investiga = Column(Text, nullable=True)
    observaciones = Column(Text, nullable=True)

    # Sumidero
    tipo_sumidero = Column(Text, nullable=True)
    ancho_sumidero = Column(Float, nullable=True)
    largo_sumidero = Column(Float, nullable=True)
    altura_sumidero = Column(Float, nullable=True)

    ancho_rejilla = Column(Float, nullable=True)
    largo_rejilla = Column(Float, nullable=True)
    altura_rejilla = Column(Float, nullable=True)
    material_rejilla = Column(Text, nullable=True)

    # FK
    id_proyecto = Column(
        Integer,
        ForeignKey("proyecto.id", ondelete="CASCADE"),
        nullable=False,
    )

    material_sumidero = Column(Text, nullable=True)

    proyecto = relationship("Proyecto", back_populates="estructuras_hidraulicas")
