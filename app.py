"""
GymFlow - Sistema de Gestión para Gimnasios de Barrio
BETA VERSION - Demo comercial

Stack: Flask + SQLite
Compatible con Flask 3.0+ y Render
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta
import sqlite3
import json
import secrets
import os

# ===============================
# CONFIGURACIÓN DE LA APP
# ===============================

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))

# En Render solo /tmp es escribible, en local usa el directorio actual
DATABASE = os.environ.get('DATABASE_URL', 'gymflow.db')
if DATABASE.startswith('sqlite:///'):
    DATABASE = DATABASE.replace('sqlite:///', '')
# Si estamos en Render, usar /tmp
if os.environ.get('RENDER'):
    DATABASE = '/tmp/gymflow.db'

# ===============================
# FUNCIONES DE BASE DE DATOS
# ===============================

def get_db():
    """Conecta a la base de datos SQLite"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Inicializa la base de datos con las tablas y datos de ejemplo"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Tabla de usuarios (admin/profesores)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            nombre TEXT NOT NULL
        )
    ''')
    
    # Tabla de alumnos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alumnos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            telefono TEXT,
            email TEXT,
            username TEXT UNIQUE,
            password TEXT,
            fecha_inicio DATE NOT NULL,
            fecha_vencimiento DATE NOT NULL,
            notas TEXT,
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabla de rutinas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rutinas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alumno_id INTEGER NOT NULL,
            nombre TEXT NOT NULL,
            fecha_inicio DATE NOT NULL,
            fecha_fin DATE NOT NULL,
            ejercicios TEXT NOT NULL,
            creada_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (alumno_id) REFERENCES alumnos(id)
        )
    ''')
    
    # Tabla de campañas de marketing
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS campanas_marketing (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            mensaje TEXT NOT NULL,
            tipo TEXT NOT NULL,
            destinatarios TEXT NOT NULL,
            enviado INTEGER DEFAULT 0,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_envio TIMESTAMP
        )
    ''')
    
    # Insertar usuario admin si no existe
    cursor.execute("SELECT 1 FROM usuarios WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO usuarios (username, password, nombre)
            VALUES ('admin', 'admin123', 'Juan Rodríguez')
        ''')
    
    # Insertar datos de ejemplo solo si no hay alumnos
    cursor.execute("SELECT COUNT(*) as count FROM alumnos")
    if cursor.fetchone()['count'] == 0:
        alumnos_ejemplo = [
            ('María López', '381-555-1234', 'maria.lopez@email.com', 'maria', 'gym123', '2025-12-01', '2026-02-28', 'Lesión rodilla izquierda'),
            ('Carlos Gómez', '381-555-5678', 'carlos.gomez@email.com', 'carlos', 'gym123', '2025-11-15', '2026-01-15', ''),
            ('Ana Martínez', '381-555-9012', 'ana.martinez@email.com', 'ana', 'gym123', '2026-01-10', '2026-03-10', ''),
            ('Pedro Fernández', '381-555-3456', 'pedro.fernandez@email.com', 'pedro', 'gym123', '2025-10-01', '2026-01-20', 'Principiante'),
        ]
        
        for alumno in alumnos_ejemplo:
            cursor.execute('''
                INSERT INTO alumnos (nombre, telefono, email, username, password, fecha_inicio, fecha_vencimiento, notas)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', alumno)
        
        # Rutinas de ejemplo
        rutina_ejemplo = json.dumps([
            {
                "nombre": "Sentadillas",
                "series": 4,
                "repeticiones": "12",
                "descanso": "90 seg",
                "notas": "Bajar hasta 90° - mantener rodillas alineadas"
            },
            {
                "nombre": "Press de banca",
                "series": 3,
                "repeticiones": "10",
                "descanso": "120 seg",
                "notas": "Controlar la bajada"
            }
        ])
        
        cursor.execute('''
            INSERT INTO rutinas (alumno_id, nombre, fecha_inicio, fecha_fin, ejercicios)
            VALUES (1, 'Hipertrofia - Febrero 2026', '2026-01-27', '2026-03-27', ?)
        ''', (rutina_ejemplo,))
    
    conn.commit()
    conn.close()

# ===============================
# FUNCIONES AUXILIARES
# ===============================

def calcular_estado_alumno(fecha_vencimiento_str):
    """Calcula el estado de un alumno según su fecha de vencimiento"""
    fecha_venc = datetime.strptime(fecha_vencimiento_str, '%Y-%m-%d').date()
    hoy = datetime.now().date()
    dias_restantes = (fecha_venc - hoy).days
    
    if dias_restantes < 0:
        return 'vencido'
    elif dias_restantes <= 7:
        return 'por_vencer'
    else:
        return 'activo'

def calcular_estado_rutina(fecha_fin_str):
    """Calcula el estado de una rutina según su fecha de fin"""
    fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
    hoy = datetime.now().date()
    dias_restantes = (fecha_fin - hoy).days
    
    if dias_restantes < 0:
        return 'vencida'
    elif dias_restantes <= 7:
        return 'por_vencer'
    else:
        return 'vigente'

def dias_restantes(fecha_str):
    """Calcula días restantes desde hoy hasta una fecha"""
    fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    hoy = datetime.now().date()
    return (fecha - hoy).days

# ===============================
# RUTAS - LANDING Y LOGIN
# ===============================

@app.route('/')
def index():
    """Landing page pública del sistema"""
    return render_template('landing.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    """Login del dueño/admin"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db()
        user = conn.execute(
            'SELECT * FROM usuarios WHERE username = ? AND password = ?',
            (username, password)
        ).fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['nombre'] = user['nombre']
            flash('¡Bienvenido de nuevo!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
    
    return render_template('login.html')

@app.route('/alumno/login', methods=['GET', 'POST'])
def alumno_login():
    """Login para alumnos"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db()
        alumno = conn.execute(
            'SELECT * FROM alumnos WHERE username = ? AND password = ?',
            (username, password)
        ).fetchone()
        conn.close()
        
        if alumno:
            session['alumno_id'] = alumno['id']
            session['alumno_nombre'] = alumno['nombre']
            session['is_alumno'] = True
            flash('¡Bienvenido de nuevo!', 'success')
            return redirect(url_for('alumno_portal'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
    
    return render_template('alumno_login.html')

@app.route('/logout')
def logout():
    """Cerrar sesión (admin o alumno)"""
    session.clear()
    flash('Sesión cerrada correctamente', 'success')
    return redirect(url_for('index'))

# ===============================
# RUTAS - DASHBOARD
# ===============================

@app.route('/dashboard')
def dashboard():
    """Panel principal del dueño con métricas clave"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    alumnos = conn.execute('SELECT * FROM alumnos ORDER BY nombre').fetchall()
    
    total_alumnos = len(alumnos)
    alumnos_vencidos = 0
    alumnos_por_vencer = 0
    
    for alumno in alumnos:
        estado = calcular_estado_alumno(alumno['fecha_vencimiento'])
        if estado == 'vencido':
            alumnos_vencidos += 1
        elif estado == 'por_vencer':
            alumnos_por_vencer += 1
    
    rutinas = conn.execute('SELECT * FROM rutinas ORDER BY fecha_fin').fetchall()
    rutinas_por_vencer = sum(1 for r in rutinas if calcular_estado_rutina(r['fecha_fin']) == 'por_vencer')
    
    conn.close()
    
    return render_template('dashboard.html',
                         total_alumnos=total_alumnos,
                         alumnos_vencidos=alumnos_vencidos,
                         alumnos_por_vencer=alumnos_por_vencer,
                         rutinas_por_vencer=rutinas_por_vencer)

# ===============================
# RUTAS - ALUMNOS
# ===============================

@app.route('/alumnos')
def alumnos():
    """Lista de todos los alumnos con filtros"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    filtro = request.args.get('filtro', 'todos')
    busqueda = request.args.get('busqueda', '')
    
    conn = get_db()
    query = 'SELECT * FROM alumnos'
    params = []
    
    if busqueda:
        query += ' WHERE nombre LIKE ?'
        params.append(f'%{busqueda}%')
    
    query += ' ORDER BY nombre'
    alumnos_db = conn.execute(query, params).fetchall()
    conn.close()
    
    alumnos_procesados = []
    for alumno in alumnos_db:
        estado = calcular_estado_alumno(alumno['fecha_vencimiento'])
        
        if filtro == 'activos' and estado == 'vencido':
            continue
        elif filtro == 'vencidos' and estado != 'vencido':
            continue
        
        alumnos_procesados.append({
            'id': alumno['id'],
            'nombre': alumno['nombre'],
            'telefono': alumno['telefono'],
            'fecha_vencimiento': alumno['fecha_vencimiento'],
            'notas': alumno['notas'],
            'estado': estado,
            'dias_restantes': dias_restantes(alumno['fecha_vencimiento'])
        })
    
    return render_template('alumnos.html', 
                         alumnos=alumnos_procesados, 
                         filtro=filtro,
                         busqueda=busqueda)

@app.route('/alumno/nuevo', methods=['GET', 'POST'])
def alumno_nuevo():
    """Formulario para crear un nuevo alumno"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        telefono = request.form.get('telefono')
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        fecha_inicio = request.form.get('fecha_inicio')
        fecha_vencimiento = request.form.get('fecha_vencimiento')
        notas = request.form.get('notas', '')
        
        conn = get_db()
        conn.execute('''
            INSERT INTO alumnos (nombre, telefono, email, username, password, fecha_inicio, fecha_vencimiento, notas)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (nombre, telefono, email, username, password, fecha_inicio, fecha_vencimiento, notas))
        conn.commit()
        conn.close()
        
        flash(f'Alumno {nombre} agregado correctamente. Usuario: {username} | Contraseña: {password}', 'success')
        return redirect(url_for('alumnos'))
    
    hoy = datetime.now().date()
    vencimiento_default = (hoy + timedelta(days=30)).strftime('%Y-%m-%d')
    
    return render_template('alumno_form.html', 
                         alumno=None, 
                         hoy=hoy.strftime('%Y-%m-%d'),
                         vencimiento_default=vencimiento_default)

