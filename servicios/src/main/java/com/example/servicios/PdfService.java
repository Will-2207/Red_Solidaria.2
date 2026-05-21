package com.example.servicios;

import com.itextpdf.io.image.ImageDataFactory;
import com.itextpdf.kernel.colors.DeviceRgb;
import com.itextpdf.kernel.events.Event;
import com.itextpdf.kernel.events.IEventHandler;
import com.itextpdf.kernel.events.PdfDocumentEvent;
import com.itextpdf.kernel.pdf.PdfDocument;
import com.itextpdf.kernel.pdf.PdfPage;
import com.itextpdf.kernel.pdf.PdfWriter;
import com.itextpdf.kernel.pdf.canvas.PdfCanvas;
import com.itextpdf.kernel.pdf.colorspace.PdfDeviceCs;
import com.itextpdf.kernel.pdf.colorspace.PdfShading;
import com.itextpdf.kernel.geom.Rectangle;
import com.itextpdf.layout.Canvas;
import com.itextpdf.layout.Document;
import com.itextpdf.layout.element.Cell;
import com.itextpdf.layout.element.Image;
import com.itextpdf.layout.element.Paragraph;
import com.itextpdf.layout.element.Table;
import com.itextpdf.layout.properties.HorizontalAlignment;
import com.itextpdf.layout.properties.TextAlignment;
import com.itextpdf.layout.properties.UnitValue;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Service;

import java.io.ByteArrayOutputStream;
import java.util.List;
import java.util.Map;

@Service
public class PdfService {

