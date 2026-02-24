#!/usr/bin/env python3
# =============================================================================
# SISTEMA DE SEGUIMIENTO DE FORMACIÓN - ÁREA IIAD / ICA
# Versión 1.0 | Desarrollado para cumplimiento ISO 17034 & ISO 17043
# =============================================================================
# INSTALACIÓN:
#   pip install streamlit pandas plotly openpyxl
# EJECUCIÓN:
#   streamlit run app_iiad.py
# =============================================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import os
from datetime import datetime, date
from io import BytesIO

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN GENERAL DE LA APP
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Sistema Formación IIAD - ICA",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_PATH = "iiad_formacion.db"

# ─────────────────────────────────────────────────────────────────────────────
# INICIALIZACIÓN DE BASE DE DATOS
# ─────────────────────────────────────────────────────────────────────────────
def init_db():
    """Crea las tablas si no existen y carga datos iniciales."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS personal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            rol TEXT NOT NULL,
            fecha_ingreso TEXT,
            estado TEXT DEFAULT 'Activo'
        );

        CREATE TABLE IF NOT EXISTS documentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT NOT NULL,
            nombre TEXT NOT NULL,
            categoria TEXT,
            horas REAL,
            nivel TEXT,
            norma_cubierta TEXT,
            es_critico INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS requisitos_rol (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rol TEXT NOT NULL,
            documento_id INTEGER,
            FOREIGN KEY (documento_id) REFERENCES documentos(id)
        );

        CREATE TABLE IF NOT EXISTS avances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            persona_id INTEGER,
            documento_id INTEGER,
            estado TEXT DEFAULT 'Pendiente',
            fecha_inicio TEXT,
            fecha_completitud TEXT,
            calificacion REAL,
            observaciones TEXT,
            registrado_por TEXT,
            timestamp_registro TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (persona_id) REFERENCES personal(id),
            FOREIGN KEY (documento_id) REFERENCES documentos(id)
        );

        CREATE TABLE IF NOT EXISTS cronograma (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            semana INTEGER,
            mes INTEGER,
            mes_nombre TEXT,
            bloque TEXT,
            documento_id INTEGER,
            codigo_doc TEXT,
            nombre_actividad TEXT,
            horas REAL,
            roles_aplicables TEXT,
            modalidad TEXT,
            prioridad TEXT,
            FOREIGN KEY (documento_id) REFERENCES documentos(id)
        );
    """)

    # Cargar datos iniciales si las tablas están vacías
    if c.execute("SELECT COUNT(*) FROM documentos").fetchone()[0] == 0:
        _cargar_datos_iniciales(c)

    conn.commit()
    conn.close()


