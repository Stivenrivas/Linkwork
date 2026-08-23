import os, re, uuid, hashlib, datetime
from flask import Flask, request, jsonify, send_from_directory, session, g, redirect
from flask_cors import CORS
from functools import wraps
import mysql.connector

app = Flask(__name__, static_folder='.')
app.secret_key = os.getenv('SECRET_KEY', 'LinkWork-2026-Secret-Key!')
app.config.update(
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=False,
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,
)
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)
CORS(app, supports_credentials=True)
ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf'}

import urllib.parse as _urlparse
_mysql_url = os.getenv('MYSQL_URL') or os.getenv('DATABASE_URL') or os.getenv('MYSQL_PUBLIC_URL')
if _mysql_url:
    _u = _urlparse.urlparse(_mysql_url)
    DB_CONFIG = {
        'host': _u.hostname,
        'user': _u.username,
        'password': _u.password or '',
        'database': _u.path.lstrip('/'),
        'port': _u.port or 3306
    }
else:
    DB_CONFIG = {
        'host': os.getenv('MYSQLHOST', 'localhost'),
        'user': os.getenv('MYSQLUSER', 'root'),
        'password': os.getenv('MYSQLPASSWORD', ''),
        'database': os.getenv('MYSQLDATABASE', 'Linkwork'),
        'port': int(os.getenv('MYSQLPORT', 3306))
    }

def allowed_file(name):
    return '.' in name and name.rsplit('.', 1)[1].lower() in ALLOWED_EXT

def _validar_hora(h):
    if h is None or h == '':
        return None
    h = str(h)
    if len(h) == 5 and h[2] == ':' and h[:2].isdigit() and h[3:].isdigit():
        hh, mm = int(h[:2]), int(h[3:])
        if 0 <= hh <= 23 and 0 <= mm <= 59:
            return h
    raise ValueError('Horario inválido (usa formato HH:MM)')

def _validate_horario(data, fallback=None):
    fallback = fallback or {}
    try:
        return _validar_hora(data.get('hora_entrada', fallback.get('hora_entrada'))), \
               _validar_hora(data.get('hora_salida', fallback.get('hora_salida')))
    except ValueError as e:
        raise ValueError(str(e))

# --- MySQL XAMPP ---

def get_db():
    if 'db' not in g:
        g.db = mysql.connector.connect(**DB_CONFIG)
    return g.db

