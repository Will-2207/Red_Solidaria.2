__all__ = ["UsuarioController"]
from models.usuario_model import UsuarioModel
from flask import render_template, request, redirect, url_for, session, current_app
import os
import mysql.connector
from werkzeug.utils import secure_filename

class UsuarioController:

    def __init__(self, donacion_model=None):
        from models.usuario_model import UsuarioModel
        self.modelo = UsuarioModel()
        self.donacion_model = donacion_model

    def ver_perfil_view(self):
        from flask import session, render_template, redirect, url_for
        if "usuario_id" not in session:
            return redirect(url_for("login"))
        usuario_datos = {
            "nombre":   session.get("nombre"),
            "telefono": session.get("telefono")
        }
        return render_template("ver_perfil.html", usuario=usuario_datos)

    def login_view(self):
        from flask import render_template, request, redirect, url_for, session, flash
        if request.method == "POST":
            correo   = request.form.get("correo").strip()
            password = request.form.get("password")
            usuario  = self.modelo.validar_usuario(correo, password)
            if usuario:
                session["usuario_id"] = usuario["id"]
                session["nombre"]     = usuario.get("nombre_usuario", usuario["nombre"])
                session["rol"]        = int(usuario["rol_id"])
                session["estado"]     = usuario["estado"]
                print(f"DEBUG LOGIN: {usuario['nombre']} (Rol: {usuario['rol_id']}, Estado: {usuario['estado']}) ha iniciado sesión.")
                rol_id = int(usuario["rol_id"])
                if rol_id == 1:
                    return redirect(url_for("home_administrador"))
                elif rol_id == 3:
                    return redirect(url_for("home_fundacion"))
                else:
                    return redirect(url_for("home_donador"))
            else:
                # CAMBIO AQUÍ: Se usa redirect para limpiar el flujo POST y evitar la alerta del navegador
                flash("Correo o contraseña incorrectos", "danger")
                return redirect(url_for("login"))
        return render_template("login.html")

    def editar_perfil_view(self):
        from flask import session, render_template, request, redirect, url_for, flash
        from models.usuario_model import UsuarioModel
        import os
        from werkzeug.utils import secure_filename

        if "usuario_id" not in session:
            return redirect(url_for("login"))

        usuario_id = session["usuario_id"]
        rol        = int(session.get("rol", 0))

        if request.method == "POST":
            nombre_formulario = request.form.get("nombre")
            telefono = request.form.get("telefono")
            usuario_encargado = request.form.get("usuario_encargado") if rol == 3 else None
            
            archivo_foto  = request.files.get("foto_perfil")
            nombre_archivo = None

            if archivo_foto and archivo_foto.filename != '':
                nombre_archivo = secure_filename(f"perfil_{usuario_id}_{archivo_foto.filename}")
                ruta_carpeta   = os.path.join('static', 'img')
                if not os.path.exists(ruta_carpeta):
                    os.makedirs(ruta_carpeta)
                archivo_foto.save(os.path.join(ruta_carpeta, nombre_archivo))

            modelo = UsuarioModel()
            
            exito = modelo.actualizar_perfil_fundacion(
                usuario_id=usuario_id,
                nombre_fundacion=nombre_formulario, 
                nombre_encargado=usuario_encargado,
                telefono=telefono,
                foto_perfil=nombre_archivo,
                rol=rol
            )
            
            if exito:
                if rol == 3:
                    session["usuario_encargado"] = usuario_encargado
                    session["nombre"] = usuario_encargado  
                    session["fundacion_nombre"] = nombre_formulario 
                else:
                    session["nombre"] = nombre_formulario  
                
                session["telefono"] = telefono
                if nombre_archivo:
                    session["foto_perfil"] = nombre_archivo
                
                flash("✅ Perfil actualizado con éxito", "success")
            else:
                flash("❌ Error al actualizar el perfil", "danger")

            if rol == 1:
                return redirect(url_for("home_administrador"))
            elif rol == 3:
                return redirect(url_for("home_fundacion"))
            else:
                return redirect(url_for("home_donador"))

        usuario_datos = {
            "nombre":      session.get("nombre"),
            "telefono":    session.get("telefono"),
            "foto_perfil": session.get("foto_perfil")
        }

        fundacion_datos = None
        if rol == 3:
            modelo = UsuarioModel()
            fundacion_datos = modelo.obtener_fundacion_por_usuario(usuario_id)

        return render_template("editar_perfil.html", usuario=usuario_datos, fundacion=fundacion_datos)
    
    def registrar(self, nombre, correo, password, rol_id, nit=None, organizacion=None, descripcion_fundacion=None):
        import mysql.connector
        import requests
        conn = None
        try:
            config = {
                'host': 'localhost', 'user': 'root',
                'password': '', 'database': 'donaciones_db', 'port': 3307
            }
            conn   = mysql.connector.connect(**config)
            cursor = conn.cursor()

            cursor.execute("SELECT id FROM usuarios WHERE correo = %s", (correo,))
            if cursor.fetchone():
                print(f"ERROR: El correo {correo} ya está registrado")
                return False

            estado_db = 'pendiente' if int(rol_id) == 3 else 'aprobado'
            cursor.execute(
                "INSERT INTO usuarios (nombre, correo, password, rol_id, estado, fecha_registro) VALUES (%s, %s, %s, %s, %s, NOW())",
                (nombre, correo, password, rol_id, estado_db)
            )
            nuevo_id = cursor.lastrowid

            if int(rol_id) == 3:
                cursor.execute(
                    "INSERT INTO fundaciones (usuario_id, nombre, nit, descripcion) VALUES (%s, %s, %s, %s)",
                    (nuevo_id, organizacion, nit, descripcion_fundacion or '')
                )

            conn.commit()
            print("¡LOG: REGISTRO REALIZADO EN DB CON ÉXITO!")

            if int(rol_id) == 3:
                try:
                    requests.post(
                        "http://localhost:8080/api/email/enviar",
                        json={
                            "destinatario":    correo,
                            "nombreFundacion": organizacion if organizacion else nombre,
                            "estado":          "PENDIENTE"
                        },
                        timeout=5
                    )
                    print(f"✅ Notificación enviada a Java para {correo}")
                except Exception as e_mail:
                    print(f"⚠️ Error al conectar con Java Mail: {e_mail}")

            return True
        except Exception as e:
            print(f"¡ERROR DETECTADO!: {e}")
            return False
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def registro_view(self):
        from flask import request, redirect, url_for, render_template, flash
        if request.method == "POST":
            print(f"DEBUG: Datos recibidos: {request.form}")
            rol_id = request.form.get("rol")
            if not rol_id:
                flash("Debe seleccionar un rol", "danger")
                return redirect(url_for("registro"))

            rol_id = int(rol_id)
            if rol_id == 3:
                nombre                = request.form.get("nombre_fundador") or request.form.get("nombre")
                organizacion          = request.form.get("organizacion")
                descripcion_fundacion = request.form.get("descripcion_fundacion", '')
            else:
                nombre                = request.form.get("nombre_fundador") or request.form.get("nombre")
                organizacion          = None
                descripcion_fundacion = None

            correo   = request.form.get("correo")
            password = request.form.get("password")
            nit      = request.form.get("nit")

            exito = self.registrar(nombre, correo, password, rol_id, nit, organizacion, descripcion_fundacion)
            if exito:
                flash("🎉 ¡Registro exitoso! Ya puedes iniciar sesión.", "success")
                return redirect(url_for("login"))
            else:
                # CAMBIO AQUÍ: Cambiado a redirect para limpiar el formulario si el correo ya existe
                flash("Error al registrar. El correo puede estar en uso.", "danger")
                return redirect(url_for("registro"))
        return render_template("registro.html")
        

    def home_fundacion_view(self):
        if "rol" not in session:
            return redirect(url_for("login"))
        if int(session["rol"]) != 3:
            return "Acceso no autorizado"

        usuario_id = session["usuario_id"]
        fundacion = self.modelo.obtener_fundacion_por_usuario(usuario_id)
        
        if not fundacion:
            return "Error: No se encontraron datos de la fundación."

        # Configurar sesión con datos de fundación
        session['fundacion_nombre'] = fundacion.get('nombre_fundacion')
        session['usuario_encargado'] = fundacion.get('nombre_encargado') 
        if fundacion.get('foto_perfil'):
            session['foto_perfil'] = fundacion['foto_perfil']

        fundacion_id = fundacion["id"]
        
        # --- FILTROS ---
        query = request.args.get('q', '')
        donante = request.args.get('donante', '')
        categoria_raw = request.args.get('categoria', '')
        categoria_filtro = categoria_raw.lower().strip() if categoria_raw and categoria_raw.lower() != 'todas' else categoria_raw
        estado_raw = request.args.get('est', '').lower()
        
        if estado_raw in ['rechazada', 'rechazado', 'rechazados']: estado_filtro = 'rechazado'
        elif estado_raw in ['recibida', 'recibido', 'recibidos']: estado_filtro = 'recibido'
        else: estado_filtro = estado_raw

        # --- DATOS USANDO EL MODELO (Limpio y profesional) ---
        mis_donaciones = self.donacion_model.obtener_donaciones_por_fundacion(
            fundacion_id, q=query, donante=donante, categoria=categoria_filtro, estado=estado_filtro
        )
        
        # Nueva llamada limpia al modelo para monetarias
        donaciones_monetarias = self.donacion_model.get_historial_monetario_detallado(fundacion_id)
        solicitudes_ayuda = self.donacion_model.obtener_necesidades_por_fundacion(fundacion_id)
        stats_db = self.donacion_model.obtener_estadisticas_fundacion(fundacion_id)
        motivos_eliminacion = self.modelo.obtener_motivos_eliminacion()

        # Validación de fotos
        ruta_fotos = os.path.join(current_app.root_path, 'static', 'img', 'donaciones')
        for d in mis_donaciones:
            nombre_foto = d.get('fotos')
            d['foto_existe'] = bool(nombre_foto and os.path.exists(os.path.join(ruta_fotos, nombre_foto)))
        
        stats = {
            'pendientes': stats_db.get('pendientes', 0) if stats_db else 0,
            'recibidas': stats_db.get('recibidas', 0) if stats_db else 0,
            'rechazadas': stats_db.get('rechazadas', 0) if stats_db else 0,
            'alimentos': stats_db.get('alimentos', 0) if stats_db else 0,
            'ropa': stats_db.get('ropa', 0) if stats_db else 0,
            'otros': stats_db.get('otros', 0) if stats_db else 0,
            'total': stats_db.get('total', 0) if stats_db else 0,
            'monetarias': len(donaciones_monetarias)
        }

        return render_template(
            "home_fundacion.html",
            fundacion=fundacion,
            donaciones=mis_donaciones,
            donaciones_monetarias=donaciones_monetarias,
            solicitudes_ayuda=solicitudes_ayuda,
            motivos_eliminacion=motivos_eliminacion,
            stats=stats,
            q_actual=query,
            donante_actual=donante,
            cat_actual=categoria_raw,
            est_actual=estado_raw
        )
        
    def solicitar_ayuda_view(self):
        from flask import session, redirect, url_for, request, flash, render_template
        from models.donacion_model import DonacionModel

        if "usuario_id" not in session or int(session.get("rol")) != 3:
            return redirect(url_for("login"))

        usuario_id = session.get("usuario_id")
        modelo_donacion = DonacionModel()
        
        fundacion_datos = modelo_donacion.obtener_fundacion_por_usuario(usuario_id)
        if fundacion_datos and 'nombre_fundacion' in fundacion_datos:
            fundacion_datos['nombre'] = fundacion_datos['nombre_fundacion']

        if request.method == "POST":
            fundacion_id = fundacion_datos['id'] if fundacion_datos else usuario_id
            categoria = request.form.get("categoria")
            text_cantidad = request.form.get("cantidad")
            cantidad = int(text_cantidad) if text_cantidad and text_cantidad.isdigit() else 0
            urgencia = request.form.get("urgencia")
            fecha_limite = request.form.get("fecha_limite")
            ubicacion = request.form.get("ubicacion")
            telefono = request.form.get("telefono")
            descripcion = request.form.get("descripcion")
            
            correo_contacto = fundacion_datos.get('correo') if fundacion_datos else ''

            exito = modelo_donacion.crear_necesidad(
                fundacion_id, categoria, cantidad, urgencia,
                fecha_limite, ubicacion, telefono, descripcion, correo_contacto
            )

            if exito:
                flash("🚀 ¡Tu solicitud de ayuda ha sido publicada con éxito!", "success")
                return redirect(url_for("home_fundacion"))
            else:
                flash("❌ Hubo un error al publicar la solicitud.", "danger")
                return render_template("solicitar_ayuda.html", fundacion=fundacion_datos)

        return render_template("solicitar_ayuda.html", fundacion=fundacion_datos)

    
    def editar_solicitud_view(self, id):
        from flask import session, redirect, url_for, request, flash, render_template
        from models.donacion_model import DonacionModel

        if "usuario_id" not in session or int(session.get("rol")) != 3:
            return redirect(url_for("login"))

        usuario_id = session.get("usuario_id")
        modelo_donacion = DonacionModel()

        solicitud = modelo_donacion.obtener_necesidad_por_id(id)
        
        if not solicitud:
            flash("❌ La solicitud no existe.", "danger")
            return redirect(url_for("home_fundacion"))

        if solicitud.get('estado') != 'pendiente':
            flash("⚠️ No puedes editar esta solicitud porque ya ha sido vinculada o aceptada por un donante.", "warning")
            return redirect(url_for("home_fundacion"))

        fundacion_datos = modelo_donacion.obtener_fundacion_por_usuario(usuario_id)
        if fundacion_datos and 'nombre_fundacion' in fundacion_datos:
            fundacion_datos['nombre'] = fundacion_datos['nombre_fundacion']

        if request.method == "POST":
            categoria    = request.form.get("categoria")
            text_cantidad = request.form.get("cantidad")
            cantidad     = int(text_cantidad) if text_cantidad and text_cantidad.isdigit() else 0
            urgencia     = request.form.get("urgencia")
            fecha_limite = request.form.get("fecha_limite")
            ubicacion    = request.form.get("ubicacion")
            telefono     = request.form.get("telefono")
            descripcion  = request.form.get("descripcion")

            exito = modelo_donacion.actualizar_necesidad(
                id, categoria, cantidad, urgencia,
                fecha_limite, ubicacion, telefono, descripcion
            )

            if exito:
                flash("💾 ¡Solicitud actualizada correctamente!", "success")
                return redirect(url_for("home_fundacion"))
            else:
                flash("❌ Error al guardar los cambios de la solicitud.", "danger")

        return render_template("solicitar_ayuda.html", solicitud=solicitud, fundacion=fundacion_datos)

    def eliminar_solicitud_view(self, id):
        from flask import session, redirect, url_for, flash
        from models.donacion_model import DonacionModel

        if "usuario_id" not in session or int(session.get("rol")) != 3:
            return redirect(url_for("login"))

        modelo_donacion = DonacionModel()
        solicitud = modelo_donacion.obtener_necesidad_por_id(id)

        if not solicitud:
            flash("❌ La solicitud no existe.", "danger")
            return redirect(url_for("home_fundacion"))

        if solicitud.get('estado') != 'pendiente':
            flash("⚠️ No puedes eliminar esta solicitud porque ya está asignada o completada.", "warning")
            return redirect(url_for("home_fundacion"))

        exito = modelo_donacion.cambiar_estado_necesidad(id, 'eliminada')

        if exito:
            flash("🗑️ La solicitud ha sido eliminada del panel con éxito (Guardada en historial).", "success")
        else:
            flash("❌ Hubo un error al intentar eliminar la solicitud.", "danger")

        return redirect(url_for("home_fundacion"))

    def home_donador_view(self):
        from flask import session, redirect, url_for, render_template, request, flash
        from models.donacion_model import DonacionModel
        import requests
        import json
        from app import serializar_datos, mysql # Asegúrate de importar mysql aquí

        if "usuario_id" not in session:
            return redirect(url_for("login"))

        usuario_id = session.get("usuario_id")

        # --- INICIO DE LÓGICA DE CONTADORES ---
        cur = mysql.connection.cursor()
        cur.execute("SELECT estado_donante, COUNT(*) FROM donaciones WHERE usuario_id = %s GROUP BY estado_donante", (usuario_id,))
        resultados = cur.fetchall()
        cur.close()

        # Convertimos los resultados en un diccionario para fácil acceso
        stats = {row[0]: row[1] for row in resultados}
        contadores = {
            'pendientes': stats.get('pendiente', 0),
            'recibidas': stats.get('recibido', 0),
            'rechazadas': stats.get('rechazado', 0)
        }
        # --- FIN DE LÓGICA DE CONTADORES ---

        datos_donador = {
            "nombre":      session.get("nombre"),
            "foto_perfil": session.get("foto_perfil"),
            "telefono":    session.get("telefono"),
            "estado":      session.get("estado") if session.get("estado") else "Activo"
        }

        modelo_donacion = DonacionModel()
        q              = request.args.get('q', '')
        cat            = request.args.get('cat', '')
        est            = request.args.get('est', '')
        fundacion_busq = request.args.get('fundacion', '')
        accion         = request.args.get('accion')
        correo_reporte = request.args.get('correo_reporte')

        # 1. Obtención de necesidades
        necesidades = modelo_donacion.obtener_necesidades_activas(q=q, cat=cat, usuario_id=usuario_id) or []
        
        # 2. Obtención del historial
        mis_donaciones = modelo_donacion.obtener_donaciones_por_usuario_filtrado(
            usuario_id, 
            q=q, 
            categoria=cat, 
            estado=est, 
            fundacion=fundacion_busq
        ) or []

        # 3. Lógica de reporte a Java
        if accion == 'reporte':
            if not correo_reporte:
                flash("Por favor, ingresa un correo para el reporte", "warning")
            else:
                try:
                    url_java = "http://localhost:8080/api/email/enviar-reporte-donador"
                    desglose_dict = {}
                    
                    for d in mis_donaciones:
                        desc             = d.get('descripcion', 'Otros')
                        cant             = int(d.get('cantidad', 0))
                        est_don          = d.get('estado_donante', 'Verificado')
                        cat_don          = d.get('categoria_nombre', 'Otros')
                        fundacion_nombre = d.get('fundacion_nombre', 'N/A')
                        
                        clave = (desc, est_don, cat_don, fundacion_nombre)
                        
                        if clave in desglose_dict:
                            desglose_dict[clave]['cantidad'] += cant
                        else:
                            desglose_dict[clave] = {
                                "descripcion": desc, 
                                "cantidad": cant,
                                "estado": est_don, 
                                "nombre_categoria": cat_don,
                                "fundacion_nombre": fundacion_nombre
                            }
                            
                    lista_desglosada = list(desglose_dict.values())
                    total_donaciones = sum(item['cantidad'] for item in lista_desglosada)
                    
                    payload = {
                        "destinatario":       correo_reporte,
                        "nombreDonador":      datos_donador["nombre"],
                        "telefono":           datos_donador.get("telefono", "N/A"),
                        "amountDonaciones":   total_donaciones,
                        "donaciones":         lista_desglosada,
                        "categoriaFiltrada":  cat,
                        "estadoFiltrado":     est
                    }
                    
                    datos_limpios = json.loads(json.dumps(payload, default=serializar_datos))
                    response = requests.post(url_java, json=datos_limpios, timeout=10)
                    
                    if response.status_code == 200:
                        flash(f"✅ ¡Reporte enviado con éxito a {correo_reporte}!", "success")
                    else:
                        flash("Java recibió los datos pero hubo un error al generar el PDF", "danger")
                except Exception as e:
                    print(f"❌ Error de conexión con Java: {e}")
                    flash("No se pudo conectar con el servicio de correos (Java)", "danger")
                    
                    historial_monetario = self.modelo.get_historial_monetario(usuario_id) \
                    if hasattr(self.modelo, 'get_historial_monetario') else []

        return render_template(
            "home_donador.html",
            donador=datos_donador,
            necesidades=necesidades,
            donaciones=mis_donaciones,
            contadores=contadores # <-- AQUÍ SE ENVÍAN LOS DATOS
        )
        
    def admin_panel_view(self):
        from flask import session, redirect, url_for, render_template
        if "rol" not in session:
            return redirect(url_for("login"))
        if int(session["rol"]) != 1:
            return "Acceso no autorizado"
        return render_template("admin.html")

    def subir_foto(self, request, session, app):
        from flask import redirect, url_for
        if "usuario_id" not in session:
            return redirect(url_for("login"))
        if "foto" not in request.files:
            return redirect(url_for("home_donador"))
        foto = request.files["foto"]
        if foto.filename == "":
            return redirect(url_for("home_donador"))
        filename     = secure_filename(foto.filename)
        ruta         = app.config["UPLOAD_FOLDER"]
        if not os.path.exists(ruta):
            os.makedirs(ruta)
        foto.save(os.path.join(ruta, filename))
        session["foto"] = filename
        return redirect(url_for("home_donador"))
    
    def administrar_cuenta_view(self):
        if 'usuario_id' not in session:
            return redirect(url_for('login'))
        
        from models.usuario_model import UsuarioModel
        modelo_usuario = UsuarioModel()
        
        if request.method == 'POST':
            nombre_fundacion = request.form.get('nombre_fundacion')
            nombre_encargado = request.form.get('usuario_encargado')
            telefono = request.form.get('telefono')
            
            actualizado = modelo_usuario.actualizar_perfil_fundacion(
                usuario_id=session['usuario_id'],
                nombre_fundacion=nombre_fundacion,
                nombre_encargado=nombre_encargado,
                telefono=telefono
            )
            
            if actualizado:
                flash("✨ ¡Datos de la fundación actualizados!", "success")
            else:
                flash("❌ Hubo un error al actualizar los datos", "danger")
                
        return redirect(url_for('home_fundacion'))
    
    def solicitudes_completo_view(self):
        from flask import render_template, session, redirect, url_for, flash
        from models.donacion_model import DonacionModel
        
        if 'usuario_id' not in session:
            return redirect(url_for('login'))
            
        usuario_id = session.get('usuario_id')
        modelo_donacion = DonacionModel()
        
        fundacion_datos = modelo_donacion.obtener_fundacion_por_usuario(usuario_id)
        
        if not fundacion_datos:
            flash("❌ No se encontraron datos vinculados a esta fundación.", "danger")
            return redirect(url_for('home_fundacion'))
            
        if 'nombre_fundacion' in fundacion_datos:
            fundacion_datos['nombre'] = fundacion_datos['nombre_fundacion']
            
        fundacion_id = fundacion_datos['id'] 
        
        solicitudes = modelo_donacion.obtener_necesidades_por_fundacion(fundacion_id)
        
        return render_template('solicitudes_completo.html', 
                            solicitudes_ayuda=solicitudes, 
                            fundacion=fundacion_datos)