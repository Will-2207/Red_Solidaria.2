__all__ = ["UsuarioController"]
from models.usuario_model import UsuarioModel, Usuario
import os
from werkzeug.utils import secure_filename
from flask import render_template, request, redirect, url_for, session, flash

class UsuarioController:

    def __init__(self):
        self.modelo = UsuarioModel()

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
                flash("Correo o contraseña incorrectos", "danger")
                return render_template("login.html")
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
            
            # Llamamos al método pasándole todos los parámetros ordenados
            exito = modelo.actualizar_perfil_fundacion(
                usuario_id=usuario_id,
                nombre_fundacion=nombre_formulario, 
                nombre_encargado=usuario_encargado,
                telefono=telefono,
                foto_perfil=nombre_archivo,
                rol=rol
            )
            
            if exito:
                # ── ASIGNACIÓN CORRECTA DE SESIONES SEGÚN EL ROL ──
                if rol == 3:
                    session["usuario_encargado"] = usuario_encargado
                    session["nombre"] = usuario_encargado  # El nombre del encargado va para el saludo general
                    session["fundacion_nombre"] = nombre_formulario # Guardamos el nombre de la institución de forma explícita
                else:
                    session["nombre"] = nombre_formulario  # Donador o admin guardan su nombre normal
                
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

        # ── LÓGICA GET ──
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

            # Verificar correo duplicado
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
        from flask import request, redirect, url_for, render_template
        if request.method == "POST":
            print(f"DEBUG: Datos recibidos: {request.form}")
            rol_id = request.form.get("rol")
            if not rol_id:
                return render_template("registro.html", error="Debe seleccionar un rol")

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
                return redirect(url_for("login"))
            else:
                return render_template("registro.html", error="Error al registrar. El correo puede estar en uso.")
        return render_template("registro.html")

    def publicar_donacion_view(self, request, session, necesidad_id=None):
        from flask import redirect, url_for, render_template, flash
        from models.donacion_model import DonacionModel
        import os
        from werkzeug.utils import secure_filename

        if "usuario_id" not in session:
            return redirect(url_for("login"))

        modelo               = DonacionModel()
        necesidad_prellenada = None
        todas_las_categorias = modelo.obtener_categorias()

        if necesidad_id:
            necesidad_prellenada = modelo.obtener_necesidad_por_id(necesidad_id)

        # ── Fundaciones activas CON descripción ──
        fundaciones_activas = self.modelo.obtener_fundaciones_activas_con_descripcion()

        if request.method == "POST":
            donador_id   = session["usuario_id"]
            fundacion_id = request.form.get("fundacion_id")
            categoria_id = request.form.get("categoria_id")
            cantidad     = request.form.get("cantidad")
            descripcion  = request.form.get("descripcion")

            # ── Procesar fotos (máx. 3) ──
            fotos_guardadas = []
            archivos_fotos  = request.files.getlist("fotos_donacion")
            carpeta_fotos   = os.path.join('static', 'img', 'donaciones')
            if not os.path.exists(carpeta_fotos):
                os.makedirs(carpeta_fotos)

            for foto in archivos_fotos[:3]:
                if foto and foto.filename != '':
                    nombre_foto = secure_filename(f"don_{donador_id}_{foto.filename}")
                    foto.save(os.path.join(carpeta_fotos, nombre_foto))
                    fotos_guardadas.append(nombre_foto)
                    print(f"DEBUG: Foto guardada: {nombre_foto}")

            fotos_str = ','.join(fotos_guardadas) if fotos_guardadas else None

            exito = modelo.registrar_donacion(
                donador_id, fundacion_id, categoria_id,
                cantidad, descripcion, fotos_str
            )

            if exito:
                flash("🎉 ¡Gracias! Tu ayuda ha sido registrada correctamente.", "success")
                return redirect(url_for("home_donador"))
            else:
                flash("❌ Hubo un problema al procesar la donación.", "danger")

        return render_template(
            "donar.html",
            necesidad=necesidad_prellenada,
            categorias=todas_las_categorias,
            fundaciones_activas=fundaciones_activas
        )

    def home_fundacion_view(self):
        from flask import session, redirect, url_for, render_template, request, flash
        from models.donacion_model import DonacionModel
        import requests
        import json
        from app import serializar_datos

        # 1. Verificación de Seguridad
        if "rol" not in session:
            return redirect(url_for("login"))
        if int(session["rol"]) != 3:
            return "Acceso no autorizado"

        # 2. Obtener datos de la fundación y SINCRONIZAR SESIÓN
        usuario_id = session["usuario_id"]
        fundacion = self.modelo.obtener_fundacion_por_usuario(usuario_id)
        
        if not fundacion:
            return "Error: No se encontraron datos de la fundación."

        # CORREGIDO: Usamos los nuevos alias del modelo para que no se pisen en el Popup
        if fundacion:
            session['fundacion_nombre'] = fundacion.get('nombre_fundacion')
            session['usuario_encargado'] = fundacion.get('nombre_encargado') # <-- AQUÍ CAPTURA TU NOMBRE REAL
            if fundacion.get('foto_perfil'):
                session['foto_perfil'] = fundacion['foto_perfil']

        # 3. Captura de filtros desde la URL y NORMALIZACIÓN DE ESTADO Y CATEGORÍA
        fundacion_id = fundacion["id"]
        query = request.args.get('q', '')
        donante = request.args.get('donante', '')
        accion = request.args.get('accion')
        correo_reporte = request.args.get('correo_reporte')
        
        # --- NORMALIZACIÓN DE CATEGORÍA (Evita fallos por mayúsculas/minúsculas) ---
        categoria_raw = request.args.get('categoria', '')
        if categoria_raw and categoria_raw.lower() != 'todas':
            categoria_filtro = categoria_raw.lower().strip()
        else:
            categoria_filtro = categoria_raw  # Mantiene 'Todas' o vacío

        # --- Lógica de normalización para que el filtro funcione (rechazada -> rechazado) ---
        estado_raw = request.args.get('est', '').lower()
        if estado_raw in ['rechazada', 'rechazado', 'rechazados']:
            estado_filtro = 'rechazado'
        elif estado_raw in ['recibida', 'recibido', 'recibidos']:
            estado_filtro = 'recibido'
        else:
            estado_filtro = estado_raw

        # 4. Obtener donaciones filtradas usando el estado y categoría normalizados
        donacion_model = DonacionModel()
        mis_donaciones = donacion_model.obtener_donaciones_por_fundacion(
            fundacion_id, 
            q=query, 
            donante=donante, 
            categoria=categoria_filtro, # <-- Enviado normalizado
            estado=estado_filtro
        )
        
        # --- ESTADÍSTICAS (Contadores laterales) ---
        stats_db = donacion_model.obtener_estadisticas_fundacion(fundacion_id)
        stats = {
            'pendientes': stats_db.get('pendientes', 0) if stats_db else 0,
            'recibidas': stats_db.get('recibidas', 0) if stats_db else 0,
            'rechazadas': stats_db.get('rechazadas', 0) if stats_db else 0,
            'alimentos': stats_db.get('alimentos', 0) if stats_db else 0,
            'ropa': stats_db.get('ropa', 0) if stats_db else 0,
            'otros': stats_db.get('otros', 0) if stats_db else 0,
            'total': stats_db.get('total', 0) if stats_db else 0
        }

        # 5. Lógica de Generación de Reportes (Integración con Java)
        if accion == 'reporte':
            if not correo_reporte:
                flash("Por favor, ingresa un correo para el reporte", "warning")
            else:
                try:
                    # CORRECCIÓN DE ENDPOINT: Apuntamos al servicio exclusivo de fundaciones
                    url_java = f"http://localhost:8080/api/email/enviar-reporte-fundacion"
                    desglose_dict = {}
                    
                    for d in mis_donaciones:
                        desc = d.get('descripcion', 'Sin descripción')
                        cant = int(d.get('cantidad', 0))
                        est = d.get('estado_donante', 'Pendiente')
                        cat = d.get('nombre_categoria', 'Otros')
                        clave = (desc, est, cat)
                        
                        if clave in desglose_dict:
                            desglose_dict[clave]['cantidad'] += cant
                        else:
                            desglose_dict[clave] = {
                                "descripcion": desc,
                                "cantidad": cant,
                                "estado": est,
                                "nombre_categoria": cat
                            }
                    
                    lista_desglosada = list(desglose_dict.values())
                    total_donaciones = sum(item['cantidad'] for item in lista_desglosada)
                    
                    payload = {
                        "destinatario": correo_reporte,
                        "nombreFundacion": fundacion.get('nombre'),
                        "nit": fundacion.get('nit', 'N/A'),
                        "cantidadDonaciones": total_donaciones,
                        "donaciones": lista_desglosada,
                        "fundacionId": fundacion_id,
                        "categoriaFiltrada": categoria_raw,
                        "estadoFiltrado": estado_raw
                    }
                    
                    datos_limpios = json.loads(json.dumps(payload, default=serializar_datos))
                    response = requests.post(url_java, json=datos_limpios, timeout=10)
                    
                    if response.status_code == 200:
                        flash(f"✅ ¡Reporte enviado con éxito a {correo_reporte}!", "success")
                    else:
                        print(f"DEBUG Java Error: {response.text}")
                        flash("Error en el servicio de reportes Java", "danger")
                except Exception as e:
                    print(f"❌ Error de conexión con Java: {e}")
                    flash("No se pudo conectar con el servicio de correos", "danger")
                    
        # 6. Preparar datos adicionales (CORREGIDO para filtrar por tu fundación)
        solicitudes_ayuda = donacion_model.obtener_necesidades_por_fundacion(fundacion_id)
        motivos_eliminacion = self.modelo.obtener_motivos_eliminacion()

        # 7. Retorno al Template
        return render_template(
            "home_fundacion.html",
            fundacion=fundacion,
            donaciones=mis_donaciones,
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

        if request.method == "POST":
            fundacion_id = session["usuario_id"]
            categoria    = request.form.get("categoria")
            cantidad     = request.form.get("cantidad")
            urgencia     = request.form.get("urgencia")
            fecha_limite = request.form.get("fecha_limite")
            ubicacion    = request.form.get("ubicacion")
            telefono     = request.form.get("telefono")
            descripcion  = request.form.get("descripcion")

            modelo_donacion = DonacionModel()
            exito = modelo_donacion.crear_necesidad(
                fundacion_id, categoria, cantidad, urgencia,
                fecha_limite, ubicacion, telefono, descripcion
            )

            if exito:
                flash("🚀 ¡Tu solicitud de ayuda ha sido publicada con éxito!", "success")
                return redirect(url_for("home_fundacion"))
            else:
                flash("❌ Hubo un error al publicar la solicitud.", "danger")
                return render_template("solicitar_ayuda.html")

        return render_template("solicitar_ayuda.html")

    def home_donador_view(self):
        from flask import session, redirect, url_for, render_template, request, flash
        from models.donacion_model import DonacionModel
        import requests
        import json
        from app import serializar_datos

        # 1. Verificación de seguridad
        if "usuario_id" not in session:
            return redirect(url_for("login"))

        # 2. Preparar datos del perfil (MODIFICADO PARA EVITAR EL 'NONE')
        datos_donador = {
            "nombre":      session.get("nombre"),
            "foto_perfil": session.get("foto_perfil"),
            "telefono":    session.get("telefono"),
            "estado":      session.get("estado") if session.get("estado") else "Activo"
        }

        # 3. Captura de filtros desde la URL
        modelo_donacion = DonacionModel()
        q              = request.args.get('q', '')
        cat            = request.args.get('cat', '')
        est            = request.args.get('est', '')
        fundacion_busq = request.args.get('fundacion', '')
        accion         = request.args.get('accion')
        correo_reporte = request.args.get('correo_reporte')

        # 4. Obtener datos para la vista (Necesidades y Donaciones propias)
        necesidades = modelo_donacion.obtener_necesidades_activas(q, cat)
        
        mis_donaciones = modelo_donacion.obtener_donaciones_por_usuario_filtrado(
            session["usuario_id"], 
            q=q, 
            categoria=cat, 
            estado=est, 
            fundacion=fundacion_busq
        )

        # 5. Lógica de Reportes para Donadores (Integración Java)
        if accion == 'reporte':
            if not correo_reporte:
                flash("Por favor, ingresa un correo para el reporte", "warning")
            else:
                try:
                    url_java      = "http://localhost:8080/api/email/enviar-reporte-donador"
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
                        "cantidadDonaciones": total_donaciones,
                        "donaciones":         lista_desglosada,
                        "categoriaFiltrada":  cat,
                        "estadoFiltrado":     est
                    }
                    
                    datos_limpios = json.loads(json.dumps(payload, default=serializar_datos))
                    response      = requests.post(url_java, json=datos_limpios, timeout=10)
                    
                    if response.status_code == 200:
                        flash(f"✅ ¡Reporte enviado con éxito a {correo_reporte}!", "success")
                    else:
                        flash("Java recibió los datos pero hubo un error al generar el PDF", "danger")
                except Exception as e:
                    print(f"❌ Error de conexión con Java: {e}")
                    flash("No se pudo conectar con el servicio de correos (Java)", "danger")

        # 6. Renderizar el template con los datos del donador
        return render_template(
            "home_donador.html",
            donador=datos_donador,
            necesidades=necesidades,
            donaciones=mis_donaciones
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