@app.teardown_appcontext
def close_db(e):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def _serializable(row):
    if not row:
        return row
    out = {}
    for k, v in row.items():
        if isinstance(v, datetime.timedelta):
            total = int(v.total_seconds())
            out[k] = '%02d:%02d' % (total // 3600, (total % 3600) // 60)
        else:
            out[k] = v
    return out

def query(sql, params=None):
    c = get_db().cursor(dictionary=True)
    c.execute(sql, params or ())
    rows = c.fetchall()
    c.close()
    return [_serializable(r) for r in rows]

def query_one(sql, params=None):
    c = get_db().cursor(dictionary=True)
    c.execute(sql, params or ())
    r = c.fetchone()
    c.close()
    return _serializable(r) if r else None

def execute(sql, params=None):
    db = get_db()
    c = db.cursor()
    c.execute(sql, params or ())
    db.commit()
    n = c.rowcount
    c.close()
    return n

def execute_lastid(sql, params=None):
    db = get_db()
    c = db.cursor()
    c.execute(sql, params or ())
    db.commit()
    n = c.lastrowid
    c.close()
    return n

def init_db():
    # Crea las tablas si no existen (funciona tanto en XAMPP como en Railway)
    try:
        db = mysql.connector.connect(**DB_CONFIG)
        c = db.cursor()
        # --- tablas base ---
        c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL UNIQUE,
            phone VARCHAR(255) NOT NULL,
            password VARCHAR(255) NOT NULL,
            role VARCHAR(50) NOT NULL,
            frecuencia INT DEFAULT 0,
            avatar VARCHAR(500),
            cv_url VARCHAR(500),
            ciudad VARCHAR(255),
            profesion VARCHAR(255),
            especialidad VARCHAR(255),
            habilidades VARCHAR(500),
            experiencia VARCHAR(255),
            sobre_mi TEXT,
            zona VARCHAR(255),
            portafolio TEXT,
            pregunta_seguridad VARCHAR(500),
            respuesta_hash VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')
        c.execute('''CREATE TABLE IF NOT EXISTS empleos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            company VARCHAR(255) NOT NULL,
            location VARCHAR(255) NOT NULL,
            salary VARCHAR(255),
            description TEXT NOT NULL,
            email VARCHAR(255) NOT NULL,
            employer VARCHAR(255) NOT NULL,
            imagen VARCHAR(500),
            tipo VARCHAR(50) DEFAULT 'fijo',
            horas INT DEFAULT 0,
            cupos INT DEFAULT 1,
            formalidad VARCHAR(20) DEFAULT 'formal',
            hora_entrada TIME NULL,
            hora_salida TIME NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')
        c.execute('''CREATE TABLE IF NOT EXISTS servicios (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            category VARCHAR(255) NOT NULL,
            price VARCHAR(255),
            description TEXT NOT NULL,
            providerEmail VARCHAR(255) NOT NULL,
            provider VARCHAR(255) NOT NULL,
            imagen VARCHAR(500),
            horarios VARCHAR(500) NULL,
            ubicacion VARCHAR(255) NULL,
            duracion VARCHAR(100) NULL,
            incluye VARCHAR(500) NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')
        c.execute('''CREATE TABLE IF NOT EXISTS aplicaciones (
            id INT AUTO_INCREMENT PRIMARY KEY,
            tipo VARCHAR(50) NOT NULL,
            ref_id INT NOT NULL,
            solicitante_id INT NOT NULL,
            solicitante_nombre VARCHAR(255) NOT NULL,
            solicitante_email VARCHAR(255) NOT NULL,
            propietario_email VARCHAR(255) NOT NULL,
            mensaje TEXT,
            estado VARCHAR(50) DEFAULT 'pendiente',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')
        c.execute('''CREATE TABLE IF NOT EXISTS contratos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            empleador_id INT NOT NULL,
            empleador_email VARCHAR(255) NOT NULL,
            trabajador_id INT NOT NULL,
            trabajador_nombre VARCHAR(255) NOT NULL,
            trabajador_email VARCHAR(255) NOT NULL,
            tipo VARCHAR(50) NOT NULL,
            ref_id INT NOT NULL,
            ref_titulo VARCHAR(255) NOT NULL,
            monto DECIMAL(12,2) DEFAULT 0,
            horas INT DEFAULT 0,
            estado VARCHAR(50) DEFAULT 'activo',
            hora_entrada TIME NULL,
            hora_salida TIME NULL,
            dias_trabajados INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')
        c.execute('''CREATE TABLE IF NOT EXISTS mensajes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            remitente_id INT NOT NULL,
            remitente_nombre VARCHAR(255) NOT NULL,
            destinatario_id INT NOT NULL,
            destinatario_nombre VARCHAR(255) NOT NULL,
            tipo_ref VARCHAR(50) NOT NULL DEFAULT 'general',
            ref_id INT NOT NULL,
            mensaje TEXT NOT NULL,
            leido INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')
        c.execute('''CREATE TABLE IF NOT EXISTS solicitudes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            contrato_id INT NOT NULL,
            trabajador_id INT NOT NULL,
            trabajador_email VARCHAR(255) NOT NULL,
            trabajador_nombre VARCHAR(100) NOT NULL,
            empleador_id INT NOT NULL,
            empleador_email VARCHAR(255) NOT NULL,
            solicitud_tipo VARCHAR(20) NOT NULL,
            dias INT NOT NULL DEFAULT 1,
            fecha_inicio DATE NULL,
            descripcion TEXT,
            imagen_url VARCHAR(500),
            estado VARCHAR(20) DEFAULT 'pendiente',
            mensaje_respuesta TEXT,
            visto_por_trabajador TINYINT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')
        c.execute('''CREATE TABLE IF NOT EXISTS asistencia (
            contrato_id INT NOT NULL,
            trabajador_id INT NOT NULL,
            trabajador_email VARCHAR(255) NOT NULL,
            fecha DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (contrato_id, fecha)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')
        # admin
        c.execute("SELECT id FROM usuarios WHERE email=%s", ('admin@admin.com',))
        if not c.fetchone():
            admin_pw = hashlib.sha256(b'admin123').hexdigest()
            c.execute("INSERT INTO usuarios (username, email, phone, password, role) VALUES (%s,%s,%s,%s,%s)",
                       ('admin', 'admin@admin.com', '0000000000', admin_pw, 'admin'))
            db.commit()
        c.close()
        db.close()
    except Exception as e:
        print(f"init_db aviso: {e}")

init_db()

# --- Auth helpers ---

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return jsonify({'error': 'No autorizado'}), 401
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return jsonify({'error': 'No autorizado'}), 401
        if session['user']['role'] != 'admin':
            return jsonify({'error': 'Se requieren permisos de administrador'}), 403
        return f(*args, **kwargs)
    return decorated

def get_user():
    return session.get('user')

# --- Auth API ---

@app.route('/api/me')
def api_me():
    if 'user' in session:
        r = query_one('SELECT id, username, email, phone, role, frecuencia, avatar, cv_url, ciudad, profesion, especialidad, habilidades, experiencia, sobre_mi, zona, portafolio FROM usuarios WHERE email=%s', (session['user']['email'],))
        if r:
            for k in ('avatar', 'cv_url', 'ciudad', 'profesion', 'especialidad', 'habilidades', 'experiencia', 'sobre_mi', 'zona', 'portafolio'):
                r[k] = r[k] or ''
            session['user'] = dict(r)
            return jsonify(session['user'])
        return jsonify(session['user'])
    return jsonify({'error': 'No autenticado'}), 401

@app.route('/api/perfil', methods=['PATCH'])
@login_required
def api_update_perfil():
    user = get_user()
    data = request.json
    username = (data.get('username') or '').strip()
    phone = (data.get('phone') or '').strip()
    avatar = (data.get('avatar') or '').strip()
    cv_url = (data.get('cv_url') or '').strip()
    if not username:
        return jsonify({'error': 'El nombre es obligatorio'}), 400
    execute('UPDATE usuarios SET username=%s, phone=%s, avatar=%s, cv_url=%s, ciudad=%s, profesion=%s, especialidad=%s, habilidades=%s, experiencia=%s, sobre_mi=%s, zona=%s, portafolio=%s WHERE email=%s',
            (username, phone, avatar or None, cv_url or None,
             (data.get('ciudad') or '').strip(), (data.get('profesion') or '').strip(),
             (data.get('especialidad') or '').strip(), (data.get('habilidades') or '').strip(),
             (data.get('experiencia') or '').strip(), (data.get('sobre_mi') or '').strip(),
             (data.get('zona') or '').strip(), (data.get('portafolio') or ''),
             user['email']))
    session['user']['username'] = username
    session['user']['phone'] = phone
    session['user']['avatar'] = avatar or None
    session['user']['cv_url'] = cv_url or None
    return jsonify({'message': 'Perfil actualizado'})

@app.route('/api/perfil/password', methods=['POST'])
@login_required
def api_perfil_password():
    user = get_user()
    data = request.json
    current = data.get('current', '')
    new = data.get('new', '')
    if len(new) < 6:
        return jsonify({'error': 'La nueva contraseña debe tener al menos 6 caracteres'}), 400
    if not query_one('SELECT id FROM usuarios WHERE email=%s AND password=%s', (user['email'], hash_pw(current))):
        return jsonify({'error': 'La contraseña actual es incorrecta'}), 400
    execute('UPDATE usuarios SET password=%s WHERE email=%s', (hash_pw(new), user['email']))
    return jsonify({'message': 'Contraseña actualizada'})

# --- Certificados ---

@app.route('/api/certificados', methods=['GET'])
@login_required
def api_get_certificados():
    user = get_user()
    return jsonify(query(
        'SELECT * FROM certificados WHERE user_email=%s ORDER BY created_at DESC', (user['email'],)))

@app.route('/api/certificados', methods=['POST'])
@login_required
def api_add_certificado():
    user = get_user()
    data = request.json
    titulo = (data.get('titulo') or '').strip()
    if not titulo:
        return jsonify({'error': 'El título del certificado es obligatorio'}), 400
    eid = execute_lastid(
        'INSERT INTO certificados (user_email, titulo, institucion, anio, url_imagen) VALUES (%s,%s,%s,%s,%s)',
        (user['email'], titulo, data.get('institucion', ''), data.get('anio', ''),
         (data.get('url_imagen') or '').strip() or None))
    return jsonify({'id': eid, 'message': 'Certificado agregado'}), 201

@app.route('/api/certificados/<int:id>', methods=['DELETE'])
@login_required
def api_delete_certificado(id):
    user = get_user()
    execute('DELETE FROM certificados WHERE id=%s AND user_email=%s', (id, user['email']))
    return jsonify({'message': 'Certificado eliminado'})

# --- Empresa ---

@app.route('/api/perfil/empresa', methods=['GET'])
@login_required
def api_get_empresa():
    user = get_user()
    r = query_one('SELECT * FROM empresa WHERE empleador_email=%s', (user['email'],))
    return jsonify(r or {})

@app.route('/api/perfil/empresa', methods=['POST'])
@login_required
def api_save_empresa():
    user = get_user()
    data = request.json
    exist = query_one('SELECT id FROM empresa WHERE empleador_email=%s', (user['email'],))
    if exist:
        execute('UPDATE empresa SET nombre=%s, nit=%s, rubro=%s, descripcion=%s, tamano=%s, sede=%s, logo=%s, web=%s WHERE empleador_email=%s',
                (data.get('nombre'), data.get('nit'), data.get('rubro'), data.get('descripcion'),
                 data.get('tamano'), data.get('sede'), (data.get('logo') or '').strip() or None,
                 data.get('web'), user['email']))
    else:
        execute('INSERT INTO empresa (empleador_email, nombre, nit, rubro, descripcion, tamano, sede, logo, web) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                (user['email'], data.get('nombre'), data.get('nit'), data.get('rubro'), data.get('descripcion'),
                 data.get('tamano'), data.get('sede'), (data.get('logo') or '').strip() or None, data.get('web')))
    return jsonify({'message': 'Empresa guardada'})

@app.route('/api/usuarios', methods=['GET'])
@admin_required
def api_get_usuarios():
    return jsonify(query('SELECT id, username, email, phone, role, frecuencia, created_at FROM usuarios ORDER BY id'))

@app.route('/api/registro', methods=['POST'])
def api_registro():
    data = request.json
    username = (data.get('username') or '').strip()
    email = (data.get('email') or '').strip()
    phone = (data.get('phone') or '').strip()
    password = data.get('password', '')
    role = data.get('role', '')
    if not all([username, email, phone, password, role]):
        return jsonify({'error': 'Todos los campos son obligatorios'}), 400
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        return jsonify({'error': 'Correo inválido'}), 400
    if len(password) < 6:
        return jsonify({'error': 'La contraseña debe tener al menos 6 caracteres'}), 400
    if query_one('SELECT id FROM usuarios WHERE email = %s', (email,)):
        return jsonify({'error': 'Este correo ya está registrado'}), 409
    if query_one('SELECT id FROM usuarios WHERE username = %s', (username,)):
        return jsonify({'error': 'Este usuario ya existe'}), 409
    execute('INSERT INTO usuarios (username, email, phone, password, role) VALUES (%s, %s, %s, %s, %s)',
            (username, email, phone, hash_pw(password), role))
    return jsonify({'message': 'Cuenta creada correctamente'}), 201

@app.route('/api/login', methods=['POST'])
def api_login():
    try:
        data = request.json
        email = (data.get('email') or '').strip()
        password = data.get('password', '')
        user = query_one('SELECT * FROM usuarios WHERE email = %s AND password = %s', (email, hash_pw(password)))
        if not user:
            return jsonify({'error': 'Credenciales incorrectas'}), 401
        session['user'] = {
            'id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'role': user['role'],
            'phone': user['phone'],
            'frecuencia': user.get('frecuencia', 0),
        }
        session.permanent = True
        return jsonify(session['user'])
    except Exception as e:
        # --- TEMPORAL: solo para depurar, quitar este bloque después ---
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'DEBUG {type(e).__name__}: {e}'}), 500
        # --- fin bloque temporal ---

@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'message': 'Sesión cerrada'})

@app.route('/api/frecuentes', methods=['GET'])
@login_required
def api_frecuentes():
    me = get_user()
    return jsonify(query(
        'SELECT u.id, u.username, u.email, u.role, COUNT(a.id) AS frecuencia '
        'FROM aplicaciones a JOIN usuarios u ON u.email = a.solicitante_email '
        'WHERE a.tipo="servicio" AND a.propietario_email=%s AND a.solicitante_email<>%s '
        'GROUP BY u.id, u.username, u.email, u.role '
        'ORDER BY frecuencia DESC', (me['email'], me['email'])
    ))

@app.route('/api/usuarios/<email>', methods=['DELETE'])
@login_required
def api_delete_usuario(email):
    me = get_user()
    if email != me['email'] and me.get('role') != 'admin':
        return jsonify({'error': 'Solo puedes eliminar tu propia cuenta'}), 403
    if email.lower() == 'admin@admin.com':
        return jsonify({'error': 'No se puede eliminar la cuenta de administrador'}), 400
    u = query_one('SELECT id FROM usuarios WHERE LOWER(email)=LOWER(%s)', (email,))
    if not u:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    uid = u['id']
    for sql in [
        'DELETE FROM certificados WHERE user_email=%s',
        'DELETE FROM empresa WHERE empleador_email=%s',
        'DELETE FROM favoritos WHERE user_email=%s',
        'DELETE FROM grupo_lectura WHERE user_email=%s',
        'DELETE FROM grupo_mensajes WHERE user_email=%s',
        'DELETE FROM empleos WHERE email=%s',
        'DELETE FROM servicios WHERE providerEmail=%s',
        'DELETE FROM aplicaciones WHERE solicitante_email=%s OR propietario_email=%s',
        'DELETE FROM contratos WHERE empleador_email=%s OR trabajador_email=%s',
        'DELETE FROM grupos WHERE empleador_email=%s',
        'DELETE FROM solicitudes WHERE trabajador_email=%s OR empleador_email=%s',
        'DELETE FROM asistencia WHERE trabajador_email=%s',
        'DELETE FROM finanzas WHERE user_email=%s',
    ]:
        execute(sql, (email, email) if sql.count('%s') > 1 else (email,))
    execute('DELETE FROM mensajes WHERE remitente_id=%s OR destinatario_id=%s', (uid, uid))
    execute('DELETE FROM usuarios WHERE LOWER(email)=LOWER(%s)', (email,))
    session.pop('user', None)
    return jsonify({'message': 'Usuario eliminado'})

# --- Pregunta de seguridad (recuperar contraseña) ---

@app.route('/api/perfil/pregunta', methods=['GET'])
@login_required
def api_pregunta_get():
    u = query_one('SELECT pregunta_seguridad FROM usuarios WHERE email=%s', (get_user()['email'],))
    p = (u or {}).get('pregunta_seguridad') or ''
    return jsonify({'pregunta': p, 'tiene_pregunta': bool(p)})

@app.route('/api/perfil/pregunta', methods=['POST'])
@login_required
def api_pregunta_post():
    data = request.json or {}
    pregunta = (data.get('pregunta') or '').strip()
    respuesta = (data.get('respuesta') or '').strip()
    if not pregunta:
        return jsonify({'error': 'Escribe la pregunta de seguridad'}), 400
    if len(respuesta) < 3:
        return jsonify({'error': 'La respuesta debe tener al menos 3 caracteres'}), 400
    execute('UPDATE usuarios SET pregunta_seguridad=%s, respuesta_hash=%s WHERE email=%s',
            (pregunta, hash_pw(respuesta.lower()), get_user()['email']))
    return jsonify({'message': 'Pregunta de seguridad guardada'})

# --- Recuperación de contraseña ---

@app.route('/api/recuperar/solicitar', methods=['POST'])
def api_recuperar_solicitar():
    data = request.json or {}
    email = (data.get('email') or '').strip()
    if not email:
        return jsonify({'error': 'Ingresa tu correo'}), 400
    u = query_one('SELECT pregunta_seguridad FROM usuarios WHERE LOWER(email)=LOWER(%s)', (email,))
    if not u or not (u.get('pregunta_seguridad') or ''):
        return jsonify({'tiene_pregunta': False, 'message': 'Ese correo no tiene una pregunta de seguridad configurada'})
    return jsonify({'tiene_pregunta': True, 'pregunta': u['pregunta_seguridad']})

@app.route('/api/recuperar/cambiar', methods=['POST'])
def api_recuperar_cambiar():
    data = request.json or {}
    email = (data.get('email') or '').strip()
    respuesta = (data.get('respuesta') or '').strip()
    nueva = data.get('nueva_password') or ''
    if not email or not respuesta or not nueva:
        return jsonify({'error': 'Completa todos los campos'}), 400
    if len(nueva) < 6:
        return jsonify({'error': 'La nueva contraseña debe tener al menos 6 caracteres'}), 400
    u = query_one('SELECT respuesta_hash FROM usuarios WHERE LOWER(email)=LOWER(%s)', (email,))
    if not u or not u.get('respuesta_hash'):
        return jsonify({'error': 'Ese correo no tiene una pregunta de seguridad configurada'}), 400
    if u['respuesta_hash'] != hash_pw(respuesta.lower()):
        return jsonify({'error': 'La respuesta no es correcta'}), 403
    execute('UPDATE usuarios SET password=%s WHERE LOWER(email)=LOWER(%s)', (hash_pw(nueva), email))
    return jsonify({'message': 'Contraseña actualizada. Ya puedes iniciar sesión.'})

@app.route('/api/publico/<email>', methods=['GET'])
@login_required
def api_perfil_publico(email):
    u = query_one(
        'SELECT id, username, email, phone, role, avatar, cv_url, ciudad, profesion, especialidad, habilidades, experiencia, sobre_mi, zona, portafolio FROM usuarios WHERE email=%s',
        (email,))
    if not u:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    certs = query('SELECT titulo, institucion, anio, url_imagen FROM certificados WHERE user_email=%s ORDER BY created_at DESC', (email,)) if email else []
    empresa = query_one('SELECT nombre, nit, rubro, tamano, sede, logo, web, descripcion FROM empresa WHERE empleador_email=%s', (email,)) if u['role'] == 'empleador' else None
    return jsonify({'usuario': u, 'certificados': certs, 'empresa': empresa})

# --- Upload ---

@app.route('/api/upload', methods=['POST'])
@login_required
def api_upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No se envió archivo'}), 400
    f = request.files['file']
    if not f or not allowed_file(f.filename):
        return jsonify({'error': 'Formato no permitido (png, jpg, jpeg, gif, webp, pdf)'}), 400
    ext = f.filename.rsplit('.', 1)[1].lower()
    name = f"{uuid.uuid4().hex}.{ext}"
    f.save(os.path.join(UPLOAD_DIR, name))
    return jsonify({'url': f'/uploads/{name}'})

@app.route('/uploads/<name>')
def serve_upload(name):
    return send_from_directory(UPLOAD_DIR, name)

# --- Empleos ---

@app.route('/api/empleos', methods=['GET'])
def api_get_empleos():
    return jsonify(query(
        'SELECT e.*, (SELECT COUNT(*) FROM aplicaciones a '
        'WHERE a.tipo="empleo" AND a.ref_id=e.id AND a.estado="aceptado" '
        'AND NOT EXISTS (SELECT 1 FROM contratos ct '
        'WHERE ct.tipo="empleo" AND ct.ref_id=e.id AND ct.trabajador_email=a.solicitante_email '
        'AND ct.estado="finalizado")) AS cupos_ocupados '
        'FROM empleos e ORDER BY e.created_at DESC'))

@app.route('/api/empleos/mis', methods=['POST'])
@login_required
def api_mis_empleos():
    return jsonify(query(
        'SELECT e.*, (SELECT COUNT(*) FROM aplicaciones a '
        'WHERE a.tipo="empleo" AND a.ref_id=e.id AND a.estado="aceptado" '
        'AND NOT EXISTS (SELECT 1 FROM contratos ct '
        'WHERE ct.tipo="empleo" AND ct.ref_id=e.id AND ct.trabajador_email=a.solicitante_email '
        'AND ct.estado="finalizado")) AS cupos_ocupados '
        'FROM empleos e WHERE email = %s ORDER BY created_at DESC', (session['user']['email'],)))

@app.route('/api/empleos', methods=['POST'])
@login_required
def api_create_empleo():
    data = request.json
    if not all([data.get('title'), data.get('company'), data.get('location'), data.get('description')]):
        return jsonify({'error': 'Completa todos los campos obligatorios'}), 400
    try:
        hora_e, hora_s = _validate_horario(data)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    eid = execute_lastid(
        'INSERT INTO empleos (title, company, location, salary, description, email, employer, imagen, tipo, horas, cupos, formalidad, hora_entrada, hora_salida) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
        (data['title'], data['company'], data['location'], data.get('salary', ''), data['description'],
         session['user']['email'], session['user']['username'],
         data.get('imagen'), data.get('tipo', 'fijo'), int(data.get('horas') or 0),
         int(data.get('cupos') or 1), data.get('formalidad', 'formal') if data.get('formalidad') in ('formal', 'informal') else 'formal',
         hora_e, hora_s)
    )
    return jsonify({'message': 'Empleo publicado', 'id': eid}), 201

@app.route('/api/empleos/<int:id>', methods=['PATCH'])
@login_required
def api_update_empleo(id):
    data = request.json
    emp = query_one('SELECT * FROM empleos WHERE id=%s', (id,))
    if not emp:
        return jsonify({'error': 'Empleo no encontrado'}), 404
    if emp['email'] != session['user']['email']:
        return jsonify({'error': 'Solo el empleador dueño puede editar este empleo'}), 403
    if 'title' in data and not data['title'].strip():
        return jsonify({'error': 'El título no puede estar vacío'}), 400
    try:
        hora_e, hora_s = _validate_horario(data, emp)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    formalidad = data.get('formalidad', emp.get('formalidad', 'formal'))
    if formalidad not in ('formal', 'informal'):
        formalidad = emp.get('formalidad', 'formal')
    execute(
        'UPDATE empleos SET title=%s, company=%s, location=%s, salary=%s, description=%s, imagen=%s, tipo=%s, horas=%s, cupos=%s, formalidad=%s, hora_entrada=%s, hora_salida=%s WHERE id=%s',
        (data.get('title', emp['title']), data.get('company', emp['company']),
         data.get('location', emp['location']), data.get('salary', emp.get('salary') or ''),
         data.get('description', emp['description']), data.get('imagen', emp.get('imagen')),
         data.get('tipo', emp.get('tipo', 'fijo')), int(data.get('horas') or emp.get('horas') or 0),
         int(data.get('cupos') or emp.get('cupos') or 1), formalidad, hora_e, hora_s, id)
    )
    if hora_e or hora_s:
        execute(
            'UPDATE contratos SET hora_entrada=%s, hora_salida=%s WHERE tipo="empleo" AND ref_id=%s AND estado="activo" AND (hora_entrada IS NULL OR hora_salida IS NULL)',
            (hora_e, hora_s, id)
        )
    return jsonify({'message': 'Empleo actualizado'})

@app.route('/api/empleos/<int:id>', methods=['DELETE'])
@login_required
def api_delete_empleo(id):
    execute('DELETE FROM empleos WHERE id = %s', (id,))
    return jsonify({'message': 'Empleo eliminado'})

# --- Favoritos / Destacados ---

@app.route('/api/favoritos', methods=['POST'])
@login_required
def api_toggle_favorito():
    data = request.json
    tipo = data.get('tipo')
    ref_id = data.get('ref_id')
    if tipo not in ('empleo', 'servicio') or not ref_id:
        return jsonify({'error': 'Datos inválidos'}), 400
    user_email = session['user']['email']
    tabla = 'empleos' if tipo == 'empleo' else 'servicios'
    if not query_one('SELECT id FROM %s WHERE id=%%s' % tabla, (ref_id,)):
        return jsonify({'error': 'El elemento no existe'}), 404
    ex = query_one('SELECT id FROM favoritos WHERE user_email=%s AND ref_tipo=%s AND ref_id=%s', (user_email, tipo, ref_id))
    if ex:
        execute('DELETE FROM favoritos WHERE id=%s', (ex['id'],))
        return jsonify({'message': 'Quitado de destacados', 'activo': False})
    execute('INSERT INTO favoritos (user_email, ref_tipo, ref_id) VALUES (%s,%s,%s)', (user_email, tipo, ref_id))
    return jsonify({'message': 'Marcado como destacado', 'activo': True})

@app.route('/api/favoritos/mis', methods=['GET'])
@login_required
def api_mis_favoritos():
    return jsonify(query('SELECT ref_tipo AS tipo, ref_id FROM favoritos WHERE user_email=%s', (session['user']['email'],)))

# --- Servicios ---

@app.route('/api/servicios', methods=['GET'])
def api_get_servicios():
    return jsonify(query('SELECT * FROM servicios ORDER BY created_at DESC'))

@app.route('/api/servicios/mis', methods=['POST'])
@login_required
def api_mis_servicios():
    return jsonify(query('SELECT * FROM servicios WHERE providerEmail = %s ORDER BY created_at DESC', (session['user']['email'],)))

@app.route('/api/servicios', methods=['POST'])
@login_required
def api_create_servicio():
    data = request.json
    if not all([data.get('title'), data.get('category'), data.get('description')]):
        return jsonify({'error': 'Completa todos los campos obligatorios'}), 400
    execute(
        'INSERT INTO servicios (title, category, price, description, providerEmail, provider, imagen, horarios, ubicacion, duracion, incluye) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
        (data['title'], data['category'], data.get('price', ''), data['description'],
         session['user']['email'], session['user']['username'], data.get('imagen'),
         data.get('horarios'), data.get('ubicacion'), data.get('duracion'), data.get('incluye'))
    )
    return jsonify({'message': 'Servicio publicado'}), 201

@app.route('/api/servicios/<int:id>', methods=['PUT'])
@login_required
def api_update_servicio(id):
    data = request.json
    user = get_user()
    own = query_one('SELECT id FROM servicios WHERE id=%s AND providerEmail=%s', (id, user['email']))
    if not own:
        return jsonify({'error': 'Solo puedes editar tus propios servicios'}), 403
    if not all([data.get('title'), data.get('category'), data.get('description')]):
        return jsonify({'error': 'Completa todos los campos obligatorios'}), 400
    execute(
        'UPDATE servicios SET title=%s, category=%s, price=%s, description=%s, imagen=%s, horarios=%s, ubicacion=%s, duracion=%s, incluye=%s WHERE id=%s',
        (data['title'], data['category'], data.get('price', ''), data['description'], data.get('imagen'),
         data.get('horarios'), data.get('ubicacion'), data.get('duracion'), data.get('incluye'), id)
    )
    return jsonify({'message': 'Servicio actualizado'})

@app.route('/api/servicios/<int:id>', methods=['DELETE'])
@login_required
def api_delete_servicio(id):
    execute('DELETE FROM servicios WHERE id = %s', (id,))
    return jsonify({'message': 'Servicio eliminado'})

# --- Aplicaciones ---

@app.route('/api/aplicaciones', methods=['POST'])
@login_required
def api_aplicar():
    data = request.json
    user = get_user()
    tipo = data.get('tipo')
    ref_id = data.get('ref_id')
    mensaje = (data.get('mensaje') or '').strip()
    if tipo not in ('empleo', 'servicio') or not ref_id:
        return jsonify({'error': 'Datos inválidos'}), 400
    previas = query('SELECT estado FROM aplicaciones WHERE tipo=%s AND ref_id=%s AND solicitante_email=%s', (tipo, ref_id, user['email']))
    if previas:
        if tipo == 'servicio' or any(p['estado'] == 'pendiente' for p in previas):
            return jsonify({'error': 'Ya te has postulado a esto'}), 409
        if any(p['estado'] == 'aceptado' for p in previas):
            activa = query_one(
                'SELECT 1 FROM contratos ct WHERE ct.tipo=%s AND ct.ref_id=%s AND ct.trabajador_email=%s '
                'AND NOT EXISTS (SELECT 1 FROM contratos c2 WHERE c2.tipo="empleo" AND c2.ref_id=ct.ref_id '
                'AND c2.trabajador_email=ct.trabajador_email AND c2.estado="finalizado")',
                (tipo, ref_id, user['email']))
            if activa:
                return jsonify({'error': 'Ya estás contratado en esta empresa'}), 409
    if tipo == 'empleo':
        r = query_one('SELECT email, horas FROM empleos WHERE id=%s', (ref_id,))
        if r:
            prop_email = r['email']
            ocupando = query_one(
                'SELECT 1 FROM contratos ct WHERE ct.tipo="empleo" AND ct.estado="activo" '
                'AND ct.trabajador_email=%s AND ct.empleador_email=%s',
                (user['email'], prop_email))
            if ocupando:
                return jsonify({'error': 'Ya estás contratado en esta empresa'}), 409
            horas_nuevo = int(r.get('horas') or 0)
            if horas_nuevo > 0:
                horas_actuales = query_one(
                    'SELECT COALESCE(SUM(COALESCE(e.horas,0)),0) AS h FROM contratos ct '
                    'JOIN empleos e ON e.id=ct.ref_id '
                    'WHERE ct.tipo="empleo" AND ct.estado="activo" AND ct.trabajador_email=%s',
                    (user['email'],)) or {}
                if int(horas_actuales.get('h') or 0) + horas_nuevo > 56:
                    return jsonify({'error': 'Superas las 56 horas semanales permitidas: ya tienes ' + str(horas_actuales.get('h') or 0) + ' h y este empleo son ' + str(horas_nuevo) + ' h'}), 409
    else:
        r = query_one('SELECT providerEmail FROM servicios WHERE id=%s', (ref_id,))
        if r: prop_email = r['providerEmail']
    if not prop_email:
        return jsonify({'error': 'Referencia no encontrada'}), 404
    execute(
        'INSERT INTO aplicaciones (tipo, ref_id, solicitante_id, solicitante_nombre, solicitante_email, propietario_email, mensaje) VALUES (%s,%s,%s,%s,%s,%s,%s)',
        (tipo, ref_id, user['id'], user['username'], user['email'], prop_email, mensaje)
    )
    if tipo == 'servicio':
        execute('UPDATE usuarios SET frecuencia = frecuencia + 1 WHERE email=%s', (user['email'],))
    if mensaje:
        prop = query_one('SELECT id, username FROM usuarios WHERE email=%s', (prop_email,))
        if prop:
            execute(
                'INSERT INTO mensajes (remitente_id, remitente_nombre, destinatario_id, destinatario_nombre, tipo_ref, ref_id, mensaje) '
                'VALUES (%s,%s,%s,%s,%s,%s,%s)',
                (user['id'], user['username'], prop['id'], prop['username'],
                 tipo, ref_id, mensaje)
            )
    return jsonify({'message': 'Postulación enviada'}), 201

@app.route('/api/aplicaciones/recibidas', methods=['GET'])
@login_required
def api_aplicaciones_recibidas():
    user = get_user()
    rows = query(
        'SELECT a.*, a.estado as status, COALESCE(e.title, s.title) as ref_titulo '
        'FROM aplicaciones a '
        'LEFT JOIN empleos e ON a.tipo="empleo" AND a.ref_id=e.id '
        'LEFT JOIN servicios s ON a.tipo="servicio" AND a.ref_id=s.id '
        'WHERE a.propietario_email=%s ORDER BY a.created_at DESC', (user['email'],)
    )
    return jsonify(rows)

@app.route('/api/aplicaciones/enviadas', methods=['GET'])
@login_required
def api_aplicaciones_enviadas():
    user = get_user()
    rows = query(
        'SELECT a.*, a.estado as status, COALESCE(e.title, s.title) as ref_titulo '
        'FROM aplicaciones a '
        'LEFT JOIN empleos e ON a.tipo="empleo" AND a.ref_id=e.id '
        'LEFT JOIN servicios s ON a.tipo="servicio" AND a.ref_id=s.id '
        'WHERE a.solicitante_email=%s ORDER BY a.created_at DESC', (user['email'],)
    )
    return jsonify(rows)

@app.route('/api/aplicaciones/<int:id>/estado', methods=['PATCH'])
@login_required
def api_cambiar_estado_aplicacion(id):
    data = request.json
    estado = data.get('estado')
    if estado not in ('aceptado', 'rechazado'):
        return jsonify({'error': 'Estado inválido'}), 400
    if estado == 'aceptado':
        appq = query_one('SELECT ref_id, tipo FROM aplicaciones WHERE id=%s', (id,))
        if appq and appq.get('tipo') == 'empleo':
            emp = query_one('SELECT cupos FROM empleos WHERE id=%s', (appq['ref_id'],))
            if emp:
                cupos = int(emp['cupos'] or 1)
                ocup = query_one(
                    'SELECT COUNT(*) AS n FROM aplicaciones a '
                    'WHERE a.tipo=%s AND a.ref_id=%s AND a.estado=%s '
                    'AND NOT EXISTS (SELECT 1 FROM contratos ct '
                    'WHERE ct.tipo="empleo" AND ct.ref_id=a.ref_id AND ct.trabajador_email=a.solicitante_email '
                    'AND ct.estado="finalizado")',
                    ('empleo', appq['ref_id'], 'aceptado')) or {}
                if int(ocup.get('n') or 0) >= cupos:
                    return jsonify({'error': 'Los cupos de este empleo ya están llenos'}), 409
    execute('UPDATE aplicaciones SET estado=%s WHERE id=%s', (estado, id))
    return jsonify({'message': f'Solicitud {estado}'})

# --- Contratos ---

@app.route('/api/contratos', methods=['POST'])
@login_required
def api_crear_contrato():
    data = request.json
    user = get_user()
    trabajador_id = data.get('trabajador_id')
    if not trabajador_id and data.get('trabajador_email'):
        r = query_one('SELECT id FROM usuarios WHERE email=%s', (data['trabajador_email'],))
        if r: trabajador_id = r['id']
    hora_e = hora_s = None
    horas_cont = int(data.get('horas') or 0)
    if data.get('tipo') == 'empleo':
        emp = query_one('SELECT hora_entrada, hora_salida, horas FROM empleos WHERE id=%s', (data.get('ref_id'),))
        if emp:
            hora_e = data.get('hora_entrada', emp['hora_entrada'])
            hora_s = data.get('hora_salida', emp['hora_salida'])
            if not horas_cont:
                horas_cont = int(emp['horas'] or 0)
    try:
        hora_e, hora_s = _validate_horario({'hora_entrada': hora_e, 'hora_salida': hora_s})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    eid = execute_lastid(
        'INSERT INTO contratos (empleador_id, empleador_email, trabajador_id, trabajador_nombre, trabajador_email, tipo, ref_id, ref_titulo, monto, horas, hora_entrada, hora_salida) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
        (user['id'], user['email'], trabajador_id, data['trabajador_nombre'],
         data['trabajador_email'], data['tipo'], data['ref_id'], data['ref_titulo'],
         float(data.get('monto', 0)), horas_cont, hora_e, hora_s)
    )
    return jsonify({'id': eid, 'message': 'Contrato creado'}), 201

@app.route('/api/contratos/mis', methods=['GET'])
@login_required
def api_mis_contratos():
    user = get_user()
    contratos = query(
        'SELECT * FROM contratos WHERE empleador_email=%s OR trabajador_email=%s ORDER BY created_at DESC',
        (user['email'], user['email'])
    )
    for c in contratos:
        if c.get('tipo') == 'empleo':
            registrar_dias_automaticos(c)
            c['dias_trabajados'] = contar_dias_trabajados(c['id'])
        else:
            c['dias_trabajados'] = 0
    return jsonify(contratos)

@app.route('/api/contratos/<int:id>', methods=['PATCH'])
@login_required
def api_finalizar_contrato(id):
    data = request.json or {}
    user = get_user()
    c = query_one('SELECT * FROM contratos WHERE id=%s', (id,))
    if not c:
        return jsonify({'error': 'Contrato no encontrado'}), 404
    if user['role'] != 'empleador' or c['empleador_email'] != user['email']:
        return jsonify({'error': 'Sin permisos sobre este contrato'}), 403
    if data.get('estado') == 'finalizado':
        execute('UPDATE contratos SET estado="finalizado" WHERE id=%s', (id,))
        return jsonify({'message': 'Contrato finalizado'})
    cambios = []
    params = []
    if 'hora_entrada' in data or 'hora_salida' in data:
        cambios.append('hora_entrada=%s')
        cambios.append('hora_salida=%s')
        params += [data.get('hora_entrada') or None, data.get('hora_salida') or None]
    if 'monto' in data:
        try:
            monto = float(data['monto'] or 0)
        except (TypeError, ValueError):
            return jsonify({'error': 'Monto inválido'}), 400
        if monto < 0:
            return jsonify({'error': 'El monto no puede ser negativo'}), 400
        cambios.append('monto=%s')
        params.append(monto)
    if cambios:
        execute('UPDATE contratos SET %s WHERE id=%%s' % ', '.join(cambios), params + [id])
        return jsonify({'message': 'Contrato actualizado'})
    return jsonify({'message': 'Contrato actualizado'})

def registrar_dias_automaticos(contrato):
    """Suma un día de asistencia por cada día que pasa con el contrato activo."""
    if not contrato or contrato.get('tipo') != 'empleo' or contrato.get('estado') != 'activo':
        return
    hoy = datetime.date.today()
    creado = contrato.get('created_at')
    fecha_ini = creado.date() if creado else hoy
    if fecha_ini > hoy:
        return
    cur = fecha_ini
    rows = []
    while cur <= hoy:
        rows.append((contrato['id'], contrato['trabajador_id'], contrato['trabajador_email'], cur))
        cur += datetime.timedelta(days=1)
    if not rows:
        return
    db = get_db()
    c = db.cursor()
    try:
        c.executemany(
            'INSERT IGNORE INTO asistencia (contrato_id, trabajador_id, trabajador_email, fecha) VALUES (%s,%s,%s,%s)',
            rows)
    finally:
        db.commit()
        c.close()

def contar_dias_trabajados(contrato_id):
    dias = query_one('SELECT COUNT(*) AS n FROM asistencia WHERE contrato_id=%s', (contrato_id,))
    return dias['n'] if dias else 0

def _estado_trabajo(email):
    row = query_one("SELECT solicitud_tipo FROM solicitudes WHERE trabajador_email=%s AND estado='aceptado' ORDER BY created_at DESC LIMIT 1", (email,))
    if row and row['solicitud_tipo'] == 'vacaciones':
        return 'vacaciones'
    if row and row['solicitud_tipo'] == 'permiso':
        return 'permiso'
    return 'activo'

@app.route('/api/mi-empresa', methods=['GET'])
@login_required
def api_mi_empresa():
    user = get_user()
    if user['role'] == 'empleador':
        return jsonify({'error': 'Tu rol no aplica para esta vista'}), 400
    contrato = query_one(
        'SELECT * FROM contratos WHERE trabajador_email=%s AND tipo="empleo" AND estado="activo" ORDER BY created_at DESC LIMIT 1',
        (user['email'],))
    if not contrato:
        return jsonify({'contrato': None, 'empresa': None, 'compañeros': []})
    registrar_dias_automaticos(contrato)
    cont = contar_dias_trabajados(contrato['id'])
    contrato['dias_trabajados'] = cont
    empresa = query_one('SELECT * FROM empresa WHERE empleador_email=%s', (contrato['empleador_email'],))
    companeros = query(
        'SELECT u.id, u.username, u.email, u.avatar, u.profesion, u.especialidad, ct.ref_titulo AS trabajo FROM usuarios u '
        'JOIN contratos ct ON ct.trabajador_id=u.id '
        'WHERE ct.empleador_id=%s AND ct.tipo="empleo" AND ct.estado="activo" AND u.id != %s',
        (contrato['empleador_id'], user['id']))
    for comp in companeros:
        comp['estado_trabajo'] = _estado_trabajo(comp['email'])
    return jsonify({'contrato': contrato, 'empresa': empresa, 'compañeros': companeros})

@app.route('/api/solicitudes', methods=['POST'])
@login_required
def api_crear_solicitud():
    data = request.json or {}
    user = get_user()
    if user['role'] == 'empleador':
        return jsonify({'error': 'Solo los trabajadores pueden enviar solicitudes'}), 403
    contrato = query_one(
        'SELECT * FROM contratos WHERE trabajador_email=%s AND tipo="empleo" AND estado="activo" ORDER BY created_at DESC LIMIT 1',
        (user['email'],))
    if not contrato:
        return jsonify({'error': 'No tienes un empleo activo'}), 400
    tipo = data.get('solicitud_tipo')
    if tipo not in ('vacaciones', 'permiso'):
        return jsonify({'error': 'Tipo de solicitud inválido'}), 400
    dias = int(data.get('dias') or 1)
    if tipo == 'vacaciones':
        if dias > 15:
            return jsonify({'error': 'Máximo 15 días de vacaciones al año'}), 400
        anio = datetime.date.today().year
        exist = query_one(
            'SELECT id FROM solicitudes WHERE trabajador_email=%s AND solicitud_tipo="vacaciones" AND strftime("%Y", fecha_inicio)=%s',
            (user['email'], anio))
        if exist:
            return jsonify({'error': 'Ya solicitaste tus vacaciones este año'}), 400
    else:
        if dias < 1 or dias > 3:
            return jsonify({'error': 'Los permisos se solicitan de 1 a 3 días'}), 400
    execute(
        'INSERT INTO solicitudes (contrato_id, trabajador_id, trabajador_email, trabajador_nombre, empleador_id, empleador_email, solicitud_tipo, dias, fecha_inicio, descripcion, imagen_url) '
        'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
        (contrato['id'], user['id'], user['email'], user['username'],
         contrato['empleador_id'], contrato['empleador_email'], tipo, dias,
         data.get('fecha_inicio') or None, data.get('descripcion'), data.get('imagen_url')))
    return jsonify({'message': 'Solicitud enviada'}), 201

@app.route('/api/solicitudes', methods=['GET'])
@login_required
def api_mis_solicitudes():
    user = get_user()
    rows = query(
        'SELECT * FROM solicitudes WHERE trabajador_email=%s ORDER BY created_at DESC', (user['email'],))
    if rows:
        execute("UPDATE solicitudes SET visto_por_trabajador=1 WHERE trabajador_email=%s AND estado IN ('aceptado','rechazado')", (user['email'],))
    return jsonify(rows)

@app.route('/api/solicitudes/recibidas', methods=['GET'])
@login_required
def api_solicitudes_recibidas():
    user = get_user()
    if user['role'] != 'empleador':
        return jsonify({'error': 'Solo empleadores'}), 403
    return jsonify(query(
        'SELECT s.*, c.ref_titulo FROM solicitudes s JOIN contratos c ON c.id=s.contrato_id '
        'WHERE s.empleador_email=%s ORDER BY (s.estado="pendiente") DESC, s.created_at DESC',
        (user['email'],)))

@app.route('/api/solicitudes/<int:id>/estado', methods=['PATCH'])
@login_required
def api_responder_solicitud(id):
    data = request.json or {}
    user = get_user()
    s = query_one('SELECT * FROM solicitudes WHERE id=%s', (id,))
    if not s:
        return jsonify({'error': 'Solicitud no encontrada'}), 404
    if user['role'] != 'empleador' or s['empleador_email'] != user['email']:
        return jsonify({'error': 'Sin permisos sobre esta solicitud'}), 403
    estado = data.get('estado')
    if estado not in ('aceptado', 'rechazado'):
        return jsonify({'error': 'Estado inválido'}), 400
    execute('UPDATE solicitudes SET estado=%s, mensaje_respuesta=%s, visto_por_trabajador=0 WHERE id=%s',
            (estado, data.get('mensaje_respuesta'), id))
    return jsonify({'message': 'Solicitud respondida'})

# --- Chat de equipo (grupos) ---

def _get_or_create_grupo(empleador_email):
    g = query_one('SELECT * FROM grupos WHERE empleador_email=%s', (empleador_email,))
    if g:
        return g
    empresa = query_one('SELECT nombre FROM empresa WHERE empleador_email=%s', (empleador_email,))
    empleador = query_one('SELECT username FROM usuarios WHERE email=%s', (empleador_email,))
    nombre = (empresa['nombre'] if empresa and empresa['nombre'] else '') or (empleador['username'] if empleador else empleador_email)
    gid = execute_lastid('INSERT INTO grupos (nombre, empleador_email) VALUES (%s,%s)', (nombre, empleador_email))
    return query_one('SELECT * FROM grupos WHERE id=%s', (gid,))

def _es_miembro_grupo(g, user_email):
    if g['empleador_email'] == user_email:
        return True
    c = query_one(
        'SELECT id FROM contratos WHERE empleador_email=%s AND trabajador_email=%s AND estado="activo" LIMIT 1',
        (g['empleador_email'], user_email))
    return bool(c)

def _miembros_grupo(g):
    rows = query(
        'SELECT DISTINCT u.email, u.username, u.role FROM usuarios u JOIN contratos c ON u.email=c.trabajador_email '
        'WHERE c.empleador_email=%s AND c.estado="activo"',
        (g['empleador_email'],))
    empleador = query_one('SELECT username FROM usuarios WHERE email=%s', (g['empleador_email'],))
    miembros = [{'email': g['empleador_email'], 'nombre': (empleador['username'] if empleador else g['empleador_email']), 'rol': 'empleador'}] + \
               [{'email': r['email'], 'nombre': r['username'], 'rol': r.get('role', 'usuario')} for r in rows]
    out, seen = [], set()
    for m in miembros:
        if m['email'] not in seen:
            seen.add(m['email'])
            out.append(m)
    return out

def _no_leidos_grupo(g, user_email):
    r = query_one('SELECT last_read_id FROM grupo_lectura WHERE user_email=%s AND grupo_id=%s', (user_email, g['id']))
    last = r['last_read_id'] if r else 0
    q = query_one('SELECT COUNT(*) AS n FROM grupo_mensajes WHERE grupo_id=%s AND id>%s AND user_email<>%s', (g['id'], last, user_email))
    return q['n'] if q else 0

def _grupos_usuario(user):
    groups = []
    if user['role'] == 'empleador':
        g = _get_or_create_grupo(user['email'])
        if g:
            groups.append(g)
    else:
        for row in query('SELECT DISTINCT empleador_email FROM contratos WHERE trabajador_email=%s AND estado="activo" AND tipo="empleo"', (user['email'],)):
            g = _get_or_create_grupo(row['empleador_email'])
            if g:
                groups.append(g)
    return groups

@app.route('/api/grupo/mis', methods=['GET'])
@login_required
def api_mis_grupos():
    user = get_user()
    out = []
    for g in _grupos_usuario(user):
        out.append({
            'id': g['id'],
            'nombre': g['nombre'],
            'empleador_email': g['empleador_email'],
            'miembros': _miembros_grupo(g),
            'noLeidos': _no_leidos_grupo(g, user['email'])
        })
    return jsonify(out)

@app.route('/api/grupo/<int:id>/mensajes', methods=['GET'])
@login_required
def api_grupo_mensajes(id):
    user = get_user()
    g = query_one('SELECT * FROM grupos WHERE id=%s', (id,))
    if not g:
        return jsonify({'error': 'Grupo no encontrado'}), 404
    if not _es_miembro_grupo(g, user['email']):
        return jsonify({'error': 'No perteneces a este grupo'}), 403
    mensajes = query('SELECT * FROM grupo_mensajes WHERE grupo_id=%s ORDER BY created_at ASC', (id,))
    for m in mensajes:
        m['es_mio'] = 1 if m['user_email'] == user['email'] else 0
    last_id = mensajes[-1]['id'] if mensajes else 0
    execute(
        'INSERT INTO grupo_lectura (user_email, grupo_id, last_read_id) VALUES (%s,%s,%s) '
        'ON CONFLICT(user_email, grupo_id) DO UPDATE SET last_read_id=%s',
        (user['email'], id, last_id, last_id))
    return jsonify({'grupo': g, 'mensajes': mensajes, 'miembros': _miembros_grupo(g)})

@app.route('/api/grupo/<int:id>/mensajes', methods=['POST'])
@login_required
def api_grupo_enviar(id):
    user = get_user()
    g = query_one('SELECT * FROM grupos WHERE id=%s', (id,))
    if not g:
        return jsonify({'error': 'Grupo no encontrado'}), 404
    if not _es_miembro_grupo(g, user['email']):
        return jsonify({'error': 'No perteneces a este grupo'}), 403
    mensaje = (request.json or {}).get('mensaje', '').strip()
    if not mensaje:
        return jsonify({'error': 'Escribe un mensaje'}), 400
    eid = execute_lastid(
        'INSERT INTO grupo_mensajes (grupo_id, user_email, user_nombre, mensaje) VALUES (%s,%s,%s,%s)',
        (id, user['email'], user['username'], mensaje))
    m = query_one('SELECT * FROM grupo_mensajes WHERE id=%s', (eid,))
    return jsonify(m if m else {'message': 'Mensaje enviado'}), 201

@app.route('/api/notificaciones', methods=['GET'])
@login_required
def api_notificaciones():
    user = get_user()
    out = {}
    nl = query_one('SELECT COUNT(*) AS n FROM mensajes WHERE destinatario_id=%s AND leido=0', (user['id'],))
    out['chat'] = nl['n'] if nl else 0
    if user['role'] != 'admin':
        try:
            total_grupo = sum(_no_leidos_grupo(g, user['email']) for g in _grupos_usuario(user))
        except Exception:
            total_grupo = 0
        out['grupo'] = total_grupo
    if user['role'] == 'empleador':
        ap = query_one("SELECT COUNT(*) AS n FROM aplicaciones WHERE propietario_email=%s AND estado='pendiente'", (user['email'],))
        out['aplicaciones'] = ap['n'] if ap else 0
        sp = query_one("SELECT COUNT(*) AS n FROM solicitudes WHERE empleador_email=%s AND estado='pendiente'", (user['email'],))
        out['solicitudes'] = sp['n'] if sp else 0
    elif user['role'] != 'admin':
        sr = query_one("SELECT COUNT(*) AS n FROM solicitudes WHERE trabajador_email=%s AND estado IN ('aceptado','rechazado') AND visto_por_trabajador=0", (user['email'],))
        out['respuestas'] = sr['n'] if sr else 0
    return jsonify(out)

@app.route('/api/recibo/<int:id>', methods=['GET'])
@login_required
def api_recibo(id):
    user = get_user()
    c = query_one('SELECT * FROM contratos WHERE id=%s', (id,))
    if not c:
        return jsonify({'error': 'Contrato no encontrado'}), 404
    if user['role'] != 'empleador' and c['trabajador_email'] != user['email']:
        return jsonify({'error': 'Sin permisos sobre este contrato'}), 403
    empleado = query_one('SELECT username, email, phone FROM usuarios WHERE email=%s', (c['trabajador_email'],)) or {}
    empresa = query_one('SELECT nombre, nit, sede, descripcion FROM empresa WHERE empleador_email=%s', (user['email'],)) or {}
    if c.get('tipo') == 'empleo':
        registrar_dias_automaticos(c)
    dias = contar_dias_trabajados(id)
    base = float(c.get('monto') or 0)
    por_hora = False
    if c.get('tipo') == 'empleo' and c.get('ref_id'):
        emp = query_one('SELECT tipo FROM empleos WHERE id=%s', (c['ref_id'],))
        if emp and emp.get('tipo') == 'hora':
            por_hora = True
    smmlv = 1400000.0
    aux = 0.0
    if not por_hora:
        aux = 162000.0 if base < 2 * smmlv else 0.0
    salud = round(base * 0.04, 2) if not por_hora else 0.0
    pension = round(base * 0.04, 2) if not por_hora else 0.0
    deducciones = round(salud + pension, 2)
    devengado = round(base + aux, 2)
    neto = round(devengado - deducciones, 2)
    return jsonify({
        'contrato': c,
        'empleado': empleado,
        'empresa': empresa,
        'dias_trabajados': dias,
        'base': base,
        'por_hora': por_hora,
        'auxilio': aux,
        'salud': salud,
        'pension': pension,
        'deducciones': deducciones,
        'devengado': devengado,
        'neto': neto,
        'periodo': datetime.date.today().strftime('%B %Y'),
        'fecha': datetime.date.today().isoformat()
    })

# --- Finanzas ---

@app.route('/api/finanzas', methods=['POST'])
@login_required
def api_crear_finanza():
    data = request.json
    user = get_user()
    execute(
        'INSERT INTO finanzas (user_id, user_email, tipo, categoria, ref_tipo, ref_id, concepto, monto, fecha_registro) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)',
        (user['id'], user['email'], data['tipo'], data['categoria'],
         data.get('ref_tipo'), data.get('ref_id'), data['concepto'],
         float(data['monto']), data.get('fecha_registro', datetime.date.today().isoformat()))
    )
    return jsonify({'message': 'Registro financiero creado'}), 201

@app.route('/api/finanzas', methods=['GET'])
@login_required
def api_get_finanzas():
    user = get_user()
    year = request.args.get('year')
    month = request.args.get('month')
    sql = 'SELECT *, fecha_registro AS fecha FROM finanzas WHERE user_email=%s'
    params = [user['email']]
    if year and month:
        sql += ' AND strftime("%Y", fecha_registro)=%s AND strftime("%m", fecha_registro)=%s'
        params += [str(int(year)), f"{int(month):02d}"]
    sql += ' ORDER BY fecha_registro DESC, created_at DESC'
    return jsonify(query(sql, tuple(params)))

@app.route('/api/finanzas/resumen', methods=['GET'])
@login_required
def api_resumen_finanzas():
    user = get_user()
    year = request.args.get('year')
    month = request.args.get('month')
    if year and month:
        rows = query(
            'SELECT tipo, SUM(monto) as total FROM finanzas WHERE user_email=%s AND strftime("%Y", fecha_registro)=%s AND strftime("%m", fecha_registro)=%s GROUP BY tipo',
            (user['email'], str(int(year)), f"{int(month):02d}")
        )
    else:
        rows = query(
            'SELECT tipo, SUM(monto) as total FROM finanzas WHERE user_email=%s GROUP BY tipo',
            (user['email'],)
        )
    ingresos = 0
    egresos = 0
    for r in rows:
        if r['tipo'] == 'ingreso':
            ingresos = float(r['total'])
        else:
            egresos = float(r['total'])
    return jsonify({'ingresos': ingresos, 'egresos': egresos, 'balance': ingresos - egresos, 'total': ingresos})

@app.route('/api/finanzas/mensual', methods=['GET'])
@login_required
def api_finanzas_mensual():
    user = get_user()
    rows = query(
        "SELECT strftime('%Y', fecha_registro) as anio, strftime('%m', fecha_registro) as mes, "
        "SUM(CASE WHEN tipo='ingreso' THEN monto ELSE 0 END) as ingresos, "
        "SUM(CASE WHEN tipo='egreso' THEN monto ELSE 0 END) as egresos "
        "FROM finanzas WHERE user_email=%s "
        "GROUP BY strftime('%Y', fecha_registro), strftime('%m', fecha_registro) ORDER BY anio, mes",
        (user['email'],)
    )
    meses = []
    for r in rows:
        meses.append({
            'anio': r['anio'],
            'mes': r['mes'],
            'etiqueta': f"{int(r['mes']):02d}/{r['anio']}",
            'ingresos': float(r['ingresos'] or 0),
            'egresos': float(r['egresos'] or 0),
        })
    return jsonify(meses)

# --- Mensajes ---

@app.route('/api/mensajes', methods=['POST'])
@login_required
def api_enviar_mensaje():
    data = request.json
    user = get_user()
    dest_id = data.get('destinatario_id')
    dest_nombre = data.get('destinatario_nombre')
    if not dest_id and data.get('destinatario_email'):
        r = query_one('SELECT id, username FROM usuarios WHERE email=%s', (data['destinatario_email'],))
        if r:
            dest_id = r['id']
            dest_nombre = dest_nombre or r['username']
    if not dest_id:
        return jsonify({'error': 'Destinatario no encontrado'}), 404
    if not dest_nombre:
        r = query_one('SELECT username FROM usuarios WHERE id=%s', (dest_id,))
        if r:
            dest_nombre = r['username']
    if not dest_nombre:
        dest_nombre = 'Usuario'
    if dest_id == user['id']:
        return jsonify({'error': 'No puedes enviarte un mensaje a ti mismo'}), 400
    eid = execute_lastid(
        'INSERT INTO mensajes (remitente_id, remitente_nombre, destinatario_id, destinatario_nombre, tipo_ref, ref_id, mensaje) VALUES (%s,%s,%s,%s,%s,%s,%s)',
        (user['id'], user['username'], dest_id, dest_nombre,
         data['tipo_ref'], data['ref_id'], data['mensaje'])
    )
    r = query_one('SELECT * FROM mensajes WHERE id=%s', (eid,))
    return jsonify(r if r else {'message': 'Mensaje enviado'}), 201

@app.route('/api/mensajes/<tipo_ref>/<int:ref_id>', methods=['GET'])
@login_required
def api_get_mensajes(tipo_ref, ref_id):
    user = get_user()
    if tipo_ref not in ('empleo', 'servicio'):
        return jsonify({'error': 'Tipo inválido'}), 400
    rows = query(
        'SELECT *, CASE WHEN remitente_id=%s THEN 1 ELSE 0 END as es_mio FROM mensajes WHERE tipo_ref=%s AND ref_id=%s AND (remitente_id=%s OR destinatario_id=%s) ORDER BY created_at ASC',
        (user['id'], tipo_ref, ref_id, user['id'], user['id'])
    )
    return jsonify(rows)

@app.route('/api/mensajes/no-leidos', methods=['GET'])
@login_required
def api_mensajes_no_leidos():
    user = get_user()
    r = query_one('SELECT COUNT(*) as total FROM mensajes WHERE destinatario_id=%s AND leido=0', (user['id'],))
    return jsonify({'total': r['total'] if r else 0})

@app.route('/api/mensajes/leer/<int:id>', methods=['PATCH'])
@login_required
def api_marcar_leido(id):
    execute('UPDATE mensajes SET leido=1 WHERE id=%s AND destinatario_id=%s', (id, get_user()['id']))
    return jsonify({'message': 'Marcado como leído'})

def ref_titulo(tipo, ref_id):
    if not ref_id:
        return ''
    if tipo == 'empleo':
        r = query_one('SELECT title FROM empleos WHERE id=%s', (ref_id,))
    else:
        r = query_one('SELECT title FROM servicios WHERE id=%s', (ref_id,))
    return r['title'] if r else ''

@app.route('/api/mensajes/conversaciones', methods=['GET'])
@login_required
def api_conversaciones():
    user = get_user()
    uid = user['id']
    # Un dialog between two people regardless of solicitud estado.
    rows = query(
        'SELECT * FROM mensajes WHERE remitente_id=%s OR destinatario_id=%s ORDER BY created_at DESC',
        (uid, uid)
    )
    seen = {}
    for m in rows:
        if m['remitente_id'] == uid:
            other = m['destinatario_id']
            other_name = m['destinatario_nombre']
        else:
            other = m['remitente_id']
            other_name = m['remitente_nombre']
        if not other:
            continue
        if other not in seen:
            o = query_one('SELECT id, username, email FROM usuarios WHERE id=%s', (other,))
            seen[other] = {
                'otro_id': other,
                'otro_nombre': o['username'] if o else (other_name or ('Usuario-' + str(other))),
                'otro_email': o['email'] if o else '',
                'last_message': m['mensaje'],
                'tipo': m['tipo_ref'],
                'ref_id': m['ref_id'],
                'ref_titulo': ref_titulo(m['tipo_ref'], m['ref_id']),
                'unread': 0,
            }
        if m['destinatario_id'] == uid and m['leido'] == 0:
            seen[other]['unread'] += 1
    return jsonify(list(seen.values()))

@app.route('/api/mensajes/conversacion', methods=['GET'])
@login_required
def api_mensajes_conversacion():
    user = get_user()
    uid = user['id']
    otro_id = request.args.get('id', type=int)
    otro_email = request.args.get('email')
    otro_nombre = request.args.get('nombre') or ''
    if not otro_id and otro_email:
        r = query_one('SELECT id, username, email FROM usuarios WHERE email=%s', (otro_email,))
        if r:
            otro_id = r['id']
            otro_nombre = otro_nombre or r['username']
        else:
            return jsonify([])
    if not otro_id:
        return jsonify([])
    rows = query(
        'SELECT * FROM mensajes WHERE (remitente_id=%s AND destinatario_id=%s) OR (remitente_id=%s AND destinatario_id=%s) ORDER BY created_at ASC',
        (uid, otro_id, otro_id, uid)
    )
    out = []
    for m in rows:
        d = dict(m)
        d['es_mio'] = d['remitente_id'] == uid
        out.append(d)
    return jsonify(out)

# --- Recomendaciones ---

@app.route('/api/recomendaciones', methods=['GET'])
@login_required
def api_recomendaciones():
    user = get_user()
    applied = query('SELECT ref_id FROM aplicaciones WHERE solicitante_email=%s AND tipo="empleo"', (user['email'],))
    applied_ids = [r['ref_id'] for r in applied]
    rows = query('SELECT * FROM empleos WHERE tipo="hora" AND horas > 0 AND horas < 48 ORDER BY horas DESC')
    out = []
    for r in rows:
        if r['id'] in applied_ids:
            continue
        ocup = query_one('SELECT COUNT(*) AS n FROM aplicaciones WHERE tipo="empleo" AND ref_id=%s AND estado="aceptado"', (r['id'],)) or {}
        if int(ocup.get('n') or 0) >= int(r.get('cupos') or 1):
            continue
        h = r['horas'] or 0
        falta = 48 - h
        rec = 56 - h
        r['horas_actuales'] = h
        r['recomendacion'] = f"Te faltan {falta}h para llegar a 48h semanales (máx recomendado: {rec}h)"
        r['horas_faltantes'] = max(0, falta)
        out.append(r)
    return jsonify(out)

# --- Dashboard stats ---

@app.route('/api/dashboard/stats')
@admin_required
def api_dashboard_stats():
    u = query_one('SELECT COUNT(*) as t FROM usuarios')['t']
    e = query_one('SELECT COUNT(*) as t FROM empleos')['t']
    s = query_one('SELECT COUNT(*) as t FROM servicios')['t']
    c = query_one('SELECT COUNT(*) as t FROM contratos')['t']
    a = query_one('SELECT COUNT(*) as t FROM aplicaciones WHERE estado="pendiente"')['t']
    return jsonify({'usuarios': u, 'empleos': e, 'servicios': s, 'contratos': c, 'aplicaciones_pendientes': a})

# --- Static files ---

BASE = os.path.dirname(os.path.abspath(__file__))
LOGIN = os.path.join(BASE, 'Login')
WED = os.path.join(BASE, 'wed_site')

@app.route('/')
def index():
    return send_from_directory(LOGIN, 'intro.html')

@app.route('/<path:path>')
def static_files(path):
    if path.startswith('wed_site/') and 'user' not in session:
        return redirect('/')
    for dire in [BASE, LOGIN, WED]:
        raw = os.path.join(dire, path)
        if os.path.isdir(raw):
            p = os.path.join(raw, 'index.html')
            if os.path.isfile(p):
                return send_from_directory(os.path.join(dire, path), 'index.html')
        elif os.path.isfile(raw):
            return send_from_directory(dire, path)
    return '', 404

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'No encontrado'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Error interno del servidor'}), 500

@app.after_request
def no_cache_html(resp):
    if resp.content_type and resp.content_type.startswith('text/html'):
        resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return resp

if __name__ == '__main__':
    port = int(os.getenv('PORT', '5000'))
    print(f'  LinkWork API corriendo en http://localhost:{port}')
    app.run(host='0.0.0.0', port=port, threaded=True)
