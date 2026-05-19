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

    
    # --- MÉTODO PARA QUE LA FUNDACIÓN SOLICITE AYUDA (NECESIDADES) ---
    # --- MÉTODO PARA QUE LA FUNDACIÓN SOLICITE AYUDA (NECESIDADES) ---
    def solicitar_ayuda_view(self, session):
        # Primero obtenemos el ID interno de la fundación desde la sesión
        from models.usuario_model import UsuarioModel
        user_model = UsuarioModel()
        fundacion = user_model.obtener_fundacion_por_usuario(session.get('usuario_id'))
        
        if not fundacion:
            return "Error: No se encontró la fundación asociada a este usuario."
            
        fundacion_id = fundacion['id']

        if request.method == 'POST':
            categoria_texto = request.form.get('categoria')
            cantidad = request.form.get('cantidad')
            urgencia = request.form.get('urgencia')
            fecha_limite = request.form.get('fecha_limite')
            ubicacion = request.form.get('ubicacion')
            telefono = request.form.get('telefono')
            descripcion = request.form.get('descripcion')
            fecha_vencimiento = request.form.get('fecha_vencimiento')

            # Mapeo de Categorías
            mapeo_categorias = {
                "Alimentos": 1,
                "Ropa": 2,
                "Higiene": 3,
                "Educación": 4,
                "Mobiliario": 5,
                "Otros": 6
            }
            categoria_id = mapeo_categorias.get(categoria_texto, 6)

            if not fecha_limite: fecha_limite = None
            if not fecha_vencimiento: fecha_vencimiento = None

            # Instancia e inserción limpia
            from models.donacion_model import DonacionModel
            modelo_donacion_local = DonacionModel()

            exito = modelo_donacion_local.crear_necesidad(
                fundacion_id=fundacion_id, 
                categoria_id=categoria_id,
                cantidad=cantidad,
                urgencia=urgencia,
                fecha_limite=fecha_limite,
                ubicacion=ubicacion,
                telefono=telefono,
                descripcion=descripcion,
                fecha_vencimiento=fecha_vencimiento
            )

            if exito:
                return redirect(url_for('home_fundacion'))
            else:
                return render_template('solicitar_ayuda.html', error="No se pudo registrar la solicitud")

        # Si es GET, renderiza la vista pasando las categorías si las necesitas
        categorias = modelo_donacion_local.obtener_categorias() if 'modelo_donacion_local' in locals() else []
        return render_template('solicitar_ayuda.html', categorias=categorias)

    # --- MÉTODO PARA QUE EL DONADOR PUBLIQUE UNA DONACIÓN ---
    def publicar_donacion_view(self, request, session, necesidad_id=None):
        from models.donacion_model import DonacionModel
        
        # 1. Seguridad: El usuario debe estar logueado
        if "usuario_id" not in session:
            return redirect(url_for("login"))
            
        modelo = DonacionModel()
        necesidad_prellenada = None

        # 2. Si viene desde una necesidad específica en el muro, traemos los datos
        if necesidad_id:
            necesidad_prellenada = modelo.obtener_necesidad_por_id(necesidad_id)

        # Obtener fundaciones activas (usuarios con estado aprobado y rol fundación)
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
                # Donación a una sola fundación (por necesidad)
                fundacion_ids = [str(necesidad_prellenada["fundacion_id"])]


            else:
                # Donación general: solo una fundación seleccionada
                fundacion_id = request.form.get("fundacion_id")
                print("DEBUG fundacion_id crudo:", fundacion_id, type(fundacion_id))
                fundacion_ids = [fundacion_id] if fundacion_id else []
                print("DEBUG fundacion_ids lista:", fundacion_ids)
                if not fundacion_ids or not fundacion_ids[0]:
                    flash("Debes seleccionar una fundación destino.", "danger")
                    categorias = modelo.obtener_categorias()
                    return render_template("donar.html", necesidad=necesidad_prellenada, categorias=categorias, fundaciones_activas=fundaciones_activas)

            exito = modelo.registrar_donacion(
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
                flash("❌ Hubo un problema al registrar tu donación.", "danger")

        categorias = modelo.obtener_categorias()
        return render_template("donar.html", necesidad=necesidad_prellenada, categorias=categorias, fundaciones_activas=fundaciones_activas)

    # --- MÉTODO PARA CARGAR EL PANEL DEL DONADOR ---
    def home_donador_view(self, session, request):
        from models.donacion_model import DonacionModel
        
        if "usuario_id" not in session:
            return redirect(url_for("login"))

        usuario_id = session["usuario_id"]
        modelo = DonacionModel()

        # 1. Capturar filtros del buscador (si los hay)
        q = request.args.get('q')
        categoria = request.args.get('categoria')
        estado = request.args.get('estado')
        fundacion = request.args.get('fundacion')

        # 2. Llamar al método corregido que trae fundacion_nombre y estado_donante
        historial = modelo.obtener_donaciones_por_usuario_filtrado(
            usuario_id, q=q, categoria=categoria, estado=estado, fundacion=fundacion
        )

        # 3. Obtener categorías para el select del filtro
        categorias = modelo.obtener_categorias()

        return render_template("home_donador.html", 
                               historial=historial, 
                               categorias=categorias) 
        
    def gestionar_donacion_accion(self):
        import requests
        if "usuario_id" not in session:
            return redirect(url_for("login"))

        donacion_id = request.form.get('donacion_id')
        accion = request.form.get('accion')
        # Obtenemos el ID de la fundación de la sesión
        fundacion_id = session.get('usuario_id') 

        # Mapeo de acciones a estados de tu DB
        nuevo_estado = {
            'aceptar': 'recibido',
            'rechazar': 'rechazado',
            'eliminar': 'eliminado'
        }.get(accion)

        if not nuevo_estado:
            flash("❌ Acción no válida", "danger")
            return redirect(url_for('home_fundacion'))

        # Llamada al modelo con el nuevo parámetro fundacion_id
        exito = self.modelo.actualizar_estado_donacion(donacion_id, nuevo_estado, fundacion_id)

        if exito:
            # Notificación a Java solo si se acepta o rechaza
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
# Fin del Controlador DonacionController