def _cargar_datos_iniciales(c):
    """Carga el catálogo de documentos y roles del área IIAD."""

    # ── DOCUMENTOS ──────────────────────────────────────────────────────────
    documentos = [
        # (codigo, nombre, categoria, horas, nivel, norma, es_critico)
        ("GSA-SAD-MC-001",  "Manual del Sistema de Calidad SAD",         "SGC Base",          1.5, "Nivel 2", "ISO 17034 §8 / ISO 17043 §8",       1),
        ("GSA-SAD-MC-003",  "Manual Técnico Áreas de Referencia",        "SGC Base",          4.0, "Nivel 4", "ISO 17034 §8.2 / ISO 17043 §8.2",   1),
        ("GSA-SAD-P-009",   "Confidencialidad e Imparcialidad SAD",      "SGC Base",          1.5, "Nivel 2", "ISO 17034 §4.2-4.3 / ISO 17043 §4.1-4.2", 1),
        ("GSA-SAD-P-020",   "Manejo de documentos y registros SAD",      "SGC Base",          1.5, "Nivel 2", "ISO 17034 §8.4 / ISO 17043 §8.3",   0),
        ("GSA-I-SAD-020",   "Manejo documentos en subgerencia",          "SGC Base",          1.5, "Nivel 2", "ISO 17034 §8.3 / ISO 17043 §8.2",   0),
        ("GSA-SAD-P-012",   "Gestión del Personal SAD",                  "SGC Base",          3.0, "Nivel 3", "ISO 17034 §6.1.4 / ISO 17043 §6.2.3", 0),
        ("GSA-SAD-P-013",   "Supervisión en la SAD",                     "SGC Base",          1.5, "Nivel 2", "ISO 17034 §6.1.1 / ISO 17043 §6.2.1", 0),
        ("GSA-SAD-G-012",   "Guía requisitos formación personal",        "SGC Base",          1.5, "Nivel 2", "ISO 17034 §6.1.4 / ISO 17043 §6.2.3", 0),
        # Normas ISO
        ("ISO 17034:2017",  "ISO 17034:2017 - Requisitos PMR",           "Normas ISO",        4.0, "Nivel 4", "Norma completa PMR",                 1),
        ("ISO 17043:2023",  "ISO/IEC 17043:2023 - Requisitos PEA",       "Normas ISO",        4.0, "Nivel 4", "Norma completa PEA",                 1),
        ("ISO 17025:2017",  "ISO/IEC 17025:2017 - Laboratorios",         "Normas ISO",        3.0, "Nivel 3", "Base laboratorios",                  0),
        ("ISO 13528:2022",  "ISO 13528:2022 - Métodos Estadísticos PT",  "Normas ISO",        8.0, "Nivel 4", "ISO 17043 §7.2.2-7.4",               1),
        ("ISO 33405:2022",  "ISO 33405:2022 - Homog. y Estabilidad",     "Normas ISO",        4.0, "Nivel 4", "ISO 17034 §7.10-7.11",               1),
        ("ISO 33403:2023",  "ISO 33403:2023 - Caracterización MR",       "Normas ISO",        4.0, "Nivel 4", "ISO 17034 §7.12",                    1),
        ("ISO 33402:2022",  "ISO 33402:2022 - Certificados MRC",         "Normas ISO",        3.0, "Nivel 3", "ISO 17034 §7.14",                    0),
        ("ISO Guide 30",    "ISO Guide 30:2015 - Términos MR",           "Normas ISO",        1.5, "Nivel 2", "Definiciones MR",                    0),
        ("ISO 2859-1",      "ISO 2859-1 - Muestreo",                     "Normas ISO",        3.0, "Nivel 3", "ISO 17034 §7.10",                    0),
        # Procesos técnicos
        ("GSA-SAD-P-024",   "Planificación y control producción MR",     "Proceso Técnico",   3.0, "Nivel 3", "ISO 17034 §7.2-7.3",                 1),
        ("GSA-SAD-P-026",   "Evaluación Homogeneidad y Estabilidad",     "Proceso Técnico",   4.0, "Nivel 4", "ISO 17034 §7.10-7.11",               1),
        ("GSA-SAD-P-031",   "Diseño y planificación EA/CI",              "Proceso Técnico",   4.0, "Nivel 4", "ISO 17043 §7.2.1-7.2.2",             1),
        ("GSA-SAD-P-033",   "Diseño estadístico PT",                     "Proceso Técnico",   4.0, "Nivel 4", "ISO 17043 §7.2.2",                   1),
        ("GSA-SAD-P-030",   "Gestión de ítems de ensayo",                "Proceso Técnico",   3.0, "Nivel 3", "ISO 17034 §7.5 / ISO 17043 §7.3.1",  0),
        ("GSA-SAD-P-027",   "Análisis y reporte datos PT",               "Proceso Técnico",   4.0, "Nivel 4", "ISO 17043 §7.4.1-7.4.2",             1),
        ("GSA-SAD-P-003",   "Estimación de Incertidumbre",               "Proceso Técnico",   4.0, "Nivel 4", "ISO 17034 §7.13",                    0),
        ("GSA-SAD-P-002",   "Validación/Verificación de métodos",        "Proceso Técnico",   4.0, "Nivel 4", "ISO 17034 §7.6 / ISO 17043 §6.1.2",  0),
        # SGC Operativo
        ("GSA-SAD-P-001",   "Gestión de equipos",                        "SGC Operativo",     3.0, "Nivel 3", "ISO 17034 §7.7",                     0),
        ("GSA-SAD-P-004",   "Trabajo no conforme",                       "SGC Operativo",     3.0, "Nivel 3", "ISO 17034 §7.17 / ISO 17043 §7.5.4", 0),
        ("GSA-SAD-P-007",   "Emisión de reportes e informes",            "SGC Operativo",     3.0, "Nivel 3", "ISO 17034 §7.14",                    0),
        ("GSA-SAD-P-006",   "Revisión solicitudes de servicios",         "SGC Operativo",     1.5, "Nivel 2", "ISO 17034 §4.1 / ISO 17043 §7.1.1",  0),
        ("GSA-SAD-P-008",   "Adquisiciones",                             "SGC Operativo",     1.5, "Nivel 2", "ISO 17034 §6.2",                     0),
        ("GSA-SAD-P-014",   "Instalaciones y condiciones ambientales",   "SGC Operativo",     1.5, "Nivel 2", "ISO 17034 §7.17 / ISO 17043 §7.5.4", 0),
        ("GSA-SAD-P-017",   "Recepción de ítems",                        "SGC Operativo",     1.5, "Nivel 2", "ISO 17034 §7.5",                     0),
        ("GSA-SAD-P-025",   "Distribución MR e ítems EA",                "SGC Operativo",     1.5, "Nivel 2", "ISO 17034 §7.15 / ISO 17043 §7.3.4", 0),
        ("GSA-I-SAD-006",   "Auditorías internas en laboratorios",       "SGC Operativo",     1.5, "Nivel 2", "ISO 17034 §8.7 / ISO 17043 §8.8",    0),
        ("GSA-I-SAD-039",   "Trabajos colaborativos MR/CI/EA",           "SGC Operativo",     3.0, "Nivel 3", "ISO 17034 §6.2 / ISO 17043 §6.4",    0),
        ("GSA-I-SAD-040",   "Requisitos de Registros MR y EA",           "SGC Operativo",     3.0, "Nivel 3", "ISO 17034 §7.14-7.16",               0),
        ("GSA-I-SAD-041",   "Integridad SGC ante cambios",               "SGC Operativo",     3.0, "Nivel 3", "ISO 17034 §5.5 / ISO 17043 §5.5",    0),
        # Calidad Avanzada
        ("GSA-I-SAD-001",   "Quejas en laboratorios",                    "Calidad Avanzada",  3.0, "Nivel 3", "ISO 17034 §7.18 / ISO 17043 §7.6",   0),
        ("GSA-I-SAD-007",   "Acciones correctivas y de mejora",          "Calidad Avanzada",  3.0, "Nivel 3", "ISO 17034 §8.9 / ISO 17043 §8.7",    0),
        ("GSA-SAD-007",     "Acciones correctivas SAD",                  "Calidad Avanzada",  1.5, "Nivel 2", "Mejora continua",                    0),
        ("GSA-I-SAD-038",   "Riesgos y oportunidades",                   "Calidad Avanzada",  3.0, "Nivel 3", "ISO 17034 §8.8 / ISO 17043 §8.5",    0),
        ("GSA-I-SAD-042",   "Apelaciones EA",                            "Calidad Avanzada",  3.0, "Nivel 3", "ISO 17043 §7.7",                     0),
        ("GSA-I-SAD-012",   "Revisión del sistema de gestión",           "Calidad Avanzada",  1.5, "Nivel 2", "ISO 17034 §8.6 / ISO 17043 §8.9",    0),
        ("GSA-SAD-G-004",   "Gestión de riesgos imparcialidad",          "Calidad Avanzada",  3.0, "Nivel 3", "ISO 17034 §4.2 / ISO 17043 §4.1",    0),
        ("GSA-SAD-G-006",   "Matriz de Autoridad",                       "Calidad Avanzada",  4.0, "Nivel 4", "ISO 17034 §5.5 / ISO 17043 §5.5",    0),
        ("GSA-SAD-G-007",   "Interacción y coordinación de roles",       "Calidad Avanzada",  3.0, "Nivel 3", "ISO 17034 §5.5 / ISO 17043 §5.5",    0),
        ("GSA-SAD-G-015",   "Matriz de objetivos de calidad",            "Calidad Avanzada",  4.0, "Nivel 4", "ISO 17034 §8.8 / ISO 17043 §8.6",    0),
    ]
    c.executemany(
        "INSERT INTO documentos (codigo, nombre, categoria, horas, nivel, norma_cubierta, es_critico) VALUES (?,?,?,?,?,?,?)",
        documentos
    )

    # ── REQUISITOS POR ROL ──────────────────────────────────────────────────
    # Todos los roles comunes
    docs_todos = [
        "GSA-SAD-MC-001","GSA-SAD-MC-003","GSA-SAD-P-009","GSA-SAD-P-020",
        "GSA-I-SAD-020","GSA-SAD-P-013","GSA-SAD-G-012","ISO 17025:2017",
        "ISO Guide 30","GSA-SAD-P-003","GSA-SAD-P-014","GSA-SAD-P-017",
        "GSA-SAD-P-008","GSA-I-SAD-006","GSA-SAD-007"
    ]
    roles_config = {
        "Responsable área IIAD": docs_todos + [
            "GSA-SAD-P-012","ISO 17034:2017","ISO 17043:2023","ISO 13528:2022",
            "ISO 33405:2022","ISO 33403:2023","ISO 33402:2022","ISO 2859-1",
            "GSA-SAD-P-024","GSA-SAD-P-026","GSA-SAD-P-031","GSA-SAD-P-033",
            "GSA-SAD-P-030","GSA-SAD-P-027","GSA-SAD-P-002","GSA-SAD-P-001",
            "GSA-SAD-P-004","GSA-SAD-P-007","GSA-I-SAD-039","GSA-I-SAD-040",
            "GSA-I-SAD-041","GSA-I-SAD-038","GSA-I-SAD-007","GSA-I-SAD-012",
            "GSA-SAD-G-004","GSA-SAD-G-006","GSA-SAD-G-007","GSA-SAD-G-015",
            "GSA-I-SAD-001"
        ],
        "Profesional área IIAD": docs_todos + [
            "GSA-SAD-P-012","ISO 17034:2017","ISO 33405:2022","ISO 33403:2023",
            "ISO 33402:2022","GSA-SAD-P-024","GSA-SAD-P-026","GSA-SAD-P-030",
            "GSA-SAD-P-002","GSA-SAD-P-004","GSA-SAD-P-025","GSA-I-SAD-039",
            "GSA-I-SAD-040","GSA-SAD-G-004"
        ],
        "Líder de producción": docs_todos + [
            "GSA-SAD-P-012","ISO 17034:2017","ISO 33405:2022","ISO 33403:2023",
            "ISO 33402:2022","ISO 2859-1","GSA-SAD-P-024","GSA-SAD-P-026",
            "GSA-SAD-P-030","GSA-SAD-P-002","GSA-SAD-P-001","GSA-SAD-P-004",
            "GSA-SAD-P-007","GSA-SAD-P-006","GSA-SAD-P-025","GSA-I-SAD-039",
            "GSA-I-SAD-040","GSA-I-SAD-007","GSA-I-SAD-001"
        ],
        "Líder de comparación": docs_todos + [
            "GSA-SAD-P-012","ISO 17043:2023","ISO 13528:2022","ISO 33405:2022",
            "ISO 2859-1","GSA-SAD-P-031","GSA-SAD-P-033","GSA-SAD-P-030",
            "GSA-SAD-P-027","GSA-SAD-P-002","GSA-SAD-P-001","GSA-SAD-P-004",
            "GSA-SAD-P-007","GSA-SAD-P-006","GSA-SAD-P-025","GSA-I-SAD-039",
            "GSA-I-SAD-040","GSA-I-SAD-041","GSA-I-SAD-007","GSA-I-SAD-001",
            "GSA-I-SAD-042","GSA-SAD-G-007"
        ],
        "Profesional análisis datos": docs_todos + [
            "ISO 17043:2023","ISO 13528:2022","ISO 33405:2022","ISO 33403:2023",
            "GSA-SAD-P-026","GSA-SAD-P-031","GSA-SAD-P-033","GSA-SAD-P-027",
            "GSA-I-SAD-038","GSA-I-SAD-012","GSA-I-SAD-040"
        ],
    }

    for rol, codigos in roles_config.items():
        for codigo in set(codigos):
            doc_id = c.execute("SELECT id FROM documentos WHERE codigo=?", (codigo,)).fetchone()
            if doc_id:
                c.execute("INSERT INTO requisitos_rol (rol, documento_id) VALUES (?,?)",
                          (rol, doc_id[0]))

    # ── PERSONAL DE EJEMPLO ─────────────────────────────────────────────────
    personal_ejemplo = [
        ("Juan Pérez García",     "Responsable área IIAD",     "2023-01-15", "Activo"),
        ("María González López",  "Profesional área IIAD",     "2024-03-20", "Activo"),
        ("Carlos Rodríguez M.",   "Líder de producción",       "2025-06-10", "Activo"),
        ("Ana Martínez Silva",    "Profesional análisis datos","2026-01-15", "Activo"),
        ("Pedro Gómez Torres",    "Líder de comparación",      "2024-09-01", "Activo"),
    ]
    c.executemany(
        "INSERT INTO personal (nombre, rol, fecha_ingreso, estado) VALUES (?,?,?,?)",
        personal_ejemplo
    )


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIONES DE ACCESO A DATOS
# ─────────────────────────────────────────────────────────────────────────────
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def get_personal():
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM personal WHERE estado='Activo' ORDER BY nombre", conn)
    conn.close()
    return df

