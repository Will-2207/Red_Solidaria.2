package com.example.servicios; 

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.io.ClassPathResource;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.mail.javamail.MimeMessageHelper;
import org.springframework.stereotype.Service;
import org.springframework.core.io.ByteArrayResource;
import jakarta.mail.util.ByteArrayDataSource;
// ... los que ya tenías

import jakarta.mail.internet.MimeMessage;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;

@Service
public class EmailService {

    @Autowired
    private JavaMailSender mailSender;

    public void enviarNotificacion(EmailRequest request) {
        try {
            MimeMessage message = mailSender.createMimeMessage();
            MimeMessageHelper helper = new MimeMessageHelper(message, true, "UTF-8");

            helper.setTo(request.getDestinatario());

            String subject      = "";
            String mensajeCuerpo = "";
            String botonTexto   = "Ir al Panel";
            String colorInicio  = "#1e52ff";
            String colorFin     = "#63ff5e";
            String colorBoton   = "#28a745";

            switch (request.getEstado().toUpperCase()) {

                case "PENDIENTE":
                    subject      = "Solicitud Recibida - Red Solidaria";
                    mensajeCuerpo = "Hemos recibido tu registro. Tu cuenta está en proceso de validación por nuestro equipo técnico.";
                    botonTexto   = "Ver mi Estado";
                    break;

                case "APROBADO":
                    subject      = "¡Felicidades! Tu cuenta ha sido activada";
                    mensajeCuerpo = "¡Buenas noticias! Tu cuenta ha sido activada con éxito. Ya puedes acceder al panel para gestionar donaciones.";
                    break;

                case "RECHAZADO":
                    subject      = "Información sobre tu solicitud";
                    colorInicio  = "#ff0000";
                    colorFin     = "#dc2626";
                    colorBoton   = "#b91c1c";
                    mensajeCuerpo = "Lamentamos informarte que tu solicitud no pudo ser aprobada en este momento.";
                    botonTexto   = "Contactar Soporte";
                    break;

                // ── NUEVO: ELIMINADO ──────────────────────────────
                // ── ACTUALIZADO: ELIMINADO (Donantes y Fundaciones) ──
                case "ELIMINADO":
                    subject = "Notificación de cuenta - Red Solidaria";
                    colorInicio = "#7f1d1d";
                    colorFin = "#dc2626";
                    colorBoton = "#b91c1c";
                    botonTexto = "Contactar Soporte";

                    // El motivo viene en el campo mensaje del request (ya sea predefinido o "Otros")
                    String motivoElim = (request.getMensaje() != null && !request.getMensaje().isEmpty())
                            ? request.getMensaje()
                            : "Decisión administrativa de Red Solidaria.";

                    mensajeCuerpo = 
                        "Lamentamos informarte que tu cuenta en la plataforma <b>Red Solidaria</b> ha sido eliminada.<br><br>" +
                        "<div style='background:#fff0f0;border-left:4px solid #dc2626;padding:15px;border-radius:8px;margin:10px 0;text-align:left;color:#333;'>" +
                        "<b>Motivo de la baja:</b><br>" + motivoElim +
                        "</div><br>" +
                        "Si consideras que esta acción es un error, por favor ponte en contacto con nuestro equipo de soporte.";
                    break;
                // ─────────────────────────────────────────────────

                case "RECIBIDO":
                    subject      = "¡Gracias por tu donación!";
                    mensajeCuerpo = "Queremos agradecerte sinceramente por tu generosa donación. <br><br>" +
                        "<b>Detalle de la donación:</b><br>" +
                        (request.getCategoriaFiltrada() != null ? ("Categoría: <b>" + request.getCategoriaFiltrada() + "</b><br>") : "") +
                        (request.getEstadoFiltrado()    != null ? ("Estado: <b>"    + request.getEstadoFiltrado()    + "</b><br>") : "") +
                        (request.getDonaciones() != null && !request.getDonaciones().isEmpty()
                            ? ("Descripción: <b>" + request.getDonaciones().get(0).getOrDefault("descripcion", "") + "</b><br>")
                            : "") +
                        "<br>¡Tu ayuda marca la diferencia!";
                    botonTexto   = "Ver mi donación";
                    break;

                case "RECHAZADO_DONACION":
                    subject      = "Tu donación ha sido rechazada";
                    mensajeCuerpo = "Lamentamos informarte que tu donación no cumple con los requisitos de la fundación y ha sido rechazada.<br><br>" +
                        (request.getCategoriaFiltrada() != null ? ("Categoría: <b>" + request.getCategoriaFiltrada() + "</b><br>") : "") +
                        (request.getEstadoFiltrado()    != null ? ("Estado: <b>"    + request.getEstadoFiltrado()    + "</b><br>") : "") +
                        (request.getDonaciones() != null && !request.getDonaciones().isEmpty()
                            ? ("Descripción: <b>" + request.getDonaciones().get(0).getOrDefault("descripcion", "") + "</b><br>")
                            : "") +
                        "<br>Te invitamos a revisar los requisitos y volver a intentarlo.";
                    botonTexto   = "Ver detalles";
                    colorInicio  = "#ff0000";
                    colorFin     = "#dc2626";
                    colorBoton   = "#b91c1c";
                    break;

                default:
                    subject      = "Notificación - Red Solidaria";
                    mensajeCuerpo = "Tienes una notificación pendiente en Red Solidaria.";
                    break;
            }

            helper.setSubject(subject);

            String htmlContent =
                "<div style='font-family:\"Segoe UI\",Tahoma,Geneva,Verdana,sans-serif;background-color:#f0f2f5;padding:20px;'>" +
                    "<div style='max-width:600px;margin:auto;background:white;border-radius:20px;overflow:hidden;" +
                             "box-shadow:0 20px 50px rgba(0,0,0,0.15);border:1px solid #e1e1e1;'>" +
                        "<div style='background:linear-gradient(135deg," + colorInicio + " 0%," + colorFin + " 100%);" +
                                 "padding:40px;text-align:center;color:white;'>" +
                            "<img src='cid:logoImage' alt='Logo' style='max-height:85px;background:white;" +
                                 "padding:10px;border-radius:15px;margin-bottom:15px;'/>" +
                            "<h1 style='margin:0;font-size:30px;font-weight:bold;text-shadow:1px 1px 4px rgba(0,0,0,0.2);'>" +
                                "Red Solidaria</h1>" +
                        "</div>" +
                        "<div style='padding:45px;text-align:center;background-color:#fffef5;'>" +
                            "<h2 style='color:#333;font-size:24px;margin-bottom:20px;'>¡Hola, " + request.getNombreFundacion() + "!</h2>" +
                            "<p style='color:#555;font-size:17px;line-height:1.6;'>" + mensajeCuerpo + "</p>" +
                            "<br><br>" +
                            "<a href='http://localhost:5000/login' style='background:linear-gradient(135deg," + colorBoton + ",#20c997);" +
                                 "color:white;padding:16px 35px;text-decoration:none;border-radius:12px;" +
                                 "font-weight:bold;font-size:16px;display:inline-block;text-transform:uppercase;" +
                                 "letter-spacing:1px;box-shadow:0 5px 20px rgba(40,167,69,0.3);'>" +
                                 botonTexto + "</a>" +
                        "</div>" +
                        "<div style='background-color:#f8f9fa;padding:20px;text-align:center;font-size:13px;" +
                                 "color:#777;border-top:1px solid #eee;'>" +
                            "Estás recibiendo este correo porque formas parte de la <b>Red Solidaria</b>.<br>" +
                            "© 2026 Red Solidaria - Uniendo corazones." +
                        "</div>" +
                    "</div>" +
                "</div>";

            helper.setText(htmlContent, true);
            ClassPathResource image = new ClassPathResource("static/images/logo.jpeg");
            helper.addInline("logoImage", image);
            mailSender.send(message);
            System.out.println("✅ Notificación de estado enviada!");

        } catch (Exception e) {
            System.out.println("❌ Error: " + e.getMessage());
            e.printStackTrace();
        }
    }

