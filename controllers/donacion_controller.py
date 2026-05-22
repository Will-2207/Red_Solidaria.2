from flask import render_template, redirect, url_for, flash, request, session
from models.donacion_model import DonacionModel

class DonacionController:
    def __init__(self, modelo=None):
        self.modelo = modelo if modelo else DonacionModel()

    def cambiar_estado(self, donacion_id, accion):
        if "usuario_id" not in session:
            return redirect(url_for("login"))
        
        # Mapeo de la acción al ENUM de tu base de datos
        estado_db = 'recibido' if accion == 'aceptar' else 'rechazado'
        
        exito = self.modelo.actualizar_estado_donacion(donacion_id, estado_db)
        
        if exito:
            flash(f"✅ La donación ha sido marcada como {estado_db}", "success")
        else:
            flash("❌ No se pudo actualizar el estado de la donación", "danger")
            
        return redirect(url_for("home_fundacion"))

    def eliminar(self, donacion_id):
        if "usuario_id" not in session:
            return redirect(url_for("login"))
            
        # Llamamos a la función de eliminación lógica
        exito = self.modelo.eliminar_donacion_logica(donacion_id)
        
        if exito:
            flash("🗑️ Donación marcada como 'eliminada' (permanece en reportes)", "info")
        else:
            flash("❌ Error al procesar la eliminación", "danger")
            
        return redirect(url_for("home_fundacion"))

    
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
                flash("❌ No se realizaron cambios o hubo un error al actualizar.", "warning")
                return redirect(url_for('home_fundacion'))

        categorias = self.modelo.obtener_categorias()
        # Cambia 'editar_necesidad.html' por 'solicitar_ayuda.html'
        return render_template('solicitar_ayuda.html', necesidad=necesidad, categories=categorias)

    def eliminar_necesidad_accion(self, necesidad_id, session):
        """Aplica el borrado lógico cambiándole el estado a 'eliminado'"""
        exito = self.modelo.cambiar_estado_necesidad(necesidad_id, 'eliminado')
        if exito:
            flash("🗑️ Solicitud de ayuda eliminada del panel.", "info")
        else:
            flash("❌ No se pudo eliminar la solicitud de ayuda.", "danger")
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

        # Obtener fundaciones activas
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

            if necesidad_prellenada:
                fundacion_ids = [str(necesidad_prellenada["fundacion_id"])]
            else:
                fundacion_id = request.form.get("fundacion_id")
                fundacion_ids = [fundacion_id] if fundacion_id else []
                if not fundacion_ids or not fundacion_ids[0]:
                    flash("Debes seleccionar una fundación destino.", "danger")
                    categorias = self.modelo.obtener_categorias()
                    return render_template("donar.html", necesidad=necesidad_prellenada, categorias=categorias, fundaciones_activas=fundaciones_activas)

            exito = self.modelo.registrar_donacion(
                donador_id,
                fundacion_ids,
                categoria_id,
                cantidad,
                descripcion
            )

            if exito:
                flash("🎉 ¡Gracias! Tu donación ha sido registrada.", "success")
                return redirect(url_for("home_donador"))
            else:
                flash("❌ Hubo un problemar al registrar tu donación.", "danger")

        categorias = self.modelo.obtener_categorias()
        return render_template("donar.html", necesidad=necesidad_prellenada, categorias=categorias, fundaciones_activas=fundaciones_activas)


    def home_donador_view(self, session, request):
        if "usuario_id" not in session:
            return redirect(url_for("login"))

        usuario_id = session["usuario_id"]

        q = request.args.get('q')
        categoria = request.args.get('categoria')
        estado = request.args.get('estado')
        fundacion = request.args.get('fundacion')

        historial = self.modelo.obtener_donaciones_por_usuario_filtrado(
            usuario_id, q=q, Lazy_loading=False, categoria=categoria, estado=estado, fundacion=fundacion
        )

        categorias = self.modelo.obtener_categorias()

        return render_template("home_donador.html", 
                               historial=historial, 
                               categorias=categorias) 
        
    def gestionar_donacion_accion(self):
        import requests
        if "usuario_id" not in session:
            return redirect(url_for("login"))

        donacion_id = request.form.get('donacion_id')
        accion = request.form.get('accion')
        fundacion_id = session.get('usuario_id') 

        nuevo_estado = {
            'aceptar': 'recibido',
            'rechazar': 'rechazado',
            'eliminar': 'eliminado'
        }.get(accion)

        if not nuevo_estado:
            flash("❌ Acción no válida", "danger")
            return redirect(url_for('home_fundacion'))

        exito = self.modelo.actualizar_estado_donacion(donacion_id, nuevo_estado, fundacion_id)

        if exito:
            if accion in ['aceptar', 'rechazar']:
                try:
                    datos_correo = {
                        "destinatario": session.get("email", "admin@redsolidaria.com"),
                        "nombreFundacion": session.get("nombre", "Fundación"),
                        "estado": "RECIBIDO" if accion == "aceptar" else "RECHAZADO_DONACION"
                    }
                    requests.post("http://localhost:8080/api/email/enviar", json=datos_correo, timeout=5)
                except Exception as e:
                    print(f"Error notificación Java: {e}")
            
            flash(f"✅ Donación marcada como {nuevo_estado}", "success")
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