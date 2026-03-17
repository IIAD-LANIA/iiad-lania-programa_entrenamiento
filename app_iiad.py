#!/usr/bin/env python3
# =============================================================================
# SISTEMA DE SEGUIMIENTO DE FORMACIÓN - ÁREA IIAD / ICA
# Versión 2.5 | Almacenamiento: JSON en repositorio GitHub
# Desarrollado para cumplimiento ISO 17034 & ISO 17043
# Estilo visual: alineado con Dashboard-SG-IDI_V4
# NUEVO v2.5: gestión completa de catálogo de documentos
#             - Agregar nuevos documentos con asignación de roles
#             - Editar roles asociados a documentos existentes
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
GITHUB_OWNER = st.secrets.get("GITHUB_OWNER", "IIAD-LANIA")
GITHUB_REPO  = st.secrets.get("GITHUB_REPO",  "iiad-lania-programa_entrenamiento")
DATA_FILE    = "data/formacion_iiad.json"

# Lista canónica de roles disponibles
ROLES_DISPONIBLES = [
    "Responsable área IIAD",
    "Profesional área IIAD",
    "Líder de producción",
    "Líder de comparación",
    "Profesional análisis datos",
]

CATEGORIAS_DISPONIBLES = [
    "SGC Base",
    "Normas ISO",
    "Proceso Técnico",
    "SGC Operativo",
    "Calidad Avanzada",
]

NIVELES_DISPONIBLES = [
    "Nivel 1",
    "Nivel 2",
    "Nivel 3",
    "Nivel 4",
]

# ─────────────────────────────────────────────────────────────────────────────
# CAPA DE PERSISTENCIA — GITHUB JSON
# ─────────────────────────────────────────────────────────────────────────────
def _gh_headers():
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }


def load_data_from_github():
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{DATA_FILE}"
    try:            
        r = requests.get(url, headers=_gh_headers(), timeout=10)
        if r.status_code == 200:
            payload = r.json()
            raw  = base64.b64decode(payload["content"]).decode("utf-8")
            data = json.loads(raw)
            # ── Migración automática: "rol" (str) → "roles" (lista) ──────────
            data, migrated = _migrar_roles(data)
            if migrated:
                save_data_to_github(data, payload["sha"])
            return data, payload["sha"]
        elif r.status_code == 404:
            return _datos_iniciales(), None
        else:
            st.warning(f"GitHub respondió {r.status_code}. Usando datos de sesión.")
            return _datos_iniciales(), None
    except Exception as e:
        st.error(f"Error de conexión con GitHub: {e}")
        return _datos_iniciales(), None

def _migrar_roles(data):
    """Convierte el campo legacy 'rol' (string) a 'roles' (lista).
    Retorna (data, migrated) donde migrated=True si hubo cambios."""
    migrated = False
    for p in data.get("personal", []):
        if "roles" not in p:
            p["roles"] = [p["rol"]] if p.get("rol") else []
            migrated = True
        if isinstance(p.get("roles"), str):
            p["roles"] = [p["roles"]]
            migrated = True
    return data, migrated

def save_data_to_github(data, sha=None, max_retries=2):
    """Guarda data en GitHub con reintento automático ante conflictos de SHA (fix BUG-001)."""
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{DATA_FILE}"
    current_sha = sha

    for attempt in range(max_retries + 1):
        if attempt > 0:
            try:
                r_get = requests.get(url, headers=_gh_headers(), timeout=10)
                if r_get.status_code == 200:
                    current_sha = r_get.json().get("sha")
                    st.session_state["data_sha"] = current_sha
            except Exception:
                pass

        content_b64 = base64.b64encode(
            json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        ).decode("utf-8")
        payload = {
            "message": f"Actualización formación IIAD [{datetime.now().strftime('%Y-%m-%d %H:%M')}]",
            "content": content_b64,
        }
        if current_sha:
            payload["sha"] = current_sha

        try:
            r = requests.put(url, headers=_gh_headers(), json=payload, timeout=15)
            if r.status_code in [200, 201]:
                st.session_state["data_sha"] = r.json()["content"]["sha"]
                return True
            elif r.status_code == 409 and attempt < max_retries:
                st.warning(f"⚠️ Conflicto de versión. Reintentando ({attempt + 1}/{max_retries})…")
                continue
            else:
                error_msg = r.json().get("message", "")
                st.error(f"Error al guardar: {r.status_code} — {error_msg}")
                if r.status_code == 409:
                    st.error(
                        "⚠️ Conflicto de versión: otro usuario modificó los datos simultáneamente. "
                        "Use '🔄 Forzar recarga' en ⚙️ Administración → Datos GitHub e intente de nuevo."
                    )
                return False
        except Exception as e:
            st.error(f"Error al conectar con GitHub: {e}")
            return False

    return False

def get_data():
    if "app_data" not in st.session_state or st.session_state.get("refresh", False):
        data, sha = load_data_from_github()
        st.session_state["app_data"] = data
        st.session_state["data_sha"] = sha
        st.session_state["refresh"] = False
        st.session_state["data_version"] = st.session_state.get("data_version", 0) + 1
    return st.session_state["app_data"]


def save_data(data):
    sha = st.session_state.get("data_sha")
    ok  = save_data_to_github(data, sha)
    if ok:
        st.session_state["app_data"]    = data
        st.session_state["refresh"]     = True
        st.session_state["data_version"] = st.session_state.get("data_version", 0) + 1
    return ok


