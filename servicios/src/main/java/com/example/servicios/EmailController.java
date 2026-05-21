package com.example.servicios;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/email")
public class EmailController {

    @Autowired
    private EmailService emailService;

    @Autowired
    private PdfService pdfService;

    // 1. Notificaciones de cuenta (Pendiente/Aprobado/Rechazado)
    @PostMapping("/enviar")
    public ResponseEntity<String> enviarEmail(@RequestBody EmailRequest request) {
        try {
            emailService.enviarNotificacion(request);
            return ResponseEntity.ok("{\"status\": \"Notificación enviada\"}");
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body("{\"status\": \"Error\", \"error\": \"No se pudo enviar la notificación\"}");
        }
    }

    // 2. Reporte fundación con PDF adjunto + botón descarga (¡COMPLETADO!)
    @PostMapping("/enviar-reporte-fundacion")
    public ResponseEntity<String> enviarReporteFundacion(@RequestBody EmailRequest request) {
        try {
            if (request.getDestinatario() == null || request.getDestinatario().isEmpty()) {
                return ResponseEntity.badRequest()
                    .body("{\"status\": \"Error\", \"error\": \"Sin destinatario\"}");
            }
            System.out.println("[DEBUG] Iniciando envío de reporte para Fundación: " + request.getNombreFundacion());
            
            // Generamos el contenido del PDF usando el método normal de la fundación
            byte[] pdfContenido = pdfService.generarReporte(request);
            
            // Enviamos el correo marcando el tipo como "FUNDACION"
            emailService.enviarReporteEmail(request, pdfContenido, "FUNDACION");
            
            return ResponseEntity.status(HttpStatus.OK)
                .header(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
                .body("{\"status\": \"Reporte de fundación enviado con botón de descarga\"}");
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body("{\"status\": \"Error\", \"error\": \"" + e.getMessage() + "\"}");
        }
    }
    

    // 2b. Reporte con PDF Adjunto para Donante (¡ACTUALIZADO!)
    @PostMapping("/enviar-reporte-donador")
    public ResponseEntity<String> enviarReporteDonador(@RequestBody EmailRequest request) {
        try {
            if (request.getDestinatario() == null || request.getDestinatario().isEmpty()) {
                return ResponseEntity.badRequest()
                    .body("{\"status\": \"Error\", \"error\": \"Sin destinatario\"}");
            }
            System.out.println("[DEBUG] Iniciando envío de reporte para Donante: " + request.getNombreDonador());
            
            byte[] pdfContenido = pdfService.generarReporte(request);
            
            // Enviamos el correo marcando el tipo como "DONANTE"
            emailService.enviarReporteEmail(request, pdfContenido, "DONANTE");
            
            return ResponseEntity.status(HttpStatus.OK)
                .header(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
                .body("{\"status\": \"Reporte enviado con botón de descarga\"}");
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body("{\"status\": \"Error\", \"error\": \"" + e.getMessage() + "\"}");
        }
    }
    
// // 1. MÉTODO PARA ENVIAR EL REPORTE POR EMAIL (CORREGIDO PARA EVITAR MEZCLAS CON FUNDACIÓN)
    @PostMapping("/enviar-reporte")
    public ResponseEntity<String> enviarReporte(@RequestBody EmailRequest request) {
        try {
            // 1. Sincronizamos los conteos de todas las listas posibles que mande Flask
            if (request.getDonaciones() != null) request.setCantidadDonaciones(request.getDonaciones().size());
            
            byte[] pdfContenido;
            String tipoReporte;

            // ── CONTROL DE DESVÍO CRÍTICO ──
            // Si la petición trae un fundacionId válido mayor a 0, significa que NO es el admin global, sino una Fundación.
            if (request.getFundacionId() > 0) {
                System.out.println("[DEBUG] Desviando petición errónea: Generando Reporte de Actividad para Fundación ID: " + request.getFundacionId());
                pdfContenido = pdfService.generarReporte(request); // <-- Cambia al diseño limpio de la Fundación
                tipoReporte = "FUNDACION";                         // <-- Cambia el asunto del correo automáticamente
            } else {
                System.out.println("[DEBUG] Iniciando envío de reporte global desde Panel Administrativo");
                pdfContenido = pdfService.generarReporteAdmin(request); // <-- Se mantiene Admin solo si es el admin real
                tipoReporte = "ADMIN";
            }
            
            // 3. Enviamos el email marcando el tipo correspondiente de forma segura
            emailService.enviarReporteEmail(request, pdfContenido, tipoReporte);

            int totalDonaciones = request.getDonaciones() != null ? request.getDonaciones().size() : 0;
            return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
                .body("{\"status\": \"Reporte enviado con éxito\", \"registros\": " + totalDonaciones + "}");

        } catch (Exception e) {
            System.err.println("[ERROR] en enviarReporte Admin: " + e.getMessage());
            e.printStackTrace();
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body("{\"status\": \"Error\", \"error\": \"" + e.getMessage() + "\"}");
        }
    }

// 3. MÉTODO AUXILIAR (Para no repetir código de base de datos)
@SuppressWarnings("unused")
private List<Map<String, Object>> obtenerDonacionesDeDB(int fundacionId, String categoria, String estado) throws Exception {
    List<Map<String, Object>> listaDonaciones = new ArrayList<>();
    Class.forName("org.mariadb.jdbc.Driver");
    try (java.sql.Connection conn = java.sql.DriverManager.getConnection("jdbc:mariadb://localhost:3307/donaciones_db", "root", "")) {
        StringBuilder query = new StringBuilder();
        
        // ── CORRECCIÓN AQUÍ: Agregamos f.nit en el SELECT ──
        query.append("SELECT d.descripcion, d.cantidad, df.estado as estado_fundacion, d.estado_donante, f.nombre as fundacion_real, f.nit as nit_real "); 
        query.append("FROM donaciones d ");
        query.append("LEFT JOIN donaciones_fundaciones df ON d.id = df.donacion_id ");
        query.append("LEFT JOIN categorias c ON d.categoria_id = c.id ");
        query.append("LEFT JOIN fundaciones f ON d.fundacion_id = f.id ");
        query.append("WHERE d.fundacion_id = ? AND d.estado_donante != 'eliminado' "); 
        
        List<Object> params = new ArrayList<>();
        params.add(fundacionId);

       // 1. FILTRO DE CATEGORÍA (Blindado con LOWER y TRIM)
        if (categoria != null && !categoria.trim().isEmpty() && !categoria.equalsIgnoreCase("Todas")) {
            query.append("AND LOWER(c.nombre) = ? ");
            params.add(categoria.toLowerCase().trim());
        }

        // 2. FILTRO DE ESTADO (Blindado para vacíos, Todos y plurales)
        if (estado != null && !estado.trim().isEmpty() && !estado.equalsIgnoreCase("Todos") && !estado.equals("")) {
            String estadoFormateado = estado.toLowerCase().trim();
            
            // Por si acaso llega a viajar en plural "recibidos"
            if (estadoFormateado.endsWith("s")) {
                estadoFormateado = estadoFormateado.substring(0, estadoFormateado.length() - 1);
            }
            
            query.append("AND (LOWER(df.estado) LIKE ? OR LOWER(d.estado_donante) LIKE ?) ");
            params.add("%" + estadoFormateado + "%");
            params.add("%" + estadoFormateado + "%");
        }

        try (java.sql.PreparedStatement stmt = conn.prepareStatement(query.toString())) {
            for (int i = 0; i < params.size(); i++) stmt.setObject(i + 1, params.get(i));
            
            try (java.sql.ResultSet rs = stmt.executeQuery()) {
                while (rs.next()) {
                    Map<String, Object> don = new HashMap<>();
                    don.put("descripcion", rs.getString("descripcion") != null ? rs.getString("descripcion") : "Sin descripción");
                    don.put("cantidad", rs.getInt("cantidad"));
                    don.put("estado_fundacion", rs.getString("estado_fundacion") != null ? rs.getString("estado_fundacion") : "Pendiente");
                    don.put("estado_donante", rs.getString("estado_donante") != null ? rs.getString("estado_donante") : "Pendiente");
                    don.put("Fundación", rs.getString("fundacion_real") != null ? rs.getString("fundacion_real") : "Mi Fundación");
                    
                    // ── Mapeamos el NIT recuperado para que viaje al PdfService ──
                    don.put("nit", rs.getString("nit_real") != null ? rs.getString("nit_real") : "N/A");

                    listaDonaciones.add(don);
                }
            }
        }
    }
    return listaDonaciones;
}
    // ══════════════════════════════════════════════════════════════
    // 4. DESCARGA REPORTE ADMIN — 3 secciones: Donaciones,
    //    Fundaciones y Donantes, con filtros multicriterio.
    // ══════════════════════════════════════════════════════════════
    @GetMapping("/descargar-reporte-admin")
    public ResponseEntity<byte[]> descargarReporteAdmin(
            @RequestParam(required = false, defaultValue = "Administrador") String nombre,
            @RequestParam(required = false, defaultValue = "Todas") String categoria,
            @RequestParam(name = "est", required = false, defaultValue = "Todos") String estado,
            @RequestParam(required = false, defaultValue = "") String donante,
            @RequestParam(required = false, defaultValue = "") String fundacion) {

        System.out.println("[DEBUG] Reporte Admin -> Cat: " + categoria + " | Est: " + estado + " | Don: " + donante + " | Fun: " + fundacion);

        try {
            List<Map<String, Object>> listaDonaciones  = new ArrayList<>();
            List<Map<String, Object>> listaFundaciones = new ArrayList<>();
            List<Map<String, Object>> listaDonantes    = new ArrayList<>();

            // CORRECCIÓN CRÍTICA: Normalizar el estado a Mayúsculas para que coincida con la DB
            String estadoFormateado = (estado != null) ? estado.trim().toUpperCase() : "TODOS";

            Class.forName("org.mariadb.jdbc.Driver");
            try (java.sql.Connection conn = java.sql.DriverManager.getConnection(
                    "jdbc:mariadb://localhost:3307/donaciones_db", "root", "")) {

                // ── CONSULTA 1: DONACIONES ──
                StringBuilder qDon = new StringBuilder();
                qDon.append("SELECT d.descripcion, d.cantidad, u.nombre AS nombre_donante, ");
                qDon.append("c.nombre AS nombre_categoria, f.nombre AS fundacion_nombre, ");
                qDon.append("COALESCE(df.estado, d.estado_donante) AS estado_fundacion "); // Corregido a estado_donante
                qDon.append("FROM donaciones d ");
                qDon.append("INNER JOIN usuarios u ON d.usuario_id = u.id ");
                qDon.append("LEFT JOIN categorias c ON d.categoria_id = c.id ");
                qDon.append("LEFT JOIN donaciones_fundaciones df ON d.id = df.donacion_id ");
                qDon.append("LEFT JOIN fundaciones fun ON df.fundacion_id = fun.id ");
                qDon.append("LEFT JOIN usuarios f ON fun.usuario_id = f.id ");
                qDon.append("WHERE 1=1 ");

                List<Object> pDon = new ArrayList<>();
                if (!categoria.equalsIgnoreCase("Todas")) {
                    qDon.append("AND c.nombre = ? ");
                    pDon.add(categoria);
                }
                if (!estadoFormateado.equalsIgnoreCase("TODOS")) {
                    qDon.append("AND (UPPER(COALESCE(df.estado, d.estado_donante)) = ? ) ");
                    pDon.add(estadoFormateado);
                }
                if (!donante.isEmpty()) {
                    qDon.append("AND u.nombre LIKE ? ");
                    pDon.add("%" + donante + "%");
                }
                if (!fundacion.isEmpty()) {
                    qDon.append("AND f.nombre LIKE ? ");
                    pDon.add("%" + fundacion + "%");
                }
                qDon.append("ORDER BY d.id DESC"); // Cambiado a d.id por seguridad de existencia

                try (java.sql.PreparedStatement stmtDon = conn.prepareStatement(qDon.toString())) {
                    for (int i = 0; i < pDon.size(); i++) stmtDon.setObject(i + 1, pDon.get(i));
                    try (java.sql.ResultSet rsDon = stmtDon.executeQuery()) {
                        while (rsDon.next()) {
                            Map<String, Object> row = new HashMap<>();
                            row.put("descripcion", rsDon.getString("descripcion") != null ? rsDon.getString("descripcion") : "Sin descripción");
                            row.put("cantidad", rsDon.getObject("cantidad") != null ? rsDon.getObject("cantidad") : 0);
                            row.put("estado_fundacion", rsDon.getString("estado_fundacion") != null ? rsDon.getString("estado_fundacion") : "PENDIENTE");
                            row.put("nombre_donante", rsDon.getString("nombre_donante") != null ? rsDon.getString("nombre_donante") : "Anónimo");
                            row.put("nombre_categoria", rsDon.getString("nombre_categoria") != null ? rsDon.getString("nombre_categoria") : "General");
                            row.put("fundacion_nombre", rsDon.getString("fundacion_nombre") != null ? rsDon.getString("fundacion_nombre") : "Sin asignar");
                            listaDonaciones.add(row);
                        }
                    }
                }

                // ── CONSULTA 2: FUNDACIONES ──
                StringBuilder qFun = new StringBuilder();
                qFun.append("SELECT f.nombre, f.nit, u.correo, u.fecha_registro, f.estado_validacion ");
                qFun.append("FROM fundaciones f INNER JOIN usuarios u ON f.usuario_id = u.id WHERE 1=1 ");
                List<Object> pFun = new ArrayList<>();
                if (!fundacion.isEmpty()) { qFun.append("AND f.nombre LIKE ? "); pFun.add("%" + fundacion + "%"); }
                if (!estadoFormateado.equalsIgnoreCase("TODOS")) { qFun.append("AND UPPER(f.estado_validacion) = ? "); pFun.add(estadoFormateado); }
                qFun.append("ORDER BY u.fecha_registro DESC");

                try (java.sql.PreparedStatement stmtFun = conn.prepareStatement(qFun.toString())) {
                    for (int i = 0; i < pFun.size(); i++) stmtFun.setObject(i + 1, pFun.get(i));
                    try (java.sql.ResultSet rsFun = stmtFun.executeQuery()) {
                        while (rsFun.next()) {
                            Map<String, Object> row = new HashMap<>();
                            row.put("nombre", rsFun.getString("nombre"));
                            row.put("nit", rsFun.getString("nit"));
                            row.put("correo", rsFun.getString("correo"));
                            row.put("fecha_registro", rsFun.getString("fecha_registro"));
                            row.put("estado_validacion", rsFun.getString("estado_validacion"));
                            listaFundaciones.add(row);
                        }
                    }
                }

                // ── CONSULTA 3: DONANTES ──
                StringBuilder qDona = new StringBuilder();
                qDona.append("SELECT nombre, correo, fecha_registro, estado FROM usuarios WHERE rol_id = 2 ");
                List<Object> pDona = new ArrayList<>();
                if (!donante.isEmpty()) { qDona.append("AND nombre LIKE ? "); pDona.add("%" + donante + "%"); }
                if (!estadoFormateado.equalsIgnoreCase("TODOS")) { qDona.append("AND UPPER(estado) = ? "); pDona.add(estadoFormateado); }
                qDona.append("ORDER BY fecha_registro DESC");

                try (java.sql.PreparedStatement stmtDona = conn.prepareStatement(qDona.toString())) {
                    for (int i = 0; i < pDona.size(); i++) stmtDona.setObject(i + 1, pDona.get(i));
                    try (java.sql.ResultSet rsDona = stmtDona.executeQuery()) {
                        while (rsDona.next()) {
                            Map<String, Object> row = new HashMap<>();
                            row.put("nombre", rsDona.getString("nombre"));
                            row.put("correo", rsDona.getString("correo"));
                            row.put("fecha_registro", rsDona.getString("fecha_registro"));
                            row.put("estado", rsDona.getString("estado"));
                            listaDonantes.add(row);
                        }
                    }
                }
            }

            // Armar el objeto de datos para el PDF
            EmailRequest datos = new EmailRequest();
            datos.setNombreFundacion(nombre);
            datos.setNit("Panel Administrativo");
            datos.setCategoriaFiltrada(categoria);
            datos.setEstadoFiltrado(estadoFormateado);
            datos.setDonaciones(listaDonaciones);
            datos.setFundaciones(listaFundaciones);
            datos.setDonantes(listaDonantes);

            // Forzar cantidad total basada en la lista de la sección correspondiente
            if (estadoFormateado.equals("ELIMINADO")) {
                datos.setCantidadDonaciones(listaDonaciones.size() + listaFundaciones.size() + listaDonantes.size());
            } else {
                datos.setCantidadDonaciones(listaDonaciones.size());
            }

            byte[] pdfBytes = pdfService.generarReporteAdmin(datos);

            org.springframework.http.HttpHeaders headers = new org.springframework.http.HttpHeaders();
            headers.setContentType(org.springframework.http.MediaType.APPLICATION_PDF);
            headers.setContentDispositionFormData("attachment", "Reporte_Admin_Red_Solidaria.pdf");
            
            System.out.println("[DEBUG] PDF generado con éxito para descarga admin. Tamaño: " + pdfBytes.length);
            return new org.springframework.http.ResponseEntity<>(pdfBytes, headers, org.springframework.http.HttpStatus.OK);

        } catch (Exception e) {
            System.err.println("[ERROR] Fallo catastrófico en descargarReporteAdmin: " + e.getMessage());
            e.printStackTrace();
            return new org.springframework.http.ResponseEntity<>(org.springframework.http.HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }
    // ══════════════════════════════════════════════════════════════
    // 5. DESCARGA REPORTE FUNDACIÓN — ¡CORREGIDO Y BLINDADO!
    // ══════════════════════════════════════════════════════════════
    @GetMapping("/descargar-reporte-fundacion")
    public ResponseEntity<byte[]> descargarReporteFundacion(
            @RequestParam(name = "fundacion_id") int fundacionId,
            @RequestParam(required = false, defaultValue = "Todas") String categoria,
            @RequestParam(name = "est", required = false, defaultValue = "Todos") String estado) {

        System.out.println("[DEBUG] Descargando PDF desde link de correo para Fundación ID: " + fundacionId + " | Cat: " + categoria + " | Est: " + estado);

        try {
            // 1. Forzamos que la consulta extraiga ÚNICAMENTE las donaciones de esta fundación
            List<Map<String, Object>> donacionesFiltradas = obtenerDonacionesDeDB(fundacionId, categoria, estado);

            // 2. Creamos el EmailRequest de transporte de datos
            EmailRequest datos = new EmailRequest();
            datos.setFundacionId(fundacionId);
            datos.setCategoriaFiltrada(categoria);
            datos.setEstadoFiltrado(estado);
            datos.setDonaciones(donacionesFiltradas);
            datos.setCantidadDonaciones(donacionesFiltradas.size());

            // 3. ¡SOLUCIÓN LOGO Y NIT!: Obtenemos los datos reales de la fundación
            String nombreRealFundacion = "Fundación Registrada";
            String nitRealFundacion = "N/A"; // <-- AQUÍ YA QUEDA DECLARADA CORRECTAMENTE
            
            if (!donacionesFiltradas.isEmpty()) {
                if (donacionesFiltradas.get(0).get("Fundación") != null) {
                    nombreRealFundacion = donacionesFiltradas.get(0).get("Fundación").toString();
                }
                // Rescatamos el NIT mapeado desde el método auxiliar de la DB
                if (donacionesFiltradas.get(0).get("nit") != null) {
                    nitRealFundacion = donacionesFiltradas.get(0).get("nit").toString();
                }
            } else {
                // Si la lista está vacía, le dejamos un título acorde a su ID
                nombreRealFundacion = "Mi Fundación (ID: " + fundacionId + ")";
            }
            
            datos.setNombreFundacion(nombreRealFundacion);
            datos.setNit(nitRealFundacion); // <-- Ahora sí la va a encontrar sin problemas
            // 4. Generamos el PDF exclusivo usando el servicio tradicional de fundaciones
            byte[] pdfBytes = pdfService.generarReporte(datos);

            org.springframework.http.HttpHeaders headers = new org.springframework.http.HttpHeaders();
            headers.setContentType(org.springframework.http.MediaType.APPLICATION_PDF);
            // Nombre del archivo PDF dinámico para el navegador
            String nombreArchivo = "Reporte_" + nombreRealFundacion.replace(" ", "_") + ".pdf";
            headers.setContentDispositionFormData("attachment", nombreArchivo);

            return new org.springframework.http.ResponseEntity<>(pdfBytes, headers, org.springframework.http.HttpStatus.OK);

        } catch (Exception e) {
            System.err.println("[ERROR] Fallo al descargar reporte de fundación: " + e.getMessage());
            return new org.springframework.http.ResponseEntity<>(org.springframework.http.HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }
    // ══════════════════════════════════════════════════════════════
    // 6. DESCARGA REPORTE DONANTE — Basado en su correo o filtros
    // ══════════════════════════════════════════════════════════════
    @GetMapping("/descargar-reporte-donante")
    public ResponseEntity<byte[]> descargarReporteDonante(
            @RequestParam String correo,
            @RequestParam(required = false, defaultValue = "Todas") String categoria,
            @RequestParam(name = "est", required = false, defaultValue = "Todos") String estado) {

        System.out.println("[DEBUG] Descargando PDF desde link de correo para Donante: " + correo);

        try {
            // Aquí puedes conectar la consulta de donaciones hechas por este donante específico si lo requieres.
            // Por ahora, estructuramos la respuesta segura del PDF:
            EmailRequest datos = new EmailRequest();
            datos.setDestinatario(correo);
            datos.setCategoriaFiltrada(categoria);
            datos.setEstadoFiltrado(estado);
            
            // Generamos el PDF del donante
            byte[] pdfBytes = pdfService.generarReporte(datos);

            org.springframework.http.HttpHeaders headers = new org.springframework.http.HttpHeaders();
            headers.setContentType(org.springframework.http.MediaType.APPLICATION_PDF);
            headers.setContentDispositionFormData("attachment", "Mi_Reporte_Donaciones.pdf");

            return new org.springframework.http.ResponseEntity<>(pdfBytes, headers, org.springframework.http.HttpStatus.OK);

        } catch (Exception e) {
            System.err.println("[ERROR] Fallo al descargar reporte de donante: " + e.getMessage());
            return new org.springframework.http.ResponseEntity<>(org.springframework.http.HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }
}