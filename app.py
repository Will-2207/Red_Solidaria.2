import os
import json
import requests
from datetime import date, datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from flask import session, redirect, url_for

# Controllers
from controllers.auth_controller import AuthController
from controllers.usuario_controller import UsuarioController
from controllers.donacion_controller import DonacionController
from controllers.home_administrador_controller import mostrar_home_administrador

# ================= FUNCIONES DE UTILIDAD =================

def serializar_datos(obj):
    """Convierte fechas de MySQL a texto para que Java las entienda."""
    if isinstance(obj, (date, datetime)):
        return obj.strftime('%Y-%m-%d')
    return str(obj)

# ================= CONFIGURACIÓN APP =================

app = Flask(__name__)
app.secret_key = "123456"

# Registrar Blueprint de rutas API admin
from controllers.home_administrador_controller import api_admin
app.register_blueprint(api_admin)

# ================= RUTA PARA GESTIONAR DONACIONES =================
@app.route("/gestionar_donacion", methods=["POST"])
def gestionar_donacion():
    from models.donacion_model import DonacionModel
    if "usuario_id" not in session or int(session.get("rol")) != 3:
        flash("Acceso no autorizado", "danger")
        return redirect(url_for("home_fundacion"))
    donacion_id = request.form.get("donacion_id")
    accion = request.form.get("accion")
    if not donacion_id or accion not in ["aceptar", "rechazar", "eliminar"]:
        flash("Solicitud inválida", "danger")
        return redirect(url_for("home_fundacion"))

    conn = None
    try:
        conn = __import__('database.db').db.get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT df.estado, d.usuario_id FROM donaciones_fundaciones df "
            "JOIN donaciones d ON df.donacion_id = d.id "
            "WHERE df.donacion_id = %s AND df.fundacion_id = "
            "(SELECT id FROM fundaciones WHERE usuario_id = %s)",
            (donacion_id, session["usuario_id"])
        )
        don = cursor.fetchone()

        if accion != "eliminar" and (not don or don["estado"] != "pendiente"):
            flash("La donación ya fue gestionada o no existe.", "warning")
            return redirect(url_for("home_fundacion"))

        cursor.execute(
            "SELECT u.correo, u.nombre FROM usuarios u WHERE u.id = %s",
            (don["usuario_id"],)
        )
        donante = cursor.fetchone()
        correo_donante = donante["correo"] if donante else None
        nombre_donante  = donante["nombre"] if donante else None

        if accion == "eliminar":
            cursor.execute(
                "UPDATE donaciones_fundaciones SET estado = 'eliminada' "
                "WHERE donacion_id = %s AND fundacion_id = "
                "(SELECT id FROM fundaciones WHERE usuario_id = %s)",
                (donacion_id, session["usuario_id"])
            )
            conn.commit()
            cursor.execute(
                "SELECT estado FROM donaciones_fundaciones WHERE donacion_id = %s "
                "AND fundacion_id = (SELECT id FROM fundaciones WHERE usuario_id = %s)",
                (donacion_id, session["usuario_id"])
            )
            estado_actual = cursor.fetchone()
            if estado_actual and estado_actual["estado"] == "eliminada":
                flash("Donación eliminada correctamente.", "warning")
            else:
                flash("Error: No se pudo marcar como eliminada.", "danger")
        else:
            nuevo_estado = "aceptada" if accion == "aceptar" else "rechazada"
            cursor.execute(
                "UPDATE donaciones_fundaciones SET estado = %s "
                "WHERE donacion_id = %s AND fundacion_id = "
                "(SELECT id FROM fundaciones WHERE usuario_id = %s)",
                (nuevo_estado, donacion_id, session["usuario_id"])
            )
            conn.commit()
            if accion == "aceptar":
                flash("Donación recibida correctamente.", "success")
            else:
                flash("Donación rechazada correctamente.", "danger")

            if correo_donante:
                fundacion_nombre = session.get("nombre", "Fundación")
                cursor.execute(
                    "SELECT d.descripcion, c.nombre as categoria FROM donaciones d "
                    "LEFT JOIN categorias c ON d.categoria_id = c.id WHERE d.id = %s",
                    (donacion_id,)
                )
                donacion_detalle = cursor.fetchone()
                descripcion = donacion_detalle["descripcion"] if donacion_detalle else ""
                categoria   = donacion_detalle["categoria"]   if donacion_detalle else ""
                estado_correo = "RECIBIDO" if accion == "aceptar" else "RECHAZADO_DONACION"
                datos_correo = {
                    "destinatario":    correo_donante,
                    "nombreFundacion": fundacion_nombre,
                    "estado":          estado_correo,
                    "categoriaFiltrada": categoria,
                    "donaciones": [{"descripcion": descripcion}]
                }
                try:
                    response = requests.post(
                        "http://localhost:8080/api/email/enviar",
                        json=datos_correo, timeout=5
                    )
                    if response.status_code != 200:
                        flash("No se pudo notificar al donante por correo.", "warning")
                except Exception as e:
                    print(f"Error conectando con Java: {e}")
                    flash("No se pudo notificar al donante por correo.", "warning")
    except Exception as e:
        print(f"Error al actualizar estado de donación: {e}")
        flash("Error al actualizar el estado de la donación.", "danger")
    finally:
        if conn:
            conn.close()
    return redirect(url_for("home_fundacion"))

# Configuración subida de archivos
UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Instancias de controllers
auth         = AuthController()
usuario_ctrl = UsuarioController()
donacion_ctrl = DonacionController()

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
        print(f"Error enviando PDF a Java: {e}")
        return False

# ================= RUTAS DE AUTENTICACIÓN =================

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
    from flask import jsonify
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

@app.route('/home_administrador')
def home_administrador():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    return mostrar_home_administrador()

# ── REPORTE ADMIN: GET renderiza la página, POST/GET con JSON van al blueprint ──
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

@app.route("/donar", methods=["GET", "POST"])
@app.route("/donar/<int:necesidad_id>", methods=["GET", "POST"])
def donar(necesidad_id=None):
    return donacion_ctrl.publicar_donacion_view(request, session, necesidad_id)

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

@app.route('/solicitar-ayuda', methods=['GET', 'POST'])
def solicitar_ayuda():
    return donacion_ctrl.solicitar_ayuda_view(session)

@app.route('/ver_perfil')
def ver_perfil():
    return usuario_ctrl.ver_perfil_view()

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)