    // ══════════════════════════════════════════════
    // REPORTE FUNDACIÓN (existente — sin cambios)
    // ══════════════════════════════════════════════
    public byte[] generarReporte(EmailRequest datos) {
    ByteArrayOutputStream out = new ByteArrayOutputStream();
    
    // El try-with-resources asegura que el writer se cierre y libere los bytes al stream 'out'
    try (PdfWriter writer = new PdfWriter(out)) { 
        PdfDocument pdf = new PdfDocument(writer);
        pdf.addEventHandler(PdfDocumentEvent.END_PAGE, new FooterHandler());
        Document document = new Document(pdf);
        document.setBottomMargin(50);

        float[] colorAzul  = new float[]{30f/255f, 82f/255f, 255f/255f};
        float[] colorVerde = new float[]{99f/255f, 255f/255f, 94f/255f};
        DeviceRgb grisFondo = new DeviceRgb(248, 249, 250);

        PdfCanvas canvas = new PdfCanvas(pdf.addNewPage());
        float width  = pdf.getDefaultPageSize().getWidth();
        float height = pdf.getDefaultPageSize().getHeight();
        Rectangle headerRect = new Rectangle(0, height - 150, width, 150);
        
        PdfShading.Axial axial = new PdfShading.Axial(new PdfDeviceCs.Rgb(),
            headerRect.getLeft(), headerRect.getBottom(), colorAzul,
            headerRect.getRight(), headerRect.getBottom(), colorVerde);
        
        canvas.saveState().rectangle(headerRect).clip().endPath().paintShading(axial).restoreState();

        // Bloque del Logo
        try {
            ClassPathResource res = new ClassPathResource("static/images/logo.jpeg");
            Image logo = new Image(ImageDataFactory.create(res.getURL().getPath()));
            logo.setMaxHeight(65).setHorizontalAlignment(HorizontalAlignment.CENTER)
                .setMarginTop(10).setBackgroundColor(DeviceRgb.WHITE).setPadding(8);
            document.add(logo);
        } catch (Exception e) { 
            System.out.println("⚠️ Logo no encontrado en la ruta especificada."); 
        }

        // Títulos DINÁMICOS (Muestra el nombre real de la Fundación debajo del logo)
        String tituloEncabezado = (datos.getNombreFundacion() != null && !datos.getNombreFundacion().isEmpty()) 
            ? datos.getNombreFundacion().toUpperCase() 
            : "RED SOLIDARIA";

        document.add(new Paragraph(tituloEncabezado)
            .setFontColor(DeviceRgb.WHITE).setTextAlignment(TextAlignment.CENTER)
            .setBold().setFontSize(22).setMarginTop(5));
        
        document.add(new Paragraph("Reporte de Impacto de Donaciones Recibidas")
            .setFontColor(DeviceRgb.WHITE).setTextAlignment(TextAlignment.CENTER)
            .setFontSize(13).setMarginBottom(45));

        // --- REEMPLAZA DESDE AQUÍ (Tabla de información NIT y Fundación) ---
        Table infoTable = new Table(UnitValue.createPercentArray(new float[]{1, 1})).useAllAvailableWidth();
        infoTable.setBackgroundColor(grisFondo).setPadding(10).setMarginBottom(20);
        
        // Fila 1: Fundación y NIT
        infoTable.addCell(new Cell().add(new Paragraph("Fundación: " + datos.getNombreFundacion()).setBold())
            .setBorder(com.itextpdf.layout.borders.Border.NO_BORDER));
        
        infoTable.addCell(new Cell().add(new Paragraph("NIT: " + (datos.getNit() != null ? datos.getNit() : "N/A"))
            .setTextAlignment(TextAlignment.RIGHT))
            .setBorder(com.itextpdf.layout.borders.Border.NO_BORDER));
        
        // Fila 2: Filtro Categoría y Filtro Estado (ESTA ES LA PARTE QUE DEBES ASEGURAR)
        String categoria = (datos.getCategoriaFiltrada() != null && !datos.getCategoriaFiltrada().isEmpty()) 
            ? datos.getCategoriaFiltrada() : "Todas";
        
        String estadoFiltro = (datos.getEstadoFiltrado() != null && !datos.getEstadoFiltrado().isEmpty()) 
            ? datos.getEstadoFiltrado() : "Todos";
            
        infoTable.addCell(new Cell().add(new Paragraph("Filtro Categoría: " + categoria))
            .setBorder(com.itextpdf.layout.borders.Border.NO_BORDER));

        infoTable.addCell(new Cell().add(new Paragraph("Filtro Estado: " + estadoFiltro) // <--- AGREGADO
            .setTextAlignment(TextAlignment.RIGHT))
            .setBorder(com.itextpdf.layout.borders.Border.NO_BORDER));
        
        // Fila 3: Total Registros
        infoTable.addCell(new Cell(1, 2).add(new Paragraph("Total Registros: " + datos.getCantidadDonaciones())
            .setBold().setTextAlignment(TextAlignment.CENTER))
            .setMarginTop(5)
            .setBorder(com.itextpdf.layout.borders.Border.NO_BORDER));
        
        document.add(infoTable);
        // --- HASTA AQUÍ ---

        // --- TABLA DE DONACIONES (COPIA DESDE AQUÍ) ---
        Table table = new Table(new float[]{250f, 100f, 100f}).useAllAvailableWidth();

        // Encabezados de la tabla
        table.addHeaderCell(new Cell().add(new Paragraph("Descripción").setBold().setFontColor(DeviceRgb.WHITE))
            .setBackgroundColor(new DeviceRgb(30, 82, 255)));
        table.addHeaderCell(new Cell().add(new Paragraph("Cantidad").setBold().setFontColor(DeviceRgb.WHITE))
            .setBackgroundColor(new DeviceRgb(30, 82, 255)).setTextAlignment(TextAlignment.CENTER));
        table.addHeaderCell(new Cell().add(new Paragraph("Estado").setBold().setFontColor(DeviceRgb.WHITE))
            .setBackgroundColor(new DeviceRgb(30, 82, 255)).setTextAlignment(TextAlignment.CENTER));

        // Contenido de la tabla
        if (datos.getDonaciones() != null && !datos.getDonaciones().isEmpty()) {
            for (Map<String, Object> d : datos.getDonaciones()) {
                // 1. Descripción y Cantidad
                table.addCell(new Cell().add(new Paragraph(d.getOrDefault("descripcion", "Sin descripción").toString())).setPadding(5));
                table.addCell(new Cell().add(new Paragraph(d.getOrDefault("cantidad", "0").toString())).setTextAlignment(TextAlignment.CENTER));
                
                // 2. Lógica de Estado (Priorizamos estado_donante que es el ENUM de tu DB)
                String estadoAMostrar = d.getOrDefault("estado_donante", 
                                        d.getOrDefault("estado_fundacion", "pendiente")).toString();

                // 3. Ajuste visual: Si hay un filtro activo, mostramos ese estado para que el PDF sea coherente
                if (datos.getEstadoFiltrado() != null && 
                    !datos.getEstadoFiltrado().isEmpty() && 
                    !datos.getEstadoFiltrado().equalsIgnoreCase("Todos")) {
                    estadoAMostrar = datos.getEstadoFiltrado();
                }
                
                table.addCell(new Cell().add(new Paragraph(estadoAMostrar)).setTextAlignment(TextAlignment.CENTER));
            }
        } else {
            table.addCell(new Cell(1, 3).add(new Paragraph("No se encontraron donaciones con los filtros seleccionados.")).setPadding(5));
        }

// --- HASTA AQUÍ ---
        document.add(table);
        document.close(); // Cierre del documento
        
    } catch (Exception e) { 
        System.err.println("❌ Error al generar el PDF: " + e.getMessage());
        e.printStackTrace(); 
    }
    
    return out.toByteArray();
}

