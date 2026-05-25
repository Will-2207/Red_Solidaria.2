from flask import render_template, redirect, url_for, flash, request, session
from models.donacion_model import DonacionModel
from flask import current_app as app

class DonacionController:
    def __init__(self, modelo=None):
        self.modelo = modelo if modelo else DonacionModel()

    def cambiar_estado(self, donacion_id, accion):
        if "usuario_id" not in session:
            return redirect(url_for("login"))
        
        # Mapeo de la acción al ENUM de tu base de datos
        estado_db = 'recibido' if accion == 'aceptar' else 'rechazado'
        
        exito = self.modelo.cambiar_estado_donacion(donacion_id, estado_db)
        
        if exito:
            flash(f"✅ La donación ha sido marcada como {estado_db}", "success")
        else:
            flash("❌ No se pudo actualizar el estado de la donación", "danger")
            
        return redirect(url_for("home_fundacion"))

    def eliminar(self, donacion_id):
        """Elimina lógicamente una donación del panel de la fundación."""
        if 'usuario_id' not in session:
            return redirect(url_for('login'))
            
        # Usamos el método unificado del modelo
        exito = self.modelo.cambiar_estado_donacion(donacion_id, 'eliminado')
        
        if exito:
            flash("🗑️ Donación eliminada del panel con éxito.", "success")
        else:
            flash("❌ Error al intentar eliminar la donación.", "danger")
        
        return redirect(url_for('home_fundacion'))
    
    # =========================================================================
    # GESTIÓN DE NECESIDADES (SOLICITUDES DE AYUDA)
    # =========================================================================
    
    def solicitar_ayuda_view(self, session):
        # Primero obtenemos el ID interno de la fundación desde la sesión
        from models.usuario_model import UsuarioModel
        user_model = UsuarioModel()
        fundacion = user_model.obtener_fundacion_por_usuario(session.get('usuario_id'))
        
        if not fundacion:
            return "Error: No se encontró la fundación asociada a este usuario."
            
        fundacion_id = fundacion['id']

        if request.method == 'POST':
            categoria_texto = request.form.get('categoria') # "Alimentos", "Ropa", etc.
            cantidad = request.form.get('cantidad')
            urgencia = request.form.get('urgencia')
            telefono = request.form.get('telefono')
            descripcion = request.form.get('descripcion')
            fecha_vencimiento = request.form.get('fecha_vencimiento')
            tipo_recurso_especial = request.form.get('tipo_recurso_especial')

            # ── DETECTOR DINÁMICO DE CATEGORÍAS REALES ──
            # Traemos las categorías que tienes registradas en tu DB
            lista_categorias = self.modelo.obtener_categorias()
            categoria_id = None

            # Buscamos el ID cuyo nombre coincida con lo que viene del HTML
            for cat in lista_categorias:
                # Comparamos ignorando mayúsculas y espacios
                if cat['nombre'].strip().lower() in categoria_texto.strip().lower() or categoria_texto.strip().lower() in cat['nombre'].strip().lower():
                    categoria_id = cat['id']
                    break

            # Si por alguna razón sigue sin encontrar coincidencia, agarramos el primer ID que exista en tu DB
            if not categoria_id and lista_categorias:
                categoria_id = lista_categorias[0]['id']

            if not fecha_vencimiento: 
                fecha_vencimiento = None
                
            correo_usuario = session.get('correo') # Capturas el correo de quien crea la solicitud    

            # Insertamos en la DB con el ID real verificado
            exito = self.modelo.crear_necesidad(
                fundacion_id=fundacion_id, 
                categoria_id=categoria_id,
                cantidad=cantidad,
                urgencia=urgencia,
                fecha_limite=None,
                ubicacion=None,
                telefono=telefono,
                descripcion=descripcion,
                contacto_correo=correo_usuario, # Guardamos el correo de contacto en la DB
                fecha_vencimiento=fecha_vencimiento,
                tipo_recurso_especial=tipo_recurso_especial,
                punto_entrega=None
            )

            if exito:
                flash("✨ Solicitud de ayuda creada con éxito.", "success")
                return redirect(url_for('home_fundacion'))
            else:
                categorias = self.modelo.obtener_categorias()
                return render_template('solicitar_ayuda.html', error="No se pudo registrar la solicitud", categorias=categorias)

        categorias = self.modelo.obtener_categorias()
        return render_template('solicitar_ayuda.html', categories=categorias, fundacion=fundacion)
    
    def editar_necesidad_view(self, necesidad_id, session):
        """Renderiza y procesa el formulario de edición de una necesidad"""
        necesidad = self.modelo.obtener_necesidad_por_id(necesidad_id)
        if not necesidad:
            flash("❌ La solicitud de ayuda no existe.", "danger")
            return redirect(url_for('home_fundacion'))

        # Mapeo de Categorías
        mapeo_categories = {
            "Alimentos": 1, "Ropa": 2, "Higiene": 3,
            "Educación": 4, "Mobiliario": 5, "Otros": 6
        }

        if request.method == 'POST':
            categoria_texto = request.form.get('categoria')
            cantidad = request.form.get('cantidad')
            urgencia = request.form.get('urgencia')
            telefono = request.form.get('telefono')
            descripcion = request.form.get('descripcion')
            fecha_vencimiento = request.form.get('fecha_vencimiento')
            
            # NUEVOS CAMPOS CAPTURADOS DESDE TU FORMULARIO INTERFAZ
            tipo_recurso_especial = request.form.get('tipo_recurso_especial')
            punto_entrega = request.form.get('punto_entrega')

            categoria_id = mapeo_categories.get(categoria_texto, 6)

            if not fecha_vencimiento: fecha_vencimiento = None

            # Actualización enviando los nuevos campos a la Base de Datos
            exito = self.modelo.actualizar_necesidad(
                necesidad_id=necesidad_id,
                categoria_id=categoria_id,
                cantidad=cantidad,
                urgencia=urgencia,
                fecha_limite=None,
                ubicacion=None,
                telefono=telefono,
                descripcion=descripcion,
                fecha_vencimiento=fecha_vencimiento,
                tipo_recurso_especial=tipo_recurso_especial,
                punto_entrega=punto_entrega
            )

            if exito:
                flash("✅ Solicitud de ayuda actualizada correctamente.", "success")
                return redirect(url_for('home_fundacion'))
            else:
                categorias = self.modelo.obtener_categorias()
                flash("❌ No se realizaron cambios o hubo un error al actualizar.", "warning")
                return render_template('solicitar_ayuda.html', necesidad=necesidad, categories=categorias)

        categorias = self.modelo.obtener_categorias()
        # Cambia 'editar_necesidad.html' por 'solicitar_ayuda.html'
        return render_template('solicitar_ayuda.html', necesidad=necesidad, categories=categorias)
    
    
    def eliminar(self, donacion_id):
        """Elimina lógicamente una donación del panel de la fundación."""
        # Validación de seguridad: Asegúrate que el usuario tenga sesión activa
        if 'usuario_id' not in session:
            return redirect(url_for('login'))
            
        # El método cambiar_estado_donacion debe existir en tu modelo
        # y ejecutar el: UPDATE donaciones SET estado_donante = 'eliminado' WHERE id = ...
        exito = self.modelo.cambiar_estado_donacion(donacion_id, 'eliminado')
        
        if exito:
            flash("🗑️ Donación eliminada del panel con éxito.", "success")
        else:
            flash("❌ Error al intentar eliminar la donación.", "danger")
        
        return redirect(url_for('home_fundacion'))
    # =========================================================================
    # MÉTODOS DE DONACIONES PARA DONADORES
    # =========================================================================

    def publicar_donacion_view(self, request, session, necesidad_id=None):
        if "usuario_id" not in session:
            return redirect(url_for("login"))
            
        necesidad_prellenada = None
        if necesidad_id:
            necesidad_prellenada = self.modelo.obtener_necesidad_por_id(necesidad_id)

        from database.db import get_connection
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT f.id, f.nombre
            FROM fundaciones f
            JOIN usuarios u ON f.usuario_id = u.id
            WHERE u.estado = 'aprobado' AND u.rol_id = 3
            ORDER BY f.nombre ASC
        """)
        fundaciones_activas = cursor.fetchall()
        conn.close()

        if request.method == "POST":
            donador_id = session["usuario_id"]
            categoria_id = request.form.get("categoria_id")
            cantidad = request.form.get("cantidad")
            descripcion = request.form.get("descripcion")

           # Reemplaza la lógica de guardado actual con esto:
            import os
            from flask import current_app
            from werkzeug.utils import secure_filename

            if fotos_lista:
                # Obtenemos solo el primer archivo
                primer_archivo = fotos_lista[0]
                
                # Verificamos que realmente sea un archivo
                if primer_archivo and primer_archivo.filename != '':
                    nombre_foto = secure_filename(primer_archivo.filename)
                    
                    # Ruta absoluta
                    directorio_static = os.path.join(current_app.root_path, 'static')
                    carpeta_destino = os.path.join(directorio_static, 'img', 'donaciones')
                    
                    # Puntos de control (DEBUG)
                    print(f"DEBUG: Carpeta destino verificada: {carpeta_destino}")
                    print(f"DEBUG: ¿Existe la carpeta?: {os.path.exists(carpeta_destino)}")
                    
                    if not os.path.exists(carpeta_destino):
                        os.makedirs(carpeta_destino, exist_ok=True)
                        
                    ruta_destino = os.path.join(carpeta_destino, nombre_foto)
                    
                    print(f"DEBUG: Intentando guardar en: {ruta_destino}")
                    print(f"DEBUG: Guardando en ruta absoluta: {os.path.abspath(ruta_destino)}")
                    
                    primer_archivo.save(ruta_destino)
                    
                    # ¡IMPORTANTE! Verificamos si realmente se creó el archivo
                    if os.path.exists(ruta_destino):
                        print("DEBUG: ¡ÉXITO! El archivo SÍ se creó físicamente.")
                    else:
                        print("DEBUG: ¡ERROR! El archivo NO aparece en el disco.")
                    
                    # Guardamos en BD solo el nombre del archivo
                    nombre_foto_bd = nombre_foto
                else:
                    nombre_foto_bd = None
            else:
                nombre_foto_bd = None
                
            if necesidad_prellenada:
                fundacion_id = necesidad_prellenada["fundacion_id"]
                exito = self.modelo.registrar_donacion_con_necesidad(
                    donador_id, fundacion_id, categoria_id, cantidad, descripcion, necesidad_prellenada["id"], nombre_foto_bd
                )
            else:
                fundacion_id = request.form.get("fundacion_id")
                if not fundacion_id:
                    flash("Debes seleccionar una fundación destino.", "danger")
                    categorias = self.modelo.obtener_categorias()
                    return render_template("donar.html", necesidad=necesidad_prellenada, categorias=categorias, fundaciones_activas=fundaciones_activas)
                exito = self.modelo.registrar_donacion(donador_id, fundacion_id, categoria_id, cantidad, descripcion, nombre_foto_bd)

            if exito:
                try:
                    if necesidad_prellenada and "id" in necesidad_prellenada:
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute("UPDATE necesidades SET estado = 'completada' WHERE id = %s", (necesidad_prellenada["id"],))
                        conn.commit()
                        conn.close()

                    import requests
                    datos_correo = {
                        "destinatario": session.get("correo", "usuario@ejemplo.com"),
                        "nombreFundacion": "Red Solidaria",
                        "estado": "DONACION_REGISTRADA"
                    }
                    requests.post("http://localhost:8080/api/email/enviar", json=datos_correo, timeout=3)
                except Exception as e:
                    print(f"⚠️ Error al finalizar el proceso: {e}")

                flash("🎉 ¡Gracias! Tu donación ha sido registrada exitosamente.", "success")
                return redirect(url_for("home_donador"))
            else:
                flash("❌ Hubo un problema al registrar tu donación.", "danger")

        categorias = self.modelo.obtener_categorias()
        return render_template("donar.html", necesidad=necesidad_prellenada, categorias=categorias, fundaciones_activas=fundaciones_activas)
    
    
    def home_donador_view(self, session, request):
        if "usuario_id" not in session:
            return redirect(url_for("login"))

        usuario_id = session["usuario_id"]

        # 1. Capturamos los filtros del formulario
        q = request.args.get('q')
        categoria = request.args.get('cat')
        estado = request.args.get('est')
        fundacion = request.args.get('fundacion')

        # 2. Obtenemos el historial FILTRADO
        historial = self.modelo.obtener_donaciones_por_usuario_filtrado(
            usuario_id, q=q, categoria=categoria, estado=estado, fundacion=fundacion
        )

        # 3. Obtenemos los contadores (asegúrate de que en el modelo este método use SQL COUNT)
        contadores = self.modelo.obtener_contadores_donaciones(usuario_id)

        # 4. Obtenemos el carrusel (Pasando usuario_id y los filtros opcionales q y cat)
        necesidades = self.modelo.obtener_necesidades_activas(usuario_id=usuario_id, q=q, cat=categoria)

        # 5. Categorías para el filtro
        categorias = self.modelo.obtener_categorias()

        return render_template("home_donador.html", 
                               historial=historial, 
                               categorias=categorias,
                               necesidades=necesidades,
                               contadores=contadores)
        
        
    def gestionar_donacion_accion(self):
        import requests
        if "usuario_id" not in session:
            return redirect(url_for("login"))

        donacion_id = request.form.get('donacion_id')
        accion = request.form.get('accion')
        
        usuario_id = session.get('usuario_id') 

        # Esto mapea la acción a una cadena de texto para actualizar la BD
        # 'eliminar' pasará a ser el estado 'eliminado' en la tabla, no borra el registro.
        nuevo_estado = {
            'aceptar': 'recibido',
            'rechazar': 'rechazado',
            'eliminar': 'eliminado'
        }.get(accion)

        if not nuevo_estado:
            flash("❌ Acción no válida", "danger")
            return redirect(url_for('home_fundacion'))

        # 1. Obtenemos datos ANTES de actualizar
        donacion_info = self.modelo.obtener_donacion_por_id(donacion_id)

        # 2. Actualizamos el estado (ESTO DEBE SER UN UPDATE EN TU MODELO, NO UN DELETE)
        exito = self.modelo.cambiar_estado_donacion(donacion_id, nuevo_estado)

        if exito:
            # ── Sincronización con la Solicitud de Ayuda ──
            try:
                if donacion_info and donacion_info.get('necesidad_id'):
                    nec_id = donacion_info['necesidad_id']
                    if accion == 'rechazar':
                        self.modelo.cambiar_estado_necesidad(nec_id, 'activa')
                    elif accion == 'aceptar':
                        self.modelo.cambiar_estado_necesidad(nec_id, 'completada')
            except Exception as e:
                print(f"⚠️ Error al sincronizar estado necesidad: {e}")

            # ── Notificaciones ──
            if accion in ['aceptar', 'rechazar'] and donacion_info:
                try:
                    datos_correo = {
                        "destinatario": donacion_info.get("donador_email", "admin@redsolidaria.com"),
                        "nombreFundacion": session.get("nombre", "Fundación"),
                        "estado": "RECIBIDO" if accion == "aceptar" else "RECHAZADO_DONACION"
                    }
                    requests.post("http://localhost:8080/api/email/enviar", json=datos_correo, timeout=5)
                except Exception as e:
                    print(f"Error notificación Java: {e}")
            
            flash(f"✅ Estado de la donación actualizado a: {nuevo_estado}", "success")
        else:
            flash("❌ No se pudo actualizar la donación", "danger")

        return redirect(url_for('home_fundacion'))
    # =========================================================================
    # NUEVO: ACCIÓN PARA RECHAZAR/OCULTAR UNA NECESIDAD DESDE EL DONANTE
    # =========================================================================
    def rechazar_necesidad_accion(self, necesidad_id, session):
        """Registra que un donador específico ocultó una necesidad de su vista"""
        usuario_id = session.get("usuario_id")
        
        # Llamamos al modelo para insertar en la tabla pivote de exclusión/rechazo
        exito = self.modelo.guardar_rechazo_necesidad(usuario_id, necesidad_id)
        
        if exito:
            flash("👁️ Solicitud ocultada. No volverá a aparecer en tu carrusel.", "info")
        else:
            flash("❌ No se pudo ocultar la solicitud.", "danger")
            
        return redirect(url_for("home_donador"))