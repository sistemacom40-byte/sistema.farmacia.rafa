from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, make_response
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta
from functools import wraps
import os

from config import Config
from models import db, Usuario, Categoria, Proveedor, Medicamento, Cliente, Venta, DetalleVenta

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Inicia sesion para continuar"

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

@app.context_processor
def inject_now():
    return {'now': datetime.now()}

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.rol != 'Administrador':
            flash('No tienes permiso para acceder a esta seccion', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

with app.app_context():
    db.create_all()
    if not Usuario.query.filter_by(correo='sistemacom40@gmail.com').first():
        admin = Usuario(
            nombre='Administrador',
            correo='sistemacom40@gmail.com',
            password=generate_password_hash('Admin123'),
            rol='Administrador'
        )
        db.session.add(admin)
        db.session.commit()

# ─── AUTH ───────────────────────────────────────────────────────────────────

@app.route('/', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        correo = request.form['correo']
        password = request.form['password']
        user = Usuario.query.filter_by(correo=correo, activo=True).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Correo o contrasena incorrectos', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ─── DASHBOARD ───────────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    total_meds = Medicamento.query.count()
    total_clientes = Cliente.query.count()
    total_proveedores = Proveedor.query.count()
    
    hoy = date.today()
    inicio_semana = hoy - timedelta(days=6)
    ventas_hoy = Venta.query.filter(db.func.date(Venta.fecha) == hoy).all()
    ventas_hoy_total = sum(v.total for v in ventas_hoy)
    
    stock_bajo = Medicamento.query.filter(Medicamento.stock <= Medicamento.stock_minimo).all()
    
    proximos_vencer = Medicamento.query.filter(
        Medicamento.fecha_vencimiento != None,
        Medicamento.fecha_vencimiento <= date.today() + timedelta(days=30)
    ).all()
    
    # Ventas ultimos 7 dias para grafica
    ventas_semana = []
    for i in range(6, -1, -1):
        d = hoy - timedelta(days=i)
        vs = Venta.query.filter(db.func.date(Venta.fecha) == d).all()
        ventas_semana.append({'fecha': d.strftime('%d/%m'), 'total': sum(v.total for v in vs)})
    
    return render_template('dashboard.html',
        total_meds=total_meds,
        total_clientes=total_clientes,
        total_proveedores=total_proveedores,
        ventas_hoy=ventas_hoy_total,
        stock_bajo=stock_bajo,
        proximos_vencer=proximos_vencer,
        ventas_semana=ventas_semana
    )

# ─── MEDICAMENTOS ─────────────────────────────────────────────────────────────

@app.route('/medicamentos')
@login_required
def medicamentos():
    buscar = request.args.get('buscar', '')
    cat_id = request.args.get('categoria', '')
    query = Medicamento.query
    if buscar:
        query = query.filter(
            db.or_(Medicamento.nombre.ilike(f'%{buscar}%'), Medicamento.codigo.ilike(f'%{buscar}%'))
        )
    if cat_id:
        query = query.filter(Medicamento.categoria_id == cat_id)
    page = request.args.get('page', 1, type=int)
    meds = query.paginate(page=page, per_page=10)
    categorias = Categoria.query.all()
    return render_template('medicamentos.html', meds=meds, categorias=categorias, buscar=buscar, cat_id=cat_id)

@app.route('/medicamentos/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_medicamento():
    if request.method == 'POST':
        med = Medicamento(
            codigo=request.form['codigo'],
            nombre=request.form['nombre'],
            categoria_id=request.form.get('categoria_id') or None,
            proveedor_id=request.form.get('proveedor_id') or None,
            precio_compra=float(request.form.get('precio_compra', 0)),
            precio_venta=float(request.form['precio_venta']),
            stock=int(request.form.get('stock', 0)),
            stock_minimo=int(request.form.get('stock_minimo', 5)),
            descripcion=request.form.get('descripcion', '')
        )
        fv = request.form.get('fecha_vencimiento')
        if fv:
            med.fecha_vencimiento = datetime.strptime(fv, '%Y-%m-%d').date()
        db.session.add(med)
        db.session.commit()
        flash('Medicamento agregado correctamente', 'success')
        return redirect(url_for('medicamentos'))
    categorias = Categoria.query.all()
    proveedores = Proveedor.query.all()
    return render_template('medicamento_form.html', med=None, categorias=categorias, proveedores=proveedores)

@app.route('/medicamentos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_medicamento(id):
    med = Medicamento.query.get_or_404(id)
    if request.method == 'POST':
        med.codigo = request.form['codigo']
        med.nombre = request.form['nombre']
        med.categoria_id = request.form.get('categoria_id') or None
        med.proveedor_id = request.form.get('proveedor_id') or None
        med.precio_compra = float(request.form.get('precio_compra', 0))
        med.precio_venta = float(request.form['precio_venta'])
        med.stock = int(request.form.get('stock', 0))
        med.stock_minimo = int(request.form.get('stock_minimo', 5))
        med.descripcion = request.form.get('descripcion', '')
        fv = request.form.get('fecha_vencimiento')
        med.fecha_vencimiento = datetime.strptime(fv, '%Y-%m-%d').date() if fv else None
        db.session.commit()
        flash('Medicamento actualizado', 'success')
        return redirect(url_for('medicamentos'))
    categorias = Categoria.query.all()
    proveedores = Proveedor.query.all()
    return render_template('medicamento_form.html', med=med, categorias=categorias, proveedores=proveedores)

@app.route('/medicamentos/eliminar/<int:id>', methods=['POST'])
@login_required
@admin_required
def eliminar_medicamento(id):
    med = Medicamento.query.get_or_404(id)
    db.session.delete(med)
    db.session.commit()
    flash('Medicamento eliminado', 'success')
    return redirect(url_for('medicamentos'))

@app.route('/medicamentos/buscar_codigo')
@login_required
def buscar_por_codigo():
    codigo = request.args.get('codigo', '')
    med = Medicamento.query.filter_by(codigo=codigo).first()
    if med:
        return jsonify({'found': True, 'id': med.id, 'nombre': med.nombre,
                        'precio': med.precio_venta, 'stock': med.stock, 'codigo': med.codigo})
    return jsonify({'found': False})

# ─── CATEGORIAS ───────────────────────────────────────────────────────────────

@app.route('/categorias')
@login_required
def categorias():
    cats = Categoria.query.all()
    return render_template('categorias.html', cats=cats)

@app.route('/categorias/nuevo', methods=['POST'])
@login_required
def nueva_categoria():
    cat = Categoria(nombre=request.form['nombre'], descripcion=request.form.get('descripcion', ''))
    db.session.add(cat)
    db.session.commit()
    flash('Categoria agregada', 'success')
    return redirect(url_for('categorias'))

@app.route('/categorias/editar/<int:id>', methods=['POST'])
@login_required
def editar_categoria(id):
    cat = Categoria.query.get_or_404(id)
    cat.nombre = request.form['nombre']
    cat.descripcion = request.form.get('descripcion', '')
    db.session.commit()
    flash('Categoria actualizada', 'success')
    return redirect(url_for('categorias'))

@app.route('/categorias/eliminar/<int:id>', methods=['POST'])
@login_required
@admin_required
def eliminar_categoria(id):
    cat = Categoria.query.get_or_404(id)
    db.session.delete(cat)
    db.session.commit()
    flash('Categoria eliminada', 'success')
    return redirect(url_for('categorias'))

# ─── PROVEEDORES ──────────────────────────────────────────────────────────────

@app.route('/proveedores')
@login_required
def proveedores():
    provs = Proveedor.query.all()
    return render_template('proveedores.html', provs=provs)

@app.route('/proveedores/nuevo', methods=['POST'])
@login_required
def nuevo_proveedor():
    prov = Proveedor(
        nombre=request.form['nombre'],
        telefono=request.form.get('telefono', ''),
        correo=request.form.get('correo', ''),
        direccion=request.form.get('direccion', '')
    )
    db.session.add(prov)
    db.session.commit()
    flash('Proveedor agregado', 'success')
    return redirect(url_for('proveedores'))

@app.route('/proveedores/editar/<int:id>', methods=['POST'])
@login_required
def editar_proveedor(id):
    prov = Proveedor.query.get_or_404(id)
    prov.nombre = request.form['nombre']
    prov.telefono = request.form.get('telefono', '')
    prov.correo = request.form.get('correo', '')
    prov.direccion = request.form.get('direccion', '')
    db.session.commit()
    flash('Proveedor actualizado', 'success')
    return redirect(url_for('proveedores'))

@app.route('/proveedores/eliminar/<int:id>', methods=['POST'])
@login_required
@admin_required
def eliminar_proveedor(id):
    prov = Proveedor.query.get_or_404(id)
    db.session.delete(prov)
    db.session.commit()
    flash('Proveedor eliminado', 'success')
    return redirect(url_for('proveedores'))

# ─── CLIENTES ─────────────────────────────────────────────────────────────────

@app.route('/clientes')
@login_required
def clientes():
    buscar = request.args.get('buscar', '')
    query = Cliente.query
    if buscar:
        query = query.filter(Cliente.nombre.ilike(f'%{buscar}%'))
    page = request.args.get('page', 1, type=int)
    clts = query.paginate(page=page, per_page=10)
    return render_template('clientes.html', clts=clts, buscar=buscar)

@app.route('/clientes/nuevo', methods=['POST'])
@login_required
def nuevo_cliente():
    cli = Cliente(
        nombre=request.form['nombre'],
        telefono=request.form.get('telefono', ''),
        direccion=request.form.get('direccion', '')
    )
    db.session.add(cli)
    db.session.commit()
    flash('Cliente agregado', 'success')
    return redirect(url_for('clientes'))

@app.route('/clientes/editar/<int:id>', methods=['POST'])
@login_required
def editar_cliente(id):
    cli = Cliente.query.get_or_404(id)
    cli.nombre = request.form['nombre']
    cli.telefono = request.form.get('telefono', '')
    cli.direccion = request.form.get('direccion', '')
    db.session.commit()
    flash('Cliente actualizado', 'success')
    return redirect(url_for('clientes'))

@app.route('/clientes/eliminar/<int:id>', methods=['POST'])
@login_required
@admin_required
def eliminar_cliente(id):
    cli = Cliente.query.get_or_404(id)
    db.session.delete(cli)
    db.session.commit()
    flash('Cliente eliminado', 'success')
    return redirect(url_for('clientes'))

# ─── VENTAS ───────────────────────────────────────────────────────────────────

@app.route('/ventas')
@login_required
def ventas():
    buscar = request.args.get('buscar', '')
    desde = request.args.get('desde', '')
    hasta = request.args.get('hasta', '')
    query = Venta.query
    if buscar:
        query = query.join(Cliente, isouter=True).filter(
            db.or_(Venta.numero.ilike(f'%{buscar}%'),
                   Cliente.nombre.ilike(f'%{buscar}%'))
        )
    if desde:
        query = query.filter(db.func.date(Venta.fecha) >= datetime.strptime(desde, '%Y-%m-%d').date())
    if hasta:
        query = query.filter(db.func.date(Venta.fecha) <= datetime.strptime(hasta, '%Y-%m-%d').date())
    page = request.args.get('page', 1, type=int)
    vs = query.order_by(Venta.fecha.desc()).paginate(page=page, per_page=10)
    return render_template('ventas.html', vs=vs, buscar=buscar, desde=desde, hasta=hasta)

@app.route('/ventas/nueva', methods=['GET', 'POST'])
@login_required
def nueva_venta():
    if request.method == 'POST':
        data = request.get_json()
        cliente_id = data.get('cliente_id') or None
        items = data.get('items', [])
        descuento = float(data.get('descuento', 0))
        metodo_pago = data.get('metodo_pago', 'Efectivo')
        monto_recibido = float(data.get('monto_recibido', 0))
        
        if not items:
            return jsonify({'error': 'No hay productos en la venta'}), 400
        
        # Generar numero de venta
        ultimo = Venta.query.order_by(Venta.id.desc()).first()
        num = f"F-{str((ultimo.id if ultimo else 0) + 1).zfill(6)}"
        
        subtotal = sum(float(i['precio']) * int(i['cantidad']) for i in items)
        total = subtotal - descuento
        
        venta = Venta(
            numero=num,
            cliente_id=cliente_id,
            usuario_id=current_user.id,
            subtotal=subtotal,
            descuento=descuento,
            total=total,
            metodo_pago=metodo_pago,
            monto_recibido=monto_recibido if metodo_pago == 'Efectivo' else total,
            cambio=max(0, monto_recibido - total) if metodo_pago == 'Efectivo' else 0
        )
        db.session.add(venta)
        db.session.flush()
        
        for item in items:
            med = Medicamento.query.get(item['id'])
            if not med or med.stock < int(item['cantidad']):
                db.session.rollback()
                return jsonify({'error': f'Stock insuficiente para {item["nombre"]}'}), 400
            med.stock -= int(item['cantidad'])
            det = DetalleVenta(
                venta_id=venta.id,
                medicamento_id=med.id,
                cantidad=int(item['cantidad']),
                precio_unitario=float(item['precio']),
                subtotal=float(item['precio']) * int(item['cantidad'])
            )
            db.session.add(det)
        
        db.session.commit()
        return jsonify({'success': True, 'venta_id': venta.id, 'numero': num})
    
    clientes_list = Cliente.query.order_by(Cliente.nombre).all()
    return render_template('nueva_venta.html', clientes=clientes_list)

@app.route('/ventas/ticket/<int:id>')
@login_required
def ticket_venta(id):
    venta = Venta.query.get_or_404(id)
    return render_template('ticket.html', venta=venta)

# ─── USUARIOS ─────────────────────────────────────────────────────────────────

@app.route('/usuarios')
@login_required
@admin_required
def usuarios():
    users = Usuario.query.all()
    return render_template('usuarios.html', users=users)

@app.route('/usuarios/nuevo', methods=['POST'])
@login_required
@admin_required
def nuevo_usuario():
    if Usuario.query.filter_by(correo=request.form['correo']).first():
        flash('El correo ya esta registrado', 'danger')
        return redirect(url_for('usuarios'))
    user = Usuario(
        nombre=request.form['nombre'],
        correo=request.form['correo'],
        password=generate_password_hash(request.form['password']),
        rol=request.form.get('rol', 'Cajero')
    )
    db.session.add(user)
    db.session.commit()
    flash('Usuario creado', 'success')
    return redirect(url_for('usuarios'))

@app.route('/usuarios/toggle/<int:id>', methods=['POST'])
@login_required
@admin_required
def toggle_usuario(id):
    user = Usuario.query.get_or_404(id)
    user.activo = not user.activo
    db.session.commit()
    return redirect(url_for('usuarios'))

@app.route('/usuarios/eliminar/<int:id>', methods=['POST'])
@login_required
@admin_required
def eliminar_usuario(id):
    user = Usuario.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    flash('Usuario eliminado', 'success')
    return redirect(url_for('usuarios'))

# ─── REPORTES ─────────────────────────────────────────────────────────────────

@app.route('/reportes/ventas')
@login_required
def reporte_ventas():
    desde = request.args.get('desde', date.today().strftime('%Y-%m-%d'))
    hasta = request.args.get('hasta', date.today().strftime('%Y-%m-%d'))
    d = datetime.strptime(desde, '%Y-%m-%d').date()
    h = datetime.strptime(hasta, '%Y-%m-%d').date()
    
    vs = Venta.query.filter(
        db.func.date(Venta.fecha) >= d,
        db.func.date(Venta.fecha) <= h
    ).order_by(Venta.fecha.desc()).all()
    
    total_ventas = sum(v.total for v in vs)
    total_transacciones = len(vs)
    promedio = total_ventas / total_transacciones if total_transacciones else 0
    
    # Agrupar por dia
    por_dia = {}
    for v in vs:
        key = v.fecha.strftime('%d/%m')
        if key not in por_dia:
            por_dia[key] = 0
        por_dia[key] += v.total
    
    return render_template('reporte_ventas.html',
        vs=vs, desde=desde, hasta=hasta,
        total_ventas=total_ventas, total_transacciones=total_transacciones,
        promedio=promedio, por_dia=por_dia
    )

@app.route('/reportes/inventario')
@login_required
def reporte_inventario():
    meds = Medicamento.query.all()
    valor_total = sum(m.stock * m.precio_venta for m in meds)
    return render_template('reporte_inventario.html', meds=meds, valor_total=valor_total)

# ─── ERRORES ──────────────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

# ─── CAMBIAR PASSWORD ─────────────────────────────────────────────────────────

@app.route('/cambiar-password', methods=['GET', 'POST'])
@login_required
def cambiar_password():
    if request.method == 'POST':
        actual = request.form['password_actual']
        nueva = request.form['password_nueva']
        confirmar = request.form['password_confirmar']
        if not check_password_hash(current_user.password, actual):
            flash('La contrasena actual es incorrecta', 'danger')
        elif nueva != confirmar:
            flash('Las contrasenas nuevas no coinciden', 'danger')
        elif len(nueva) < 6:
            flash('La contrasena debe tener al menos 6 caracteres', 'danger')
        else:
            current_user.password = generate_password_hash(nueva)
            db.session.commit()
            flash('Contrasena cambiada correctamente', 'success')
            return redirect(url_for('dashboard'))
    return render_template('cambiar_password.html')

# ─── EXPORTAR EXCEL ───────────────────────────────────────────────────────────

@app.route('/reportes/ventas/excel')
@login_required
def exportar_ventas_excel():
    desde = request.args.get('desde', date.today().strftime('%Y-%m-%d'))
    hasta = request.args.get('hasta', date.today().strftime('%Y-%m-%d'))
    d = datetime.strptime(desde, '%Y-%m-%d').date()
    h = datetime.strptime(hasta, '%Y-%m-%d').date()
    vs = Venta.query.filter(
        db.func.date(Venta.fecha) >= d,
        db.func.date(Venta.fecha) <= h
    ).order_by(Venta.fecha.desc()).all()

    import csv, io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Numero', 'Fecha', 'Cliente', 'Cajero', 'Subtotal', 'Descuento', 'Total'])
    for v in vs:
        writer.writerow([
            v.numero,
            v.fecha.strftime('%d/%m/%Y %H:%M'),
            v.cliente.nombre if v.cliente else 'General',
            v.usuario.nombre,
            v.subtotal, v.descuento, v.total
        ])
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = f'attachment; filename=ventas_{desde}_{hasta}.csv'
    response.headers['Content-type'] = 'text/csv'
    return response

@app.route('/reportes/inventario/excel')
@login_required
def exportar_inventario_excel():
    meds = Medicamento.query.all()
    import csv, io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Codigo', 'Nombre', 'Categoria', 'Proveedor', 'Stock', 'Precio Venta', 'Valor Total'])
    for m in meds:
        writer.writerow([
            m.codigo, m.nombre,
            m.categoria.nombre if m.categoria else '',
            m.proveedor.nombre if m.proveedor else '',
            m.stock, m.precio_venta,
            m.stock * m.precio_venta
        ])
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=inventario.csv'
    response.headers['Content-type'] = 'text/csv'
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
