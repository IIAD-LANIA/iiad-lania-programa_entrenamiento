#!/usr/bin/env python3
# =============================================================================
# SISTEMA DE SEGUIMIENTO DE FORMACIÓN - ÁREA IIAD / ICA
# Versión 2.0 | Almacenamiento: JSON en repositorio GitHub
# Desarrollado para cumplimiento ISO 17034 & ISO 17043
# =============================================================================
# INSTALACIÓN:
#   pip install streamlit pandas plotly openpyxl requests
#
# CONFIGURACIÓN (.streamlit/secrets.toml):
#   GITHUB_TOKEN = "ghp_xxxxxxxxxxxxxxxxxxxx"
#   GITHUB_OWNER = "Mauricio-CHEM"
#   GITHUB_REPO  = "programa_entrenamiento_iiad"
#
# EJECUCIÓN:
#   streamlit run app_iiad.py
# =============================================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import json
import base64
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

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN GITHUB  (desde Streamlit Secrets)
# ─────────────────────────────────────────────────────────────────────────────
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_OWNER = st.secrets.get("GITHUB_OWNER", "Mauricio-CHEM")
GITHUB_REPO  = st.secrets.get("GITHUB_REPO",  "programa_entrenamiento_iiad")
DATA_FILE    = "data/formacion_iiad.json"


# ─────────────────────────────────────────────────────────────────────────────
# CAPA DE PERSISTENCIA — GITHUB JSON
# ─────────────────────────────────────────────────────────────────────────────
def _gh_headers():
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }


def load_data_from_github():
    """Lee el JSON de datos desde el repositorio GitHub.
    Retorna (data_dict, sha_str). Si el archivo no existe crea los datos iniciales."""
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{DATA_FILE}"
    try:
        r = requests.get(url, headers=_gh_headers(), timeout=10)
        if r.status_code == 200:
            payload = r.json()
            raw  = base64.b64decode(payload["content"]).decode("utf-8")
            data = json.loads(raw)
            return data, payload["sha"]
        elif r.status_code == 404:
            # Primera ejecución: crear con datos iniciales
            return _datos_iniciales(), None
        else:
            st.warning(f"GitHub respondió {r.status_code}. Usando datos de sesión.")
            return _datos_iniciales(), None
    except Exception as e:
        st.error(f"Error de conexión con GitHub: {e}")
        return _datos_iniciales(), None


def save_data_to_github(data, sha=None):
    """Escribe el JSON de datos en el repositorio GitHub (PUT)."""
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{DATA_FILE}"
    content_b64 = base64.b64encode(
        json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    ).decode("utf-8")
    payload = {
        "message": f"Actualización formación IIAD [{datetime.now().strftime('%Y-%m-%d %H:%M')}]",
        "content": content_b64,
    }
    if sha:
        payload["sha"] = sha
    try:
        r = requests.put(url, headers=_gh_headers(), json=payload, timeout=15)
        if r.status_code in [200, 201]:
            st.session_state["data_sha"] = r.json()["content"]["sha"]
            return True
        else:
            st.error(f"Error al guardar: {r.status_code} — {r.json().get('message', '')}")
            return False
    except Exception as e:
        st.error(f"Error al conectar con GitHub: {e}")
        return False


def get_data():
    """Retorna los datos desde session_state (caché intra-sesión)."""
    if "app_data" not in st.session_state or st.session_state.get("refresh", False):
        data, sha = load_data_from_github()
        st.session_state["app_data"] = data
        st.session_state["data_sha"] = sha
        st.session_state["refresh"] = False
    return st.session_state["app_data"]


def save_data(data):
    """Guarda datos en GitHub y actualiza session_state."""
    sha = st.session_state.get("data_sha")
    ok  = save_data_to_github(data, sha)
    if ok:
        st.session_state["app_data"] = data
        st.session_state["refresh"]  = True
    return ok