def get_documentos():
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM documentos ORDER BY categoria, codigo", conn)
    conn.close()
    return df

def get_docs_por_rol(rol):
    conn = get_conn()
    df = pd.read_sql("""
        SELECT d.id, d.codigo, d.nombre, d.categoria, d.horas, d.nivel,
               d.norma_cubierta, d.es_critico
        FROM documentos d
        JOIN requisitos_rol rr ON d.id = rr.documento_id
        WHERE rr.rol = ?
        ORDER BY d.es_critico DESC, d.categoria, d.codigo
    """, conn, params=(rol,))
    conn.close()
    return df

def get_avance_persona(persona_id):
    conn = get_conn()
    df = pd.read_sql("""
        SELECT a.documento_id, a.estado, a.fecha_completitud,
               a.calificacion, a.observaciones, a.fecha_inicio
        FROM avances a
        WHERE a.persona_id = ?
    """, conn, params=(persona_id,))
    conn.close()
    return df

def guardar_avance(persona_id, documento_id, estado, fecha_inicio,
                   fecha_completitud, calificacion, observaciones, registrado_por):
    conn = get_conn()
    c = conn.cursor()
    existing = c.execute(
        "SELECT id FROM avances WHERE persona_id=? AND documento_id=?",
        (persona_id, documento_id)
    ).fetchone()
    if existing:
        c.execute("""
            UPDATE avances SET estado=?, fecha_inicio=?, fecha_completitud=?,
            calificacion=?, observaciones=?, registrado_por=?,
            timestamp_registro=datetime('now','localtime')
            WHERE persona_id=? AND documento_id=?
        """, (estado, fecha_inicio, fecha_completitud, calificacion,
              observaciones, registrado_por, persona_id, documento_id))
    else:
        c.execute("""
            INSERT INTO avances (persona_id, documento_id, estado, fecha_inicio,
            fecha_completitud, calificacion, observaciones, registrado_por)
            VALUES (?,?,?,?,?,?,?,?)
        """, (persona_id, documento_id, estado, fecha_inicio,
              fecha_completitud, calificacion, observaciones, registrado_por))
    conn.commit()
    conn.close()

