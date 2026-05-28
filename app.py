import os
import json
import requests
import uuid
from datetime import date, datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_mysqldb import MySQL
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename

# Modelos
from models.donacion_model import DonacionModel
from models.soportemodel import SoporteModel

# Controladores
from controllers.auth_controller import AuthController
from controllers.usuario_controller import UsuarioController
from controllers.donacion_controller import DonacionController
from controllers.soportecontroller import SoporteController
from controllers.home_administrador_controller import mostrar_home_administrador, api_admin
donacion_ctrl = DonacionController()  # Inicialización temporal para evitar errores de referencia circular

basedir = os.path.abspath(os.path.dirname(__file__))
# Cambia tu línea de inicialización de la app por esta:
app = Flask(__name__, static_folder=os.path.join(basedir, 'static'))
app.secret_key = "123456"

# ================= CONFIGURACIÓN DE CORREO =================
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'cartuji7@gmail.com' 
app.config['MAIL_PASSWORD'] = 'fozwuruetypmfwho' 
app.config['MAIL_DEFAULT_SENDER'] = 'cartuji7@gmail.com'

# ================= CONFIGURACIÓN DE BASE DE DATOS =================
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_PORT'] = 3307 
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'donaciones_db'

# ================= INICIALIZACIÓN DE COMPONENTES =================
mysql = MySQL(app)
mail = Mail(app)

# 1. Inicialización de Modelos
soporte_model = SoporteModel(mysql)
# Busca esta línea y cámbiala por:
donacion_model = DonacionModel(mysql)

# 2. Inicialización de Controladores
auth = AuthController()
usuario_ctrl = UsuarioController(donacion_model)
donacion_ctrl = DonacionController(donacion_model)
soporte_controller = SoporteController(soporte_model, mail)

# ================= RUTAS DE SOPORTE =================

@app.route('/soporte/nuevo')
def vista_enviar_soporte():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    return render_template('enviar_soporte.html')

@app.route('/enviar_incidencia', methods=['POST'])
def enviar_incidencia():
    return soporte_controller.registrar_incidencia()
    
@app.route('/soporte_incidencias')
def soporte_incidencias():
    return soporte_controller.listar_incidencias()
    
@app.route('/gestion_ticket/<int:id>')
def gestion_ticket(id):
    return soporte_controller.detalle_ticket(id)
    
@app.route('/resolver_ticket/<int:id>', methods=['POST'])
def resolver_ticket(id):
    return soporte_controller.procesar_resolucion(id)

@app.route('/api/contar_pendientes')
def contar_pendientes():
    total = soporte_model.contar_tickets_abiertos() 
    return jsonify({"pendientes": total})

# ================= CONFIGURACIÓN APP =================

# Registrar Blueprint de rutas API admin
app.register_blueprint(api_admin)

# ================= FUNCIONES DE UTILIDAD =================

def serializar_datos(obj):
    """Función para convertir objetos de fecha a texto para JSON"""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"Tipo {type(obj)} no es serializable")

# ================= RUTA PARA GESTIONAR DONACIONES =================
@app.route('/gestionar_donacion', methods=['POST'])
def gestionar_donacion():
    return donacion_ctrl.gestionar_donacion_accion()

# ================= RUTAS DE ACCIONES =================

# Agrupamos todas las rutas que llevan a la misma función aquí arriba:

@app.route("/donar", methods=["GET", "POST"])
@app.route("/donar/<int:necesidad_id>", methods=["GET", "POST"])
def donar(necesidad_id=None):
    fundacion_id = request.form.get('fundacion_id')
    n_id = necesidad_id if necesidad_id != 0 else None
    
    # LLAMADA POSICIONAL: Quitamos 'necesidad_id=' y 'fundacion_id='
    # Esto envía: request -> request, n_id -> necesidad_id, fundacion_id -> fundacion_id
    return donacion_ctrl.publicar_donacion_view(request, n_id, fundacion_id)
# ================= FUNCIONES DE COMUNICACIÓN CON JAVA =================

def enviar_al_correo_java(email, nombre, estado):
    url_java = "http://localhost:8080/api/email/enviar"
    datos = {"destinatario": email, "nombreFundacion": nombre, "estado": estado}
    try:
        response = requests.post(url_java, json=datos, timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"Error conectando con Java: {e}")
        return False

