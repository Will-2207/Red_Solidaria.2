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
        try:
            cursor = conn.cursor(dictionary=True)
            # MODIFICADO: Aseguramos la selección explícita de f.id, f.usuario_id y u.correo
            query = '''
                SELECT f.id, f.usuario_id, f.nombre, f.nit, f.descripcion, f.telefono, 
                       u.foto_perfil, u.estado as estado_usuario, f.estado_validacion,
                       u.nombre AS usuario_encargado, u.correo
                FROM fundaciones f
                JOIN usuarios u ON f.usuario_id = u.id
                WHERE f.usuario_id = %s
            '''
            cursor.execute(query, (usuario_id,))
            resultado = cursor.fetchone()
            
            if resultado:
                print(f"DEBUG: Fundación encontrada: {resultado['nombre']} con ID Interno: {resultado['id']}")
                return resultado
            
            return None
                
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

    def actualizar_perfil_fundacion(self, usuario_id, nombre_fundacion, nombre_encargado, telefono, foto_perfil=None, rol=3):
        conn = get_connection()
        print(f"DEBUG: Intentando administrar cuenta para usuario_id: {usuario_id} con Rol: {rol}")
        try:
            cursor = conn.cursor()
            
            # 1. ACTUALIZAR TABLA GENERAL USUARIOS
            # Si es Fundación (rol 3), guardamos el nombre del ENCARGADO en la cuenta de usuario general
            nombre_a_guardar = nombre_encargado if int(rol) == 3 else nombre_fundacion

            if foto_perfil:
                query_usr = "UPDATE usuarios SET nombre = %s, telefono = %s, foto_perfil = %s WHERE id = %s"
                cursor.execute(query_usr, (nombre_a_guardar, telefono, foto_perfil, usuario_id))
            else:
                query_usr = "UPDATE usuarios SET nombre = %s, telefono = %s WHERE id = %s"
                cursor.execute(query_usr, (nombre_a_guardar, telefono, usuario_id))

            # 2. ACTUALIZAR TABLA ESPECÍFICA DE FUNDACIONES (Solo si es Rol 3)
            # Corregido: Quitamos 'usuario_encargado' porque no existe en la estructura de tu tabla fundaciones
            if int(rol) == 3:
                query_fun = "UPDATE fundaciones SET nombre = %s, telefono = %s WHERE usuario_id = %s"
                cursor.execute(query_fun, (nombre_fundacion, telefono, usuario_id))

            conn.commit()
            print("DEBUG: Datos de perfil sincronizados en la Base de Datos con éxito.")
            return True
        except Exception as e:
            if conn: conn.rollback()
            print(f"ERROR en actualizar_perfil_fundacion: {e}")
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
                
    
                
    def obtener_motivos_eliminacion(self):
        return {
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
            "info_falsa":    "Información de contacto falsa o no verificable."
        }            