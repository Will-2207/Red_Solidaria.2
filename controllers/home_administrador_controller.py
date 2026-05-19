import requests  # Asegúrate de haber hecho: pip install requests
from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for, current_app
from datetime import datetime
from flask import request, jsonify, Response

# Importación de la base de datos
from database.db import get_connection

# Importaciones directas desde el paquete de modelos
from models.home_administrador_model import HomeAdminModel, ReporteAdminModel
from models.usuario_model import UsuarioModel

api_admin = Blueprint('api_admin', __name__)
    
api_admin = Blueprint('api_admin', __name__)

JAVA_BASE = "http://localhost:8080/api/email"

MOTIVOS_ELIMINACION = {
    "normas":        "Incumplimiento de las normas y políticas de publicación de Red Solidaria.",
    "contenido":     "Publicación de contenido falso, engañoso o fraudulento.",
    "uso_indebido":  "Uso indebido de la plataforma para fines no autorizados.",
    "documentacion": "Documentación legal incompleta o vencida.",
    "nit_invalido":  "NIT inválido o no verificable ante la DIAN.",
    "no_legal":      "La organización no está legalmente constituida en Colombia.",
    "inactividad":   "Inactividad prolongada sin justificación (más de 90 días).",
    "comportamiento":"Comportamiento inapropiado hacia donantes o usuarios de la plataforma.",
    "reincidencia":  "Reincidencia en infracciones previamente notificadas.",
    "transparencia": "Manejo inadecuado o no transparente de las donaciones recibidas.",
    "incumplimiento":"Incumplimiento en la entrega o gestión de donaciones físicas.",
    "sin_reporte":   "Falta de reporte sobre el destino de los recursos recibidos.",
    "duplicada":     "Organización duplicada ya registrada en la plataforma.",
    "suplantacion":  "Suplantación de identidad de otra fundación o entidad.",
    "info_falsa":    "Información de contacto falsa o no verificable.",
}

MOTIVOS_ELIMINACION_DONANTE = {
    "normas":        "Incumplimiento de las normas y políticas de uso de Red Solidaria.",
    "comportamiento":"Comportamiento inapropiado hacia fundaciones o usuarios de la plataforma.",
    "info_falsa":    "Información personal falsa o no verificable.",
    "inactividad":   "Inactividad prolongada sin justificación (más de 90 días).",
    "fraude":        "Intento de fraude o uso indebido de la plataforma.",
    "reincidencia":  "Reincidencia en infracciones previamente notificadas.",
    "duplicado":     "Cuenta duplicada ya registrada en la plataforma.",
    "suplantacion":  "Suplantación de identidad de otra persona.",
}


# ──────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────


