from database.db import get_connection
from flask import current_app
import mysql.connector
from mysql.connector import Error


class HomeAdminModel:

    # ──────────────────────────────────────────────
    # FUNDACIONES
    # ──────────────────────────────────────────────

    @classmethod
    def obtener_fundaciones_pendientes(cls):
        query = """
            SELECT f.id, f.nombre, f.nit, u.correo,
                   u.fecha_registro, f.estado_validacion, u.estado
            FROM fundaciones f
            INNER JOIN usuarios u ON f.usuario_id = u.id
            WHERE f.estado_validacion = 'pendiente'
            ORDER BY u.fecha_registro DESC
        """
        connection = get_connection()
        try:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(query)
                return cursor.fetchall()
        except Exception as ex:
            print(f"Error en obtener_fundaciones_pendientes: {ex}")
            return []
        finally:
            if connection:
                connection.close()

    @classmethod
    def obtener_fundaciones_aprobadas(cls):
        query = """
            SELECT f.id, f.nombre, f.nit, u.correo,
                   u.fecha_registro, f.estado_validacion, u.estado
            FROM fundaciones f
            INNER JOIN usuarios u ON f.usuario_id = u.id
            WHERE f.estado_validacion = 'aprobado'
            ORDER BY u.fecha_registro DESC
        """
        connection = get_connection()
        try:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(query)
                return cursor.fetchall()
        except Exception as ex:
            print(f"Error en obtener_fundaciones_aprobadas: {ex}")
            return []
        finally:
            if connection:
                connection.close()

    @classmethod
    def obtener_fundaciones_rechazadas(cls):
        query = """
            SELECT f.id, f.nombre, f.nit, u.correo,
                   u.fecha_registro, f.estado_validacion, u.estado
            FROM fundaciones f
            INNER JOIN usuarios u ON f.usuario_id = u.id
            WHERE f.estado_validacion = 'rechazado'
            ORDER BY u.fecha_registro DESC
        """
        connection = get_connection()
        try:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(query)
                return cursor.fetchall()
        except Exception as ex:
            print(f"Error en obtener_fundaciones_rechazadas: {ex}")
            return []
        finally:
            if connection:
                connection.close()

    @classmethod
    def aprobar_fundacion(cls, fundacion_id):
        connection = get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT usuario_id FROM fundaciones WHERE id = %s", (fundacion_id,))
                resultado = cursor.fetchone()
                if not resultado:
                    return False
                usuario_id = resultado[0]
                cursor.execute("UPDATE usuarios SET estado = 'aprobado' WHERE id = %s", (usuario_id,))
                cursor.execute("UPDATE fundaciones SET estado_validacion = 'aprobado' WHERE id = %s", (fundacion_id,))
                connection.commit()
                return True
        except Exception as ex:
            print(f"Error en aprobar_fundacion: {ex}")
            return False
        finally:
            if connection:
                connection.close()

    @classmethod
    def rechazar_fundacion(cls, fundacion_id):
        connection = get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT usuario_id FROM fundaciones WHERE id = %s", (fundacion_id,))
                resultado = cursor.fetchone()
                if not resultado:
                    return False
                usuario_id = resultado[0]
                cursor.execute("UPDATE usuarios SET estado = 'rechazado' WHERE id = %s", (usuario_id,))
                cursor.execute("UPDATE fundaciones SET estado_validacion = 'rechazado' WHERE id = %s", (fundacion_id,))
                connection.commit()
                return True
        except Exception as ex:
            print(f"Error en rechazar_fundacion: {ex}")
            return False
        finally:
            if connection:
                connection.close()

    # ── NUEVO: ELIMINAR FUNDACIÓN ──────────────────
    @classmethod
    def eliminar_fundacion(cls, fundacion_id):
        """
        Marca la fundación como 'eliminado' en estado_validacion
        y el usuario como 'eliminado' en estado.
        No borra físicamente el registro.
        """
        connection = get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT usuario_id FROM fundaciones WHERE id = %s", (fundacion_id,))
                resultado = cursor.fetchone()
                if not resultado:
                    return False
                usuario_id = resultado[0]
                cursor.execute(
                    "UPDATE usuarios SET estado = 'eliminado' WHERE id = %s",
                    (usuario_id,)
                )
                cursor.execute(
                    "UPDATE fundaciones SET estado_validacion = 'eliminado' WHERE id = %s",
                    (fundacion_id,)
                )
                connection.commit()
                return True
        except Exception as ex:
            print(f"Error en eliminar_fundacion: {ex}")
            return False
        finally:
            if connection:
                connection.close()

    @classmethod
    def contar_pendientes(cls):
        connection = get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM fundaciones WHERE estado_validacion = 'pendiente'")
                resultado = cursor.fetchone()
                return resultado[0] if resultado else 0
        except Exception as ex:
            print(f"Error en contar_pendientes: {ex}")
            return 0
        finally:
            if connection:
                connection.close()

    # ──────────────────────────────────────────────
    # DONANTES
    # ──────────────────────────────────────────────

    @classmethod
    def obtener_donantes_activos(cls):
        query = """
            SELECT id, nombre, correo, fecha_registro, estado
            FROM usuarios
            WHERE rol_id = 2 AND estado = 'aprobado'
            ORDER BY fecha_registro DESC
        """
        connection = get_connection()
        try:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(query)
                return cursor.fetchall()
        except Exception as ex:
            print(f"Error en obtener_donantes_activos: {ex}")
            return []
        finally:
            if connection:
                connection.close()
                
    # ── NUEVO: ELIMINADO ──────────────────────────────
    @classmethod
    def eliminar_donante(cls, usuario_id):
        """
        Cambia el estado del donante a 'eliminado' en lugar de borrarlo físicamente.
        Retorna (bool exito, str nombre, str correo) para la notificación.
        """
        connection = get_connection()
        nombre, correo = None, None
        try:
            with connection.cursor(dictionary=True) as cursor:
                # 1. Obtener datos antes de actualizar para la notificación por correo
                cursor.execute("SELECT nombre, correo FROM usuarios WHERE id = %s AND rol_id = 2", (usuario_id,))
                usuario = cursor.fetchone()
                
                if not usuario:
                    return False, None, None
                
                nombre = usuario['nombre']
                correo = usuario['correo']

                # 2. Actualización lógica
                cursor.execute("UPDATE usuarios SET estado = 'eliminado' WHERE id = %s", (usuario_id,))
                
                connection.commit()
                return True, nombre, correo

        except Exception as ex:
            print(f"Error en eliminar_donante (Model): {ex}")
            if connection: 
                connection.rollback()
            return False, None, None
        finally:
            if connection: 
                connection.close()
   # ──────────────────────────────────────────────
    # DONACIONES FÍSICAS
    # ──────────────────────────────────────────────

    @classmethod
    def obtener_todas_donaciones(cls):
        query = """
            SELECT 
                d.id, 
                u_don.nombre AS donador_nombre, 
                COALESCE(f.nombre, 'Sin asignar') AS fundacion_nombre, 
                c.nombre AS categoria_nombre, 
                d.descripcion, 
                d.cantidad, 
                d.fecha,
                d.estado_donante AS estado
            FROM donaciones d
            INNER JOIN usuarios u_don ON d.usuario_id = u_don.id
            LEFT JOIN categorias c ON d.categoria_id = c.id
            /* Unimos directamente usando la columna fundacion_id de la tabla donaciones */
            LEFT JOIN fundaciones f ON d.fundacion_id = f.id
            ORDER BY d.fecha DESC
        """
        connection = get_connection()
        try:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(query)
                return cursor.fetchall()
        except Exception as ex:
            print(f"Error en obtener_todas_donaciones: {ex}")
            return []
        finally:
            if connection:
                connection.close()
    # ──────────────────────────────────────────────
    # REPORTE MULTICRITERIO
    # ──────────────────────────────────────────────

    @classmethod
    def buscar_reporte_admin(cls,
                             donante=None, fundacion=None, categoria=None,
                             estado=None, fecha_desde=None, fecha_hasta=None,
                             monto_min=None, monto_max=None, pasarela=None):
        connection = get_connection()
        try:
            with connection.cursor(dictionary=True) as cursor:

                # ── DONACIONES ──
                # Se usa d.estado_donante para evitar el error 'Unknown column'
                sql_don = """
                    SELECT d.id, u_don.nombre AS donador_nombre, u_don.correo AS donador_correo,
                           f_nom.nombre AS fundacion_nombre, c.nombre AS categoria_nombre,
                           d.descripcion, d.cantidad, d.fecha,
                           COALESCE(df.estado, d.estado_donante) AS estado
                    FROM donaciones d
                    INNER JOIN usuarios u_don ON d.usuario_id    = u_don.id
                    LEFT  JOIN categorias c   ON d.categoria_id  = c.id
                    LEFT  JOIN donaciones_fundaciones df ON d.id  = df.donacion_id
                    LEFT  JOIN fundaciones fun           ON df.fundacion_id = fun.id
                    LEFT  JOIN usuarios f_nom            ON fun.usuario_id  = f_nom.id
                    WHERE 1=1
                """
                params_don = []
                if donante:
                    sql_don += " AND u_don.nombre LIKE %s"; params_don.append(f"%{donante}%")
                if fundacion:
                    sql_don += " AND f_nom.nombre LIKE %s"; params_don.append(f"%{fundacion}%")
                if categoria:
                    sql_don += " AND c.nombre = %s"; params_don.append(categoria)
                if estado:
                    sql_don += " AND COALESCE(df.estado, d.estado_donante) = %s"; params_don.append(estado)
                if fecha_desde:
                    sql_don += " AND DATE(d.fecha) >= %s"; params_don.append(fecha_desde)
                if fecha_hasta:
                    sql_don += " AND DATE(d.fecha) <= %s"; params_don.append(fecha_hasta)
                
                sql_don += " ORDER BY d.fecha DESC"
                cursor.execute(sql_don, tuple(params_don))
                donaciones = cursor.fetchall()

                # ── FUNDACIONES ──
                sql_fun = """
                    SELECT f.id, f.nombre, f.nit, u.correo, u.fecha_registro, f.estado_validacion
                    FROM fundaciones f
                    INNER JOIN usuarios u ON f.usuario_id = u.id
                    WHERE 1=1
                """
                params_fun = []
                if fundacion:
                    sql_fun += " AND f.nombre LIKE %s"; params_fun.append(f"%{fundacion}%")
                if estado:
                    sql_fun += " AND f.estado_validacion = %s"; params_fun.append(estado)
                sql_fun += " ORDER BY u.fecha_registro DESC"
                cursor.execute(sql_fun, tuple(params_fun))
                fundaciones = cursor.fetchall()

                # ── DONANTES ──
                sql_donan = "SELECT id, nombre, correo, fecha_registro, estado FROM usuarios WHERE rol_id = 2"
                params_donan = []
                if donante:
                    sql_donan += " AND nombre LIKE %s"; params_donan.append(f"%{donante}%")
                if estado:
                    sql_donan += " AND estado = %s"; params_donan.append(estado)
                sql_donan += " ORDER BY fecha_registro DESC"
                cursor.execute(sql_donan, tuple(params_donan))
                donantes = cursor.fetchall()

                return {
                    "donaciones":  donaciones,
                    "fundaciones": fundaciones,
                    "donantes":    donantes,
                    "totales": {
                        "total_donaciones":  len(donaciones),
                        "total_fundaciones": len(fundaciones),
                        "total_donantes":    len(donantes),
                    }
                }
        except Exception as ex:
            print(f"Error en buscar_reporte_admin: {ex}")
            return {"donaciones": [], "fundaciones": [], "donantes": [], "totales": {
                "total_donaciones": 0, "total_fundaciones": 0, "total_donantes": 0
            }}
        finally:
            if connection:
                connection.close()

    # ──────────────────────────────────────────────
    # UTILIDADES
    # ──────────────────────────────────────────────

    @classmethod
    def registrar_fundacion_completo(cls, nombre, correo, password, rol_id, nit, organizacion):
        connection = get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO usuarios (nombre, correo, password, rol_id, estado, fecha_registro) VALUES (%s,%s,%s,%s,'pendiente',NOW())",
                    (nombre, correo, password, rol_id)
                )
                nuevo_usuario_id = cursor.lastrowid
                cursor.execute(
                    "INSERT INTO fundaciones (usuario_id, nombre, nit, estado_validacion) VALUES (%s,%s,%s,'pendiente')",
                    (nuevo_usuario_id, organizacion, nit)
                )
                connection.commit()
                return True
        except Exception as ex:
            print(f"Error en registrar_fundacion_completo: {ex}")
            return False
        finally:
            if connection:
                connection.close()

    @classmethod
    def obtener_datos_fundacion(cls, id_usuario):
        connection = get_connection()
        try:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(
                    "SELECT u.correo, f.nombre FROM usuarios u JOIN fundaciones f ON u.id = f.usuario_id WHERE u.id = %s",
                    (id_usuario,)
                )
                return cursor.fetchone()
        except Exception as ex:
            print(f"Error en obtener_datos_fundacion: {ex}")
            return None
        finally:
            if connection:
                connection.close()
                
