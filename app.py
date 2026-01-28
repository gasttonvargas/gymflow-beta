"""
GymFlow - Sistema de Gestión para Gimnasios de Barrio
BETA VERSION - Demo comercial

Stack: Flask + SQLite
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
import sqlite3
import secrets
import os

# ===============================
# APP
# ===============================

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'gymflow.db')

# ===============================
# DB
# ===============================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Usuarios
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            nombre TEXT NOT NULL
        )
    """)

    # Alumnos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alumnos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            telefono TEXT,
            fecha_alta TEXT,
            activo INTEGER DEFAULT 1
        )
    """)

    # Usuario admin demo
    cursor.execute("SELECT * FROM usuarios WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO usuarios (username, password, nombre)
            VALUES (?, ?, ?)
        """, ('admin', 'admin123', 'Administrador'))

    # Alumnos demo
    cursor.execute("SELECT COUNT(*) FROM alumnos")
    if cursor.fetchone()[0] == 0:
        alumnos_demo = [
            ('Juan Pérez', '1133445566', '2024-01-01'),
            ('María Gómez', '1144556677', '2024-02-10'),
            ('Lucas Díaz', '1122334455', '2024-03-05')
        ]
        cursor.executemany("""
            INSERT INTO alumnos (nombre, telefono, fecha_alta)
            VALUES (?, ?, ?)
        """, alumnos_demo)

    conn.commit()
    conn.close()


# 👉 IMPORTANTE PARA RENDER
init_db()

# ===============================
# AUTH
# ===============================

@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM usuarios WHERE username = ? AND password = ?",
            (username, password)
        ).fetchone()
        conn.close()

        if user:
            session['user_id'] = user['id']
            session['nombre'] = user['nombre']
            return redirect(url_for('dashboard'))
        else:
            flash('Usuario o contraseña incorrectos')

    return render_template('login.html')


@app.route('/admin/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


def login_required(func):
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    return wrapper


# ===============================
# VIEWS
# ===============================

@app.route('/')
def home():
    return redirect(url_for('login'))


@app.route('/admin/dashboard')
@login_required
def dashboard():
    conn = get_db()
    total_alumnos = conn.execute(
        "SELECT COUNT(*) FROM alumnos WHERE activo = 1"
    ).fetchone()[0]
    conn.close()

    return render_template(
        'dashboard.html',
        total_alumnos=total_alumnos,
        nombre=session.get('nombre')
    )


@app.route('/admin/alumnos')
@login_required
def alumnos():
    conn = get_db()
    alumnos = conn.execute(
        "SELECT * FROM alumnos WHERE activo = 1"
    ).fetchall()
    conn.close()

    return render_template('alumnos.html', alumnos=alumnos)


@app.route('/admin/alumnos/nuevo', methods=['POST'])
@login_required
def nuevo_alumno():
    nombre = request.form['nombre']
    telefono = request.form['telefono']

    conn = get_db()
    conn.execute("""
        INSERT INTO alumnos (nombre, telefono, fecha_alta)
        VALUES (?, ?, ?)
    """, (nombre, telefono, datetime.now().strftime('%Y-%m-%d')))
    conn.commit()
    conn.close()

    return redirect(url_for('alumnos'))


# ===============================
# MAIN (solo local)
# ===============================

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
