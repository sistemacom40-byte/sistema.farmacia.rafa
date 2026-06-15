from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class Usuario(UserMixin, db.Model):
    __tablename__ = "usuario"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    correo = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    rol = db.Column(db.String(50), default="Cajero")  # Administrador, Cajero
    activo = db.Column(db.Boolean, default=True)

class Categoria(db.Model):
    __tablename__ = "categoria"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.String(200))
    medicamentos = db.relationship('Medicamento', backref='categoria', lazy=True)

class Proveedor(db.Model):
    __tablename__ = "proveedor"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    telefono = db.Column(db.String(20))
    correo = db.Column(db.String(120))
    direccion = db.Column(db.String(200))
    medicamentos = db.relationship('Medicamento', backref='proveedor', lazy=True)

class Medicamento(db.Model):
    __tablename__ = "medicamento"
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), unique=True, nullable=False)
    nombre = db.Column(db.String(150), nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria.id'))
    proveedor_id = db.Column(db.Integer, db.ForeignKey('proveedor.id'))
    precio_compra = db.Column(db.Float, default=0)
    precio_venta = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0)
    stock_minimo = db.Column(db.Integer, default=5)
    fecha_vencimiento = db.Column(db.Date)
    descripcion = db.Column(db.String(300))

class Cliente(db.Model):
    __tablename__ = "cliente"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    telefono = db.Column(db.String(20))
    direccion = db.Column(db.String(200))
    ventas = db.relationship('Venta', backref='cliente', lazy=True)

class Venta(db.Model):
    __tablename__ = "venta"
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), unique=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    subtotal = db.Column(db.Float, default=0)
    descuento = db.Column(db.Float, default=0)
    total = db.Column(db.Float, default=0)
    detalles = db.relationship('DetalleVenta', backref='venta', lazy=True)
    usuario = db.relationship('Usuario', backref='ventas')

class DetalleVenta(db.Model):
    __tablename__ = "detalle_venta"
    id = db.Column(db.Integer, primary_key=True)
    venta_id = db.Column(db.Integer, db.ForeignKey('venta.id'))
    medicamento_id = db.Column(db.Integer, db.ForeignKey('medicamento.id'))
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    medicamento = db.relationship('Medicamento')
