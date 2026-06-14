from flask import Flask, render_template
from flask_login import LoginManager
from werkzeug.security import generate_password_hash

from config import Config
from models import db, Usuario

app = Flask(_name_)
app.config.from_object(Config)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))


# Crear tablas y usuario administrador automáticamente
with app.app_context():

    db.create_all()

    admin = Usuario.query.filter_by(
        correo="sistemacom40@gmail.com"
    ).first()

    if not admin:

        admin = Usuario(
            nombre="Administrador",
            correo="sistemacom40@gmail.com",
            password=generate_password_hash("Admin123"),
            rol="Administrador"
        )

        db.session.add(admin)
        db.session.commit()


@app.route("/")
def login():

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():

    return render_template("dashboard.html")


if _name_ == "_main_":

    app.run(debug=True)