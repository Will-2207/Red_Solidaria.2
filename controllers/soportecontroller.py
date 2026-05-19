from flask import render_template, request, redirect, url_for, session, jsonify
from flask_mail import Message
import uuid

class SoporteController:
    def __init__(self, modelo, mail):
        self.modelo = modelo
        self.mail = mail

    def listar_incidencias(self):
        if 'usuario_id' not in session:
            return redirect(url_for('login'))

        buscar_token = request.args.get('buscar_token', '')
        filtro_estado = request.args.get('filtro_estado', '')

        incidencias = self.modelo.obtener_incidencias(buscar_token, filtro_estado)
        abiertas, resueltas, total = self.modelo.obtener_estadisticas()

        return render_template('soporte_incidencias.html', 
                               incidencias=incidencias, 
                               incidencias_abiertas=abiertas, 
                               incidencias_resueltas=resueltas, 
                               total_incidencias=total)

    def registrar_incidencia(self):
        if 'usuario_id' not in session:
            return jsonify({'success': False, 'message': 'Sesión no activa'})
            
        token_uuid = str(uuid.uuid4())
        try:
            self.modelo.crear_incidencia(
                session['usuario_id'],
                token_uuid,
                request.form.get('categoria'),
                request.form.get('id_transaccion'),
                request.form.get('descripcion')
            )
            return jsonify({'success': True, 'token': token_uuid})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})

    # Esta es la función que carga el detalle del ticket
    def detalle_ticket(self, id):
        if 'usuario_id' not in session:
            return redirect(url_for('login'))
            
        ticket = self.modelo.obtener_ticket_por_id(id)
        # Importante: 'ticket' debe ser un diccionario gracias al DictCursor que pusimos antes
        return render_template('detalle_ticket.html', ticket=ticket)

    def procesar_resolucion(self, id):
        if 'usuario_id' not in session:
            return redirect(url_for('login'))
            
        respuesta_admin = request.form.get('respuesta')
        datos = self.modelo.obtener_ticket_por_id(id)

        if datos and self.mail:
            try:
                # MAPEO REAL DE LA TUPLA SEGÚN TU CONSOLA DIARIO DE DIAGNÓSTICO:
                token_seguimiento = datos[9]   # '502476d5-cce6-4179-967d-1d9cb0cdb757'
                nombre_representante = datos[10] # 'ronald morales r.'
                nombre_fundacion = datos[11] if datos[11] else "Usuario" # 'Fundacion pedacito de cielo'
                correo_destino = datos[12]     # 'cartuji7@gmail.com'

                msg = Message(f'Respuesta a tu Ticket #{token_seguimiento}',
                              recipients=[correo_destino])
                
                msg.html = render_template('email_soporte.html', 
                                           representante=nombre_representante,
                                           fundacion=nombre_fundacion, 
                                           respuesta=respuesta_admin, 
                                           token=token_seguimiento)

                # Adjuntamos el logo con la estructura de diccionario CORRECTA para Flask-Mail
                try:
                    from flask import current_app as app
                    with app.open_resource("static/img/logo.jpeg") as fp:
                        msg.attach(
                            "logo.jpeg", 
                            "image/jpeg", 
                            fp.read(), 
                            headers={'Content-ID': '<logoImage>'} # CORREGIDO: Cambiado de [] a {}
                        )
                except Exception as e:
                    print(f"Error con el logo: {e}")
                
                self.mail.send(msg)
                print(f"¡Excelente! Correo enviado con éxito a {correo_destino}")
            except Exception as e:
                print(f"Error enviando correo: {e}")
                
        self.modelo.resolver_ticket(id)
        return redirect(url_for('soporte_incidencias'))