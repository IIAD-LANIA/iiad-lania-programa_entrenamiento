# 🧮 Guía de Integración — GitHub Storage Module para app_iiad.py

## Descripción General

Este documento describe cómo integrar el módulo `github_storage.py` en la aplicación Streamlit `app_iiad.py` para usar **GitHub como base de datos persistente** mediante archivos JSON almacenados en el repositorio.

### ✅ Estado Actual

- **github_storage.py**: ✅ Creado y funcional ([ver aquí](./github_storage.py))
- **app_iiad.py**: ⚠️ Requiere integración
- **Almacenamiento JSON**: ✅ Directorio `data/registros/` preparado
- **Autenticación GitHub**: ⚠️ Requiere configuración de secretos en Streamlit Cloud

---

## 🔧 Cambios Requeridos en app_iiad.py

### 1. **Importar el módulo de almacenamiento**

Añadir al inicio del archivo (después de las importaciones existentes):

```python
# Importar módulo de almacenamiento GitHub
try:
    from github_storage import GitHubStorage, get_storage
except ImportError:
    # Fallback si el módulo no está disponible en dev local
    GitHubStorage = None
    get_storage = None
```

### 2. **Reemplazar capa de persistencia**

La sección actual (líneas ~32-125):

```python
# ─────────────────────────────────────────────────────────────────────────────
# CAPA DE PERSISTENCIA — GITHUB JSON
# ─────────────────────────────────────────────────────────────────────────────
```

Debe **reemplazarse completamente** con:

```python
# ─────────────────────────────────────────────────────────────────────────────
# CAPA DE PERSISTENCIA — GITHUB JSON (v3.0)
# ─────────────────────────────────────────────────────────────────────────────

def get_storage_instance():
    """Obtener instancia de almacenamiento GitHub con manejo de errores."""
    if GitHubStorage is None:
        st.error("❌ Módulo de almacenamiento no disponible")
        return None
    try:
        storage = get_storage()
        return storage
    except ValueError as e:
        st.error(f"❌ {e}")
        return None
    except Exception as e:
        st.error(f"❌ Error inesperado: {e}")
        return None

def load_data_from_github():
    """Cargar datos desde archivo JSON en GitHub."""
    storage = get_storage_instance()
    if storage is None:
        return _datos_iniciales(), None
    
    # Leer archivo maestro (index.json)
    try:
        data = storage.leer_archivo(f"{storage.data_dir}/formacion_iiad.json")
        if data:
            return data, None  # SHA manejo futuro
        else:
            return _datos_iniciales(), None
    except Exception as e:
        st.warning(f"⚠️ Usando datos de sesión: {e}")
        return _datos_iniciales(), None

def save_data_to_github(data, sha=None):
    """Guardar datos en archivo JSON en GitHub."""
    storage = get_storage_instance()
    if storage is None:
        st.error("❌ No se puede guardar: almacenamiento no configurado")
        return False
    
    try:
        # Guardar en archivo de respaldo con timestamp
        ok = storage.actualizar_archivo_maestro({"data": data})
        if ok:
            st.session_state["last_save"] = datetime.now()
            return True
        else:
            st.error("❌ Error guardando en GitHub")
            return False
    except Exception as e:
        st.error(f"❌ Error: {e}")
        return False

def get_data():
    """Obtener datos de sesión con caché."""
    if "app_data" not in st.session_state or st.session_state.get("refresh", False):
        data, sha = load_data_from_github()
        st.session_state["app_data"] = data
        st.session_state["data_sha"] = sha
        st.session_state["refresh"] = False
    return st.session_state["app_data"]

def save_data(data):
    """Guardar datos en GitHub y actualizar sesión."""
    ok = save_data_to_github(data)
    if ok:
        st.session_state["app_data"] = data
        st.session_state["refresh"] = False
    return ok
```

---

## 🔐 Configuración de Secretos en Streamlit Cloud

Sin crear PR aún, se debe configurar en **Streamlit Cloud settings**:

### En `.streamlit/secrets.toml` (LOCAL):

```toml
GITHUB_TOKEN = "tu_personal_access_token_aquí"
GITHUB_OWNER = "IIAD-LANIA"
GITHUB_REPO = "iiad-lania-programa_entrenamiento"
```

### En Streamlit Cloud Dashboard:

1. Ir a **Advanced settings** → **Secrets**
2. Añadir:

```
GITHUB_TOKEN = ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GITHUB_OWNER = IIAD-LANIA
GITHUB_REPO = iiad-lania-programa_entrenamiento
```

**Importante**: El `GITHUB_TOKEN` debe ser un **Personal Access Token** con permisos:
- `repo` (acceso total a repositorios privados)
- `workflow` (si aplica CI/CD futuro)

---

## 📋 Checklist de Integración

- [ ] Añadir import del módulo `github_storage`
- [ ] Reemplazar la capa de persistencia en `app_iiad.py`
- [ ] Configurar `secrets.toml` en desarrollo local
- [ ] Crear PR con cambios integrados
- [ ] Activar branch protection en PR
- [ ] Configurar secretos en Streamlit Cloud
- [ ] Desplegar versión actualizada
- [ ] Probar guardado de datos desde la app
- [ ] Verificar commits en GitHub (nuevos archivos JSON)
- [ ] Monitorear logs en Streamlit Cloud

---

## 🐛 Troubleshooting

### Error: "GITHUB_TOKEN no configurado"

**Causa**: Los secretos no están disponibles

**Solución**:
1. Verificar `.streamlit/secrets.toml` está en raíz del repo (NO es ignorado por .gitignore)
2. En Streamlit Cloud, ir a **Settings** → **Secrets** → verificar valores
3. Redeploy la app

### Error: "401 Unauthorized"

**Causa**: Token inválido o expirado

**Solución**:
1. Generar nuevo Personal Access Token en GitHub
2. Actualizar secretos en Streamlit Cloud
3. Verificar permisos del token

### Error: "Directorio /data/registros no existe"

**Solución**: El directorio debe existir en el repo. Si no:
```bash
mkdir -p data/registros
touch data/registros/.gitkeep
git add data/registros/.gitkeep
git commit -m "Add data directory structure"
```

---

## 📊 Monitoreo de Datos

Una vez integrado, los datos se guardarán en:
- **Archivo principal**: `data/registros/index.json` (maestro con historial)
- **Backups automáticos**: `data/registros/registro_*.json` (respaldos con timestamp)

Cada guardado desde Streamlit generará un **commit automático** en el repo:

```
[COMMIT MESSAGE]
feat(registro): Guardar {nombre} - 2026-03-15-14-30-45
```

---

## 🔄 Próximos Pasos

1. **Crear rama de integración**: `feature/github-storage-v3`
2. **Hacer PR** con estos cambios
3. **Activar protecciones** en main branch
4. **Mergear a main** después de revisión
5. **Desplegar** en Streamlit Cloud v3.0
6. **Monitorear** primeras semanas de datos en vivo

---

## ✅ Referencias

- [GitHub Storage Module](./github_storage.py) — Implementación de la capa de almacenamiento
- [GSA-I-IIAD-001](https://www.notion.so/GSA-I-IIAD-001) — Normas de compliance
- [Streamlit Secrets](https://docs.streamlit.io/streamlit-community-cloud/deploy-your-app/secrets-management) — Documentación oficial