@app.route('/alumno/editar/<int:id>', methods=['GET', 'POST'])
def alumno_editar(id):
    """Formulario para editar un alumno existente"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        telefono = request.form.get('telefono')
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        fecha_inicio = request.form.get('fecha_inicio')
        fecha_vencimiento = request.form.get('fecha_vencimiento')
        notas = request.form.get('notas', '')
        
        conn.execute('''
            UPDATE alumnos 
            SET nombre = ?, telefono = ?, email = ?, username = ?, password = ?, 
                fecha_inicio = ?, fecha_vencimiento = ?, notas = ?
            WHERE id = ?
        ''', (nombre, telefono, email, username, password, fecha_inicio, fecha_vencimiento, notas, id))
        conn.commit()
        conn.close()
        
        flash(f'Datos de {nombre} actualizados', 'success')
        return redirect(url_for('alumnos'))
    
    alumno = conn.execute('SELECT * FROM alumnos WHERE id = ?', (id,)).fetchone()
    conn.close()
    
    if not alumno:
        flash('Alumno no encontrado', 'error')
        return redirect(url_for('alumnos'))
    
    return render_template('alumno_form.html', alumno=alumno)

@app.route('/alumno/eliminar/<int:id>')
def alumno_eliminar(id):
    """Eliminar un alumno"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    alumno = conn.execute('SELECT nombre FROM alumnos WHERE id = ?', (id,)).fetchone()
    
    if alumno:
        conn.execute('DELETE FROM rutinas WHERE alumno_id = ?', (id,))
        conn.execute('DELETE FROM alumnos WHERE id = ?', (id,))
        conn.commit()
        flash(f'{alumno["nombre"]} eliminado del sistema', 'success')
    
    conn.close()
    return redirect(url_for('alumnos'))