class ReporteAdminModel:                
                
    @staticmethod
    def obtener_conexion():
        try:
            import mysql.connector
            return mysql.connector.connect(
                host='localhost',
                user='root',
                password='',
                database='red_solidaria'
            )
        except Exception as e:
            print(f"Error al conectar en ReporteAdminModel: {e}")
            return None
        
    @staticmethod
    def obtener_datos_reporte(filtros):
        """
        Obtiene datos de donaciones, fundaciones y donantes aplicando 
        filtros multicriterio dinámicos.
        """
        conexion = ReporteAdminModel.obtener_conexion()
        if not conexion:
            return {"donaciones": [], "fundaciones": [], "donantes": [], "totales": {}}

        cursor = conexion.cursor(dictionary=True)
        
        try:
            # --- 1. CONSULTA DE DONACIONES ---
            sql_don = """
                SELECT d.*, u.nombre as donador_nombre, f.nombre as fundacion_nombre, c.nombre as categoria_nombre 
                FROM donaciones d
                LEFT JOIN usuarios u ON d.id_usuario = u.id_usuario
                LEFT JOIN fundaciones f ON d.id_fundacion = f.id_fundacion
                LEFT JOIN categorias c ON d.id_categoria = c.id_categoria
                WHERE 1=1
            """
            params_don = []
            if filtros.get('donante'):
                sql_don += " AND u.nombre LIKE %s"
                params_don.append(f"%{filtros['donante']}%")
            if filtros.get('fundacion'):
                sql_don += " AND f.nombre LIKE %s"
                params_don.append(f"%{filtros['fundacion']}%")
            if filtros.get('categoria'):
                sql_don += " AND c.nombre = %s"
                params_don.append(filtros['categoria'])
            if filtros.get('estado'):
                sql_don += " AND d.estado = %s"
                params_don.append(filtros['estado'])
            if filtros.get('fecha_desde'):
                sql_don += " AND d.fecha >= %s"
                params_don.append(filtros['fecha_desde'])
            if filtros.get('fecha_hasta'):
                sql_don += " AND d.fecha <= %s"
                params_don.append(filtros['fecha_hasta'])
            if filtros.get('monto_min'):
                sql_don += " AND d.cantidad >= %s" # O monto si aplica
                params_don.append(filtros['monto_min'])

            cursor.execute(sql_don, params_don)
            donaciones = cursor.fetchall()

            # --- 2. CONSULTA DE FUNDACIONES ---
            sql_fun = "SELECT * FROM fundaciones WHERE 1=1"
            params_fun = []
            if filtros.get('fundacion'):
                sql_fun += " AND nombre LIKE %s"
                params_fun.append(f"%{filtros['fundacion']}%")
            if filtros.get('estado'):
                # Filtro cruzado de estado para fundaciones (aprobado/rechazado)
                sql_fun += " AND estado_validacion = %s"
                params_fun.append(filtros['estado'])
            
            cursor.execute(sql_fun, params_fun)
            fundaciones = cursor.fetchall()

            # --- 3. CONSULTA DE DONANTES (Usuarios) ---
            sql_usr = "SELECT id_usuario, nombre, correo, fecha_registro, estado FROM usuarios WHERE rol = 'donante'"
            params_usr = []
            if filtros.get('donante'):
                sql_usr += " AND nombre LIKE %s"
                params_usr.append(f"%{filtros['donante']}%")
            
            cursor.execute(sql_usr, params_usr)
            donantes = cursor.fetchall()

            # --- 4. CONSOLIDACIÓN DE RESULTADOS ---
            resultados = {
                "donaciones": donaciones,
                "fundaciones": fundaciones,
                "donantes": donantes,
                "totales": {
                    "total_donaciones": len(donaciones),
                    "total_fundaciones": len(fundaciones),
                    "total_donantes": len(donantes)
                }
            }
            return resultados

        except Error as e:
            print(f"Error en la consulta: {e}")
            return {"donaciones": [], "fundaciones": [], "donantes": [], "totales": {}}
        finally:
            cursor.close()
            conexion.close()
   

    @classmethod
    def crear_fundacion(cls, usuario_id, nombre, nit, direccion):
        connection = get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO fundaciones (usuario_id, nombre, nit, direccion, estado_validacion) VALUES (%s,%s,%s,%s,'pendiente')",
                    (usuario_id, nombre, nit, direccion)
                )
                connection.commit()
                return True
        except Exception as ex:
            print(f"Error en crear_fundacion: {ex}")
            return False
        finally:
            if connection:
                connection.close()