# ─────────────────────────────────────────────────────────────────────────────
# DATOS INICIALES
# ─────────────────────────────────────────────────────────────────────────────
def _datos_iniciales():
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
        for codigo in sorted(set(codigos)):
            if codigo in cod2id:
                requisitos_rol.append({"id": req_id, "rol": rol, "documento_id": cod2id[codigo]})
                req_id += 1

    personal_ejemplo = [
        {"id": 1, "nombre": "Iván Mauricio Huérfano",    "roles": ["Responsable área IIAD"],     "fecha_ingreso": "2026-02-11", "estado": "Activo"},
        {"id": 2, "nombre": "Claudia Marcela Duarte",    "roles": ["Profesional área IIAD"],     "fecha_ingreso": "2025-01-10", "estado": "Activo"},
        {"id": 3, "nombre": "David Esquivel Valderrama", "roles": ["Profesional área IIAD"],     "fecha_ingreso": "2026-01-10", "estado": "Activo"},
    ]

    return {
        "personal": personal_ejemplo,
        "documentos": documentos,
        "requisitos_rol": requisitos_rol,
        "avances": [],
        "_meta": {
            "version": "2.5",
            "creado": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "descripcion": "Datos formación IIAD - ICA | Multi-roles por persona | Gestión documentos"
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIONES DE ACCESO A DATOS
# ─────────────────────────────────────────────────────────────────────────────
def get_personal():
    data = get_data()
    df = pd.DataFrame([p for p in data["personal"] if p["estado"] == "Activo"])
    if df.empty:
        return df
    df["rol_display"] = df["roles"].apply(
        lambda r: " · ".join(r) if isinstance(r, list) else str(r)
    )
    return df.sort_values("nombre").reset_index(drop=True)


def get_documentos():
    data = get_data()
    df = pd.DataFrame(data["documentos"])
    return df.sort_values(["categoria", "codigo"]).reset_index(drop=True) if not df.empty else df


def get_roles_de_documento(doc_id):
    """Devuelve lista de roles asociados a un documento por su id."""
    data = get_data()
    return list({r["rol"] for r in data["requisitos_rol"] if r["documento_id"] == doc_id})


def get_docs_por_rol(rol):
    data = get_data()
    doc_ids = {r["documento_id"] for r in data["requisitos_rol"] if r["rol"] == rol}
    docs = [d for d in data["documentos"] if d["id"] in doc_ids]
    df = pd.DataFrame(docs)
    if df.empty:
        return df
    return df.sort_values(["es_critico", "categoria", "codigo"],
                          ascending=[False, True, True]).reset_index(drop=True)


def get_docs_por_persona(roles_lista):
    data = get_data()
    doc_roles: dict[int, list] = {}
    for rol in roles_lista:
        for r in data["requisitos_rol"]:
            if r["rol"] == rol:
                did = r["documento_id"]
                doc_roles.setdefault(did, [])
                if rol not in doc_roles[did]:
                    doc_roles[did].append(rol)

    docs = []
    for d in data["documentos"]:
        if d["id"] in doc_roles:
            entry = dict(d)
            entry["roles_que_cubre"] = doc_roles[d["id"]]
            entry["es_transversal"]  = len(doc_roles[d["id"]]) > 1
            docs.append(entry)

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

def agregar_personal(nombre, roles, fecha_ingreso):
    data = get_data()
    new_id = max((p.get("id", 0) for p in data["personal"]), default=0) + 1
    data["personal"].append({
        "id": new_id,
        "nombre": nombre,
        "roles": roles,
        "fecha_ingreso": str(fecha_ingreso),   # ← también fix del BUG-002
        "estado": "Activo"
    })
    return save_data(data)


def actualizar_roles_personal(persona_id, nuevos_roles):
    data = get_data()
    for p in data["personal"]:
        if p["id"] == persona_id:
            p["roles"] = nuevos_roles
            break
    return save_data(data)


def agregar_documento(codigo, nombre, categoria, horas, nivel, norma_cubierta, es_critico, roles_asignados):
    """Agrega un nuevo documento al catálogo y crea sus entradas en requisitos_rol."""
    data = get_data()
    # Verificar que el código no exista ya
    codigos_existentes = {d["codigo"] for d in data["documentos"]}
    if codigo in codigos_existentes:
        return False, "El código ya existe en el catálogo."
    # Asignar nuevo ID
    new_doc_id = max((d["id"] for d in data["documentos"]), default=0) + 1
    data["documentos"].append({
        "id": new_doc_id,
        "codigo": codigo,
        "nombre": nombre,
        "categoria": categoria,
        "horas": horas,
        "nivel": nivel,
        "norma_cubierta": norma_cubierta,
        "es_critico": 1 if es_critico else 0,
    })
    # Crear entradas en requisitos_rol para cada rol asignado
    req_id_base = max((r["id"] for r in data["requisitos_rol"]), default=0) + 1
    for i, rol in enumerate(roles_asignados):
        data["requisitos_rol"].append({
            "id": req_id_base + i,
            "rol": rol,
            "documento_id": new_doc_id
        })
    ok = save_data(data)
    return ok, None


def actualizar_roles_documento(doc_id, nuevos_roles):
    """Reemplaza los roles asociados a un documento existente."""
    data = get_data()
    # Eliminar entradas actuales del documento
    data["requisitos_rol"] = [
        r for r in data["requisitos_rol"] if r["documento_id"] != doc_id
    ]
    # Agregar nuevas entradas
    req_id_base = max((r["id"] for r in data["requisitos_rol"]), default=0) + 1
    for i, rol in enumerate(nuevos_roles):
        data["requisitos_rol"].append({
            "id": req_id_base + i,
            "rol": rol,
            "documento_id": doc_id
        })
    return save_data(data)


def calcular_estadisticas_persona(persona_id, roles_lista):
    if isinstance(roles_lista, str):
        roles_lista = [roles_lista]
    docs_persona = get_docs_por_persona(roles_lista)
    avances      = get_avance_persona(persona_id)
    if docs_persona.empty:
        return {"total": 0, "completados": 0, "en_curso": 0, "pendientes": 0,
                "pct_avance": 0.0, "horas_completadas": 0.0, "horas_totales": 0.0}
    avances_clean = avances.drop(columns=["id"], errors="ignore")
    merged = docs_persona.merge(avances_clean, left_on="id", right_on="documento_id", how="left")
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
            roles = p["roles"] if isinstance(p["roles"], list) else [p["roles"]]
            stats = calcular_estadisticas_persona(p["id"], roles)
            resumen.append({
                "Nombre": p["nombre"], "Roles": " · ".join(roles),
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
# HELPER TEMA — PLOTLY
# ─────────────────────────────────────────────────────────────────────────────
def plotly_layout_base():
    """Retorna parámetros de layout Plotly adaptados al tema activo."""
    is_dark = st.get_option("theme.base") == "dark"
    bg      = "#0E1117" if is_dark else "#FFFFFF"
    plot_bg = "#1A1E2E" if is_dark else "#F7F9FC"
    font_c  = "#E8EDF3" if is_dark else "#2C3E50"
    grid_c  = "rgba(255,255,255,0.08)" if is_dark else "rgba(0,0,0,0.06)"
    return dict(
        plot_bgcolor=plot_bg,
        paper_bgcolor=bg,
        font=dict(color=font_c, family="Inter, Segoe UI, sans-serif"),
        xaxis=dict(gridcolor=grid_c, linecolor=grid_c, zerolinecolor=grid_c),
        yaxis=dict(gridcolor=grid_c, linecolor=grid_c, zerolinecolor=grid_c),
    )
# ─────────────────────────────────────────────────────────────────────────────
# ESTILOS CSS
# ─────────────────────────────────────────────────────────────────────────────
def inject_css():
    SIDEBAR_BG   = "#0D1B2A"
    SIDEBAR_ACC  = "#1565C0"
    ACCENT_LIGHT = "#E8EDF3"
    BTN_BG       = "#1565C0"
    BTN_HOVER    = "#1976D2"
    METRIC_VAL   = "#1565C0"

    st.markdown(f"""
    <style>
    html, body, [class*="css"] {{
        font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
    }}
    [data-testid="stSidebar"],
    [data-testid="stSidebarHeader"],
    section[data-testid="stSidebar"] > div:first-child {{
        background-color: {SIDEBAR_BG} !important;
    }}
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] small,
    [data-testid="stSidebar"] .stMarkdown {{
        color: #2C3E50 !important;
    }}
    [data-testid="stSidebar"] hr {{
        border-color: rgba(255,255,255,0.15) !important;
    }}
    [data-testid="stSidebar"] .stRadio > label > div {{
        color: rgba(232,237,243,0.5) !important;
        font-size: 0.70rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.09em;
        margin-bottom: 4px;
    }}
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {{
        color: #2C3E50 !important;
        padding: 7px 14px;
        border-radius: 8px;
        font-size: 0.88rem;
        font-weight: 500;
        transition: background 0.15s;
        margin-bottom: 2px;
    }}
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover {{
        background: rgba(255,255,255,0.08) !important;
    }}
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label[data-checked="true"],
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:has(input:checked) {{
        background: rgba(21,101,192,0.35) !important;
        color: #FFFFFF !important;
        font-weight: 600;
    }}
    [data-testid="stMetric"] {{
        background: #F7F9FC;
        border-radius: 12px;
        padding: 1.1rem 1.4rem;
        box-shadow: 0 1px 6px rgba(0,0,0,0.06);
        border: 1px solid #E8ECF2;
    }}
    [data-testid="stMetricLabel"] p {{
        font-size: 0.75rem !important;
        font-weight: 600 !important;
        color: #7A8599 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}
    [data-testid="stMetricValue"] div {{
        font-size: 2.0rem !important;
        font-weight: 800 !important;
        color: #2C3E50 !important;
        line-height: 1.1 !important;
    }}
    [data-testid="stMetricDelta"] {{
        font-size: 0.78rem !important;
        color: #27ae60 !important;
    }}
    .stButton > button {{
        background: {BTN_BG};
        color: #FFFFFF !important;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.88rem;
        padding: 0.5rem 1.2rem;
        box-shadow: 0 2px 6px rgba(21,101,192,0.30);
        transition: all 0.18s;
    }}
    .stButton > button:hover {{
        background: {BTN_HOVER} !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 14px rgba(21,101,192,0.40);
    }}
    .stTabs [data-baseweb="tab-list"] {{
        background: #EEF2F8;
        border-radius: 10px;
        padding: 4px 6px;
        gap: 4px;
        overflow: visible !important;
        box-shadow: inset 0 1px 3px rgba(0,0,0,0.06);
    }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: 7px !important;
        padding: 6px 16px !important;
        font-weight: 500;
        font-size: 0.88rem;
        color: #3A4A6B !important;
        background: transparent !important;
        border: none !important;
        transition: background 0.15s;
    }}
    .stTabs [data-baseweb="tab"]:hover {{
        background: rgba(21,101,192,0.10) !important;
    }}
    .stTabs [aria-selected="true"] {{
        background: {SIDEBAR_ACC} !important;
        color: #FFFFFF !important;
        border-radius: 7px !important;
        box-shadow: 0 2px 6px rgba(21,101,192,0.35) !important;
    }}
    .stTabs [data-baseweb="tab-highlight"] {{ display: none !important; }}
    .stTabs [data-baseweb="tab-border"]    {{ display: none !important; }}
    [data-testid="stDataFrame"] {{
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }}
    .stProgress > div > div > div > div {{
        background-color: {SIDEBAR_ACC};
    }}
    .alerta-roja {{
        background: #FFF0F0;
        border-left: 4px solid #E53935;
        padding: 10px 14px;
        border-radius: 6px;
        margin: 5px 0;
        font-size: 0.88rem;
        color: #2C3E50 !important;
    }}
    .alerta-verde {{
        background: #F0FFF4;
        border-left: 4px solid #27AE60;
        padding: 10px 14px;
        border-radius: 6px;
        margin: 5px 0;
        font-size: 0.88rem;
        color: #2C3E50 !important;
    }}
    .alerta-amarilla {{
        background: #FFFDF0;
        border-left: 4px solid #F39C12;
        padding: 10px 14px;
        border-radius: 6px;
        margin: 5px 0;
        font-size: 0.88rem;
        color: #2C3E50 !important;
    }}
    .badge-rol {{
        display: inline-block;
        background: #E8F0FE;
        color: #1565C0;
        border: 1px solid #BBDEFB;
        border-radius: 12px;
        padding: 2px 10px;
        font-size: 0.78rem;
        font-weight: 600;
        margin: 2px 3px;
    }}
    .badge-transversal {{
        display: inline-block;
        background: #FFF8E1;
        color: #F57F17;
        border: 1px solid #FFE082;
        border-radius: 12px;
        padding: 2px 10px;
        font-size: 0.72rem;
        font-weight: 700;
        margin-left: 6px;
    }}
    footer    {{ visibility: hidden; }}
    #MainMenu {{ visibility: hidden; }}
    </style>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA 1 — DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
def pagina_dashboard():
    st.markdown("# Dashboard — Sistema de seguimiento a la formación del personal del área IIAD")
    st.markdown('### Basado en las normas ISO 17034 / ISO 17043 / ISO 13528')
    st.caption(f"📅 Actualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    personal = get_personal()
    if personal.empty:
        st.warning("No hay personal registrado. Ve a ⚙️ Administración para agregar personas.")
        return

    all_stats = []
    for _, p in personal.iterrows():
        roles = p["roles"] if isinstance(p["roles"], list) else [p["roles"]]
        s = calcular_estadisticas_persona(p["id"], roles)
        s["nombre"] = p["nombre"]; s["rol_display"] = p["rol_display"]
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
        color_alerta = "inverse" if personas_criticas > 0 else "normal"
        st.metric("⚠️ Personas en Alerta", str(personas_criticas),
                  delta=f"{personas_criticas} requieren atención" if personas_criticas > 0 else "Sin alertas",
                  delta_color=color_alerta)
    with col4:
        st.metric("⏱️ Horas Completadas", f"{df_stats['horas_completadas'].sum():.0f}h")
    st.divider()

    col_left, col_right = st.columns([2, 1])
    with col_left:
        st.subheader("📈 Avance por Persona")
        df_plot = df_stats.sort_values("pct_avance", ascending=True)
        colors = ["#E53935" if v < 20 else "#F39C12" if v < 60 else "#27AE60" for v in df_plot["pct_avance"]]
        fig = go.Figure(go.Bar(
            x=df_plot["pct_avance"], y=df_plot["nombre"], orientation="h",
            marker_color=colors,
            text=[f"{v:.1f}%" for v in df_plot["pct_avance"]], textposition="outside"
        ))
        fig.add_vline(x=60,  line_dash="dash", line_color="orange", annotation_text="Meta Intermedia 60%")
        fig.add_vline(x=100, line_dash="dash", line_color="green",  annotation_text="Meta Final 100%")
        fig.update_layout(
            xaxis_range=[0, 115], height=350, xaxis_title="% Avance",
            margin=dict(l=200, r=30, t=40, b=40),
            yaxis=dict(automargin=True),
            **plotly_layout_base()
        )
        st.plotly_chart(fig, use_container_width=True)
    with col_right:
        st.subheader("🥧 Distribución Global")
        fig_pie = go.Figure(go.Pie(
            labels=["Completado", "En curso", "Pendiente"],
            values=[df_stats["completados"].sum(), df_stats["en_curso"].sum(), 
        df_stats["pendientes"].sum()],
            hole=0.4,
            marker_colors=["#27AE60", "#F39C12", "#CFD8DC"],
            textinfo="percent",
            textfont=dict(color="#FFFFFF", size=13),
        ))
        fig_pie.update_layout(
            height=300,
            showlegend=True,
            legend=dict(
                font=dict(color="#E8EDF3", size=12),
                bgcolor="rgba(0,0,0,0)",
                orientation="v",
                x=1.0,
                y=0.5,
            ),
            margin=dict(l=10, r=120, t=10, b=10),
            **plotly_layout_base()
        )

    st.subheader("🚦 Sistema de Alertas")
    for _, row in df_stats[df_stats["pct_avance"] < 20].iterrows():
        st.markdown(f'<div class="alerta-roja">🔴 <strong>{row["nombre"]}</strong> ({row["rol_display"]}) — {row["pct_avance"]}% — Acción urgente requerida</div>', unsafe_allow_html=True)
    for _, row in df_stats[(df_stats["pct_avance"] >= 20) & (df_stats["pct_avance"] < 60)].iterrows():
        st.markdown(f'<div class="alerta-amarilla">🟡 <strong>{row["nombre"]}</strong> ({row["rol_display"]}) — {row["pct_avance"]}% — Revisar cronograma</div>', unsafe_allow_html=True)
    for _, row in df_stats[df_stats["pct_avance"] >= 60].iterrows():
        st.markdown(f'<div class="alerta-verde">🟢 <strong>{row["nombre"]}</strong> ({row["rol_display"]}) — {row["pct_avance"]}% — En buen camino</div>', unsafe_allow_html=True)


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
    roles   = persona["roles"] if isinstance(persona["roles"], list) else [persona["roles"]]
    with col2:
        badges = " ".join([f'<span class="badge-rol">{r}</span>' for r in roles])
        st.markdown(
            f'<div style="padding:10px 0;">👤 <strong>Roles:</strong> {badges}<br>'
            f'<small style="color:#7A8599;">Ingreso: {persona["fecha_ingreso"]}</small></div>',
            unsafe_allow_html=True
        )

    stats = calcular_estadisticas_persona(persona["id"], roles)
    st.progress(stats["pct_avance"] / 100,
                text=f"Avance global: {stats['pct_avance']}% ({stats['completados']}/{stats['total']} docs | {stats['horas_completadas']}h/{stats['horas_totales']}h)")
    
    docs_persona  = get_docs_por_persona(roles)
    avances       = get_avance_persona(persona["id"])
    avances_clean = avances.drop(columns=["id"], errors="ignore")
    # Deduplicar avances: conservar el registro más reciente por documento
    if not avances_clean.empty and "documento_id" in avances_clean.columns:
        avances_clean = avances_clean.drop_duplicates(
            subset=["documento_id"], keep="last"
        )
    merged = docs_persona.merge(avances_clean, left_on="id", right_on="documento_id", how="left")
    merged["estado"] = merged["estado"].fillna("Pendiente")


    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        filtro_estado = st.selectbox("Filtrar por estado", ["Todos","Pendiente","En curso","Completado"])
    with col_f2:
        filtro_cat = st.selectbox("Filtrar por categoría", ["Todas"] + sorted(docs_persona["categoria"].unique().tolist()))
    with col_f3:
        solo_criticos = st.checkbox("⚠️ Solo críticos")
    with col_f4:
        solo_transversal = st.checkbox("🔀 Solo transversales")

    df_filtrado = merged.copy()
    if filtro_estado    != "Todos":  df_filtrado = df_filtrado[df_filtrado["estado"]         == filtro_estado]
    if filtro_cat       != "Todas":  df_filtrado = df_filtrado[df_filtrado["categoria"]       == filtro_cat]
    if solo_criticos:                df_filtrado = df_filtrado[df_filtrado["es_critico"]      == 1]
    if solo_transversal:             df_filtrado = df_filtrado[df_filtrado["es_transversal"].fillna(False) == True]


    st.subheader(f"📋 {len(df_filtrado)} de {len(merged)} documentos mostrados")
    registrado_por = st.text_input("👤 Registrado por", value="Capacitador IIAD")

    cambios = {}
    for _, doc in df_filtrado.iterrows():
        badge_crit = "⚠️ CRÍTICO " if doc["es_critico"] else ""
        roles_cubre = doc.get("roles_que_cubre", [])
        badge_trans = " 🔀 TRANSVERSAL" if doc.get("es_transversal") else ""
        with st.expander(
            f"{badge_crit}[{doc['codigo']}] {doc['nombre']} — {doc['horas']}h — {doc['nivel']}{badge_trans} — Estado: {doc['estado']}"
        ):
            if roles_cubre:
                badges_roles = " ".join([f'<span class="badge-rol">{r}</span>' for r in roles_cubre])
                trans_badge  = '<span class="badge-transversal">🔀 Transversal</span>' if doc.get("es_transversal") else ""
                st.markdown(f"📌 **Cubre roles:** {badges_roles} {trans_badge}", unsafe_allow_html=True)
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
                    new_id = max((a.get("id", 0) for a in data["avances"]), default=0) + 1
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
    all_roles = set()
    for _, p in personal.iterrows():
        roles = p["roles"] if isinstance(p["roles"], list) else [p["roles"]]
        all_roles.update(roles)
    rol_sel = st.selectbox("🔍 Seleccionar Rol", ["Todos los roles"] + sorted(all_roles))

    if rol_sel == "Todos los roles":
        personal_filtrado = personal
    else:
        personal_filtrado = personal[personal["roles"].apply(
            lambda r: rol_sel in (r if isinstance(r, list) else [r])
        )]

    resumen = []
    for _, p in personal_filtrado.iterrows():
        roles = p["roles"] if isinstance(p["roles"], list) else [p["roles"]]
        s = calcular_estadisticas_persona(p["id"], roles)
        resumen.append({
            "Nombre": p["nombre"], "Roles": p["rol_display"],
            "% Avance": s["pct_avance"],
            "Completados": s["completados"], "Total Docs": s["total"],
            "Horas Completadas": s["horas_completadas"], "Horas Totales": s["horas_totales"],
            "Estado": "🟢 Bien" if s["pct_avance"] >= 60 else "🟡 Atención" if s["pct_avance"] >= 20 else "🔴 Crítico"
        })
    df_res = pd.DataFrame(resumen)
    st.dataframe(df_res, use_container_width=True, hide_index=True)

    if not df_res.empty:
        fig = px.bar(df_res, x="Nombre", y="% Avance", color="Estado",
                     color_discrete_map={"🟢 Bien": "#27AE60", "🟡 Atención": "#F39C12", "🔴 Crítico": "#E53935"},
                     title=f"Comparación de Avances — {rol_sel}", text="% Avance")
        fig.add_hline(y=60, line_dash="dash", annotation_text="Meta intermedia 60%")
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.update_layout(
            margin=dict(l=20, r=20, t=40, b=40),
            **plotly_layout_base()
        )
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
        (1, 1,"Mar","Fundamentos SGC",    "GSA-SAD-MC-001",  "Manual SGC SAD",             1.5,"TODOS",             "Presencial grupal",      "⚠️ CRÍTICA"),
        (1, 1,"Mar","Fundamentos SGC",    "GSA-SAD-MC-003",  "Manual Técnico AR",          4.0,"TODOS",             "Presencial grupal",      "⚠️ CRÍTICA"),
        (1, 1,"Mar","Fundamentos SGC",    "GSA-SAD-P-009",   "Confidencialidad",           1.5,"TODOS",             "Presencial grupal",      "⚠️ CRÍTICA"),
        (2, 1,"Mar","Fundamentos SGC",    "GSA-SAD-P-020",   "Manejo documentos SAD",      1.5,"TODOS",             "Presencial grupal",      "ALTA"),
        (2, 1,"Mar","Fundamentos SGC",    "GSA-SAD-P-012",   "Gestión Personal",           3.0,"Resp/Prof/Líderes", "Presencial grupal",      "ALTA"),
        (3, 1,"Mar","Normas ISO Núcleo",  "ISO 17034:2017",  "Requisitos PMR",             4.0,"Resp/Prof/Líd.Prod","Taller externo INM",     "⚠️ CRÍTICA"),
        (3, 1,"Mar","Normas ISO Núcleo",  "ISO 17043:2023",  "Requisitos PEA",             4.0,"Resp/Líd.Comp/PA",  "Taller externo INM",     "⚠️ CRÍTICA"),
        (4, 1,"Mar","Normas ISO Núcleo",  "ISO 17025:2017",  "Laboratorios",               3.0,"TODOS",             "Autoestudio guiado",     "ALTA"),
        (5, 2,"Abr","Procesos Técnicos",  "GSA-SAD-P-024",   "Producción MR",              3.0,"Resp/Prof/Líd.Prod","Taller técnico",         "⚠️ CRÍTICA"),
        (5, 2,"Abr","Procesos Técnicos",  "GSA-SAD-P-026",   "Homogeneidad y Estabilidad", 4.0,"Resp/Líd.Prod/PA",  "Taller c/ejercicios",    "⚠️ CRÍTICA"),
        (6, 2,"Abr","Procesos Técnicos",  "GSA-SAD-P-031",   "Diseño EA/CI",               4.0,"Líd.Comp/PA",       "Taller técnico",         "⚠️ CRÍTICA"),
        (6, 2,"Abr","Procesos Técnicos",  "GSA-SAD-P-033",   "Diseño estadístico PT",      4.0,"Resp/Líd.Comp/PA",  "Taller c/software",      "⚠️ CRÍTICA"),
        (7, 2,"Abr","Estadística Crítica","ISO 13528:2022",  "Métodos Estadísticos PT",    8.0,"Líd.Comp/PA/Resp",  "Curso externo CENAM",    "⚠️ MUY CRÍTICA"),
        (8, 2,"Abr","Estadística Crítica","GSA-SAD-P-027",   "Análisis datos PT",          4.0,"Resp/Líd.Comp/PA",  "Taller casos prácticos", "⚠️ CRÍTICA"),
        (9, 3,"May","Normas Técnicas",    "ISO 33405:2022",  "Homog. y Estab.",            4.0,"Todos técnicos",    "Taller externo",         "⚠️ CRÍTICA"),
        (9, 3,"May","Normas Técnicas",    "ISO 33403:2023",  "Caracterización MR",         4.0,"Resp/Prof/Líd.Prod","Taller externo",         "⚠️ CRÍTICA"),
        (10,3,"May","Normas Técnicas",    "GSA-SAD-P-003",   "Incertidumbre",              4.0,"TODOS",             "Taller c/ejercicios",    "ALTA"),
        (10,3,"May","Normas Técnicas",    "GSA-SAD-P-002",   "Validación métodos",         4.0,"Resp/Prof/Líderes", "Taller técnico",         "ALTA"),
        (11,3,"May","Normas Técnicas",    "ISO 33402:2022",  "Certificados MRC",           3.0,"Líd.Prod/Prof",     "Autoestudio/ejercicio",  "ALTA"),
        (13,4,"Jun","SGC Operativo",      "GSA-SAD-P-001",   "Gestión equipos",            3.0,"Resp/Líderes",      "Taller práctico",        "ALTA"),
        (13,4,"Jun","SGC Operativo",      "GSA-SAD-P-004",   "Trabajo no conforme",        3.0,"Resp/Prof/Líderes", "Taller c/casos",         "ALTA"),
        (15,4,"Jun","SGC Operativo",      "GSA-I-SAD-006",   "Auditorías internas",        1.5,"TODOS",             "Taller simulacro",       "ALTA"),
        (17,5,"Jul","Calidad Avanzada",   "GSA-I-SAD-038",   "Riesgos y oportunidades",    3.0,"Resp/PA",           "Taller DOFA/AMFE",       "ALTA"),
        (17,5,"Jul","Calidad Avanzada",   "GSA-I-SAD-007",   "Acciones correctivas",       3.0,"Resp/Líderes",      "Taller c/Form 3-604",    "ALTA"),
        (22,6,"Ago","Integración Final",  "SIMULACRO-AUDIT", "Simulacro auditoría",        4.0,"TODOS",             "Auditoría simulada",     "⚠️ CRÍTICA"),
        (24,6,"Ago","Certificación",      "EVAL-FINAL",      "Evaluación Final Integral",  4.0,"TODOS",             "Examen + entrevista",    "⚠️ CRÍTICA"),
    ]

    df_cron = pd.DataFrame(cronograma_data,
        columns=["Semana","Mes","MesNom","Bloque","Código","Actividad","Horas",
                 "Roles","Modalidad","Prioridad"])

    mes_sel = st.selectbox("Filtrar por mes", ["Todos"] + [f"Mes {i}" for i in range(1, 7)])
    if mes_sel != "Todos":
        df_cron = df_cron[df_cron["Mes"] == int(mes_sel.split(" ")[1])]

    st.dataframe(df_cron[["Semana","MesNom","Bloque","Código","Actividad",
                           "Horas","Roles","Modalidad","Prioridad"]],
                 use_container_width=True, hide_index=True)

    orden_meses = ["Mar", "Abr", "May", "Jun", "Jul", "Ago"]
    meses_horas = df_cron.groupby("MesNom")["Horas"].sum().reset_index()
    meses_horas["MesNom"] = pd.Categorical(
        meses_horas["MesNom"], categories=orden_meses, ordered=True
    )
    meses_horas = meses_horas.sort_values("MesNom")
    fig = px.bar(meses_horas, x="MesNom", y="Horas",
                 title="Distribución de Horas por Mes",
                 color="Horas", color_continuous_scale="Blues", text="Horas")
    fig.update_traces(texttemplate="%{text:.0f}h", textposition="outside")
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        **plotly_layout_base()
    )
    st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA 5 — REPORTES
# ─────────────────────────────────────────────────────────────────────────────
def pagina_reportes():
    st.title("📋 Generación de Reportes")
    personal = get_personal()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Reporte Individual")
        nombre_sel = st.selectbox("Seleccionar persona", personal["nombre"].tolist(), key="rep_ind")
        persona = personal[personal["nombre"] == nombre_sel].iloc[0]
        if st.button("Generar Vista Previa"):
            roles = persona["roles"] if isinstance(persona["roles"], list) else [persona["roles"]]
            stats       = calcular_estadisticas_persona(persona["id"], roles)
            docs_persona = get_docs_por_persona(roles)
            avances     = get_avance_persona(persona["id"])
            avances_clean = avances.drop(columns=["id"], errors="ignore")
            if not avances_clean.empty and "documento_id" in avances_clean.columns:
                avances_clean = avances_clean.drop_duplicates(
                    subset=["documento_id"], keep="last"
                )
            merged = docs_persona.merge(avances_clean, left_on="id", right_on="documento_id", how="left")
            merged["estado"] = merged["estado"].fillna("Pendiente")
            st.info(f"**{persona['nombre']}** | Roles: {persona['rol_display']} | "
                    f"Avance: {stats['pct_avance']}% | "
                    f"Docs: {stats['completados']}/{stats['total']} | "
                    f"Horas: {stats['horas_completadas']}h/{stats['horas_totales']}h")
            cols_mostrar = ["codigo","nombre","categoria","horas","nivel","estado","fecha_completitud","calificacion"]
            if "es_transversal" in merged.columns:
                cols_mostrar.append("es_transversal")
            st.dataframe(merged[cols_mostrar], use_container_width=True, hide_index=True)

    with col2:
        st.subheader("Reporte Ejecutivo Excel")
        excel_data = exportar_excel()
        st.download_button(
            label="📥 Descargar Reporte Excel",
            data=excel_data,
            file_name=f"ReporteFormacionIIAD_{date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )
        st.caption("Incluye: Maestro de personal · Resumen de avances por persona")


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA 6 — ADMINISTRACIÓN
# ─────────────────────────────────────────────────────────────────────────────
def pagina_admin():
    st.title("⚙️ Administración del Sistema")
    tab1, tab2, tab3 = st.tabs(["👥 Personal", "📚 Documentos", "🗄️ Datos GitHub"])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — PERSONAL
    # ══════════════════════════════════════════════════════════════════════════
    with tab1:
        st.subheader("Personal Activo")
        personal = get_personal()

        if not personal.empty:
            df_display = personal[["nombre", "rol_display", "fecha_ingreso", "estado"]].copy()
            df_display.columns = ["Nombre", "Roles", "Ingreso", "Estado"]
            st.dataframe(df_display, use_container_width=True, hide_index=True)

        st.divider()

        # ── Editar roles de persona existente ────────────────────────────────
        st.subheader("✏️ Editar Roles de Persona Existente")
        if not personal.empty:
            nombre_edit = st.selectbox("Seleccionar persona a editar", personal["nombre"].tolist(), key="edit_sel")
            persona_edit = personal[personal["nombre"] == nombre_edit].iloc[0]
            roles_actuales = persona_edit["roles"] if isinstance(persona_edit["roles"], list) else [persona_edit["roles"]]

            nuevos_roles = st.multiselect(
                "Roles asignados",
                options=ROLES_DISPONIBLES,
                default=roles_actuales,
                key="edit_roles"
            )
            if nuevos_roles:
                badges = " ".join([f'<span class="badge-rol">{r}</span>' for r in nuevos_roles])
                st.markdown(f"**Roles seleccionados:** {badges}", unsafe_allow_html=True)

            col_btn1, col_btn2 = st.columns([1, 3])
            with col_btn1:
                if st.button("💾 Actualizar Roles", type="primary"):
                    if not nuevos_roles:
                        st.warning("⚠️ Debe asignar al menos un rol.")
                    else:
                        with st.spinner("Guardando en GitHub..."):
                            if actualizar_roles_personal(int(persona_edit["id"]), nuevos_roles):
                                st.success(f"✅ Roles actualizados para {nombre_edit}")
                                st.rerun()

        st.divider()

        # ── Agregar nueva persona ─────────────────────────────────────────────
        st.subheader("➕ Agregar Nueva Persona")
        with st.form("form_persona"):
            nombre = st.text_input("Nombre Completo")
            roles_nuevos = st.multiselect(
                "Roles (puede seleccionar varios)",
                options=ROLES_DISPONIBLES,
                default=[ROLES_DISPONIBLES[0]]
            )
            if len(roles_nuevos) > 1:
                st.info(f"ℹ️ Los documentos comunes a los {len(roles_nuevos)} roles seleccionados "
                        f"se marcarán como **transversales** y solo se registrarán una vez.")
            fecha_ingreso = st.date_input("Fecha de ingreso")
            if st.form_submit_button("Guardar") and nombre:
                if not roles_nuevos:
                    st.warning("⚠️ Seleccione al menos un rol.")
                else:
                    with st.spinner("Guardando en GitHub..."):
                        if agregar_personal(nombre, roles_nuevos, fecha_ingreso):
                            st.success(f"✅ {nombre} agregado con roles: {' · '.join(roles_nuevos)}")
                            st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — DOCUMENTOS
    # ══════════════════════════════════════════════════════════════════════════
    with tab2:
        st.subheader("Catálogo de Documentos")

        docs_df = get_documentos()
        # Agregar columna de roles para cada documento
        if not docs_df.empty:
            docs_df["roles_asignados"] = docs_df["id"].apply(
                lambda did: " · ".join(get_roles_de_documento(did)) or "—"
            )
            st.dataframe(
                docs_df[["codigo", "nombre", "categoria", "horas", "nivel",
                          "norma_cubierta", "es_critico", "roles_asignados"]],
                use_container_width=True,
                hide_index=True
            )
            st.caption(f"📄 Total: {len(docs_df)} documentos en catálogo")

        st.divider()

        # ── Editar roles de documento existente ───────────────────────────────
        st.subheader("✏️ Editar Roles de Documento Existente")
        if not docs_df.empty:
            # Selector de documento
            opciones_docs = {
                f"[{row['codigo']}] {row['nombre']}": row["id"]
                for _, row in docs_df.iterrows()
            }
            doc_sel_label = st.selectbox(
                "Seleccionar documento",
                options=list(opciones_docs.keys()),
                key="doc_edit_sel"
            )
            doc_sel_id = opciones_docs[doc_sel_label]
            roles_doc_actuales = get_roles_de_documento(doc_sel_id)

            # Mostrar roles actuales con badges
            if roles_doc_actuales:
                badges_doc = " ".join([f'<span class="badge-rol">{r}</span>' for r in roles_doc_actuales])
                st.markdown(f"**Roles actuales:** {badges_doc}", unsafe_allow_html=True)
            else:
                st.warning("Este documento no tiene roles asignados actualmente.")

            nuevos_roles_doc = st.multiselect(
                "Roles asignados al documento",
                options=ROLES_DISPONIBLES,
                default=roles_doc_actuales,
                key="doc_edit_roles"
            )

            col_d1, col_d2 = st.columns([1, 3])
            with col_d1:
                if st.button("💾 Actualizar Roles del Documento", type="primary"):
                    if not nuevos_roles_doc:
                        st.warning("⚠️ Debe asignar al menos un rol antes de guardar.")
                    else:
                        with st.spinner("Guardando en GitHub..."):
                            if actualizar_roles_documento(doc_sel_id, nuevos_roles_doc):
                                st.success(f"✅ Roles actualizados para [{docs_df[docs_df['id'] == doc_sel_id]['codigo'].values[0]}]")
                                st.rerun()
        st.divider()

        # ── Agregar nuevo documento ───────────────────────────────────────────
        st.subheader("➕ Agregar Nuevo Documento")
        with st.form("form_nuevo_documento"):
            col_a, col_b = st.columns(2)
            with col_a:
                nuevo_codigo   = st.text_input("Código del documento",     placeholder="Ej: GSA-SAD-P-099")
                nuevo_nombre   = st.text_input("Nombre / Título",           placeholder="Ej: Procedimiento de validación...")
                nueva_categoria = st.selectbox("Categoría", CATEGORIAS_DISPONIBLES)
                nuevo_nivel    = st.selectbox("Nivel de formación", NIVELES_DISPONIBLES, index=1)
            with col_b:
                nuevas_horas   = st.number_input("Horas de formación", min_value=0.5, max_value=40.0,
                                                  value=3.0, step=0.5)
                nueva_norma    = st.text_input("Normas cubiertas",
                                               placeholder="Ej: ISO 17034 §7.2 / ISO 17043 §6.1")
                es_critico_new = st.checkbox("⚠️ Documento crítico")
                roles_nuevos_doc = st.multiselect(
                    "Roles que deben estudiar este documento",
                    options=ROLES_DISPONIBLES,
                    default=[]
                )

            # Nota informativa sobre transversalidad
            if len(roles_nuevos_doc) > 1:
                st.info(
                    f"ℹ️ Este documento aparecerá como **transversal** para las personas "
                    f"que tengan ≥2 de los {len(roles_nuevos_doc)} roles seleccionados."
                )
            elif len(roles_nuevos_doc) == 0:
                st.warning("⚠️ Sin roles asignados, el documento no aparecerá en ningún plan de formación.")

            submitted = st.form_submit_button("💾 Guardar Nuevo Documento", type="primary")
            if submitted:
                if not nuevo_codigo.strip():
                    st.error("❌ El código es obligatorio.")
                elif not nuevo_nombre.strip():
                    st.error("❌ El nombre es obligatorio.")
                else:
                    with st.spinner("Guardando en GitHub..."):
                        ok, err = agregar_documento(
                            codigo=nuevo_codigo.strip(),
                            nombre=nuevo_nombre.strip(),
                            categoria=nueva_categoria,
                            horas=nuevas_horas,
                            nivel=nuevo_nivel,
                            norma_cubierta=nueva_norma.strip(),
                            es_critico=es_critico_new,
                            roles_asignados=roles_nuevos_doc
                        )
                        if ok:
                            roles_str = " · ".join(roles_nuevos_doc) if roles_nuevos_doc else "ningún rol"
                            st.success(
                                f"✅ Documento **{nuevo_codigo}** agregado al catálogo. "
                                f"Asignado a: {roles_str}"
                            )
                            st.rerun()
                        else:
                            st.error(f"❌ {err}")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 — DATOS GITHUB
    # ══════════════════════════════════════════════════════════════════════════
    with tab3:
        st.subheader("Información del Sistema — Almacenamiento GitHub")
        data = get_data()
        c1, c2, c3 = st.columns(3)
        c1.metric("Personal registrado",    len(data.get("personal", [])))
        c2.metric("Documentos en catálogo", len(data.get("documentos", [])))
        c3.metric("Registros de avance",    len(data.get("avances", [])))
        st.info(f"📦 Repositorio: `{GITHUB_OWNER}/{GITHUB_REPO}` | Archivo: `{DATA_FILE}`")
        meta = data.get("_meta", {})
        if meta:
            st.caption(f"Versión: {meta.get('version')} | Creado: {meta.get('creado')}")
        if st.button("🔄 Forzar recarga desde GitHub"):
            for k in ["app_data", "data_sha", "refresh"]:
                st.session_state.pop(k, None)
            st.rerun()
        st.divider()
        st.subheader("Descargar JSON")
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        st.download_button("📥 Descargar formacion_iiad.json", data=json_str,
                           file_name=f"formacion_iiad_{date.today()}.json",
                           mime="application/json")
        with st.expander("Vista previa JSON"):
            preview = {**data, "avances": data.get("avances", [])[:5]}
            st.json(preview)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    inject_css()

    with st.sidebar:
        LOGO_URL = (
            "https://raw.githubusercontent.com/"
            "IIAD-LANIA/iiad-lania-programa_entrenamiento/main/assets/logo_ica.png"
        )
        st.markdown(f"""
        <div style="text-align:center; padding:1.6rem 0.5rem 1.0rem 0.5rem;">
            <img src="{LOGO_URL}"
                 id="ica-logo"
                 style="max-width:130px; width:100%;
                        filter:brightness(0) invert(1);
                        display:block; margin:0 auto;"
                 onerror="
                     this.style.display='none';
                     document.getElementById('ica-badge').style.display='flex';
                 " />
            <div id="ica-badge" style="
                display:none; justify-content:center; align-items:center;
                flex-direction:column; gap:4px;
            ">
                <div style="
                    width:60px; height:60px; border-radius:50%;
                    background:rgba(255,255,255,0.10);
                    border:2px solid rgba(255,255,255,0.30);
                    display:flex; align-items:center; justify-content:center;
                    font-size:1.7rem;
                ">🧪</div>
                <div style="
                    font-size:0.92rem; font-weight:800; color:#FFFFFF;
                    letter-spacing:0.12em; margin-top:4px;
                ">ICA</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style="
            text-align:center;
            padding: 0 0.8rem 1.0rem 0.8rem;
            border-bottom: 1px solid rgba(255,255,255,0.12);
            margin-bottom: 0.8rem;
        ">
            <div style="
                font-size:0.85rem; font-weight:700;
                color:#FFFFFF; letter-spacing:0.01em;
                line-height:1.4;
            ">
                Laboratorio Nacional de Insumos Agrícolas
            </div>
            <div style="font-size:0.72rem; color:rgba(232,237,243,0.55); margin-top:4px;">
                Área IIAD · ISO 17034 | ISO 17043
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('## Sistema de seguimiento de formación')
        st.markdown('### Área de Investigación e Innovación Analítica y Diagnóstica - IIAD')

        pagina = st.radio(
            "NAVEGACIÓN",
            ["🏠 Dashboard",
             "📝 Registro de Avances",
             "📊 Análisis por Rol",
             "📅 Cronograma",
             "📋 Reportes",
             "⚙️ Administración"],
        )

        st.markdown("<div style='margin-top:auto; padding-top:2rem;'></div>", unsafe_allow_html=True)
        st.markdown("""
        <div style="
            text-align:center;
            padding: 0.7rem 1rem 0.6rem 1rem;
            border-top: 1px solid rgba(255,255,255,0.10);
        ">
            <div style="font-size:0.65rem; color:rgba(232,237,243,0.35); line-height:1.7;">
                v2.5 · Feb 2026<br>
                🗄️ GitHub JSON · ARCAL RLA5091
            </div>
        </div>
        """, unsafe_allow_html=True)

    if   pagina == "🏠 Dashboard":           pagina_dashboard()
    elif pagina == "📝 Registro de Avances": pagina_registro()
    elif pagina == "📊 Análisis por Rol":    pagina_analisis_rol()
    elif pagina == "📅 Cronograma":          pagina_cronograma()
    elif pagina == "📋 Reportes":            pagina_reportes()
    elif pagina == "⚙️ Administración":      pagina_admin()


if __name__ == "__main__":
    main()