# ===============================
# RUTAS - RUTINAS
# ===============================

@app.route('/rutinas')
def rutinas():
    """Lista de todas las rutinas"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    rutinas_db = conn.execute('''
        SELECT r.*, a.nombre as alumno_nombre 
        FROM rutinas r
        JOIN alumnos a ON r.alumno_id = a.id
        ORDER BY r.fecha_fin DESC
    ''').fetchall()
    conn.close()
    
    rutinas_procesadas = []
    for rutina in rutinas_db:
        estado = calcular_estado_rutina(rutina['fecha_fin'])
        rutinas_procesadas.append({
            'id': rutina['id'],
            'alumno_id': rutina['alumno_id'],
            'alumno_nombre': rutina['alumno_nombre'],
            'nombre': rutina['nombre'],
            'fecha_inicio': rutina['fecha_inicio'],
            'fecha_fin': rutina['fecha_fin'],
            'estado': estado,
            'dias_restantes': dias_restantes(rutina['fecha_fin'])
        })
    
    return render_template('rutinas.html', rutinas=rutinas_procesadas)

@app.route('/rutina/nueva/<int:alumno_id>', methods=['GET', 'POST'])
def rutina_nueva(alumno_id):
    """Crear nueva rutina para un alumno"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    alumno = conn.execute('SELECT * FROM alumnos WHERE id = ?', (alumno_id,)).fetchone()
    
    if not alumno:
        flash('Alumno no encontrado', 'error')
        conn.close()
        return redirect(url_for('alumnos'))
    
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        fecha_inicio = request.form.get('fecha_inicio')
        fecha_fin = request.form.get('fecha_fin')
        
        ejercicios = []
        ejercicio_index = 0
        while True:
            ejercicio_nombre = request.form.get(f'ejercicio_nombre_{ejercicio_index}')
            if not ejercicio_nombre:
                break
            
            ejercicios.append({
                'nombre': ejercicio_nombre,
                'series': request.form.get(f'ejercicio_series_{ejercicio_index}'),
                'repeticiones': request.form.get(f'ejercicio_reps_{ejercicio_index}'),
                'descanso': request.form.get(f'ejercicio_descanso_{ejercicio_index}'),
                'notas': request.form.get(f'ejercicio_notas_{ejercicio_index}', '')
            })
            ejercicio_index += 1
        
        ejercicios_json = json.dumps(ejercicios)
        
        conn.execute('''
            INSERT INTO rutinas (alumno_id, nombre, fecha_inicio, fecha_fin, ejercicios)
            VALUES (?, ?, ?, ?, ?)
        ''', (alumno_id, nombre, fecha_inicio, fecha_fin, ejercicios_json))
        conn.commit()
        conn.close()
        
        flash(f'Rutina creada para {alumno["nombre"]}', 'success')
        return redirect(url_for('alumnos'))
    
    conn.close()
    
    hoy = datetime.now().date()
    fin_default = (hoy + timedelta(days=60)).strftime('%Y-%m-%d')
    
    return render_template('rutina_form.html', 
                         alumno=alumno, 
                         rutina=None,
                         hoy=hoy.strftime('%Y-%m-%d'),
                         fin_default=fin_default)