    // ══════════════════════════════════════════════════════════════
    // REPORTE ADMIN — solo muestra secciones que tienen datos
    // ══════════════════════════════════════════════════════════════
    public byte[] generarReporteAdmin(EmailRequest datos) {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        try {
            PdfWriter writer = new PdfWriter(out);
            PdfDocument pdf = new PdfDocument(writer);
            pdf.addEventHandler(PdfDocumentEvent.END_PAGE, new FooterHandler());
            Document document = new Document(pdf);
            document.setBottomMargin(50);

            DeviceRgb colorAzul  = new DeviceRgb(30, 82, 255);
            DeviceRgb colorVerde = new DeviceRgb(0, 180, 120);
            DeviceRgb colorMorado = new DeviceRgb(106, 17, 203);
            DeviceRgb grisFondo  = new DeviceRgb(248, 249, 250);

            float[] azulArr  = new float[]{30f/255f, 82f/255f, 255f/255f};
            float[] verdeArr = new float[]{99f/255f, 255f/255f, 94f/255f};

            // ── ENCABEZADO ──
            PdfCanvas canvas = new PdfCanvas(pdf.addNewPage());
            float width  = pdf.getDefaultPageSize().getWidth();
            float height = pdf.getDefaultPageSize().getHeight();
            Rectangle headerRect = new Rectangle(0, height - 160, width, 160);
            PdfShading.Axial axial = new PdfShading.Axial(new PdfDeviceCs.Rgb(),
                headerRect.getLeft(), headerRect.getBottom(), azulArr,
                headerRect.getRight(), headerRect.getBottom(), verdeArr);
            canvas.saveState().rectangle(headerRect).clip().endPath().paintShading(axial).restoreState();

            try {
                ClassPathResource res = new ClassPathResource("static/images/logo.jpeg");
                Image logo = new Image(ImageDataFactory.create(res.getURL().getPath()));
                logo.setMaxHeight(65).setHorizontalAlignment(HorizontalAlignment.CENTER)
                    .setMarginTop(10).setBackgroundColor(DeviceRgb.WHITE).setPadding(8);
                document.add(logo);
            } catch (Exception e) { System.out.println("Logo no encontrado"); }

            document.add(new Paragraph("RED SOLIDARIA — PANEL ADMINISTRATIVO")
                .setFontColor(DeviceRgb.WHITE).setTextAlignment(TextAlignment.CENTER)
                .setBold().setFontSize(22).setMarginTop(5));
            document.add(new Paragraph("Reporte Multicriterio de Actividad")
                .setFontColor(DeviceRgb.WHITE).setTextAlignment(TextAlignment.CENTER)
                .setFontSize(13).setMarginBottom(40));

            // ── RESUMEN ──
            String categoria = (datos.getCategoriaFiltrada() != null && !datos.getCategoriaFiltrada().isEmpty())
                ? datos.getCategoriaFiltrada() : "Todas";
            String estadoFiltro = (datos.getEstadoFiltrado() != null && !datos.getEstadoFiltrado().isEmpty())
                ? datos.getEstadoFiltrado() : "Todos";

            // ── Contar solo los que tienen datos ──
            List<Map<String, Object>> donaciones  = datos.getDonaciones()  != null ? datos.getDonaciones()  : List.of();
            List<Map<String, Object>> fundaciones = datos.getFundaciones() != null ? datos.getFundaciones() : List.of();
            List<Map<String, Object>> donantes    = datos.getDonantes()    != null ? datos.getDonantes()    : List.of();

            boolean hayDonaciones  = !donaciones.isEmpty();
            boolean hayFundaciones = !fundaciones.isEmpty();
            boolean hayDonantes    = !donantes.isEmpty();

            Table resumen = new Table(UnitValue.createPercentArray(new float[]{1, 1})).useAllAvailableWidth();
            resumen.setBackgroundColor(grisFondo).setPadding(10).setMarginBottom(20);
            resumen.addCell(new Cell().add(new Paragraph("Filtro Categoría: " + categoria))
                .setBorder(com.itextpdf.layout.borders.Border.NO_BORDER));
            resumen.addCell(new Cell().add(new Paragraph("Filtro Estado: " + estadoFiltro).setTextAlignment(TextAlignment.RIGHT))
                .setBorder(com.itextpdf.layout.borders.Border.NO_BORDER));

            // Solo muestra los totales de las secciones que tienen datos
            StringBuilder totalStr = new StringBuilder();
            if (hayDonaciones)  totalStr.append("Total Donaciones: ").append(donaciones.size());
            if (hayFundaciones) { if (totalStr.length() > 0) totalStr.append("   |   "); totalStr.append("Total Fundaciones: ").append(fundaciones.size()); }
            if (hayDonantes)    { if (totalStr.length() > 0) totalStr.append("   |   "); totalStr.append("Total Donantes: ").append(donantes.size()); }
            if (totalStr.length() == 0) totalStr.append("Sin resultados para los filtros seleccionados.");

            resumen.addCell(new Cell(1, 2).add(new Paragraph(totalStr.toString()).setBold().setTextAlignment(TextAlignment.CENTER))
                .setBorder(com.itextpdf.layout.borders.Border.NO_BORDER));
            document.add(resumen);

            // ══════════════════════════════════════
            // SECCIÓN 1 — DONACIONES (solo si hay)
            // ══════════════════════════════════════
            if (hayDonaciones) {
                document.add(new Paragraph("📦 Donaciones Físicas (" + donaciones.size() + ")")
                    .setBold().setFontSize(14).setFontColor(colorAzul).setMarginBottom(5).setMarginTop(10));

                Table tDon = new Table(new float[]{30f, 120f, 100f, 80f, 80f, 55f, 80f}).useAllAvailableWidth();
                String[] hDon = {"#", "Descripción", "Donador", "Categoría", "Fundación", "Cant.", "Estado"};
                for (String h : hDon)
                    tDon.addHeaderCell(new Cell()
                        .add(new Paragraph(h).setBold().setFontColor(DeviceRgb.WHITE).setFontSize(9))
                        .setBackgroundColor(colorAzul).setPadding(5));

                int idx = 1;
                for (Map<String, Object> d : donaciones) {
                    tDon.addCell(new Cell().add(new Paragraph(String.valueOf(idx++)).setFontSize(9)).setPadding(4));
                    tDon.addCell(new Cell().add(new Paragraph(str(d, "descripcion")).setFontSize(9)).setPadding(4));
                    tDon.addCell(new Cell().add(new Paragraph(str(d, "nombre_donante")).setFontSize(9)).setPadding(4));
                    tDon.addCell(new Cell().add(new Paragraph(str(d, "nombre_categoria")).setFontSize(9)).setPadding(4));
                    tDon.addCell(new Cell().add(new Paragraph(str(d, "fundacion_nombre")).setFontSize(9)).setPadding(4));
                    tDon.addCell(new Cell().add(new Paragraph(str(d, "cantidad")).setFontSize(9).setTextAlignment(TextAlignment.CENTER)).setPadding(4));
                    String est = d.containsKey("estado_fundacion") && d.get("estado_fundacion") != null
                        ? d.get("estado_fundacion").toString() : str(d, "estado");
                    tDon.addCell(new Cell().add(new Paragraph(est).setFontSize(9).setTextAlignment(TextAlignment.CENTER)).setPadding(4));
                }
                document.add(tDon);
                document.add(new Paragraph(" ").setMarginBottom(15));
            }

            // ══════════════════════════════════════
            // SECCIÓN 2 — FUNDACIONES (solo si hay)
            // ══════════════════════════════════════
            if (hayFundaciones) {
                document.add(new Paragraph("🏛️ Fundaciones (" + fundaciones.size() + ")")
                    .setBold().setFontSize(14).setFontColor(colorVerde).setMarginBottom(5).setMarginTop(10));

                Table tFun = new Table(new float[]{30f, 150f, 80f, 150f, 90f, 80f}).useAllAvailableWidth();
                String[] hFun = {"#", "Nombre", "NIT", "Correo", "Fecha Registro", "Estado"};
                for (String h : hFun)
                    tFun.addHeaderCell(new Cell()
                        .add(new Paragraph(h).setBold().setFontColor(DeviceRgb.WHITE).setFontSize(9))
                        .setBackgroundColor(colorVerde).setPadding(5));

                int idx = 1;
                for (Map<String, Object> f : fundaciones) {
                    tFun.addCell(new Cell().add(new Paragraph(String.valueOf(idx++)).setFontSize(9)).setPadding(4));
                    tFun.addCell(new Cell().add(new Paragraph(str(f, "nombre")).setFontSize(9)).setPadding(4));
                    tFun.addCell(new Cell().add(new Paragraph(str(f, "nit")).setFontSize(9)).setPadding(4));
                    tFun.addCell(new Cell().add(new Paragraph(str(f, "correo")).setFontSize(9)).setPadding(4));
                    tFun.addCell(new Cell().add(new Paragraph(str(f, "fecha_registro")).setFontSize(9)).setPadding(4));
                    tFun.addCell(new Cell().add(new Paragraph(str(f, "estado_validacion")).setFontSize(9).setTextAlignment(TextAlignment.CENTER)).setPadding(4));
                }
                document.add(tFun);
                document.add(new Paragraph(" ").setMarginBottom(15));
            }

            // ══════════════════════════════════════
            // SECCIÓN 3 — DONANTES (solo si hay)
            // ══════════════════════════════════════
            if (hayDonantes) {
                document.add(new Paragraph("👥 Donantes (" + donantes.size() + ")")
                    .setBold().setFontSize(14).setFontColor(colorMorado).setMarginBottom(5).setMarginTop(10));

                Table tDonan = new Table(new float[]{30f, 160f, 180f, 100f, 80f}).useAllAvailableWidth();
                String[] hDonan = {"#", "Nombre", "Correo", "Fecha Registro", "Estado"};
                for (String h : hDonan)
                    tDonan.addHeaderCell(new Cell()
                        .add(new Paragraph(h).setBold().setFontColor(DeviceRgb.WHITE).setFontSize(9))
                        .setBackgroundColor(colorMorado).setPadding(5));

                int idx = 1;
                for (Map<String, Object> d : donantes) {
                    tDonan.addCell(new Cell().add(new Paragraph(String.valueOf(idx++)).setFontSize(9)).setPadding(4));
                    tDonan.addCell(new Cell().add(new Paragraph(str(d, "nombre")).setFontSize(9)).setPadding(4));
                    tDonan.addCell(new Cell().add(new Paragraph(str(d, "correo")).setFontSize(9)).setPadding(4));
                    tDonan.addCell(new Cell().add(new Paragraph(str(d, "fecha_registro")).setFontSize(9)).setPadding(4));
                    tDonan.addCell(new Cell().add(new Paragraph(str(d, "estado")).setFontSize(9).setTextAlignment(TextAlignment.CENTER)).setPadding(4));
                }
                document.add(tDonan);
            }

            // Si no hay nada en ninguna sección
            if (!hayDonaciones && !hayFundaciones && !hayDonantes) {
                document.add(new Paragraph("No se encontraron resultados con los filtros seleccionados.")
                    .setTextAlignment(TextAlignment.CENTER)
                    .setFontSize(13)
                    .setFontColor(new DeviceRgb(150, 150, 150))
                    .setMarginTop(30));
            }

            document.close();
        } catch (Exception e) { e.printStackTrace(); }
        return out.toByteArray();
    }

    // Helper para leer campos del Map sin NPE
    private String str(Map<String, Object> map, String key) {
        Object val = map.get(key);
        return val != null ? val.toString() : "";
    }

    // ── PIE DE PÁGINA ──
    private class FooterHandler implements IEventHandler {
        @Override
        public void handleEvent(Event event) {
            PdfDocumentEvent docEvent = (PdfDocumentEvent) event;
            PdfPage page = docEvent.getPage();
            Rectangle pageSize = page.getPageSize();
            PdfCanvas pdfCanvas = new PdfCanvas(page);
            Canvas canvas = new Canvas(pdfCanvas, pageSize);
            canvas.showTextAligned(
                new Paragraph("© 2026 Red Solidaria - Uniendo corazones.")
                    .setFontSize(10).setFontColor(new DeviceRgb(120, 120, 120)),
                pageSize.getWidth() / 2, 20, TextAlignment.CENTER);
            canvas.close();
        }
    }
}