# 🧪 Sistema de Seguimiento de Formación — Área IIAD / ICA

> Aplicación web para el seguimiento de avances de formación del personal del Área IIAD,
> en cumplimiento de los requisitos de competencia de **ISO 17034:2017** e **ISO/IEC 17043:2023**.

---

## 🌐 Despliegue en Streamlit Cloud (vía GitHub)

### PASO 1 — Crear cuenta en GitHub
1. Ir a [https://github.com](https://github.com)
2. Clic en **Sign up**
3. Registrarse con correo institucional o personal
4. Verificar el correo

---

### PASO 2 — Crear el repositorio en GitHub

1. En GitHub, clic en **"+"** (esquina superior derecha) → **New repository**
2. Configurar el repositorio:
   - **Repository name**: `formacion-iiad-ica`  ← (puede ser cualquier nombre)
   - **Description**: `Sistema de seguimiento de formación ISO 17034/17043 - ICA`
   - **Visibility**: `Private` ✅ ← recomendado para datos institucionales
   - **Initialize with README**: ✅ marcar esta opción
3. Clic en **Create repository**

---

### PASO 3 — Subir los archivos al repositorio

#### Opción A: Desde la interfaz web de GitHub (más fácil, sin instalar nada)

1. Dentro del repositorio recién creado, clic en **"Add file"** → **"Upload files"**
2. Arrastrar o seleccionar los siguientes archivos:
   ```
   app_iiad.py          ← Código principal de la app
   requirements.txt     ← Dependencias Python
   ```
3. En la sección **"Commit changes"** escribir: `Initial commit - app formación IIAD`
4. Clic en **Commit changes**

#### Opción B: Desde terminal con Git (si tiene Git instalado)

```bash
# Clonar el repositorio vacío
git clone https://github.com/TU_USUARIO/formacion-iiad-ica.git

# Entrar a la carpeta
cd formacion-iiad-ica

# Copiar app_iiad.py y requirements.txt en esta carpeta

# Subir los archivos
git add .
git commit -m "Initial commit - app formación IIAD"
git push origin main
```

---

### PASO 4 — Crear cuenta en Streamlit Cloud

1. Ir a [https://share.streamlit.io](https://share.streamlit.io)
2. Clic en **"Sign up"**
3. Seleccionar **"Continue with GitHub"** ← importante, usar la misma cuenta de GitHub
4. Autorizar el acceso de Streamlit a GitHub

---

### PASO 5 — Desplegar la aplicación

1. En Streamlit Cloud, clic en **"New app"**
2. Configurar el despliegue:

   | Campo | Valor |
   |-------|-------|
   | **Repository** | `TU_USUARIO/formacion-iiad-ica` |
   | **Branch** | `main` |
   | **Main file path** | `app_iiad.py` |
   | **App URL** (opcional) | `iiad-formacion-ica` |

3. Clic en **"Deploy!"**
4. Esperar ~2-3 minutos mientras instala las dependencias
5. ✅ La app queda publicada en una URL como:
   ```
   https://iiad-formacion-ica.streamlit.app
   ```

---

### PASO 6 — Acceder y compartir la app

- **URL pública**: `https://iiad-formacion-ica.streamlit.app`
- Compartir el enlace con todo el equipo del área IIAD
- Funciona en **cualquier navegador** (Chrome, Firefox, Edge) y en **celular**
- **No requiere instalar nada** en los computadores de los usuarios

---

## 🔄 Actualizar la app después de cambios

Cuando se necesite modificar el código (`app_iiad.py`):

### Desde GitHub web:
1. Ir al repositorio en GitHub
2. Clic en `app_iiad.py`
3. Clic en el ícono de **lápiz ✏️** (Edit)
4. Hacer los cambios
5. Clic en **"Commit changes"**
6. ✅ Streamlit Cloud detecta el cambio y **redespliega automáticamente** en ~1 min

### Desde terminal:
```bash
# Editar app_iiad.py localmente
# Luego:
git add app_iiad.py
git commit -m "Descripción del cambio"
git push origin main
# Streamlit Cloud redespliega automáticamente ✅
```

---

## 📁 Estructura del repositorio

```
formacion-iiad-ica/
│
├── app_iiad.py          ← App principal (Streamlit)
├── requirements.txt     ← Dependencias Python
└── README.md            ← Este archivo
```

> **Nota**: La base de datos `iiad_formacion.db` se crea automáticamente
> en el servidor de Streamlit Cloud al primer inicio. Los datos persisten
> mientras la app esté activa.

---

## ⚠️ Consideración importante sobre los datos

Streamlit Cloud **reinicia la app** periódicamente (si no hay tráfico), lo que
puede borrar la base de datos SQLite. Para **persistencia permanente de datos**,
se recomienda en una siguiente versión migrar a:

- **Google Sheets** como base de datos (gratis, con `gspread`)
- **Supabase** (PostgreSQL gratuito en la nube)
- **Aiven** (MySQL/PostgreSQL gratuito)

Por ahora, para empezar y validar el sistema, SQLite es suficiente.
Se puede hacer **backup manual** desde la página ⚙️ Administración de la app.

---

## 🛠️ Dependencias (requirements.txt)

```
streamlit>=1.32.0
pandas>=2.0.0
plotly>=5.18.0
openpyxl>=3.1.0
```

---

## 📋 Normas implementadas

| Norma | Versión | Aplicación |
|-------|---------|------------|
| ISO 17034 | 2017 | Productores de Materiales de Referencia |
| ISO/IEC 17043 | 2023 | Proveedores de Ensayos de Aptitud |
| ISO 13528 | 2022 | Métodos estadísticos para EA |
| ISO 33405 | 2022 | Homogeneidad y estabilidad MR |
| ISO 33403 | 2023 | Caracterización de MR |

---

*Desarrollado para el Instituto Colombiano Agropecuario (ICA) — Subgerencia de Análisis y Diagnóstico — Área IIAD*
*Convenio ICA-INM bajo CONPES 4052 / Proyecto ARCAL RLA5091 2024-2027*