def enviar_reporte_pdf_java(payload):
    url_java = "http://localhost:8080/api/email/enviar-reporte"
    try:
        datos_limpios = json.loads(json.dumps(payload, default=serializar_datos))
        response = requests.post(url_java, json=datos_limpios, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending PDF to Java: {e}")
        return False

# ================= RUTAS DE AUTENTICACIÓN =================


@app.route('/test_ruta')
def test_ruta():
    ruta_static = app.static_folder
    return f"La carpeta estática que Flask está usando es: {ruta_static}"


@app.route("/")
def inicio():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    return auth.login_view()

@app.route("/registro", methods=["GET", "POST"])
def registro():
    return usuario_ctrl.registro_view()

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route('/verificar_correo')
def verificar_correo():
    from models.usuario_model import UsuarioModel
    correo = request.args.get('correo', '')
    usuario = UsuarioModel().obtener_usuario_por_correo(correo)
    return jsonify(existe=bool(usuario))

# ================= RUTAS DE USUARIO / ROLES =================

@app.route('/home_donador')
def home_donador():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    return usuario_ctrl.home_donador_view()

@app.route('/home_fundacion')
def home_fundacion():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    return usuario_ctrl.home_fundacion_view()

@app.route('/fundacion/solicitudes-completo')
def solicitudes_fundacion_completo():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    return usuario_ctrl.solicitudes_completo_view()

@app.route('/administrar_cuenta', methods=['GET', 'POST'])
def administrar_cuenta():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    return usuario_ctrl.administrar_cuenta_view()

@app.route('/home_administrador')
def home_administrador():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    return mostrar_home_administrador()

@app.route('/reporte_admin', methods=['GET'])
def reporte_admin():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    return render_template('reporte_admin.html')

# ================= RUTAS DE ACCIONES =================

@app.route("/subir_foto", methods=["POST"])
def subir_foto():
    return usuario_ctrl.subir_foto(request, session, app)

@app.route("/editar_perfil", methods=["GET", "POST"])
def editar_perfil():
    return usuario_ctrl.editar_perfil_view()


@app.route("/aprobar/<int:id>")
def aprobar_fundacion_ruta(id):
    from controllers.home_administrador_controller import aprobar_fundacion_controller
    from models.usuario_model import UsuarioModel
    modelo_usuario = UsuarioModel()
    datos = modelo_usuario.obtener_datos_aprobacion(id)
    if datos:
        return aprobar_fundacion_controller(id, datos['correo'], datos['nombre'])
    flash("❌ No se pudieron obtener los datos de la fundación", "danger")
    return redirect(url_for('home_admin_panel'))

@app.route("/rechazar/<int:id>")
def rechazar_fundacion_ruta(id):
    from controllers.home_administrador_controller import rechazar_fundacion_controller
    from models.usuario_model import UsuarioModel
    modelo_usuario = UsuarioModel()
    datos = modelo_usuario.obtener_datos_aprobacion(id)
    if datos:
        return rechazar_fundacion_controller(id, datos['correo'], datos['nombre'])

# ================= RUTAS DE GESTIÓN DE NECESIDADES =================

@app.route('/solicitar-ayuda', methods=['GET', 'POST'])
def solicitar_ayuda():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    return donacion_ctrl.solicitar_ayuda_view(session)

@app.route('/necesidad/editar/<int:id>', methods=['GET', 'POST'])
def editar_necesidad_ruta(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    return donacion_ctrl.editar_necesidad_view(id, session)

@app.route('/necesidad/eliminar/<int:id>')
def eliminar_necesidad_ruta(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    return donacion_ctrl.eliminar_necesidad_accion(id, session)

@app.route('/ver_perfil')
def ver_perfil():
    return usuario_ctrl.ver_perfil_view()

# Rutas para gestionar el estado de las donaciones desde el panel
@app.route('/donacion/estado/<int:id>/<nuevo_estado>')
def cambiar_estado_donacion(id, nuevo_estado):
    return donacion_ctrl.cambiar_estado(id, nuevo_estado)

@app.route('/donacion/eliminar/<int:id>')
def eliminar_donacion_ruta(id):
    return donacion_ctrl.eliminar(id)

# Nueva ruta para rechazar/ocultar una necesidad del carrusel del donante
@app.route('/rechazar_necesidad/<int:necesidad_id>', methods=['POST'])
def rechazar_necesidad(necesidad_id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    return donacion_ctrl.rechazar_necesidad_accion(necesidad_id, session)

@app.route('/debug_rutas')
def debug_rutas():
    import os
    ruta_real = os.path.join(app.root_path, 'static', 'img', 'donaciones', 'don_2_descarga_7.jpg')
    existe = os.path.exists(ruta_real)
    return f"¿Existe el archivo en {ruta_real}?: {existe}"

@app.route('/ver_carpeta')
def ver_carpeta():
    ruta = os.path.join(app.root_path, 'static', 'img', 'donaciones')
    archivos = os.listdir(ruta)
    return str(archivos)


# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)