    public void enviarReporteEmail(EmailRequest request, byte[] pdfContenido, String tipoReporte) {
    try {
        MimeMessage message = mailSender.createMimeMessage();
        MimeMessageHelper helper = new MimeMessageHelper(message, true, "UTF-8");

        helper.setTo(request.getDestinatario());
        
        // Colores y estilos originales (¡Se mantienen intactos!)
        String colorInicio = "#1e52ff";
        String colorFin    = "#63ff5e";
        String colorBoton  = "#28a745";

        // 1. Determinar saludo y asunto según el tipo de reporte
        String nombreUsuario = "Usuario";
        String asunto = "Reporte de Actividad - Red Solidaria";
        
        if ("ADMIN".equalsIgnoreCase(tipoReporte)) {
            nombreUsuario = (request.getNombreFundacion() != null) ? request.getNombreFundacion() : "Administrador";
            asunto = "Reporte Global Administrativo - Red Solidaria";
        } else if ("FUNDACION".equalsIgnoreCase(tipoReporte)) {
            nombreUsuario = (request.getNombreFundacion() != null) ? request.getNombreFundacion() : "Fundación";
            asunto = "Reporte de Actividad - " + nombreUsuario;
        } else if ("DONANTE".equalsIgnoreCase(tipoReporte)) {
            nombreUsuario = (request.getNombreDonador() != null) ? request.getNombreDonador() : "Donante";
            asunto = "Tu Reporte de Donaciones - Red Solidaria";
        }

        helper.setSubject(asunto);

        String categoriaParaUrl = (request.getCategoriaFiltrada() != null && !request.getCategoriaFiltrada().isEmpty())
                                  ? request.getCategoriaFiltrada() : "Todas";

        // 2. Construcción DINÁMICA de la URL de descarga según el tipo de reporte
        String urlDescarga = "http://localhost:8080/api/email/";
        if ("ADMIN".equalsIgnoreCase(tipoReporte)) {
            urlDescarga += "descargar-reporte-admin?nombre=" + URLEncoder.encode(nombreUsuario, StandardCharsets.UTF_8) +
                           "&categoria=" + URLEncoder.encode(categoriaParaUrl, StandardCharsets.UTF_8) +
                           "&nit=" + (request.getNit() != null ? request.getNit() : "") +
                           "&fundacion_id=" + request.getFundacionId();
        } else if ("FUNDACION".equalsIgnoreCase(tipoReporte)) {
            urlDescarga += "descargar-reporte-fundacion?fundacion_id=" + request.getFundacionId() +
                           "&categoria=" + URLEncoder.encode(categoriaParaUrl, StandardCharsets.UTF_8);
        } else if ("DONANTE".equalsIgnoreCase(tipoReporte)) {
            // Ajusta este endpoint según cómo tengas configurada la descarga del donante en Flask/Spring
            urlDescarga += "descargar-reporte-donante?correo=" + URLEncoder.encode(request.getDestinatario(), StandardCharsets.UTF_8);
        }

        if (request.getEstadoFiltrado() != null && !request.getEstadoFiltrado().isEmpty()) {
            urlDescarga += "&est=" + URLEncoder.encode(request.getEstadoFiltrado(), StandardCharsets.UTF_8);
        }

        // 3. Renderizado del HTML con los bloques condicionales
        String htmlContent =
            "<div style='font-family:\"Segoe UI\",Tahoma,Geneva,Verdana,sans-serif;background-color:#f0f2f5;padding:20px;'>" +
                "<div style='max-width:600px;margin:auto;background:white;border-radius:20px;overflow:hidden;" +
                          "box-shadow:0 20px 50px rgba(0,0,0,0.15);border:1px solid #e1e1e1;'>" +
                    
                    "<div style='background:linear-gradient(135deg," + colorInicio + " 0%," + colorFin + " 100%);" +
                               "padding:40px;text-align:center;color:white;'>" +
                        "<img src='cid:logoImage' alt='Logo' style='max-height:85px;background:white;" +
                               "padding:10px;border-radius:15px;margin-bottom:15px;'/>" +
                        "<h1 style='margin:0;font-size:28px;font-weight:bold;'>Reporte de Donaciones</h1>" +
                        "<p style='margin-top:10px;opacity:0.9;font-size:18px;'>" + nombreUsuario + "</p>" +
                    "</div>" +
                    
                    "<div style='padding:40px;text-align:center;background-color:#fffef5;'>" +
                        "<h2 style='color:#333;'>¡Hola, " + nombreUsuario + "!</h2>" +
                        
                        // Mostrar NIT solo si aplica (Admin o Fundación)
                        (!"DONANTE".equalsIgnoreCase(tipoReporte) && request.getNit() != null ? 
                            "<p style='color:#555;font-size:16px;margin-bottom:20px;'>NIT: <b>" + request.getNit() + "</b></p>" : "") + 
                        
                        "<p style='color:#555;font-size:16px;'>Hemos generado el reporte detallado solicitado. Puedes descargarlo de manera segura utilizando el siguiente botón:</p>" +
                        
                        "<div style='background:#f8f9fa;border-radius:15px;padding:25px;margin:25px 0;text-align:left;border:1px dashed #ccc;'>" +
                            "<p style='margin:5px 0;'><b>Filtro Categoría:</b> " + categoriaParaUrl + "</p>" +
                            (request.getEstadoFiltrado() != null && !request.getEstadoFiltrado().isEmpty() && !request.getEstadoFiltrado().equalsIgnoreCase("Todos")
                                ? "<p style='margin:5px 0;'><b>Filtro Estado:</b> " + request.getEstadoFiltrado() + "</p>" : "") +
                            
                            "<div style='margin-top:15px;padding-top:15px;border-top:2px solid " + colorFin + ";'>" +
                                // Total Donaciones se muestra para todos
                                (request.getCantidadDonaciones() > 0
                                    ? "<p style='font-size:16px;margin:3px 0;'><b>📦 Total Donaciones:</b> <span style='color:" + colorInicio + ";font-weight:800;'>" + request.getCantidadDonaciones() + "</span></p>" : "") +
                                
                                // Secciones Administrativas: SOLO se muestran si el tipo es ADMIN
                                ("ADMIN".equalsIgnoreCase(tipoReporte) && request.getFundaciones() != null && !request.getFundaciones().isEmpty()
                                    ? "<p style='font-size:16px;margin:3px 0;'><b>🏛️ Total Fundaciones:</b> <span style='color:" + colorInicio + ";font-weight:800;'>" + request.getFundaciones().size() + "</span></p>" : "") +
                                ("ADMIN".equalsIgnoreCase(tipoReporte) && request.getDonantes() != null && !request.getDonantes().isEmpty()
                                    ? "<p style='font-size:16px;margin:3px 0;'><b>👥 Total Donantes:</b> <span style='color:" + colorInicio + ";font-weight:800;'>" + request.getDonantes().size() + "</span></p>" : "") +
                            "</div>" +
                        "</div>" +
                        
                        "<p style='color:#777;font-size:14px;'>Haz clic en el botón para obtener el documento PDF:</p><br>" +
                        "<a href='" + urlDescarga + "' style='background:linear-gradient(135deg," + colorBoton + ",#20c997);" +
                              "color:white;padding:16px 35px;text-decoration:none;border-radius:12px;" +
                              "font-weight:bold;font-size:16px;display:inline-block;text-transform:uppercase;" +
                              "box-shadow:0 5px 20px rgba(40,167,69,0.3);'>DESCARGAR REPORTE PDF</a>" +
                    "</div>" +

                    "<div style='background-color:#f8f9fa;padding:20px;text-align:center;font-size:13px;" +
                              "color:#777;border-top:1px solid #eee;'>" +
                        "Este es un reporte automático generado por el sistema <b>Red Solidaria</b>.<br>" +
                        "© 2026 Red Solidaria - Uniendo corazones." +
                    "</div>" +
                "</div>" +
            "</div>";

        helper.setText(htmlContent, true);

        ClassPathResource image = new ClassPathResource("static/images/logo.jpeg");
        helper.addInline("logoImage", image);

        mailSender.send(message);
        System.out.println("✅ Reporte (" + tipoReporte + ") enviado con éxito a: " + request.getDestinatario());

    } catch (Exception e) {
        System.out.println("❌ Error al enviar el correo de reporte: " + e.getMessage());
        e.printStackTrace();
    }
}

}