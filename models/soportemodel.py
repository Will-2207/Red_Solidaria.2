class SoporteModel:
    def __init__(self, mysql):
        self.mysql = mysql

    def obtener_incidencias(self, buscar_token=None, filtro_estado=None):
        # CAMBIO AQUÍ: Usamos MySQLdb.cursors.DictCursor para obtener nombres de columnas
        from MySQLdb.cursors import DictCursor
        cur = self.mysql.connection.cursor(DictCursor) 
        
        query = """
            SELECT 
                i.id, 
                i.tipo_incidencia, 
                i.descripcion, 
                i.estado, 
                i.fecha_reporte, 
                t.token 
            FROM soporte_incidencias i 
            JOIN soporte_tokens t ON i.token_id = t.id 
            WHERE 1=1
        """
        params = []

        if buscar_token:
            query += " AND (t.token LIKE %s OR i.id LIKE %s)"
            params.extend([f"%{buscar_token}%", f"%{buscar_token}%"])
        
        if filtro_estado:
            query += " AND i.estado = %s"
            params.append(filtro_estado)

        query += " ORDER BY i.fecha_reporte DESC"
        
        cur.execute(query, tuple(params))
        result = cur.fetchall()
        cur.close()
        return result

    def obtener_estadisticas(self):
        cur = self.mysql.connection.cursor()
        
        cur.execute("SELECT COUNT(*) FROM soporte_incidencias WHERE estado IN ('abierto', 'pendiente')")
        abiertas = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM soporte_incidencias WHERE estado = 'resuelto'")
        resueltas = cur.fetchone()[0]
        
        cur.close()
        return abiertas, resueltas, (abiertas + resueltas)
    
    def obtener_ticket_por_id(self, id):
        cur = self.mysql.connection.cursor()
        # Hacemos JOIN con usuarios para el nombre de la persona 
        # y JOIN con fundaciones para el nombre de la entidad
        # CORREGIDO: La columna real en tu base de datos es 'token'
        query = """
            SELECT i.*, t.token, u.nombre AS representante, f.nombre AS fundacion, u.correo 
            FROM soporte_incidencias i
            JOIN soporte_tokens t ON i.usuario_id = t.usuario_id
            JOIN usuarios u ON i.usuario_id = u.id
            LEFT JOIN fundaciones f ON u.id = f.usuario_id
            WHERE i.id = %s
        """
        cur.execute(query, (id,))
        datos = cur.fetchone()
        cur.close()
        return datos
            

    # ... (tus funciones anteriores: obtener_incidencias, obtener_estadisticas, obtener_ticket_por_id) ...

    def crear_incidencia(self, usuario_id, token_uuid, tipo, transaccion_id, descripcion):
        cur = self.mysql.connection.cursor()
        try:
            # Insertar Token
            cur.execute("INSERT INTO soporte_tokens (token, usuario_id) VALUES (%s, %s)", (token_uuid, usuario_id))
            token_id_real = cur.lastrowid
            
            # Insertar Incidencia
            query = """
                INSERT INTO soporte_incidencias 
                (usuario_id, token_id, transaccion_id, tipo_incidencia, descripcion, estado)
                VALUES (%s, %s, %s, %s, %s, 'abierto')
            """
            cur.execute(query, (usuario_id, token_id_real, transaccion_id, tipo, descripcion))
            self.mysql.connection.commit()
            return True
        except Exception as e:
            self.mysql.connection.rollback()
            raise e
        finally:
            cur.close()

    def resolver_ticket(self, ticket_id):
        cur = self.mysql.connection.cursor()
        cur.execute("UPDATE soporte_incidencias SET estado = 'resuelto' WHERE id = %s", (ticket_id,))
        self.mysql.connection.commit()
        cur.close()    
        
    def contar_tickets_abiertos(self):
        cur = self.mysql.connection.cursor()
        cur.execute("SELECT COUNT(*) FROM soporte_incidencias WHERE estado = 'abierto'")
        res = cur.fetchone()
        cur.close()
        return res[0] if res else 0    