@app.route('/rutina/editar/<int:id>', methods=['GET', 'POST'])
def rutina_editar(id):
    """Editar una rutina existente"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    rutina = conn.execute('''
        SELECT r.*, a.nombre as alumno_nombre, a.id as alumno_id
        FROM rutinas r
        JOIN alumnos a ON r.alumno_id = a.id
        WHERE r.id = ?
    ''', (id,)).fetchone()
    
    if not rutina:
        flash('Rutina no encontrada', 'error')
        conn.close()
        return redirect(url_for('rutinas'))
    
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        fecha_inicio = request.form.get('fecha_inicio')
        fecha_fin = request.form.get('fecha_fin')
        
        ejercicios = []
        ejercicio_index = 0
        while True:
            ejercicio_nombre = request.form.get(f'ejercicio_nombre_{ejercicio_index}')
            if not ejercicio_nombre:
                break
            
            ejercicios.append({
                'nombre': ejercicio_nombre,
                'series': request.form.get(f'ejercicio_series_{ejercicio_index}'),
                'repeticiones': request.form.get(f'ejercicio_reps_{ejercicio_index}'),
                'descanso': request.form.get(f'ejercicio_descanso_{ejercicio_index}'),
                'notas': request.form.get(f'ejercicio_notas_{ejercicio_index}', '')
            })
            ejercicio_index += 1
        
        ejercicios_json = json.dumps(ejercicios)
        
        conn.execute('''
            UPDATE rutinas 
            SET nombre = ?, fecha_inicio = ?, fecha_fin = ?, ejercicios = ?
            WHERE id = ?
        ''', (nombre, fecha_inicio, fecha_fin, ejercicios_json, id))
        conn.commit()
        conn.close()
        
        flash('Rutina actualizada', 'success')
        return redirect(url_for('rutinas'))
    
    ejercicios = json.loads(rutina['ejercicios'])
    conn.close()
    
    return render_template('rutina_form.html', 
                         alumno={'id': rutina['alumno_id'], 'nombre': rutina['alumno_nombre']},
                         rutina=dict(rutina),
                         ejercicios=ejercicios)

@app.route('/rutina/eliminar/<int:id>')
def rutina_eliminar(id):
    """Eliminar una rutina"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    conn.execute('DELETE FROM rutinas WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    
    flash('Rutina eliminada', 'success')
    return redirect(url_for('rutinas'))

