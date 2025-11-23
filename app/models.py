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


# =====================================
#               USUARIOS
# =====================================

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


# =====================================
#               PROYECTOS
# =====================================

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


# =====================================
#      ESTRUCTURA HIDRÁULICA
# =====================================

class EstructuraHidraulica(Base):
    __tablename__ = "estructura_hidraulica"

    id = Column(String, primary_key=True, index=True)
    tipo = Column(String, nullable=False)  # Pozo / Sumidero

    # Puede ser WKT o una columna geometry en PostGIS (la usamos vía ST_AsText en el backend)
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

    material_sumidero = Column(Text, nullable=True)

    id_proyecto = Column(
        Integer,
        ForeignKey("proyecto.id", ondelete="CASCADE"),
        nullable=False,
    )

    proyecto = relationship("Proyecto", back_populates="estructuras_hidraulicas")

    # =============================
    #     RELACIÓN CON TUBERÍAS
    # =============================
    # No usamos delete-orphan aquí porque una tubería tiene dos FKs a EstructuraHidraulica.
    # El borrado se maneja con ondelete="CASCADE" en los ForeignKey de Tuberia.
    tuberias_inicio = relationship(
        "Tuberia",
        back_populates="estructura_inicio",
        foreign_keys="Tuberia.id_estructura_inicio",
    )

    tuberias_destino = relationship(
        "Tuberia",
        back_populates="estructura_destino",
        foreign_keys="Tuberia.id_estructura_destino",
    )


# =====================================
#                TUBERÍAS
# =====================================

class Tuberia(Base):
    __tablename__ = "tuberia"

    id = Column(String, primary_key=True, index=True)

    # Geometría de la tubería (LINESTRING en WKT u otro formato)
    # Debe coincidir con la columna NOT NULL que ya existe en la base de datos
    geometria = Column(Text, nullable=False)

    diametro = Column(Float, nullable=True)
    material = Column(Text, nullable=True)
    flujo = Column(Boolean, nullable=True)
    estado = Column(Text, nullable=True)
    sedimento = Column(Boolean, default=False)

    cota_clave_inicio = Column(Float, nullable=True)
    cota_batea_inicio = Column(Float, nullable=True)
    profundidad_clave_inicio = Column(Float, nullable=True)
    profundidad_batea_inicio = Column(Float, nullable=True)

    cota_clave_destino = Column(Float, nullable=True)
    cota_batea_destino = Column(Float, nullable=True)
    profundidad_clave_destino = Column(Float, nullable=True)
    profundidad_batea_destino = Column(Float, nullable=True)

    grados = Column(Float, nullable=True)
    observaciones = Column(Text, nullable=True)

    # --------------------------
    # Relaciones con estructuras
    # --------------------------
    id_estructura_inicio = Column(
        String,
        ForeignKey("estructura_hidraulica.id", ondelete="CASCADE"),
        nullable=False,
    )

    id_estructura_destino = Column(
        String,
        ForeignKey("estructura_hidraulica.id", ondelete="CASCADE"),
        nullable=False,
    )

    estructura_inicio = relationship(
        "EstructuraHidraulica",
        foreign_keys=[id_estructura_inicio],
        back_populates="tuberias_inicio",
    )

    estructura_destino = relationship(
        "EstructuraHidraulica",
        foreign_keys=[id_estructura_destino],
        back_populates="tuberias_destino",
    )