def calcular_estadisticas_persona(persona_id, rol):
    docs_rol = get_docs_por_rol(rol)
    avances = get_avance_persona(persona_id)
    if docs_rol.empty:
        return {"total": 0, "completados": 0, "en_curso": 0, "pendientes": 0,
                "pct_avance": 0.0, "horas_completadas": 0.0, "horas_totales": 0.0}
    merged = docs_rol.merge(avances, left_on="id", right_on="documento_id", how="left")
    merged["estado"] = merged["estado"].fillna("Pendiente")
    total = len(merged)
    completados = (merged["estado"] == "Completado").sum()
    en_curso = (merged["estado"] == "En curso").sum()
    pendientes = (merged["estado"] == "Pendiente").sum()
    horas_totales = merged["horas"].sum()
    horas_completadas = merged.loc[merged["estado"] == "Completado", "horas"].sum()
    pct = (completados / total * 100) if total > 0 else 0.0
    return {
        "total": total, "completados": completados, "en_curso": en_curso,
        "pendientes": pendientes, "pct_avance": round(pct, 1),
        "horas_completadas": round(horas_completadas, 1),
        "horas_totales": round(horas_totales, 1)
    }

def exportar_excel():
    personal = get_personal()
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        personal.to_excel(writer, sheet_name="Personal", index=False)
        resumen = []
        for _, p in personal.iterrows():
            stats = calcular_estadisticas_persona(p["id"], p["rol"])
            resumen.append({
                "Nombre": p["nombre"], "Rol": p["rol"],
                "% Avance": stats["pct_avance"],
                "Docs Completados": stats["completados"],
                "Docs Total": stats["total"],
                "Horas Completadas": stats["horas_completadas"],
                "Horas Totales": stats["horas_totales"],
            })
        pd.DataFrame(resumen).to_excel(writer, sheet_name="Resumen Avances", index=False)
    output.seek(0)
    return output