# ===============================
# RUTAS - PORTAL DEL ALUMNO
# ===============================

@app.route('/alumno/portal')
def alumno_portal():
    """Portal del alumno (requiere login)"""
    if 'alumno_id' not in session:
        return redirect(url_for('alumno_login'))
    
    alumno_id = session['alumno_id']
    
    conn = get_db()
    alumno = conn.execute('SELECT * FROM alumnos WHERE id = ?', (alumno_id,)).fetchone()
    
    rutina = conn.execute('''
        SELECT * FROM rutinas 
        WHERE alumno_id = ? 
        ORDER BY fecha_fin DESC 
        LIMIT 1
    ''', (alumno_id,)).fetchone()
    
    conn.close()
    
    if not alumno:
        session.clear()
        return redirect(url_for('alumno_login'))
    
    estado_alumno = calcular_estado_alumno(alumno['fecha_vencimiento'])
    dias_cuota = dias_restantes(alumno['fecha_vencimiento'])
    
    rutina_data = None
    if rutina:
        ejercicios = json.loads(rutina['ejercicios'])
        estado_rutina = calcular_estado_rutina(rutina['fecha_fin'])
        dias_rutina = dias_restantes(rutina['fecha_fin'])
        
        rutina_data = {
            'nombre': rutina['nombre'],
            'fecha_inicio': rutina['fecha_inicio'],
            'fecha_fin': rutina['fecha_fin'],
            'estado': estado_rutina,
            'dias_restantes': dias_rutina,
            'ejercicios': ejercicios
        }
    
    return render_template('alumno_portal.html',
                         alumno=alumno,
                         estado_alumno=estado_alumno,
                         dias_cuota=dias_cuota,
                         rutina=rutina_data)

@app.route('/alumno/ver/<int:id>')
def alumno_ver(id):
    """Vista pública para que el alumno vea su rutina (sin login)"""
    conn = get_db()
    
    alumno = conn.execute('SELECT * FROM alumnos WHERE id = ?', (id,)).fetchone()
    
    if not alumno:
        conn.close()
        return render_template('error.html', mensaje='Alumno no encontrado')
    
    rutina = conn.execute('''
        SELECT * FROM rutinas 
        WHERE alumno_id = ? 
        ORDER BY fecha_fin DESC 
        LIMIT 1
    ''', (id,)).fetchone()
    
    conn.close()
    
    estado_alumno = calcular_estado_alumno(alumno['fecha_vencimiento'])
    dias_cuota = dias_restantes(alumno['fecha_vencimiento'])
    
    rutina_data = None
    if rutina:
        ejercicios = json.loads(rutina['ejercicios'])
        estado_rutina = calcular_estado_rutina(rutina['fecha_fin'])
        dias_rutina = dias_restantes(rutina['fecha_fin'])
        
        rutina_data = {
            'nombre': rutina['nombre'],
            'fecha_inicio': rutina['fecha_inicio'],
            'fecha_fin': rutina['fecha_fin'],
            'estado': estado_rutina,
            'dias_restantes': dias_rutina,
            'ejercicios': ejercicios
        }
    
    return render_template('alumno_view.html',
                         alumno=alumno,
                         estado_alumno=estado_alumno,
                         dias_cuota=dias_cuota,
                         rutina=rutina_data)

