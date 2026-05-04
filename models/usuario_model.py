from database.db import get_connection
import mysql.connector

class Usuario:
    def __init__(self, id, nombre, correo, password, rol_id, estado, fecha_registro, tipo_solicitud=None, foto_perfil=None, telefono=None):
        self.id = id
        self.nombre = nombre
        self.correo = correo
        self.password = password
        self.rol_id = rol_id
        self.estado = estado
        self.fecha_registro = fecha_registro
        self.tipo_solicitud = tipo_solicitud
        self.foto_perfil = foto_perfil
        self.telefono = telefono

class UsuarioModel:

    def crear_usuario(self, usuario):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            rol_id_int = int(usuario.rol_id)
            estado = 'pendiente' if rol_id_int == 3 else 'aprobado'
            print(f"DEBUG: Intentando registrar usuario {usuario.correo} con estado {estado}")
            query = """
                INSERT INTO usuarios (nombre, correo, password, rol_id, estado, fecha_registro)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """
            cursor.execute(query, (
                usuario.nombre,
                usuario.correo,
                usuario.password,
                usuario.rol_id,
                estado
            ))
            conn.commit()
            print("DEBUG: Usuario creado con éxito en la base de datos")
            return True
        except Exception as e:
            print(f"ERROR en crear_usuario: {e}")
            return False
        finally:
            if conn:
                conn.close()
                print("DEBUG: Conexión cerrada en crear_usuario")

    def obtener_usuario_por_correo(self, correo):
        conn = None
        try:
            conn = mysql.connector.connect(
                host='localhost',
                user='root',
                password='',
                database='donaciones_db',
                port=3307
            )
            cursor = conn.cursor(dictionary=True)
            sql = "SELECT * FROM usuarios WHERE correo = %s"
            cursor.execute(sql, (correo,))
            usuario = cursor.fetchone()
            return usuario
        except Exception as e:
            print(f"ERROR CRÍTICO EN MODELO: {e}")
            return None
        finally:
            if conn and conn.is_connected():
                conn.close()

    def obtener_fundacion_por_usuario(self, usuario_id):
        conn = get_connection()
        print(f"DEBUG: Buscando fundación para usuario_id: {usuario_id}")
        try:
            cursor = conn.cursor(dictionary=True)
            query = '''
                SELECT f.*, u.estado as estado_usuario, f.estado_validacion, u.foto_perfil
                FROM fundaciones f
                JOIN usuarios u ON f.usuario_id = u.id
                WHERE f.usuario_id = %s
            '''
            cursor.execute(query, (usuario_id,))
            resultado = cursor.fetchone()
            if resultado:
                print(f"DEBUG: Fundación encontrada: {resultado['nombre']}")
            return resultado
        except Exception as e:
            print(f"ERROR en obtener_fundacion_por_usuario: {e}")
            return None
        finally:
            if conn:
                conn.close()
                print("DEBUG: Conexión cerrada en obtener_fundacion")

    def obtener_datos_aprobacion(self, fundacion_id):
        conn = get_connection()
        print(f"DEBUG: Buscando datos de correo para aprobación de fundacion_id: {fundacion_id}")
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT f.nombre, u.correo
                FROM fundaciones f
                JOIN usuarios u ON f.usuario_id = u.id
                WHERE f.id = %s
            """
            cursor.execute(query, (fundacion_id,))
            resultado = cursor.fetchone()
            if resultado:
                print(f"DEBUG: Datos de contacto obtenidos: {resultado['correo']}")
            return resultado
        except Exception as e:
            print(f"ERROR en obtener_datos_aprobacion: {e}")
            return None
        finally:
            if conn:
                conn.close()
                print("DEBUG: Conexión cerrada en obtener_datos_aprobacion")

    def obtener_donantes(self):
        conn = get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM usuarios WHERE rol_id=2")
            return cursor.fetchall()
        finally:
            conn.close()

    def obtener_fundaciones_pendientes(self):
        conn = get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM usuarios WHERE rol_id=3 AND estado='pendiente'")
            return cursor.fetchall()
        finally:
            conn.close()

    def obtener_fundaciones_aprobadas(self):
        conn = get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM usuarios WHERE rol_id=3 AND estado='aprobado'")
            return cursor.fetchall()
        finally:
            conn.close()

    def obtener_fundaciones_rechazadas(self):
        conn = get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM usuarios WHERE rol_id=3 AND estado='rechazado'")
            return cursor.fetchall()
        finally:
            conn.close()

    def actualizar_perfil(self, usuario_id, nombre, telefono, foto_perfil=None):
        conn = get_connection()
        print(f"DEBUG: Intentando actualizar perfil para usuario_id: {usuario_id}")
        try:
            cursor = conn.cursor()
            if foto_perfil:
                query = "UPDATE usuarios SET nombre = %s, telefono = %s, foto_perfil = %s WHERE id = %s"
                cursor.execute(query, (nombre, telefono, foto_perfil, usuario_id))
            else:
                query = "UPDATE usuarios SET nombre = %s, telefono = %s WHERE id = %s"
                cursor.execute(query, (nombre, telefono, usuario_id))
            conn.commit()
            print("DEBUG: Perfil actualizado correctamente")
            return True
        except Exception as e:
            print(f"ERROR en actualizar_perfil: {e}")
            return False
        finally:
            if conn:
                conn.close()

    # ──────────────────────────────────────────────────────────
    # NUEVO MÉTODO — trae fundaciones aprobadas con descripción
    # Usado en donar.html para mostrar la descripción al elegir
    # ──────────────────────────────────────────────────────────
    def obtener_fundaciones_activas_con_descripcion(self):
        """
        Devuelve todas las fundaciones aprobadas con su id, nombre
        y descripción para mostrar en el select de donar.html.
        """
        conn = get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT
                    f.id,
                    f.nombre,
                    COALESCE(f.descripcion, '') AS descripcion
                FROM fundaciones f
                INNER JOIN usuarios u ON f.usuario_id = u.id
                WHERE f.estado_validacion = 'aprobado'
                  AND u.estado = 'aprobado'
                ORDER BY f.nombre ASC
            """
            cursor.execute(query)
            return cursor.fetchall()
        except Exception as e:
            print(f"ERROR en obtener_fundaciones_activas_con_descripcion: {e}")
            return []
        finally:
            if conn:
                conn.close()