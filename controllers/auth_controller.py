from models.usuario_model import UsuarioModel

# Instancia global del modelo para uso en el controlador
modelo = UsuarioModel()

class AuthController:

    def login(self, correo, password):
        usuario = modelo.obtener_usuario_por_correo(correo)

        if not usuario:
            return None, "Usuario no existe"

        if usuario['password'] != password:
            return None, "Contraseña incorrecta"

        estado = usuario['estado'].lower()
        if estado not in ["activo", "aprobado", "pendiente"]:
            return None, "Cuenta no autorizada"

        return usuario, None

    def login_view(self):
        from flask import request, session, redirect, url_for, render_template, flash

        if request.method == "POST":
            correo   = request.form["correo"]
            password = request.form["password"]

            usuario, error = self.login(correo, password)

            if error:
                flash(error, "danger")
                return render_template("login.html")

            # ── ASIGNACIÓN DE SESIÓN BASE ──
            session["usuario_id"] = usuario['id']
            session["rol"]        = int(usuario['rol_id'])
            session["correo"]     = usuario.get('correo', '')
            session["telefono"]   = usuario.get('telefono')

            # Foto de perfil base (puede ser None)
            foto = usuario.get('foto_perfil')
            session["foto_perfil"] = foto if foto else ''

            # Nombre base desde tabla usuarios
            session["nombre"] = usuario.get('nombre_usuario', usuario.get('nombre', ''))

            rol_id = int(usuario['rol_id'])

            # ── Si es FUNDACIÓN, cargar nombre y foto reales desde tabla fundaciones ──
            if rol_id == 3:
                try:
                    modelo_u  = UsuarioModel()
                    fundacion = modelo_u.obtener_fundacion_por_usuario(usuario['id'])
                    print(f"DEBUG FUNDACION EN LOGIN: {fundacion}")
                    if fundacion:
                        if fundacion.get('nombre'):
                            session['nombre'] = fundacion['nombre']
                        if fundacion.get('foto_perfil'):
                            session['foto_perfil'] = fundacion['foto_perfil']
                        if fundacion.get('telefono'):
                            session['telefono'] = fundacion['telefono']
                except Exception as e:
                    print(f"⚠️ Error al cargar datos de fundación en login: {e}")

            print(f"DEBUG: Sesión creada para usuario: {session['nombre']} con Rol: {rol_id}")

            if rol_id == 3:
                return redirect(url_for("home_fundacion"))
            elif rol_id == 2:
                return redirect(url_for("home_donador"))
            elif rol_id == 1:
                return redirect(url_for("home_administrador"))

        return render_template("login.html")

# Fin del controlador de autenticación - Red Solidaria