# ===============================
# RUTAS - MARKETING
# ===============================

@app.route('/marketing')
def marketing():
    """Panel de marketing para el dueño"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    
    campanas = conn.execute('''
        SELECT * FROM campanas_marketing 
        ORDER BY fecha_creacion DESC
    ''').fetchall()
    
    total_alumnos = conn.execute('SELECT COUNT(*) as count FROM alumnos').fetchone()['count']
    
    alumnos_vencidos = 0
    alumnos = conn.execute('SELECT fecha_vencimiento FROM alumnos').fetchall()
    for alumno in alumnos:
        if calcular_estado_alumno(alumno['fecha_vencimiento']) == 'vencido':
            alumnos_vencidos += 1
    
    conn.close()
    
    return render_template('marketing.html',
                         campanas=campanas,
                         total_alumnos=total_alumnos,
                         alumnos_vencidos=alumnos_vencidos)

@app.route('/marketing/nueva', methods=['GET', 'POST'])
def marketing_nueva():
    """Crear nueva campaña de marketing"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        titulo = request.form.get('titulo')
        mensaje = request.form.get('mensaje')
        tipo = request.form.get('tipo')
        destinatarios = request.form.get('destinatarios')
        
        conn = get_db()
        conn.execute('''
            INSERT INTO campanas_marketing (titulo, mensaje, tipo, destinatarios)
            VALUES (?, ?, ?, ?)
        ''', (titulo, mensaje, tipo, destinatarios))
        conn.commit()
        conn.close()
        
        flash(f'Campaña "{titulo}" creada correctamente', 'success')
        return redirect(url_for('marketing'))
    
    conn = get_db()
    alumnos = conn.execute('SELECT * FROM alumnos').fetchall()
    
    stats = {
        'todos': len(alumnos),
        'activos': 0,
        'vencidos': 0,
        'por_vencer': 0
    }
    
    for alumno in alumnos:
        estado = calcular_estado_alumno(alumno['fecha_vencimiento'])
        if estado == 'activo':
            stats['activos'] += 1
        elif estado == 'vencido':
            stats['vencidos'] += 1
        elif estado == 'por_vencer':
            stats['por_vencer'] += 1
    
    conn.close()
    
    return render_template('marketing_form.html', stats=stats)

@app.route('/marketing/preview/<int:id>')
def marketing_preview(id):
    """Preview de una campaña de marketing"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    campana = conn.execute('SELECT * FROM campanas_marketing WHERE id = ?', (id,)).fetchone()
    
    if campana['destinatarios'] == 'todos':
        destinatarios = conn.execute('SELECT * FROM alumnos').fetchall()
    elif campana['destinatarios'] == 'vencidos':
        alumnos = conn.execute('SELECT * FROM alumnos').fetchall()
        destinatarios = [a for a in alumnos if calcular_estado_alumno(a['fecha_vencimiento']) == 'vencido']
    elif campana['destinatarios'] == 'activos':
        alumnos = conn.execute('SELECT * FROM alumnos').fetchall()
        destinatarios = [a for a in alumnos if calcular_estado_alumno(a['fecha_vencimiento']) == 'activo']
    else:
        destinatarios = []
    
    conn.close()
    
    return render_template('marketing_preview.html', 
                         campana=campana, 
                         destinatarios=destinatarios,
                         calcular_estado_alumno=calcular_estado_alumno)

@app.route('/marketing/eliminar/<int:id>')
def marketing_eliminar(id):
    """Eliminar campaña de marketing"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    conn.execute('DELETE FROM campanas_marketing WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    
    flash('Campaña eliminada', 'success')
    return redirect(url_for('marketing'))

# ===============================
# INICIALIZACIÓN
# ===============================

# Inicializar la base de datos al arrancar la app (compatible con Flask 3.0 y Gunicorn)
with app.app_context():
    init_db()
    print("✅ Base de datos inicializada")

if __name__ == '__main__':
    # Solo para desarrollo local
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)