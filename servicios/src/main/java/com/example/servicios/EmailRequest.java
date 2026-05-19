package com.example.servicios;

import java.util.List;
import java.util.Map;

public class EmailRequest {

    private String nombreDonador;
    private String destinatario;
    private String nombreFundacion;
    private String estado;

    // ── NUEVO: motivo/mensaje para notificaciones como ELIMINADO ──
    private String mensaje;

    // Campos para el reporte
    private String nit;
    private int cantidadDonaciones;
    private String categoriaFiltrada;
    private String estadoFiltrado;
    private int fundacionId;

    // Listas para el PDF
    private List<Map<String, Object>> donaciones;

    // Para el reporte admin con 3 secciones
    private List<Map<String, Object>> fundaciones;
    private List<Map<String, Object>> donantes;

    // ── Getters y Setters ──

    public String getNombreDonador() { return nombreDonador; }
    public void setNombreDonador(String nombreDonador) { this.nombreDonador = nombreDonador; }

    public String getDestinatario() { return destinatario; }
    public void setDestinatario(String destinatario) { this.destinatario = destinatario; }

    public String getNombreFundacion() { return nombreFundacion; }
    public void setNombreFundacion(String nombreFundacion) { this.nombreFundacion = nombreFundacion; }

    public String getEstado() { return estado; }
    public void setEstado(String estado) { this.estado = estado; }

    public String getMensaje() { return mensaje; }
    public void setMensaje(String mensaje) { this.mensaje = mensaje; }

    public String getNit() { return nit; }
    public void setNit(String nit) { this.nit = nit; }

    public int getCantidadDonaciones() { return cantidadDonaciones; }
    public void setCantidadDonaciones(int cantidadDonaciones) { this.cantidadDonaciones = cantidadDonaciones; }

    public String getCategoriaFiltrada() { return categoriaFiltrada; }
    public void setCategoriaFiltrada(String categoriaFiltrada) { this.categoriaFiltrada = categoriaFiltrada; }

    public String getEstadoFiltrado() { return estadoFiltrado; }
    public void setEstadoFiltrado(String estadoFiltrado) { this.estadoFiltrado = estadoFiltrado; }

    public int getFundacionId() { return fundacionId; }
    public void setFundacionId(int fundacionId) { this.fundacionId = fundacionId; }

    public List<Map<String, Object>> getDonaciones() { return donaciones; }
    public void setDonaciones(List<Map<String, Object>> donaciones) { this.donaciones = donaciones; }

    public List<Map<String, Object>> getFundaciones() { return fundaciones; }
    public void setFundaciones(List<Map<String, Object>> fundaciones) { this.fundaciones = fundaciones; }

    public List<Map<String, Object>> getDonantes() { return donantes; }
    public void setDonantes(List<Map<String, Object>> donantes) { this.donantes = donantes; }
}