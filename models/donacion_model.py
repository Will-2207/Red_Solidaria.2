from database.db import get_connection
import mysql.connector

class DonacionModel:

    # =========================================================================
    # MÉTODOS DE DONACIONES (HISTORIAL Y REGISTRO)
    # =========================================================================

    def registrar_donacion(self, donador_id, fundacion_id, categoria_id, cantidad, descripcion, fotos_str=None):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            c_id = int(categoria_id) if categoria_id else 0
            
            # INSERT directo: eliminamos la tabla intermedia y usamos tus columnas reales
            query = """
                INSERT INTO donaciones 
                (usuario_id, fundacion_id, categoria_id, cantidad, descripcion, estado_donante, fecha, fotos)
                VALUES (%s, %s, %s, %s, %s, 'pendiente', NOW(), %s)
            """
            cursor.execute(query, (donador_id, fundacion_id, c_id, cantidad, descripcion, fotos_str))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error CRÍTICO al registrar donación: {e}")
            return False
        finally:
            conn.close()
            
    def donaciones_por_usuario(self, usuario_id):
        """Historial para el Panel del Donador (Lista simple)"""
        conn = get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            # CORRECCIÓN: Cambiamos d.estado por d.estado_donante
            query = """
                SELECT d.id, c.nombre as categoria, d.descripcion,
                       d.cantidad, d.estado_donante, d.fecha, d.fotos
                FROM donaciones d
                LEFT JOIN categorias c ON d.categoria_id = c.id
                WHERE d.usuario_id = %s
                ORDER BY d.fecha DESC
            """
            cursor.execute(query, (usuario_id,))
            return cursor.fetchall()
        except Exception as e:
            print(f"Error en donaciones_por_usuario: {e}")
            return []
        finally:
            conn.close()

    def buscar_reporte_admin(self, filtros):
        """Método para el panel de administración que resuelve el error 1054"""
        conn = get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            # Usamos d.estado_donante para que coincida con tu base de datos
            query = """
                SELECT 
                    d.id, d.cantidad, d.fecha, d.descripcion,
                    u.nombre AS donante_nombre,
                    f.nombre AS fundacion_nombre,
                    c.nombre AS categoria_nombre,
                    d.estado_donante  -- CAMBIA 'd.estado' POR 'd.estado_donante'
                FROM donaciones d
                JOIN usuarios u ON d.usuario_id = u.id
                JOIN fundaciones f ON d.fundacion_id = f.id
                JOIN categorias c ON d.categoria_id = c.id
                WHERE 1=1
            """
            params = []

            if filtros.get('estado'):
                query += " AND d.estado_donante = %s"
                params.append(filtros.get('estado'))
            
            if filtros.get('donante'):
                query += " AND u.nombre LIKE %s"
                params.append(f"%{filtros.get('donante')}%")

            query += " ORDER BY d.fecha DESC"
            cursor.execute(query, tuple(params))
            return cursor.fetchall()
        except Exception as e:
            print(f"Error en buscar_reporte_admin: {e}")
            return []
        finally:
            conn.close()

    def obtener_donaciones_por_fundacion(self, fundacion_id, q='', categoria='', estado='', donante=''):
        from database.db import get_connection
        conn = get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            
            # 1. Base de la consulta con los alias correctos para los reportes
            query = """
                SELECT d.*, 
                       c.nombre as nombre_categoria, 
                       u.nombre as nombre_donante
                FROM donaciones d
                JOIN categorias c ON d.categoria_id = c.id
                JOIN usuarios u ON d.usuario_id = u.id
                WHERE d.fundacion_id = %s AND d.estado_donante != 'eliminado'
            """
            params = [fundacion_id]

            # 2. Filtro por búsqueda de texto (Descripción)
            if q:
                query += " AND d.descripcion LIKE %s"
                params.append(f"%{q}%")

            # 3. Filtro por categoría
            if categoria:
                query += " AND d.categoria_id = %s"
                params.append(categoria)

            # 4. Filtro por estado (Usando estado_donante para evitar el error 1054)
            if estado:
                query += " AND d.estado_donante = %s"
                params.append(estado)
            
            # 5. Filtro por nombre del donante
            if donante:
                query += " AND u.nombre LIKE %s"
                params.append(f"%{donante}%")

            query += " ORDER BY d.fecha DESC"

            cursor.execute(query, params)
            return cursor.fetchall()
            
        except Exception as e:
            print(f"❌ Error al obtener donaciones para fundación {fundacion_id}: {e}")
            return []
        finally:
            if conn:
                conn.close()
                
    def obtener_donaciones_por_usuario_filtrado(self, usuario_id, q=None, categoria=None, estado=None, fundacion=None):
        """Filtros multicriterio para el historial personal del Donador (Versión Final)."""
        conn = get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            # 1. SQL limpio sin la columna 'estado' que borramos
            query = """
                SELECT 
                d.id, d.usuario_id, d.categoria_id, d.descripcion, d.cantidad, 
                d.fecha, d.fotos, d.estado_donante, d.fundacion_id,
                c.nombre AS categoria_nombre,
                fun.nombre AS fundacion_nombre,
                d.estado_donante
            FROM donaciones d
            LEFT JOIN categorias c ON d.categoria_id = c.id
            LEFT JOIN fundaciones fun ON d.fundacion_id = fun.id
            WHERE d.usuario_id = %s
            """
            params = [usuario_id]

            # 2. Filtros dinámicos de base de datos
            if q:
                query += " AND d.descripcion LIKE %s"
                params.append(f"%{q}%")
            if categoria:
                query += " AND d.categoria_id = %s"
                params.append(categoria)
            if fundacion:
                query += " AND fun.nombre LIKE %s"
                params.append(f"%{fundacion}%")

            query += " ORDER BY d.fecha DESC"
            cursor.execute(query, tuple(params))
            donaciones = cursor.fetchall()

            # 3. Mapeo de lógica de estados
            for d in donaciones:
                e_fund = d.get('estado_fundacion')
                e_donante = d.get('estado_donante')

                if e_fund == 'aceptada':
                    d['estado_donante'] = 'recibido'
                elif e_fund == 'rechazada':
                    d['estado_donante'] = 'rechazado'
                elif not e_donante:
                    d['estado_donante'] = 'pendiente'
            
            # 4. Filtro de estado (VITAL: para que el buscador funcione)
            if estado:
                donaciones = [d for d in donaciones if d['estado_donante'] == estado]

            return donaciones
        except Exception as e:
            print(f"❌ ERROR CRÍTICO EN MODELO: {e}")
            return []
        finally:
            if conn: 
                conn.close()
    # =========================================================================
    # MÉTODOS DE NECESIDADES
    # =========================================================================

    def crear_necesidad(self, fundacion_id, categoria_id, cantidad, urgencia, fecha_limite, ubicacion, telefono, descripcion, fecha_vencimiento=None):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            # Forzamos 'pendiente' directamente en el SQL para evitar que quede en blanco
            query = """
                INSERT INTO necesidades
                    (fundacion_id, categoria_id, cantidad, tipo_urgencia,
                     fecha_limite, ubicacion, telefono, descripcion, estado, fecha_vencimiento)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pendiente', %s)
            """
            cursor.execute(query, (int(fundacion_id), categoria_id, cantidad, urgencia, fecha_limite, ubicacion, telefono, descripcion, fecha_vencimiento))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error al crear necesidad: {e}")
            return False
        finally:
            conn.close()
            
    def obtener_necesidades_activas(self, q=None, cat=None):
        conn = get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            # Agregamos el JOIN con la tabla categorias y seleccionamos c.nombre
            query = """
                SELECT n.*, f.nombre AS nombre_fundacion, c.nombre AS nombre_categoria
                FROM necesidades n
                JOIN fundaciones f ON n.fundacion_id = f.id
                JOIN categorias c ON n.categoria_id = c.id
                WHERE n.estado IN ('pendiente', 'aprobado')
            """
            params = []
            if q:
                query += " AND n.descripcion LIKE %s"
                params.append(f"%{q}%")
            if cat:
                query += " AND n.categoria_id = %s"
                params.append(cat)
                
            query += " ORDER BY n.id DESC"  
            cursor.execute(query, tuple(params))
            return cursor.fetchall()
        except Exception as e:
            print(f"Error en obtener_necesidades_activas: {e}")
            return []
        finally:
            conn.close()
            
    def obtener_necesidad_por_id(self, necesidad_id):
        conn = get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            # CORREGIDO: Cambiado 'usuarios u' por 'fundaciones f' para mantener la coherencia
            query = """
                SELECT n.*, f.nombre AS nombre_fundacion, f.id AS fundacion_id
                FROM necesidades n
                JOIN fundaciones f ON n.fundacion_id = f.id
                WHERE n.id = %s
            """
            cursor.execute(query, (necesidad_id,))
            return cursor.fetchone()
        except Exception as e:
            print(f"Error en obtener_necesidad_por_id: {e}")
            return None
        finally:
            conn.close()
    # =========================================================================
    # MÉTODOS AUXILIARES
    # =========================================================================

    def obtener_categorias(self):
        conn = get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id, nombre FROM categorias ORDER BY nombre ASC")
            return cursor.fetchall()
        except Exception as e:
            print(f"Error al obtener categorías: {e}")
            return []
        finally:
            conn.close()

    def actualizar_estado_donacion(self, donacion_id, nuevo_estado, fundacion_id=None):
        """Actualiza el estado de la donación validando que pertenezca a la fundación"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            # Si pasamos fundacion_id, aseguramos que una fundación no edite donaciones de otra
            if fundacion_id:
                query = "UPDATE donaciones SET estado_donante = %s WHERE id = %s AND fundacion_id = %s"
                cursor.execute(query, (nuevo_estado, donacion_id, fundacion_id))
            else:
                query = "UPDATE donaciones SET estado_donante = %s WHERE id = %s"
                cursor.execute(query, (nuevo_estado, donacion_id))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error al actualizar estado en DB: {e}")
            return False
        finally:
            conn.close()
            
    def obtener_estadisticas_fundacion(self, fundacion_id):
        conn = get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            # Ajustamos los nombres de columnas según tu captura de phpMyAdmin
            query = """
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN estado_donante = 'pendiente' THEN 1 ELSE 0 END) as pendientes,
                    SUM(CASE WHEN estado_donante = 'recibido' THEN 1 ELSE 0 END) as recibidas,
                    SUM(CASE WHEN estado_donante = 'rechazado' THEN 1 ELSE 0 END) as rechazadas,
                    SUM(CASE WHEN categoria_id = 1 THEN 1 ELSE 0 END) as alimentos,
                    SUM(CASE WHEN categoria_id = 2 THEN 1 ELSE 0 END) as ropa,
                    SUM(CASE WHEN categoria_id NOT IN (1, 2) THEN 1 ELSE 0 END) as otros
                FROM donaciones 
                WHERE fundacion_id = %s
            """
            cursor.execute(query, (fundacion_id,))
            resultado = cursor.fetchone()

            # Si no hay registros o el resultado es nulo, devolvemos todo en cero
            if not resultado or resultado['total'] is None:
                return {
                    'pendientes': 0, 'recibidas': 0, 'rechazadas': 0,
                    'alimentos': 0, 'ropa': 0, 'otros': 0, 'total': 0
                }
            
            # Convertimos los posibles None de SUM a 0 para que Flask no tenga problemas
            return {k: (v if v is not None else 0) for k, v in resultado.items()}

        except Exception as e:
            print(f"Error en estadísticas: {e}")
            return {
                'pendientes': 0, 'recibidas': 0, 'rechazadas': 0,
                'alimentos': 0, 'ropa': 0, 'otros': 0, 'total': 0
            }
        finally:
            conn.close()
            

    def eliminar_donacion_logica(self, donacion_id):
        """Cambia el estado a 'eliminado' para que persista en reportes"""
        from database.db import get_connection
        conn = get_connection()
        try:
            cursor = conn.cursor()
            # Cambio clave: UPDATE en lugar de DELETE
            query = "UPDATE donaciones SET estado_donante = 'eliminado' WHERE id = %s"
            cursor.execute(query, (donacion_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error en eliminación lógica: {e}")
            return False
        finally:
            conn.close()
# Fin del archivo DonacionModel - Red Solidaria