# Cambia @app.route por @api_admin.route
@api_admin.route('/admin/generar_token_soporte', methods=['POST'])
def solicitar_token_a_php():
    usuario_id = request.form.get('usuario_id')
    
    url_php = "http://localhost/red_solidaria_php/generar_token.php"
    
    try:
        # Petición al microservicio PHP
        respuesta = requests.post(url_php, data={'usuario_id': usuario_id}, timeout=5)
        datos = respuesta.json()
        
        if datos.get('status') == 'success':
            token_generado = datos['token']
            return jsonify({"mensaje": "Token generado y guardado", "token": token_generado})
        else:
            return jsonify({"error": "PHP no pudo generar el token"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
def _get_fundacion_info(fundacion_id):
    connection = get_connection()
    try:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(
                """SELECT f.id, f.nombre, f.nit, f.estado_validacion, u.correo
                   FROM fundaciones f
                   INNER JOIN usuarios u ON f.usuario_id = u.id
                   WHERE f.id = %s""",
                (fundacion_id,)
            )
            return cursor.fetchone()
    except Exception as ex:
        print(f"Error en _get_fundacion_info: {ex}")
        return None
    finally:
        if connection: connection.close()


def _notificar_java(correo, nombre, estado, mensaje=None):
    """
    Envía la notificación al microservicio de Java (Spring Boot).
    'mensaje' llevará el motivo personalizado cuando se use 'OTROS'.
    """
    try:
        # Preparamos los datos básicos
        payload = {
            "destinatario": correo, 
            "nombreFundacion": nombre, # En Java este campo se usa para el saludo ¡Hola, [Nombre]!
            "estado": estado
        }
        
        # Si existe un mensaje (el motivo de eliminación), lo añadimos al JSON
        if mensaje:
            payload["mensaje"] = mensaje
            
        # Realizamos la petición POST al servicio de Spring Boot
        # Asegúrate de que JAVA_BASE apunte a tu URL de Java (ej. http://localhost:8080/api/email)
        response = requests.post(f"{JAVA_BASE}/enviar", json=payload, timeout=5)
        
        if response.status_code == 200:
            print(f"✅ Java respondió exitosamente ({response.status_code}) para {correo}")
        else:
            print(f"⚠️ Java respondió con error {response.status_code}: {response.text}")
            
    except Exception as ex:
        print(f"❌ Error crítico al conectar con Java: {ex}")

def _serializar(lista):
    out = []
    for row in lista:
        r = {}
        for k, v in row.items():
            r[k] = str(v) if not isinstance(v, (str, int, float, type(None))) else v
        out.append(r)
    return out


# ──────────────────────────────────────────────────────────
# VISTA PRINCIPAL
# ──────────────────────────────────────────────────────────
def mostrar_home_administrador():
    # Usamos HomeAdminModel para todo lo administrativo
    donantes               = HomeAdminModel.obtener_donantes_activos()
    fundaciones_pendientes = HomeAdminModel.obtener_fundaciones_pendientes()
    fundaciones_aprobadas  = HomeAdminModel.obtener_fundaciones_aprobadas()
    fundaciones_rechazadas = HomeAdminModel.obtener_fundaciones_rechazadas()

    total_fundaciones = (
        len(fundaciones_pendientes) +
        len(fundaciones_aprobadas)  +
        len(fundaciones_rechazadas)
    )
    
    total_pendientes = len(fundaciones_pendientes)
    donaciones       = HomeAdminModel.obtener_todas_donaciones()
    
    # Listas vacías para evitar errores de renderizado si no hay datos
    donaciones_economicas = []
    pagos                 = []

    return render_template(
        "home_administrador.html",
        donantes=donantes,
        fundaciones_pendientes=fundaciones_pendientes,
        fundaciones_aprobadas=fundaciones_aprobadas,
        fundaciones_rechazadas=fundaciones_rechazadas,
        total_fundaciones=total_fundaciones,
        total_pendientes=total_pendientes,
        donaciones=donaciones,
        donaciones_economicas=donaciones_economicas,
        pagos=pagos,
        motivos_eliminacion=MOTIVOS_ELIMINACION,
        motivos_eliminacion_donante=MOTIVOS_ELIMINACION_DONANTE,
    )

# ──────────────────────────────────────────────────────────
# REPORTE ADMIN
# ──────────────────────────────────────────────────────────
@api_admin.route('/api/reporte_admin', methods=['GET', 'POST'])
def reporte_admin():
    # 1. Capturar parámetros comunes (sirve para GET y POST)
    donante     = request.values.get('donante',     '').strip() or None
    fundacion   = request.values.get('fundacion',   '').strip() or None
    categoria   = request.values.get('categoria',   '').strip() or None
    estado      = request.values.get('estado',      '').strip() or None
    fecha_desde = request.values.get('fecha_desde', '').strip() or None
    fecha_hasta = request.values.get('fecha_hasta', '').strip() or None
    monto_min   = request.values.get('monto_min',   '').strip() or None
    monto_max   = request.values.get('monto_max',   '').strip() or None
    pasarela    = request.values.get('pasarela',    '').strip() or None

    # Consultar el modelo de base de datos
    resultado = HomeAdminModel.buscar_reporte_admin(
        donante=donante, fundacion=fundacion, categoria=categoria,
        estado=estado, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta,
        monto_min=monto_min, monto_max=monto_max, pasarela=pasarela,
    )

    if request.method == 'POST':
        # 2. Soporte Híbrido: Capturar correo si viene de un JSON o de un Formulario tradicional
        correo_destino = None
        if request.is_json:
            datos_json = request.get_json()
            correo_destino = datos_json.get('correo_reporte', '').strip()
        
        # Si no vino por JSON, lo buscamos en los valores normales del request
        if not correo_destino:
            correo_destino = request.values.get('correo_reporte', '').strip()

        # Validación estricta del correo
        if not correo_destino:
            return jsonify(success=False, error="Correo destinatario requerido (campo 'correo_reporte')"), 400

        # Serializar las donaciones filtradas
        donaciones_serial = _serializar(resultado["donaciones"])
        
        # Construir el payload con los campos exactos que espera el DTO de Spring Boot
        payload = {
            "destinatario":       correo_destino,
            "nombreFundacion":    "Administrador - Red Solidaria",
            "nit":                "Panel Administrativo",
            "categoriaFiltrada":  categoria or "Todas",
            "estadoFiltrado":     estado    or "Todos",
            "cantidadDonaciones": resultado["totales"].get("total_donaciones", 0),
            "donaciones": [
                {
                    "descripcion":      d.get("descripcion", ""),
                    "cantidad":         d.get("cantidad", 0),
                    "estado":           d.get("estado", ""),
                    "estado_fundacion": d.get("estado", ""),
                    "nombre_donante":   d.get("donador_nombre", ""),
                    "nombre_categoria": d.get("categoria_nombre", ""),
                }
                for d in donaciones_serial
            ],
        }
        
        try:
            # Enviar la petición al backend de Java
            url_java = f"{JAVA_BASE}/enviar-reporte"
            resp = requests.post(url_java, json=payload, timeout=12)
            
            # Si Java responde exitosamente
            if resp.status_code in [200, 201]:
                return jsonify(
                    success=True, 
                    mensaje=f"Reporte enviado con éxito a {correo_destino}", 
                    totales=resultado["totales"]
                )
            
            # Si Java responde con un error, mostramos qué código devolvió para diagnosticarlo
            return jsonify(
                success=False, 
                error=f"El servidor de correos (Java) denegó la petición con código: {resp.status_code}"
            ), 502

        except requests.exceptions.Timeout:
            return jsonify(success=False, error="Tiempo de espera agotado con el servidor de correos"), 503
        except requests.exceptions.ConnectionError:
            return jsonify(success=False, error="No se pudo establecer conexión. ¿Está encendido Spring Boot en el puerto correcto?"), 503
        except Exception as ex:
            return jsonify(success=False, error=f"Error inesperado al conectar con Java: {str(ex)}"), 500

    # Respuesta por defecto para peticiones GET
    return jsonify(
        donaciones=_serializar(resultado["donaciones"]),
        fundaciones=_serializar(resultado["fundaciones"]),
        donantes=_serializar(resultado["donantes"]),
        totales=resultado["totales"],
    )

# ──────────────────────────────────────────────────────────
# APROBAR / RECHAZAR (redireccionamiento clásico)
# ──────────────────────────────────────────────────────────
def aprobar_fundacion_controller(id_fundacion, correo_fundacion, nombre_fundacion):
    if HomeAdminModel.aprobar_fundacion(id_fundacion):
        _notificar_java(correo_fundacion, nombre_fundacion, "APROBADO")
        flash(f"✅ Fundación '{nombre_fundacion}' aprobada y correo enviado.", "success")
    else:
        flash("❌ Error técnico: no se pudo actualizar el estado.", "danger")
    return redirect(url_for("home_administrador"))


def rechazar_fundacion_controller(id_fundacion, correo_fundacion=None, nombre_fundacion=None):
    if HomeAdminModel.rechazar_fundacion(id_fundacion):
        if correo_fundacion and nombre_fundacion:
            _notificar_java(correo_fundacion, nombre_fundacion, "RECHAZADO")
        flash("La solicitud ha sido rechazada y el correo enviado.", "info")
    else:
        flash("Error al procesar el rechazo.", "danger")
    return redirect(url_for("home_administrador"))


# ──────────────────────────────────────────────────────────
# API REST — aprobar / rechazar (AJAX)
# ──────────────────────────────────────────────────────────
@api_admin.route('/aprobar_fundacion/<int:id>', methods=['POST'])
def api_aprobar_fundacion(id):
    info  = _get_fundacion_info(id)
    exito = HomeAdminModel.aprobar_fundacion(id)
    if exito and info:
        _notificar_java(info['correo'], info['nombre'], "APROBADO")
    return jsonify(success=exito)


@api_admin.route('/rechazar_fundacion/<int:id>', methods=['POST'])
def api_rechazar_fundacion(id):
    info  = _get_fundacion_info(id)
    exito = HomeAdminModel.rechazar_fundacion(id)
    if exito and info:
        _notificar_java(info['correo'], info['nombre'], "RECHAZADO")
    return jsonify(success=exito)


# ──────────────────────────────────────────────────────────
# API REST — ELIMINAR FUNDACIÓN (AJAX)
# ──────────────────────────────────────────────────────────
@api_admin.route('/eliminar_fundacion/<int:id>', methods=['POST'])
def api_eliminar_fundacion(id):
    # 1. Obtener datos del JSON enviado por el Modal
    data = request.get_json() if request.is_json else {}
    motivo_key = data.get('motivo', '')
    mensaje_personalizado = data.get('mensaje', '') # Texto de "Otros"

    # 2. Determinar el texto del motivo
    if motivo_key == 'OTROS' and mensaje_personalizado:
        motivo_final = mensaje_personalizado
    else:
        motivo_final = MOTIVOS_ELIMINACION.get(motivo_key, "Decisión administrativa de Red Solidaria.")

    # 3. Obtener info y ejecutar eliminación en DB
    info = _get_fundacion_info(id)
    exito = HomeAdminModel.eliminar_fundacion(id)

    if exito and info:
        # Enviamos solo el motivo_final. Java ya tiene la estructura del correo lista 
        # en el case "ELIMINADO" que configuramos antes.
        _notificar_java(
            correo=info['correo'], 
            nombre=info['nombre'], 
            estado="ELIMINADO", 
            mensaje=motivo_final
        )

    return jsonify(success=exito)


# ──────────────────────────────────────────────────────────
# API REST — ELIMINAR DONANTE (AJAX) ← NUEVO
# ──────────────────────────────────────────────────────────
@api_admin.route('/eliminar_donante/<int:id>', methods=['POST'])
def api_eliminar_donante(id):
    # 1. Capturamos los datos del JSON enviado por el JS
    data = request.get_json() if request.is_json else {}
    motivo_key = data.get('motivo', '')
    mensaje_otros = data.get('mensaje', '') # Este es el texto del textarea

    # 2. Determinamos el texto del motivo
    if motivo_key == 'OTROS' and mensaje_otros:
        # Si eligió otros, usamos su texto personalizado
        motivo_texto = mensaje_otros
    else:
        # Si no, buscamos en el diccionario predefinido
        motivo_texto = MOTIVOS_ELIMINACION_DONANTE.get(motivo_key, "Decisión administrativa de Red Solidaria.")

    # 3. Ejecutamos la eliminación en la DB
    exito, nombre, correo = HomeAdminModel.eliminar_donante(id)

    # 4. Enviamos la notificación si la eliminación fue exitosa
    if exito and correo:
        mensaje_correo = (
            f"Lamentamos informarte que tu cuenta de donante ha sido eliminada de la plataforma Red Solidaria.<br><br>"
            f"<b>Motivo:</b> {motivo_texto}<br><br>"
            f"Si consideras que esta decisión es incorrecta, puedes contactar a nuestro equipo de soporte."
        )
        # Enviamos el mensaje construido al microservicio de Java
        _notificar_java(correo, nombre, "ELIMINADO", mensaje=mensaje_correo)

    return jsonify(success=exito)



# ──────────────────────────────────────────────────────────
# REPORTE ADMIN (ÚNICO CONTROLADOR ACTIVO)
# ──────────────────────────────────────────────────────────
@api_admin.route('/api/reporte_admin', methods=['GET', 'POST'])
def gestion_reporte_admin():
    """
    Controlador central para la gestión del Reporte Administrativo.
    - GET con '?descargar=true': Descarga directa del PDF desde Spring Boot.
    - GET normal: Retorna JSON para llenar las tablas en la interfaz.
    - POST: Envía los datos a Java para generar PDF y enviar por correo.
    """
    
    # 1. Captura de filtros desde la solicitud (Query params o Form data)
    filtros = {
        'donante': request.values.get('donante', ''),
        'fundacion': request.values.get('fundacion', ''),
        'categoria': request.values.get('categoria', 'Todas'),
        'estado': request.values.get('estado', 'Todos'),
        'fecha_desde': request.values.get('fecha_desde'),
        'fecha_hasta': request.values.get('fecha_hasta'),
        'monto_min': request.values.get('monto_min'),
        'pasarela': request.values.get('pasarela')
    }

    estado_mapeado = filtros['estado']

    # --- CASO A: SOLICITUD DE BÚSQUEDA O DESCARGA DIRECTA (GET) ---
    if request.method == 'GET':
        if request.args.get('descargar') == 'true':
            try:
                url_java_descarga = "http://localhost:8080/api/email/descargar-reporte-admin"
                params_java = {
                    'nombre': 'Administrador - Red Solidaria',
                    'categoria': filtros['categoria'],
                    'est': estado_mapeado,
                    'donante': filtros['donante'],
                    'fundacion': filtros['fundacion']
                }
                
                response_java = requests.get(url_java_descarga, params=params_java, timeout=20)
                
                if response_java.status_code == 200:
                    return Response(
                        response_java.content,
                        status=200,
                        mimetype="application/pdf",
                        headers={"Content-Disposition": "attachment; filename=Reporte_Admin_Red_Solidaria.pdf"}
                    )
                else:
                    return jsonify({
                        "success": False, 
                        "error": f"Java no pudo generar el PDF descargable. Status: {response_java.status_code}"
                    }), 500
                    
            except requests.exceptions.ConnectionError:
                return jsonify({"success": False, "error": "Servidor Spring Boot apagado. No se puede descargar el PDF."}), 500
            except Exception as e:
                return jsonify({"success": False, "error": f"Error al descargar: {str(e)}"}), 500

        datos_reporte = ReporteAdminModel.obtener_datos_reporte(filtros)
        return jsonify(datos_reporte)

    # --- CASO B: CONEXIÓN CON JAVA PARA PDF Y ENVÍO POR CORREO (POST) ---
    if request.method == 'POST':
        datos_reporte = ReporteAdminModel.obtener_datos_reporte(filtros)
        correo_destino = request.form.get('correo_reporte')
        
        if not correo_destino:
            return jsonify({"success": False, "error": "Falta el correo destinatario."}), 400

        try:
            ahora = datetime.now()
            donaciones_serializadas = _serializar(datos_reporte.get("donaciones", []))
            
            lista_donaciones_lista = []
            for d in donaciones_serializadas:
                lista_donaciones_lista.append({
                    "descripcion":     d.get("descripcion", ""),
                    "cantidad":        int(d.get("cantidad", 0)) if d.get("cantidad") else 0,
                    "estado":          d.get("estado", ""),          
                    "estado_fundacion": d.get("estado", ""),          
                    "nombre_donante":   d.get("donador_nombre", ""),
                    "nombre_categoria": d.get("categoria_nombre", "")
                })
            
            payload_para_java = {
                "destinatario":       correo_destino,
                "nombreFundacion":    "Administrador - Red Solidaria",
                "nit":                "Panel Administrativo",
                "categoriaFiltrada":  filtros.get('categoria', 'Todas'),
                "estadoFiltrado":     filtros.get('estado', 'Todos'),
                "cantidadDonaciones": datos_reporte["totales"].get("total_donaciones", 0),
                "donaciones":         lista_donaciones_lista
            }

            url_java_email = "http://localhost:8080/api/email/enviar-reporte"

            print("📤 [INFO] Intentando conectar con Spring Boot...")
            response = requests.post(url_java_email, json=payload_para_java, timeout=15)
            print(f"📊 [INFO] Spring Boot respondió con Status Code: {response.status_code}")

            if response.status_code == 200:
                return jsonify({
                    "success": True, 
                    "mensaje": f"Reporte procesado por el servicio de correo. Enviado a {correo_destino}"
                })
            else:
                print(f"❌ [JAVA ERROR] Detalle: {response.text}")
                return jsonify({
                    "success": False, 
                    "error": f"El servicio de Java respondió con error {response.status_code}"
                }), 502

        except requests.exceptions.ConnectionError:
            print("❌ [FLASK ERROR] No hay conexión con Spring Boot.")
            return jsonify({"success": False, "error": "No se pudo conectar con Spring Boot para el envío de correo."}), 503
        except Exception as e:
            print("⚠️ --- ERROR INTERNO DETECTADO EN EL CONTROLADOR DE PYTHON ---")
            import traceback
            traceback.print_exc()
            print("────────────────────────────────────────────────────────────────")
            return jsonify({"success": False, "error": f"Error interno en el servidor Flask: {str(e)}"}), 500