# ─────────────────────────────────────────────────────────────────────────────
# DATOS INICIALES (se usan sólo la primera vez que se crea el JSON)
# ─────────────────────────────────────────────────────────────────────────────
def _datos_iniciales():
    """Estructura JSON completa con catálogo de documentos, roles y personal de ejemplo."""
    documentos = [
        {"id":  1, "codigo": "GSA-SAD-MC-001",  "nombre": "Manual del Sistema de Calidad SAD",         "categoria": "SGC Base",         "horas": 1.5, "nivel": "Nivel 2", "norma_cubierta": "ISO 17034 §8 / ISO 17043 §8",            "es_critico": 1},
        {"id":  2, "codigo": "GSA-SAD-MC-003",  "nombre": "Manual Técnico Áreas de Referencia",        "categoria": "SGC Base",         "horas": 4.0, "nivel": "Nivel 4", "norma_cubierta": "ISO 17034 §8.2 / ISO 17043 §8.2",        "es_critico": 1},
        {"id":  3, "codigo": "GSA-SAD-P-009",   "nombre": "Confidencialidad e Imparcialidad SAD",      "categoria": "SGC Base",         "horas": 1.5, "nivel": "Nivel 2", "norma_cubierta": "ISO 17034 §4.2-4.3 / ISO 17043 §4.1-4.2","es_critico": 1},
        {"id":  4, "codigo": "GSA-SAD-P-020",   "nombre": "Manejo de documentos y registros SAD",      "categoria": "SGC Base",         "horas": 1.5, "nivel": "Nivel 2", "norma_cubierta": "ISO 17034 §8.4 / ISO 17043 §8.3",        "es_critico": 0},
        {"id":  5, "codigo": "GSA-I-SAD-020",   "nombre": "Manejo documentos en subgerencia",          "categoria": "SGC Base",         "horas": 1.5, "nivel": "Nivel 2", "norma_cubierta": "ISO 17034 §8.3 / ISO 17043 §8.2",        "es_critico": 0},
        {"id":  6, "codigo": "GSA-SAD-P-012",   "nombre": "Gestión del Personal SAD",                  "categoria": "SGC Base",         "horas": 3.0, "nivel": "Nivel 3", "norma_cubierta": "ISO 17034 §6.1.4 / ISO 17043 §6.2.3",    "es_critico": 0},
        {"id":  7, "codigo": "GSA-SAD-P-013",   "nombre": "Supervisión en la SAD",                     "categoria": "SGC Base",         "horas": 1.5, "nivel": "Nivel 2", "norma_cubierta": "ISO 17034 §6.1.1 / ISO 17043 §6.2.1",    "es_critico": 0},
        {"id":  8, "codigo": "GSA-SAD-G-012",   "nombre": "Guía requisitos formación personal",        "categoria": "SGC Base",         "horas": 1.5, "nivel": "Nivel 2", "norma_cubierta": "ISO 17034 §6.1.4 / ISO 17043 §6.2.3",    "es_critico": 0},
        {"id":  9, "codigo": "ISO 17034:2017",  "nombre": "ISO 17034:2017 - Requisitos PMR",           "categoria": "Normas ISO",       "horas": 4.0, "nivel": "Nivel 4", "norma_cubierta": "Norma completa PMR",                      "es_critico": 1},
        {"id": 10, "codigo": "ISO 17043:2023",  "nombre": "ISO/IEC 17043:2023 - Requisitos PEA",       "categoria": "Normas ISO",       "horas": 4.0, "nivel": "Nivel 4", "norma_cubierta": "Norma completa PEA",                      "es_critico": 1},
        {"id": 11, "codigo": "ISO 17025:2017",  "nombre": "ISO/IEC 17025:2017 - Laboratorios",         "categoria": "Normas ISO",       "horas": 3.0, "nivel": "Nivel 3", "norma_cubierta": "Base laboratorios",                       "es_critico": 0},
        {"id": 12, "codigo": "ISO 13528:2022",  "nombre": "ISO 13528:2022 - Métodos Estadísticos PT",  "categoria": "Normas ISO",       "horas": 8.0, "nivel": "Nivel 4", "norma_cubierta": "ISO 17043 §7.2.2-7.4",                    "es_critico": 1},
        {"id": 13, "codigo": "ISO 33405:2022",  "nombre": "ISO 33405:2022 - Homog. y Estabilidad",     "categoria": "Normas ISO",       "horas": 4.0, "nivel": "Nivel 4", "norma_cubierta": "ISO 17034 §7.10-7.11",                    "es_critico": 1},
        {"id": 14, "codigo": "ISO 33403:2023",  "nombre": "ISO 33403:2023 - Caracterización MR",       "categoria": "Normas ISO",       "horas": 4.0, "nivel": "Nivel 4", "norma_cubierta": "ISO 17034 §7.12",                         "es_critico": 1},
        {"id": 15, "codigo": "ISO 33402:2022",  "nombre": "ISO 33402:2022 - Certificados MRC",         "categoria": "Normas ISO",       "horas": 3.0, "nivel": "Nivel 3", "norma_cubierta": "ISO 17034 §7.14",                         "es_critico": 0},
        {"id": 16, "codigo": "ISO Guide 30",    "nombre": "ISO Guide 30:2015 - Términos MR",           "categoria": "Normas ISO",       "horas": 1.5, "nivel": "Nivel 2", "norma_cubierta": "Definiciones MR",                         "es_critico": 0},
        {"id": 17, "codigo": "ISO 2859-1",      "nombre": "ISO 2859-1 - Muestreo",                     "categoria": "Normas ISO",       "horas": 3.0, "nivel": "Nivel 3", "norma_cubierta": "ISO 17034 §7.10",                         "es_critico": 0},
        {"id": 18, "codigo": "GSA-SAD-P-024",   "nombre": "Planificación y control producción MR",     "categoria": "Proceso Técnico",  "horas": 3.0, "nivel": "Nivel 3", "norma_cubierta": "ISO 17034 §7.2-7.3",                      "es_critico": 1},
        {"id": 19, "codigo": "GSA-SAD-P-026",   "nombre": "Evaluación Homogeneidad y Estabilidad",     "categoria": "Proceso Técnico",  "horas": 4.0, "nivel": "Nivel 4", "norma_cubierta": "ISO 17034 §7.10-7.11",                    "es_critico": 1},
        {"id": 20, "codigo": "GSA-SAD-P-031",   "nombre": "Diseño y planificación EA/CI",              "categoria": "Proceso Técnico",  "horas": 4.0, "nivel": "Nivel 4", "norma_cubierta": "ISO 17043 §7.2.1-7.2.2",                  "es_critico": 1},
        {"id": 21, "codigo": "GSA-SAD-P-033",   "nombre": "Diseño estadístico PT",                     "categoria": "Proceso Técnico",  "horas": 4.0, "nivel": "Nivel 4", "norma_cubierta": "ISO 17043 §7.2.2",                        "es_critico": 1},
        {"id": 22, "codigo": "GSA-SAD-P-030",   "nombre": "Gestión de ítems de ensayo",                "categoria": "Proceso Técnico",  "horas": 3.0, "nivel": "Nivel 3", "norma_cubierta": "ISO 17034 §7.5 / ISO 17043 §7.3.1",       "es_critico": 0},
        {"id": 23, "codigo": "GSA-SAD-P-027",   "nombre": "Análisis y reporte datos PT",               "categoria": "Proceso Técnico",  "horas": 4.0, "nivel": "Nivel 4", "norma_cubierta": "ISO 17043 §7.4.1-7.4.2",                  "es_critico": 1},
        {"id": 24, "codigo": "GSA-SAD-P-003",   "nombre": "Estimación de Incertidumbre",               "categoria": "Proceso Técnico",  "horas": 4.0, "nivel": "Nivel 4", "norma_cubierta": "ISO 17034 §7.13",                         "es_critico": 0},
        {"id": 25, "codigo": "GSA-SAD-P-002",   "nombre": "Validación/Verificación de métodos",        "categoria": "Proceso Técnico",  "horas": 4.0, "nivel": "Nivel 4", "norma_cubierta": "ISO 17034 §7.6 / ISO 17043 §6.1.2",       "es_critico": 0},
        {"id": 26, "codigo": "GSA-SAD-P-001",   "nombre": "Gestión de equipos",                        "categoria": "SGC Operativo",    "horas": 3.0, "nivel": "Nivel 3", "norma_cubierta": "ISO 17034 §7.7",                          "es_critico": 0},
        {"id": 27, "codigo": "GSA-SAD-P-004",   "nombre": "Trabajo no conforme",                       "categoria": "SGC Operativo",    "horas": 3.0, "nivel": "Nivel 3", "norma_cubierta": "ISO 17034 §7.17 / ISO 17043 §7.5.4",      "es_critico": 0},
        {"id": 28, "codigo": "GSA-SAD-P-007",   "nombre": "Emisión de reportes e informes",            "categoria": "SGC Operativo",    "horas": 3.0, "nivel": "Nivel 3", "norma_cubierta": "ISO 17034 §7.14",                         "es_critico": 0},
        {"id": 29, "codigo": "GSA-SAD-P-006",   "nombre": "Revisión solicitudes de servicios",         "categoria": "SGC Operativo",    "horas": 1.5, "nivel": "Nivel 2", "norma_cubierta": "ISO 17034 §4.1 / ISO 17043 §7.1.1",       "es_critico": 0},
        {"id": 30, "codigo": "GSA-SAD-P-008",   "nombre": "Adquisiciones",                             "categoria": "SGC Operativo",    "horas": 1.5, "nivel": "Nivel 2", "norma_cubierta": "ISO 17034 §6.2",                          "es_critico": 0},
        {"id": 31, "codigo": "GSA-SAD-P-014",   "nombre": "Instalaciones y condiciones ambientales",   "categoria": "SGC Operativo",    "horas": 1.5, "nivel": "Nivel 2", "norma_cubierta": "ISO 17034 §7.17 / ISO 17043 §7.5.4",      "es_critico": 0},
        {"id": 32, "codigo": "GSA-SAD-P-017",   "nombre": "Recepción de ítems",                        "categoria": "SGC Operativo",    "horas": 1.5, "nivel": "Nivel 2", "norma_cubierta": "ISO 17034 §7.5",                          "es_critico": 0},
        {"id": 33, "codigo": "GSA-SAD-P-025",   "nombre": "Distribución MR e ítems EA",                "categoria": "SGC Operativo",    "horas": 1.5, "nivel": "Nivel 2", "norma_cubierta": "ISO 17034 §7.15 / ISO 17043 §7.3.4",      "es_critico": 0},
        {"id": 34, "codigo": "GSA-I-SAD-006",   "nombre": "Auditorías internas en laboratorios",       "categoria": "SGC Operativo",    "horas": 1.5, "nivel": "Nivel 2", "norma_cubierta": "ISO 17034 §8.7 / ISO 17043 §8.8",         "es_critico": 0},
        {"id": 35, "codigo": "GSA-I-SAD-039",   "nombre": "Trabajos colaborativos MR/CI/EA",           "categoria": "SGC Operativo",    "horas": 3.0, "nivel": "Nivel 3", "norma_cubierta": "ISO 17034 §6.2 / ISO 17043 §6.4",         "es_critico": 0},
        {"id": 36, "codigo": "GSA-I-SAD-040",   "nombre": "Requisitos de Registros MR y EA",           "categoria": "SGC Operativo",    "horas": 3.0, "nivel": "Nivel 3", "norma_cubierta": "ISO 17034 §7.14-7.16",                    "es_critico": 0},
        {"id": 37, "codigo": "GSA-I-SAD-041",   "nombre": "Integridad SGC ante cambios",               "categoria": "SGC Operativo",    "horas": 3.0, "nivel": "Nivel 3", "norma_cubierta": "ISO 17034 §5.5 / ISO 17043 §5.5",         "es_critico": 0},
        {"id": 38, "codigo": "GSA-I-SAD-001",   "nombre": "Quejas en laboratorios",                    "categoria": "Calidad Avanzada", "horas": 3.0, "nivel": "Nivel 3", "norma_cubierta": "ISO 17034 §7.18 / ISO 17043 §7.6",        "es_critico": 0},
        {"id": 39, "codigo": "GSA-I-SAD-007",   "nombre": "Acciones correctivas y de mejora",          "categoria": "Calidad Avanzada", "horas": 3.0, "nivel": "Nivel 3", "norma_cubierta": "ISO 17034 §8.9 / ISO 17043 §8.7",         "es_critico": 0},
        {"id": 40, "codigo": "GSA-SAD-007",     "nombre": "Acciones correctivas SAD",                  "categoria": "Calidad Avanzada", "horas": 1.5, "nivel": "Nivel 2", "norma_cubierta": "Mejora continua",                         "es_critico": 0},
        {"id": 41, "codigo": "GSA-I-SAD-038",   "nombre": "Riesgos y oportunidades",                   "categoria": "Calidad Avanzada", "horas": 3.0, "nivel": "Nivel 3", "norma_cubierta": "ISO 17034 §8.8 / ISO 17043 §8.5",         "es_critico": 0},
        {"id": 42, "codigo": "GSA-I-SAD-042",   "nombre": "Apelaciones EA",                            "categoria": "Calidad Avanzada", "horas": 3.0, "nivel": "Nivel 3", "norma_cubierta": "ISO 17043 §7.7",                          "es_critico": 0},
        {"id": 43, "codigo": "GSA-I-SAD-012",   "nombre": "Revisión del sistema de gestión",           "categoria": "Calidad Avanzada", "horas": 1.5, "nivel": "Nivel 2", "norma_cubierta": "ISO 17034 §8.6 / ISO 17043 §8.9",         "es_critico": 0},
        {"id": 44, "codigo": "GSA-SAD-G-004",   "nombre": "Gestión de riesgos imparcialidad",          "categoria": "Calidad Avanzada", "horas": 3.0, "nivel": "Nivel 3", "norma_cubierta": "ISO 17034 §4.2 / ISO 17043 §4.1",         "es_critico": 0},
        {"id": 45, "codigo": "GSA-SAD-G-006",   "nombre": "Matriz de Autoridad",                       "categoria": "Calidad Avanzada", "horas": 4.0, "nivel": "Nivel 4", "norma_cubierta": "ISO 17034 §5.5 / ISO 17043 §5.5",         "es_critico": 0},
        {"id": 46, "codigo": "GSA-SAD-G-007",   "nombre": "Interacción y coordinación de roles",       "categoria": "Calidad Avanzada", "horas": 3.0, "nivel": "Nivel 3", "norma_cubierta": "ISO 17034 §5.5 / ISO 17043 §5.5",         "es_critico": 0},
        {"id": 47, "codigo": "GSA-SAD-G-015",   "nombre": "Matriz de objetivos de calidad",            "categoria": "Calidad Avanzada", "horas": 4.0, "nivel": "Nivel 4", "norma_cubierta": "ISO 17034 §8.8 / ISO 17043 §8.6",         "es_critico": 0},
    ]

    cod2id = {d["codigo"]: d["id"] for d in documentos}
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

    req_id = 1
    requisitos_rol = []
    for rol, codigos in roles_config.items():
        for codigo in set(codigos):
            if codigo in cod2id:
                requisitos_rol.append({"id": req_id, "rol": rol, "documento_id": cod2id[codigo]})
                req_id += 1

    personal_ejemplo = [
        {"id": 1, "nombre": "Juan Pérez García",    "rol": "Responsable área IIAD",      "fecha_ingreso": "2023-01-15", "estado": "Activo"},
        {"id": 2, "nombre": "María González López", "rol": "Profesional área IIAD",      "fecha_ingreso": "2024-03-20", "estado": "Activo"},
        {"id": 3, "nombre": "Carlos Rodríguez M.",  "rol": "Líder de producción",        "fecha_ingreso": "2025-06-10", "estado": "Activo"},
        {"id": 4, "nombre": "Ana Martínez Silva",   "rol": "Profesional análisis datos", "fecha_ingreso": "2026-01-15", "estado": "Activo"},
        {"id": 5, "nombre": "Pedro Gómez Torres",   "rol": "Líder de comparación",       "fecha_ingreso": "2024-09-01", "estado": "Activo"},
    ]

    return {
        "personal": personal_ejemplo,
        "documentos": documentos,
        "requisitos_rol": requisitos_rol,
        "avances": [],
        "_meta": {
            "version": "2.0",
            "creado": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "descripcion": "Datos formación IIAD - ICA | Almacenamiento GitHub JSON"
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIONES DE ACCESO A DATOS  (operan sobre el dict en memoria)
# ─────────────────────────────────────────────────────────────────────────────
def get_personal():
    data = get_data()
    df = pd.DataFrame([p for p in data["personal"] if p["estado"] == "Activo"])
    return df.sort_values("nombre").reset_index(drop=True) if not df.empty else df


def get_documentos():
    data = get_data()
    df = pd.DataFrame(data["documentos"])
    return df.sort_values(["categoria", "codigo"]).reset_index(drop=True) if not df.empty else df


def get_docs_por_rol(rol):
    data = get_data()
    doc_ids = {r["documento_id"] for r in data["requisitos_rol"] if r["rol"] == rol}
    docs = [d for d in data["documentos"] if d["id"] in doc_ids]
    df = pd.DataFrame(docs)
    if df.empty:
        return df
    return df.sort_values(["es_critico", "categoria", "codigo"],
                          ascending=[False, True, True]).reset_index(drop=True)


def get_avance_persona(persona_id):
    data = get_data()
    avances = [a for a in data["avances"] if a["persona_id"] == persona_id]
    return pd.DataFrame(avances) if avances else pd.DataFrame(
        columns=["documento_id","estado","fecha_completitud","calificacion","observaciones","fecha_inicio"]
    )


def agregar_personal(nombre, rol, fecha_ingreso):
    data = get_data()
    new_id = max((p["id"] for p in data["personal"]), default=0) + 1
    data["personal"].append({
        "id": new_id, "nombre": nombre, "rol": rol,
        "fecha_ingreso": str(fecha_ingreso), "estado": "Activo"
    })
    return save_data(data)


def calcular_estadisticas_persona(persona_id, rol):
    docs_rol = get_docs_por_rol(rol)
    avances  = get_avance_persona(persona_id)
    if docs_rol.empty:
        return {"total": 0, "completados": 0, "en_curso": 0, "pendientes": 0,
                "pct_avance": 0.0, "horas_completadas": 0.0, "horas_totales": 0.0}
    merged = docs_rol.merge(avances, left_on="id", right_on="documento_id", how="left")
    merged["estado"] = merged["estado"].fillna("Pendiente")
    total             = len(merged)
    completados       = (merged["estado"] == "Completado").sum()
    en_curso          = (merged["estado"] == "En curso").sum()
    pendientes        = (merged["estado"] == "Pendiente").sum()
    horas_totales     = merged["horas"].sum()
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
# ESTILOS CSS
# ─────────────────────────────────────────────────────────────────────────────
def inject_css():
    st.markdown("""
    <style>
        .alerta-roja      { background:#ffe0e0; border-left:4px solid #e74c3c; padding:10px; border-radius:5px; margin:5px 0; }
        .alerta-verde     { background:#e0ffe0; border-left:4px solid #27ae60; padding:10px; border-radius:5px; margin:5px 0; }
        .alerta-amarilla  { background:#fff9e0; border-left:4px solid #f39c12; padding:10px; border-radius:5px; margin:5px 0; }
        .stProgress > div > div > div > div { background-color: #27ae60; }
    </style>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA 1 — DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
def pagina_dashboard():
    st.title("🏠 Dashboard — Sistema de Formación IIAD")
    st.caption(f"📅 Actualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    personal = get_personal()
    if personal.empty:
        st.warning("No hay personal registrado. Ve a ⚙️ Administración para agregar personas.")
        return

    all_stats = []
    for _, p in personal.iterrows():
        s = calcular_estadisticas_persona(p["id"], p["rol"])
        s["nombre"] = p["nombre"]; s["rol"] = p["rol"]
        all_stats.append(s)
    df_stats = pd.DataFrame(all_stats)

    avance_global      = df_stats["pct_avance"].mean()
    personas_completas = (df_stats["pct_avance"] >= 100).sum()
    personas_criticas  = (df_stats["pct_avance"] < 20).sum()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        color = "normal" if avance_global >= 60 else ("off" if avance_global < 20 else "inverse")
        st.metric("📊 Avance Global", f"{avance_global:.1f}%", delta="Meta: 100%", delta_color=color)
    with col2:
        st.metric("✅ Personas Certificadas", f"{personas_completas}/{len(personal)}")
    with col3:
        st.metric("⚠️ Personas en Alerta", str(personas_criticas), delta_color="inverse")
    with col4:
        st.metric("⏱️ Horas Completadas", f"{df_stats['horas_completadas'].sum():.0f}h")
    st.divider()

    col_left, col_right = st.columns([2, 1])
    with col_left:
        st.subheader("📈 Avance por Persona")
        df_plot = df_stats.sort_values("pct_avance", ascending=True)
        colors = ["#e74c3c" if v < 20 else "#f39c12" if v < 60 else "#27ae60" for v in df_plot["pct_avance"]]
        fig = go.Figure(go.Bar(
            x=df_plot["pct_avance"], y=df_plot["nombre"], orientation="h",
            marker_color=colors,
            text=[f"{v:.1f}%" for v in df_plot["pct_avance"]], textposition="outside"
        ))
        fig.add_vline(x=60,  line_dash="dash", line_color="orange", annotation_text="Meta Intermedia 60%")
        fig.add_vline(x=100, line_dash="dash", line_color="green",  annotation_text="Meta Final 100%")
        fig.update_layout(xaxis_range=[0, 110], height=350, xaxis_title="% Avance",
                          margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
    with col_right:
        st.subheader("🥧 Distribución Global")
        fig_pie = go.Figure(go.Pie(
            labels=["✅ Completado", "🔄 En curso", "⏸ Pendiente"],
            values=[df_stats["completados"].sum(), df_stats["en_curso"].sum(), df_stats["pendientes"].sum()],
            hole=0.4, marker_colors=["#27ae60", "#f39c12", "#bdc3c7"]
        ))
        fig_pie.update_layout(height=300, showlegend=True, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_pie, use_container_width=True)

    st.subheader("🚦 Sistema de Alertas")
    for _, row in df_stats[df_stats["pct_avance"] < 20].iterrows():
        st.markdown(f'<div class="alerta-roja">🔴 <strong>{row["nombre"]}</strong> ({row["rol"]}) — {row["pct_avance"]}% — Acción urgente requerida</div>', unsafe_allow_html=True)
    for _, row in df_stats[(df_stats["pct_avance"] >= 20) & (df_stats["pct_avance"] < 60)].iterrows():
        st.markdown(f'<div class="alerta-amarilla">🟡 <strong>{row["nombre"]}</strong> ({row["rol"]}) — {row["pct_avance"]}% — Revisar cronograma</div>', unsafe_allow_html=True)
    for _, row in df_stats[df_stats["pct_avance"] >= 60].iterrows():
        st.markdown(f'<div class="alerta-verde">🟢 <strong>{row["nombre"]}</strong> ({row["rol"]}) — {row["pct_avance"]}% — En buen camino</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA 2 — REGISTRO DE AVANCES
# ─────────────────────────────────────────────────────────────────────────────
def pagina_registro():
    st.title("📝 Registro de Avances de Formación")
    personal = get_personal()
    if personal.empty:
        st.warning("No hay personal registrado."); return

    col1, col2 = st.columns([1, 2])
    with col1:
        nombre_sel = st.selectbox("👤 Seleccionar persona", personal["nombre"].tolist())
    persona = personal[personal["nombre"] == nombre_sel].iloc[0]
    with col2:
        st.info(f"**Rol:** {persona['rol']} | **Ingreso:** {persona['fecha_ingreso']}")

    stats = calcular_estadisticas_persona(persona["id"], persona["rol"])
    st.progress(stats["pct_avance"] / 100,
                text=f"Avance: {stats['pct_avance']}% ({stats['completados']}/{stats['total']} docs | {stats['horas_completadas']}h/{stats['horas_totales']}h)")

    docs_rol = get_docs_por_rol(persona["rol"])
    avances  = get_avance_persona(persona["id"])
    merged   = docs_rol.merge(avances, left_on="id", right_on="documento_id", how="left")
    merged["estado"] = merged["estado"].fillna("Pendiente")
    st.divider()

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        filtro_estado = st.selectbox("Filtrar por estado", ["Todos","Pendiente","En curso","Completado"])
    with col_f2:
        filtro_cat = st.selectbox("Filtrar por categoría", ["Todas"] + sorted(docs_rol["categoria"].unique().tolist()))
    with col_f3:
        solo_criticos = st.checkbox("⚠️ Solo documentos críticos")

    df_filtrado = merged.copy()
    if filtro_estado != "Todos":   df_filtrado = df_filtrado[df_filtrado["estado"]    == filtro_estado]
    if filtro_cat   != "Todas":    df_filtrado = df_filtrado[df_filtrado["categoria"]  == filtro_cat]
    if solo_criticos:              df_filtrado = df_filtrado[df_filtrado["es_critico"] == 1]

    st.subheader(f"📋 {len(df_filtrado)} de {len(merged)} documentos mostrados")
    registrado_por = st.text_input("👤 Registrado por", value="Capacitador IIAD")

    cambios = {}
    for _, doc in df_filtrado.iterrows():
        badge = "⚠️ CRÍTICO " if doc["es_critico"] else ""
        with st.expander(f"{badge}[{doc['codigo']}] {doc['nombre']} — {doc['horas']}h — {doc['nivel']} — Estado: {doc['estado']}"):
            c1, c2, c3, c4 = st.columns([2, 2, 1, 3])
            with c1:
                nuevo_estado = st.selectbox("Estado", ["Pendiente","En curso","Completado"],
                    index=["Pendiente","En curso","Completado"].index(doc["estado"]),
                    key=f"estado_{doc['id']}")
            with c2:
                fi_val = doc.get("fecha_inicio") or ""
                fecha_inicio = st.text_input("Fecha inicio (AAAA-MM-DD)",
                    value=str(fi_val) if fi_val else "", key=f"fi_{doc['id']}")
                ff_val = doc.get("fecha_completitud") or ""
                fecha_fin = st.text_input("Fecha completitud (AAAA-MM-DD)",
                    value=str(ff_val) if ff_val else "", key=f"ff_{doc['id']}")
            with c3:
                cal_val = doc.get("calificacion") or 0.0
                calificacion = st.number_input("Nota (0-100)", min_value=0.0, max_value=100.0,
                    value=float(cal_val), key=f"cal_{doc['id']}")
            with c4:
                obs_val = doc.get("observaciones") or ""
                observaciones = st.text_area("Observaciones",
                    value=str(obs_val) if obs_val else "", key=f"obs_{doc['id']}", height=80)
                st.caption(f"📌 Normas: {doc['norma_cubierta']}")
            cambios[doc["id"]] = {
                "estado": nuevo_estado, "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin, "calificacion": calificacion, "observaciones": observaciones
            }

    if st.button("💾 GUARDAR TODOS LOS CAMBIOS", type="primary", use_container_width=True):
        with st.spinner("Guardando en GitHub..."):
            data    = get_data()
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for doc_id, d in cambios.items():
                pid = int(persona["id"]); did = int(doc_id)
                existing = next((a for a in data["avances"]
                                 if a["persona_id"] == pid and a["documento_id"] == did), None)
                if existing:
                    existing.update({
                        "estado": d["estado"],
                        "fecha_inicio": d["fecha_inicio"] or None,
                        "fecha_completitud": d["fecha_fin"] or None,
                        "calificacion": d["calificacion"],
                        "observaciones": d["observaciones"],
                        "registrado_por": registrado_por,
                        "timestamp_registro": now_str
                    })
                else:
                    new_id = max((a["id"] for a in data["avances"]), default=0) + 1
                    data["avances"].append({
                        "id": new_id, "persona_id": pid, "documento_id": did,
                        "estado": d["estado"],
                        "fecha_inicio": d["fecha_inicio"] or None,
                        "fecha_completitud": d["fecha_fin"] or None,
                        "calificacion": d["calificacion"],
                        "observaciones": d["observaciones"],
                        "registrado_por": registrado_por,
                        "timestamp_registro": now_str
                    })
            if save_data(data):
                st.success(f"✅ Avances guardados para {nombre_sel}")
                st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA 3 — ANÁLISIS POR ROL
# ─────────────────────────────────────────────────────────────────────────────
def pagina_analisis_rol():
    st.title("📊 Análisis por Rol")
    personal = get_personal()
    roles    = personal["rol"].unique().tolist()
    rol_sel  = st.selectbox("🔍 Seleccionar Rol", ["Todos los roles"] + roles)

    personal_filtrado = personal[personal["rol"] == rol_sel] if rol_sel != "Todos los roles" else personal

    resumen = []
    for _, p in personal_filtrado.iterrows():
        s = calcular_estadisticas_persona(p["id"], p["rol"])
        resumen.append({
            "Nombre": p["nombre"], "Rol": p["rol"], "% Avance": s["pct_avance"],
            "Completados": s["completados"], "Total Docs": s["total"],
            "Horas Completadas": s["horas_completadas"], "Horas Totales": s["horas_totales"],
            "Estado": "🟢 Bien" if s["pct_avance"] >= 60 else "🟡 Atención" if s["pct_avance"] >= 20 else "🔴 Crítico"
        })
    df_res = pd.DataFrame(resumen)
    st.dataframe(df_res, use_container_width=True, hide_index=True)

    if not df_res.empty:
        fig = px.bar(df_res, x="Nombre", y="% Avance", color="Estado",
                     color_discrete_map={"🟢 Bien": "#27ae60", "🟡 Atención": "#f39c12", "🔴 Crítico": "#e74c3c"},
                     title=f"Comparación de Avances — {rol_sel}", text="% Avance")
        fig.add_hline(y=60, line_dash="dash", annotation_text="Meta intermedia 60%")
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        st.plotly_chart(fig, use_container_width=True)

    if rol_sel != "Todos los roles":
        st.subheader(f"⚠️ Documentos Críticos para '{rol_sel}'")
        docs_criticos = get_docs_por_rol(rol_sel)
        docs_criticos = docs_criticos[docs_criticos["es_critico"] == 1]
        for _, doc in docs_criticos.iterrows():
            n_comp = 0; total = len(personal_filtrado)
            for _, p in personal_filtrado.iterrows():
                av = get_avance_persona(p["id"])
                if not av.empty and ((av["documento_id"] == doc["id"]) & (av["estado"] == "Completado")).any():
                    n_comp += 1
            pct   = n_comp / total * 100 if total > 0 else 0
            color = "🟢" if pct >= 80 else "🟡" if pct >= 40 else "🔴"
            st.write(f"{color} **{doc['codigo']}** — {doc['nombre']} — {n_comp}/{total} personas ({pct:.0f}%)")


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA 4 — CRONOGRAMA
# ─────────────────────────────────────────────────────────────────────────────
def pagina_cronograma():
    st.title("📅 Cronograma de Entrenamiento — 6 Meses")
    st.caption("Período: Marzo – Agosto 2026")

    cronograma_data = [
        (1, 1,"Mar","Fundamentos SGC",    "GSA-SAD-MC-001",  "Manual SGC SAD",             1.5,"TODOS",             "Presencial grupal",     "⚠️ CRÍTICA"),
        (1, 1,"Mar","Fundamentos SGC",    "GSA-SAD-MC-003",  "Manual Técnico AR",          4.0,"TODOS",             "Presencial grupal",     "⚠️ CRÍTICA"),
        (1, 1,"Mar","Fundamentos SGC",    "GSA-SAD-P-009",   "Confidencialidad",           1.5,"TODOS",             "Presencial grupal",     "⚠️ CRÍTICA"),
        (2, 1,"Mar","Fundamentos SGC",    "GSA-SAD-P-020",   "Manejo documentos SAD",      1.5,"TODOS",             "Presencial grupal",     "ALTA"),
        (2, 1,"Mar","Fundamentos SGC",    "GSA-SAD-P-012",   "Gestión Personal",           3.0,"Resp/Prof/Líderes", "Presencial grupal",     "ALTA"),
        (3, 1,"Mar","Normas ISO Núcleo",  "ISO 17034:2017",  "Requisitos PMR",             4.0,"Resp/Prof/Líd.Prod","Taller externo INM",    "⚠️ CRÍTICA"),
        (3, 1,"Mar","Normas ISO Núcleo",  "ISO 17043:2023",  "Requisitos PEA",             4.0,"Resp/Líd.Comp/PA",  "Taller externo INM",    "⚠️ CRÍTICA"),
        (4, 1,"Mar","Normas ISO Núcleo",  "ISO 17025:2017",  "Laboratorios",               3.0,"TODOS",             "Autoestudio guiado",    "ALTA"),
        (5, 2,"Abr","Procesos Técnicos",  "GSA-SAD-P-024",   "Producción MR",              3.0,"Resp/Prof/Líd.Prod","Taller técnico",        "⚠️ CRÍTICA"),
        (5, 2,"Abr","Procesos Técnicos",  "GSA-SAD-P-026",   "Homogeneidad y Estabilidad", 4.0,"Resp/Líd.Prod/PA",  "Taller c/ejercicios",   "⚠️ CRÍTICA"),
        (6, 2,"Abr","Procesos Técnicos",  "GSA-SAD-P-031",   "Diseño EA/CI",               4.0,"Líd.Comp/PA",       "Taller técnico",        "⚠️ CRÍTICA"),
        (6, 2,"Abr","Procesos Técnicos",  "GSA-SAD-P-033",   "Diseño estadístico PT",      4.0,"Resp/Líd.Comp/PA",  "Taller c/software",     "⚠️ CRÍTICA"),
        (7, 2,"Abr","Estadística Crítica","ISO 13528:2022",  "Métodos Estadísticos PT",    8.0,"Líd.Comp/PA/Resp",  "Curso externo CENAM",   "⚠️ MUY CRÍTICA"),
        (8, 2,"Abr","Estadística Crítica","GSA-SAD-P-027",   "Análisis datos PT",          4.0,"Resp/Líd.Comp/PA",  "Taller casos prácticos","⚠️ CRÍTICA"),
        (9, 3,"May","Normas Técnicas",    "ISO 33405:2022",  "Homog. y Estab.",             4.0,"Todos técnicos",    "Taller externo",        "⚠️ CRÍTICA"),
        (9, 3,"May","Normas Técnicas",    "ISO 33403:2023",  "Caracterización MR",         4.0,"Resp/Prof/Líd.Prod","Taller externo",        "⚠️ CRÍTICA"),
        (10,3,"May","Normas Técnicas",    "GSA-SAD-P-003",   "Incertidumbre",              4.0,"TODOS",             "Taller c/ejercicios",   "ALTA"),
        (10,3,"May","Normas Técnicas",    "GSA-SAD-P-002",   "Validación métodos",         4.0,"Resp/Prof/Líderes", "Taller técnico",        "ALTA"),
        (11,3,"May","Normas Técnicas",    "ISO 33402:2022",  "Certificados MRC",           3.0,"Líd.Prod/Prof",     "Autoestudio+ejercicio", "ALTA"),
        (13,4,"Jun","SGC Operativo",      "GSA-SAD-P-001",   "Gestión equipos",            3.0,"Resp/Líderes",      "Taller práctico",       "ALTA"),
        (13,4,"Jun","SGC Operativo",      "GSA-SAD-P-004",   "Trabajo no conforme",        3.0,"Resp/Prof/Líderes", "Taller c/casos",        "ALTA"),
        (15,4,"Jun","SGC Operativo",      "GSA-I-SAD-006",   "Auditorías internas",        1.5,"TODOS",             "Taller simulacro",      "ALTA"),
        (17,5,"Jul","Calidad Avanzada",   "GSA-I-SAD-038",   "Riesgos y oportunidades",    3.0,"Resp/PA",           "Taller DOFA/AMFE",      "ALTA"),
        (17,5,"Jul","Calidad Avanzada",   "GSA-I-SAD-007",   "Acciones correctivas",       3.0,"Resp/Líderes",      "Taller c/Form 3-604",   "ALTA"),
        (22,6,"Ago","Integración Final",  "SIMULACRO-AUDIT", "Simulacro auditoría",        4.0,"TODOS",             "Auditoría simulada",    "⚠️ CRÍTICA"),
        (24,6,"Ago","Certificación",      "EVAL-FINAL",      "Evaluación Final Integral",  4.0,"TODOS",             "Examen + entrevista",   "⚠️ CRÍTICA"),
    ]
    df_cron = pd.DataFrame(cronograma_data,
        columns=["Semana","Mes","Mes_Nom","Bloque","Código","Actividad","Horas",
                 "Roles","Modalidad","Prioridad"])

    mes_sel = st.selectbox("Filtrar por mes", ["Todos"] + [f"Mes {i}" for i in range(1, 7)])
    if mes_sel != "Todos":
        df_cron = df_cron[df_cron["Mes"] == int(mes_sel.split()[-1])]

    st.dataframe(df_cron[["Semana","Mes_Nom","Bloque","Código","Actividad",
                           "Horas","Roles","Modalidad","Prioridad"]],
                 use_container_width=True, hide_index=True)

    meses_horas = df_cron.groupby("Mes_Nom")["Horas"].sum().reset_index()
    fig = px.bar(meses_horas, x="Mes_Nom", y="Horas", title="Distribución de Horas por Mes",
                 color="Horas", color_continuous_scale="Blues", text="Horas")
    fig.update_traces(texttemplate="%{text:.0f}h", textposition="outside")
    st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA 5 — REPORTES
# ─────────────────────────────────────────────────────────────────────────────
def pagina_reportes():
    st.title("📋 Generación de Reportes")
    personal = get_personal()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📄 Reporte Individual")
        nombre_sel = st.selectbox("Seleccionar persona", personal["nombre"].tolist(), key="rep_ind")
        persona = personal[personal["nombre"] == nombre_sel].iloc[0]
        if st.button("Generar Vista Previa"):
            stats    = calcular_estadisticas_persona(persona["id"], persona["rol"])
            docs_rol = get_docs_por_rol(persona["rol"])
            avances  = get_avance_persona(persona["id"])
            merged   = docs_rol.merge(avances, left_on="id", right_on="documento_id", how="left")
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
# PÁGINA 6 — ADMINISTRACIÓN
# ─────────────────────────────────────────────────────────────────────────────
def pagina_admin():
    st.title("⚙️ Administración del Sistema")
    tab1, tab2, tab3 = st.tabs(["👥 Personal", "📚 Documentos", "🗄️ Datos GitHub"])

    with tab1:
        st.subheader("Gestión de Personal")
        st.dataframe(get_personal(), use_container_width=True, hide_index=True)
        st.subheader("➕ Agregar Nueva Persona")
        with st.form("form_persona"):
            nombre = st.text_input("Nombre Completo")
            rol    = st.selectbox("Rol", [
                "Responsable área IIAD","Profesional área IIAD",
                "Líder de producción","Líder de comparación","Profesional análisis datos"
            ])
            fecha_ingreso = st.date_input("Fecha de ingreso")
            if st.form_submit_button("Guardar") and nombre:
                with st.spinner("Guardando en GitHub..."):
                    if agregar_personal(nombre, rol, fecha_ingreso):
                        st.success(f"✅ {nombre} agregado correctamente")
                        st.rerun()

    with tab2:
        st.subheader("Catálogo de Documentos")
        st.dataframe(get_documentos(), use_container_width=True, hide_index=True)

    with tab3:
        st.subheader("Información del Sistema — Almacenamiento GitHub")
        data = get_data()
        c1, c2, c3 = st.columns(3)
        c1.metric("Personal registrado",    len(data.get("personal",   [])))
        c2.metric("Documentos en catálogo", len(data.get("documentos", [])))
        c3.metric("Registros de avance",    len(data.get("avances",    [])))
        st.info(f"""
        📦 **Repositorio:** `{GITHUB_OWNER}/{GITHUB_REPO}`
        📄 **Archivo JSON:** `{DATA_FILE}`
        🔗 **Ver en GitHub:** [Abrir datos](https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/blob/main/{DATA_FILE})
        """)
        meta = data.get("_meta", {})
        if meta:
            st.caption(f"Versión: {meta.get('version','—')} | Creado: {meta.get('creado','—')}")
        if st.button("🔄 Forzar recarga desde GitHub"):
            for k in ["app_data", "data_sha", "refresh"]:
                st.session_state.pop(k, None)
            st.rerun()
        st.divider()
        st.subheader("⬇️ Descargar JSON")
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        st.download_button(
            "Descargar formacion_iiad.json", data=json_str,
            file_name=f"formacion_iiad_{date.today()}.json", mime="application/json"
        )
        with st.expander("👁️ Vista previa JSON"):
            preview = {**data, "avances": data.get("avances", [])[:50]}
            st.json(preview)


# ─────────────────────────────────────────────────────────────────────────────
# NAVEGACIÓN PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────
def main():
    inject_css()
    if not GITHUB_TOKEN:
        st.sidebar.warning("⚠️ GITHUB_TOKEN no configurado en .streamlit/secrets.toml")

    with st.sidebar:
        st.image(
            "https://upload.wikimedia.org/wikipedia/commons/thumb/4/49/Instituto_Colombiano_Agropecuario.svg/320px-Instituto_Colombiano_Agropecuario.svg.png",
            width=120
        )
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
        st.caption("v2.0 — Feb 2026 | 🗄️ GitHub JSON")

    if   pagina == "🏠 Dashboard":          pagina_dashboard()
    elif pagina == "📝 Registro de Avances": pagina_registro()
    elif pagina == "📊 Análisis por Rol":    pagina_analisis_rol()
    elif pagina == "📅 Cronograma":          pagina_cronograma()
    elif pagina == "📋 Reportes":            pagina_reportes()
    elif pagina == "⚙️ Administración":      pagina_admin()


if __name__ == "__main__":
    main()