# ─────────────────────────────────────────────────────────────────────────────
# ESTILOS CSS PERSONALIZADOS
# ─────────────────────────────────────────────────────────────────────────────
def inject_css():
    st.markdown("""
    <style>
        .metric-card {
            background: #f0f2f6; border-radius: 10px;
            padding: 15px; text-align: center; margin: 5px;
        }
        .alerta-roja  { background:#ffe0e0; border-left:4px solid #e74c3c; padding:10px; border-radius:5px; margin:5px 0; }
        .alerta-verde { background:#e0ffe0; border-left:4px solid #27ae60; padding:10px; border-radius:5px; margin:5px 0; }
        .alerta-amarilla { background:#fff9e0; border-left:4px solid #f39c12; padding:10px; border-radius:5px; margin:5px 0; }
        .doc-critico  { background:#fff3cd; border-radius:5px; padding:5px 10px; font-weight:bold; }
        .stProgress > div > div > div > div { background-color: #27ae60; }
    </style>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA 1: DASHBOARD PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────
def pagina_dashboard():
    st.title("🏠 Dashboard — Sistema de Formación IIAD")
    st.caption(f"📅 Actualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    personal = get_personal()
    if personal.empty:
        st.warning("No hay personal registrado. Ve a ⚙️ Administración para agregar personas.")
        return

    # Calcular estadísticas globales
    all_stats = []
    for _, p in personal.iterrows():
        s = calcular_estadisticas_persona(p["id"], p["rol"])
        s["nombre"] = p["nombre"]
        s["rol"] = p["rol"]
        all_stats.append(s)
    df_stats = pd.DataFrame(all_stats)

    avance_global = df_stats["pct_avance"].mean()
    personas_completas = (df_stats["pct_avance"] >= 100).sum()
    personas_criticas = (df_stats["pct_avance"] < 20).sum()

    # ── KPIs Principales ────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        color = "normal" if avance_global >= 60 else ("off" if avance_global < 20 else "inverse")
        st.metric("📊 Avance Global", f"{avance_global:.1f}%",
                  delta=f"Meta: 100%", delta_color=color)
    with col2:
        st.metric("✅ Personas Certificadas", f"{personas_completas}/{len(personal)}")
    with col3:
        st.metric("⚠️ Personas en Alerta", str(personas_criticas),
                  delta_color="inverse")
    with col4:
        total_horas = df_stats["horas_completadas"].sum()
        st.metric("⏱️ Horas Completadas", f"{total_horas:.0f}h")

    st.divider()

    # ── Gráfico de Avance por Persona ────────────────────────────────────────
    col_left, col_right = st.columns([2, 1])
    with col_left:
        st.subheader("📈 Avance por Persona")
        df_plot = df_stats.sort_values("pct_avance", ascending=True)
        colors = ["#e74c3c" if v < 20 else "#f39c12" if v < 60 else "#27ae60"
                  for v in df_plot["pct_avance"]]
        fig = go.Figure(go.Bar(
            x=df_plot["pct_avance"],
            y=df_plot["nombre"],
            orientation="h",
            marker_color=colors,
            text=[f"{v:.1f}%" for v in df_plot["pct_avance"]],
            textposition="outside"
        ))
        fig.add_vline(x=60, line_dash="dash", line_color="orange",
                      annotation_text="Meta Intermedia 60%")
        fig.add_vline(x=100, line_dash="dash", line_color="green",
                      annotation_text="Meta Final 100%")
        fig.update_layout(xaxis_range=[0, 110], height=350,
                          xaxis_title="% Avance", margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("🥧 Distribución Global")
        total_docs = df_stats["total"].sum()
        completados_global = df_stats["completados"].sum()
        en_curso_global = df_stats["en_curso"].sum()
        pendientes_global = df_stats["pendientes"].sum()
        fig_pie = go.Figure(go.Pie(
            labels=["✅ Completado", "🔄 En curso", "⏸ Pendiente"],
            values=[completados_global, en_curso_global, pendientes_global],
            hole=0.4,
            marker_colors=["#27ae60", "#f39c12", "#bdc3c7"]
        ))
        fig_pie.update_layout(height=300, showlegend=True,
                               margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_pie, use_container_width=True)

    # ── Alertas ──────────────────────────────────────────────────────────────
    st.subheader("🚦 Sistema de Alertas")
    alertas_criticas = df_stats[df_stats["pct_avance"] < 20]
    alertas_atencion = df_stats[(df_stats["pct_avance"] >= 20) & (df_stats["pct_avance"] < 60)]
    alertas_bien = df_stats[df_stats["pct_avance"] >= 60]

    for _, row in alertas_criticas.iterrows():
        st.markdown(f'''<div class="alerta-roja">🔴 <strong>{row["nombre"]}</strong>
            ({row["rol"]}) — {row["pct_avance"]}% avance — Acción urgente requerida</div>''',
            unsafe_allow_html=True)
    for _, row in alertas_atencion.iterrows():
        st.markdown(f'''<div class="alerta-amarilla">🟡 <strong>{row["nombre"]}</strong>
            ({row["rol"]}) — {row["pct_avance"]}% avance — Revisar cronograma</div>''',
            unsafe_allow_html=True)
    for _, row in alertas_bien.iterrows():
        st.markdown(f'''<div class="alerta-verde">🟢 <strong>{row["nombre"]}</strong>
            ({row["rol"]}) — {row["pct_avance"]}% avance — En buen camino</div>''',
            unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA 2: REGISTRO DE AVANCES
# ─────────────────────────────────────────────────────────────────────────────
def pagina_registro():
    st.title("📝 Registro de Avances de Formación")

    personal = get_personal()
    if personal.empty:
        st.warning("No hay personal registrado.")
        return

    col1, col2 = st.columns([1, 2])
    with col1:
        nombre_sel = st.selectbox("👤 Seleccionar persona", personal["nombre"].tolist())
    persona = personal[personal["nombre"] == nombre_sel].iloc[0]

    with col2:
        st.info(f"**Rol:** {persona['rol']} | **Ingreso:** {persona['fecha_ingreso']}")

    # Calcular avance actual
    stats = calcular_estadisticas_persona(persona["id"], persona["rol"])
    st.progress(stats["pct_avance"] / 100,
                text=f"Avance: {stats['pct_avance']}% ({stats['completados']}/{stats['total']} docs | {stats['horas_completadas']}h/{stats['horas_totales']}h)")

    # Cargar documentos y avances
    docs_rol = get_docs_por_rol(persona["rol"])
    avances = get_avance_persona(persona["id"])
    merged = docs_rol.merge(avances, left_on="id", right_on="documento_id", how="left")
    merged["estado"] = merged["estado"].fillna("Pendiente")

    st.divider()

    # Filtros
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        filtro_estado = st.selectbox("Filtrar por estado",
                                     ["Todos", "Pendiente", "En curso", "Completado"])
    with col_f2:
        filtro_cat = st.selectbox("Filtrar por categoría",
                                  ["Todas"] + sorted(docs_rol["categoria"].unique().tolist()))
    with col_f3:
        solo_criticos = st.checkbox("⚠️ Solo documentos críticos")

    df_filtrado = merged.copy()
    if filtro_estado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["estado"] == filtro_estado]
    if filtro_cat != "Todas":
        df_filtrado = df_filtrado[df_filtrado["categoria"] == filtro_cat]
    if solo_criticos:
        df_filtrado = df_filtrado[df_filtrado["es_critico"] == 1]

    st.subheader(f"📋 Documentos requeridos: {len(df_filtrado)} mostrados de {len(merged)} total")

    # Formulario de actualización masiva
    registrado_por = st.text_input("👤 Registrado por (nombre capacitador/responsable)",
                                    value="Capacitador IIAD")

    cambios = {}
    for _, doc in df_filtrado.iterrows():
        critico_badge = "⚠️ CRÍTICO" if doc["es_critico"] else ""
        with st.expander(f"{critico_badge} [{doc['codigo']}] {doc['nombre']} — {doc['horas']}h — {doc['nivel']} — Estado actual: {doc['estado']}"):
            c1, c2, c3, c4 = st.columns([2, 2, 1, 3])
            with c1:
                nuevo_estado = st.selectbox(
                    "Estado", ["Pendiente", "En curso", "Completado"],
                    index=["Pendiente", "En curso", "Completado"].index(doc["estado"]),
                    key=f"estado_{doc['id']}"
                )
            with c2:
                fecha_inicio_val = doc.get("fecha_inicio") or ""
                fecha_inicio = st.text_input("Fecha inicio (AAAA-MM-DD)",
                                             value=str(fecha_inicio_val) if fecha_inicio_val else "",
                                             key=f"fi_{doc['id']}")
                fecha_fin_val = doc.get("fecha_completitud") or ""
                fecha_fin = st.text_input("Fecha completitud (AAAA-MM-DD)",
                                          value=str(fecha_fin_val) if fecha_fin_val else "",
                                          key=f"ff_{doc['id']}")
            with c3:
                cal_val = doc.get("calificacion") or 0.0
                calificacion = st.number_input("Nota (0-100)",
                                               min_value=0.0, max_value=100.0,
                                               value=float(cal_val),
                                               key=f"cal_{doc['id']}")
            with c4:
                obs_val = doc.get("observaciones") or ""
                observaciones = st.text_area("Observaciones",
                                              value=str(obs_val) if obs_val else "",
                                              key=f"obs_{doc['id']}", height=80)
                st.caption(f"📌 Normas: {doc['norma_cubierta']}")

            cambios[doc["id"]] = {
                "estado": nuevo_estado, "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin, "calificacion": calificacion,
                "observaciones": observaciones
            }

    if st.button("💾 GUARDAR TODOS LOS CAMBIOS", type="primary", use_container_width=True):
        for doc_id, data in cambios.items():
            guardar_avance(
                persona_id=persona["id"], documento_id=int(doc_id),
                estado=data["estado"],
                fecha_inicio=data["fecha_inicio"] or None,
                fecha_completitud=data["fecha_fin"] or None,
                calificacion=data["calificacion"],
                observaciones=data["observaciones"],
                registrado_por=registrado_por
            )
        st.success(f"✅ Avances guardados para {nombre_sel}")
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA 3: ANÁLISIS POR ROL
# ─────────────────────────────────────────────────────────────────────────────
def pagina_analisis_rol():
    st.title("📊 Análisis por Rol")

    personal = get_personal()
    roles = personal["rol"].unique().tolist()
    rol_sel = st.selectbox("🔍 Seleccionar Rol", ["Todos los roles"] + roles)

    if rol_sel != "Todos los roles":
        personal_filtrado = personal[personal["rol"] == rol_sel]
    else:
        personal_filtrado = personal

    # Tabla resumen
    resumen = []
    for _, p in personal_filtrado.iterrows():
        s = calcular_estadisticas_persona(p["id"], p["rol"])
        resumen.append({
            "Nombre": p["nombre"], "Rol": p["rol"],
            "% Avance": s["pct_avance"],
            "Completados": s["completados"], "Total Docs": s["total"],
            "Horas Completadas": s["horas_completadas"],
            "Horas Totales": s["horas_totales"],
            "Estado": "🟢 Bien" if s["pct_avance"] >= 60 else
                      "🟡 Atención" if s["pct_avance"] >= 20 else "🔴 Crítico"
        })
    df_res = pd.DataFrame(resumen)
    st.dataframe(df_res, use_container_width=True, hide_index=True)

    # Gráfico comparativo
    if not df_res.empty:
        fig = px.bar(df_res, x="Nombre", y="% Avance", color="Estado",
                     color_discrete_map={"🟢 Bien": "#27ae60",
                                         "🟡 Atención": "#f39c12",
                                         "🔴 Crítico": "#e74c3c"},
                     title=f"Comparación de Avances — {rol_sel}",
                     text="% Avance")
        fig.add_hline(y=60, line_dash="dash", annotation_text="Meta intermedia 60%")
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        st.plotly_chart(fig, use_container_width=True)

    # Documentos críticos pendientes por rol
    if rol_sel != "Todos los roles":
        st.subheader(f"⚠️ Documentos Críticos para '{rol_sel}'")
        docs_criticos = get_docs_por_rol(rol_sel)
        docs_criticos = docs_criticos[docs_criticos["es_critico"] == 1]

        for _, doc in docs_criticos.iterrows():
            personas_completaron = 0
            total_aplica = len(personal_filtrado)
            for _, p in personal_filtrado.iterrows():
                av = get_avance_persona(p["id"])
                if not av.empty and ((av["documento_id"] == doc["id"]) &
                                      (av["estado"] == "Completado")).any():
                    personas_completaron += 1
            pct = personas_completaron / total_aplica * 100 if total_aplica > 0 else 0
            color = "🟢" if pct >= 80 else "🟡" if pct >= 40 else "🔴"
            st.write(f"{color} **{doc['codigo']}** — {doc['nombre']} — "
                     f"{personas_completaron}/{total_aplica} personas ({pct:.0f}%)")


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA 4: CRONOGRAMA
# ─────────────────────────────────────────────────────────────────────────────
def pagina_cronograma():
    st.title("📅 Cronograma de Entrenamiento — 6 Meses")
    st.caption("Período: Marzo – Agosto 2026")

    cronograma_data = [
        (1, 1, "Mar", "Fundamentos SGC",      "GSA-SAD-MC-001",  "Manual SGC SAD",             1.5,  "TODOS",             "Presencial grupal",     "⚠️ CRÍTICA"),
        (1, 1, "Mar", "Fundamentos SGC",      "GSA-SAD-MC-003",  "Manual Técnico AR",          4.0,  "TODOS",             "Presencial grupal",     "⚠️ CRÍTICA"),
        (1, 1, "Mar", "Fundamentos SGC",      "GSA-SAD-P-009",   "Confidencialidad",           1.5,  "TODOS",             "Presencial grupal",     "⚠️ CRÍTICA"),
        (2, 1, "Mar", "Fundamentos SGC",      "GSA-SAD-P-020",   "Manejo documentos SAD",      1.5,  "TODOS",             "Presencial grupal",     "ALTA"),
        (2, 1, "Mar", "Fundamentos SGC",      "GSA-SAD-P-012",   "Gestión Personal",           3.0,  "Resp/Prof/Líderes", "Presencial grupal",     "ALTA"),
        (3, 1, "Mar", "Normas ISO Núcleo",    "ISO 17034:2017",  "Requisitos PMR",             4.0,  "Resp/Prof/Líd.Prod","Taller externo INM",    "⚠️ CRÍTICA"),
        (3, 1, "Mar", "Normas ISO Núcleo",    "ISO 17043:2023",  "Requisitos PEA",             4.0,  "Resp/Líd.Comp/PA",  "Taller externo INM",    "⚠️ CRÍTICA"),
        (4, 1, "Mar", "Normas ISO Núcleo",    "ISO 17025:2017",  "Laboratorios",               3.0,  "TODOS",             "Autoestudio guiado",    "ALTA"),
        (5, 2, "Abr", "Procesos Técnicos",    "GSA-SAD-P-024",   "Producción MR",              3.0,  "Resp/Prof/Líd.Prod","Taller técnico",        "⚠️ CRÍTICA"),
        (5, 2, "Abr", "Procesos Técnicos",    "GSA-SAD-P-026",   "Homogeneidad y Estabilidad", 4.0,  "Resp/Líd.Prod/PA",  "Taller c/ejercicios",   "⚠️ CRÍTICA"),
        (6, 2, "Abr", "Procesos Técnicos",    "GSA-SAD-P-031",   "Diseño EA/CI",               4.0,  "Líd.Comp/PA",       "Taller técnico",        "⚠️ CRÍTICA"),
        (6, 2, "Abr", "Procesos Técnicos",    "GSA-SAD-P-033",   "Diseño estadístico PT",      4.0,  "Resp/Líd.Comp/PA",  "Taller c/software",     "⚠️ CRÍTICA"),
        (7, 2, "Abr", "Estadística Crítica",  "ISO 13528:2022",  "Métodos Estadísticos PT",    8.0,  "Líd.Comp/PA/Resp",  "Curso externo CENAM",   "⚠️ MUY CRÍTICA"),
        (8, 2, "Abr", "Estadística Crítica",  "GSA-SAD-P-027",   "Análisis datos PT",          4.0,  "Resp/Líd.Comp/PA",  "Taller casos prácticos","⚠️ CRÍTICA"),
        (9, 3, "May", "Normas Técnicas",      "ISO 33405:2022",  "Homog. y Estab. (ex-G35)",   4.0,  "Todos técnicos",    "Taller externo",        "⚠️ CRÍTICA"),
        (9, 3, "May", "Normas Técnicas",      "ISO 33403:2023",  "Caracterización MR",         4.0,  "Resp/Prof/Líd.Prod","Taller externo",        "⚠️ CRÍTICA"),
        (10,3, "May", "Normas Técnicas",      "GSA-SAD-P-003",   "Incertidumbre",              4.0,  "TODOS",             "Taller c/ejercicios",   "ALTA"),
        (10,3, "May", "Normas Técnicas",      "GSA-SAD-P-002",   "Validación métodos",         4.0,  "Resp/Prof/Líderes", "Taller técnico",        "ALTA"),
        (11,3, "May", "Normas Técnicas",      "ISO 33402:2022",  "Certificados MRC",           3.0,  "Líd.Prod/Prof",     "Autoestudio+ejercicio", "ALTA"),
        (13,4, "Jun", "SGC Operativo",        "GSA-SAD-P-001",   "Gestión equipos",            3.0,  "Resp/Líderes",      "Taller práctico",       "ALTA"),
        (13,4, "Jun", "SGC Operativo",        "GSA-SAD-P-004",   "Trabajo no conforme",        3.0,  "Resp/Prof/Líderes", "Taller c/casos",        "ALTA"),
        (15,4, "Jun", "SGC Operativo",        "GSA-I-SAD-006",   "Auditorías internas",        1.5,  "TODOS",             "Taller simulacro",      "ALTA"),
        (17,5, "Jul", "Calidad Avanzada",     "GSA-I-SAD-038",   "Riesgos y oportunidades",    3.0,  "Resp/PA",           "Taller DOFA/AMFE",      "ALTA"),
        (17,5, "Jul", "Calidad Avanzada",     "GSA-I-SAD-007",   "Acciones correctivas",       3.0,  "Resp/Líderes",      "Taller c/Form 3-604",   "ALTA"),
        (22,6, "Ago", "Integración Final",    "SIMULACRO-AUDIT", "Simulacro auditoría",        4.0,  "TODOS",             "Auditoría simulada",    "⚠️ CRÍTICA"),
        (24,6, "Ago", "Certificación",        "EVAL-FINAL",      "Evaluación Final Integral",  4.0,  "TODOS",             "Examen + entrevista",   "⚠️ CRÍTICA"),
    ]
    df_cron = pd.DataFrame(cronograma_data,
        columns=["Semana","Mes","Mes_Nom","Bloque","Código","Actividad","Horas",
                 "Roles","Modalidad","Prioridad"])

    mes_sel = st.selectbox("Filtrar por mes",
                           ["Todos"] + [f"Mes {i}" for i in range(1, 7)])
    if mes_sel != "Todos":
        mes_num = int(mes_sel.split()[-1])
        df_cron = df_cron[df_cron["Mes"] == mes_num]

    st.dataframe(df_cron[["Semana","Mes_Nom","Bloque","Código","Actividad",
                           "Horas","Roles","Modalidad","Prioridad"]],
                 use_container_width=True, hide_index=True)

    # Gráfico Gantt simplificado
    meses_horas = df_cron.groupby("Mes_Nom")["Horas"].sum().reset_index()
    fig = px.bar(meses_horas, x="Mes_Nom", y="Horas",
                 title="Distribución de Horas por Mes",
                 color="Horas", color_continuous_scale="Blues",
                 text="Horas")
    fig.update_traces(texttemplate="%{text:.0f}h", textposition="outside")
    st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA 5: REPORTES
# ─────────────────────────────────────────────────────────────────────────────
def pagina_reportes():
    st.title("📋 Generación de Reportes")
    personal = get_personal()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📄 Reporte Individual")
        nombre_sel = st.selectbox("Seleccionar persona", personal["nombre"].tolist(),
                                  key="rep_ind")
        persona = personal[personal["nombre"] == nombre_sel].iloc[0]
        if st.button("Generar Vista Previa"):
            stats = calcular_estadisticas_persona(persona["id"], persona["rol"])
            docs_rol = get_docs_por_rol(persona["rol"])
            avances = get_avance_persona(persona["id"])
            merged = docs_rol.merge(avances, left_on="id", right_on="documento_id", how="left")
            merged["estado"] = merged["estado"].fillna("Pendiente")

            st.info(f"""
            **{persona['nombre']}** | Rol: {persona['rol']}
            - Avance: **{stats['pct_avance']}%**
            - Docs completados: {stats['completados']} / {stats['total']}
            - Horas: {stats['horas_completadas']}h / {stats['horas_totales']}h
            """)
            st.dataframe(merged[["codigo","nombre","categoria","horas","nivel","estado",
                                  "fecha_completitud","calificacion"]],
                         use_container_width=True, hide_index=True)

    with col2:
        st.subheader("📊 Reporte Ejecutivo (Excel)")
        st.write("Genera un resumen completo de todos los avances para exportar.")
        excel_data = exportar_excel()
        st.download_button(
            label="⬇️ Descargar Reporte Excel",
            data=excel_data,
            file_name=f"Reporte_Formacion_IIAD_{date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )
        st.caption("Incluye: Maestro de personal + Resumen de avances por persona")


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA 6: ADMINISTRACIÓN
# ─────────────────────────────────────────────────────────────────────────────
def pagina_admin():
    st.title("⚙️ Administración del Sistema")

    tab1, tab2, tab3 = st.tabs(["👥 Personal", "📚 Documentos", "🗄️ Base de Datos"])

    with tab1:
        st.subheader("Gestión de Personal")
        personal = get_personal()
        st.dataframe(personal, use_container_width=True, hide_index=True)

        st.subheader("➕ Agregar Nueva Persona")
        with st.form("form_persona"):
            nombre = st.text_input("Nombre Completo")
            rol = st.selectbox("Rol", [
                "Responsable área IIAD", "Profesional área IIAD",
                "Líder de producción", "Líder de comparación",
                "Profesional análisis datos"
            ])
            fecha_ingreso = st.date_input("Fecha de ingreso")
            submitted = st.form_submit_button("Guardar")
            if submitted and nombre:
                conn = get_conn()
                conn.execute("INSERT INTO personal (nombre, rol, fecha_ingreso) VALUES (?,?,?)",
                             (nombre, rol, str(fecha_ingreso)))
                conn.commit()
                conn.close()
                st.success(f"✅ {nombre} agregado correctamente")
                st.rerun()

    with tab2:
        st.subheader("Catálogo de Documentos")
        docs = get_documentos()
        st.dataframe(docs, use_container_width=True, hide_index=True)

    with tab3:
        st.subheader("Información del Sistema")
        conn = get_conn()
        n_personal = pd.read_sql("SELECT COUNT(*) as n FROM personal", conn).iloc[0,0]
        n_docs = pd.read_sql("SELECT COUNT(*) as n FROM documentos", conn).iloc[0,0]
        n_avances = pd.read_sql("SELECT COUNT(*) as n FROM avances", conn).iloc[0,0]
        conn.close()
        st.metric("Personal registrado", n_personal)
        st.metric("Documentos en catálogo", n_docs)
        st.metric("Registros de avance", n_avances)
        st.info(f"Base de datos: `{os.path.abspath(DB_PATH)}`")

        if st.button("🗑️ REINICIAR BASE DE DATOS (¡Irreversible!)",
                     type="secondary"):
            if os.path.exists(DB_PATH):
                os.remove(DB_PATH)
                st.warning("Base de datos eliminada. Recarga la página.")


# ─────────────────────────────────────────────────────────────────────────────
# NAVEGACIÓN PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────
def main():
    init_db()
    inject_css()

    with st.sidebar:
        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/4/49/Instituto_Colombiano_Agropecuario.svg/320px-Instituto_Colombiano_Agropecuario.svg.png",
                 width=120)
        st.title("Sistema Formación\nÁrea IIAD")
        st.caption("ISO 17034 | ISO 17043 | ICA")
        st.divider()
        pagina = st.radio("Navegación", [
            "🏠 Dashboard",
            "📝 Registro de Avances",
            "📊 Análisis por Rol",
            "📅 Cronograma",
            "📋 Reportes",
            "⚙️ Administración"
        ])
        st.divider()
        st.caption("v1.0 — Feb 2026")

    if pagina == "🏠 Dashboard":
        pagina_dashboard()
    elif pagina == "📝 Registro de Avances":
        pagina_registro()
    elif pagina == "📊 Análisis por Rol":
        pagina_analisis_rol()
    elif pagina == "📅 Cronograma":
        pagina_cronograma()
    elif pagina == "📋 Reportes":
        pagina_reportes()
    elif pagina == "⚙️ Administración":
        pagina_admin()


if __name__ == "__main__":
    main()
