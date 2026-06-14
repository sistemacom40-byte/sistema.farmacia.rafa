from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class Usuario(UserMixin, db.Model):

    _tablename_ = "usuario"

    id = db.Column(db.Integer, primary_key=True)

    nombre = db.Column(
        db.String(100),
        nullable=False
    )

    correo = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(255),
        nullable=False
    )

    rol = db.Column(
        db.String(50),
        default="Administrador"
    )

    activo = db.Column(
        db.Boolean,
        default=True
    )

    creado = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    def get_id(self):
        return str(self.id)