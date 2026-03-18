# Versión 2.6 | Bug fixes: IDs personal, SHA refresh, 
#              cronograma meses, transversales NaN, 
#              DuplicateElementKey avances

---

## [2.6.0] — 2026-03-18

### Corregido
- **`plotly_layout_base()`**: se eliminó la dependencia de `st.get_option("theme.base")`
  que no es confiable en Streamlit Cloud cuando el tema se define vía CSS inyectado.
  La función ahora acepta el parámetro `dark: bool = True` y se complementa con el
  helper `_dark()` que detecta el tema con tres niveles de fallback:
  `st.session_state["dark_mode"]` → `st.get_option("theme.base")` → `True`.
- **Gráficos Plotly en modo oscuro**: `paper_bgcolor` y `plot_bgcolor` ahora son
  transparentes / semi-transparentes para heredar el fondo del contenedor y evitar
  las "islas blancas" sobre el fondo oscuro de la app.
- **Ejes y etiquetas**: `tickfont` y `title_font` explícitos en todos los ejes
  (`#B0BEC5` modo oscuro, `#475569` modo claro) para garantizar contraste adecuado.
- **`legend`** duplicado en `fig_pie.update_layout()`: la expansión `**plotly_layout_base()`
  junto con `legend=dict(...)` explícito causaba `TypeError`. Se resolvió extrayendo
  `_base = plotly_layout_base()` y sobrescribiendo `_base["legend"]` antes del unpack.
- **`st.plotly_chart(fig_pie)`**: faltaba la llamada de renderizado del gráfico de
  torta "Distribución Global" en el dashboard — el gráfico simplemente no aparecía.
- **Sidebar — texto invisible**: color `#2C3E50` (azul oscuro) sobre fondo `#0D1B2A`
  cambiado a `#E8EDF3` en textos generales y `#CBD5E1` en ítems del menú radio.
- **`add_vline` / `add_hline` sin color de anotación**: las anotaciones de líneas
  de referencia (Meta Intermedia 60%, Meta Final 100%) heredaban color negro por
  defecto. Ahora tienen `annotation_font_color` y `annotation_bgcolor` explícitos.
- **`textposition="outside"` sin `textfont`**: etiquetas de barras en páginas
  Dashboard, Análisis por Rol y Cronograma sin color explícito eran invisibles en
  modo oscuro. Se agregó `textfont=dict(color="#E8EDF3", size=11/12)` en todos.
- **Gráfico cronograma — título recortado**: `margin=dict(t=10)` dejaba 10 px para
  el título de `px.bar()`, cortándolo visualmente. El título se movió a un
  `st.subheader()` independiente y los márgenes se ajustaron a `t=40, b=40`.
- **Colorbar del cronograma**: `tickfont` y `title_font` de la barra de color
  continua (escala Blues) eran negros e invisibles en modo oscuro.

### Añadido
- **CSS adicional en `inject_css()`**: nuevas reglas para `.stPlotlyChart iframe`
  (`background: transparent`), tablas `stDataFrame` con colores oscuros, labels de
  widgets de entrada y propiedades de `st.metric()` con colores explícitos.
- **Modo dual en gráficos**: `plotly_layout_base(dark)` soporta ahora modo claro
  (`dark=False`) con `plot_bgcolor` gris claro, fuente `#1E293B` y grillas sutiles,
  evitando el fondo azul-oscuro semitransparente sobre fondos blancos.
- **`height=380`** explícito en el gráfico de cronograma para evitar recorte de
  etiquetas superiores en barras altas.

---

## [2.5.1] - 2026-03-17

### Fixed
- BUG-001: Se agregó reintento automático ante conflictos de SHA al guardar `data/formacion_iiad.json` en GitHub, reduciendo fallos por edición concurrente.
- BUG-002: Se corrigió el filtro del cronograma en `pagina_cronograma()`, usando separación por espacio en `mes_sel` (`"Mes 1"`, `"Mes 2"`, etc.).
- BUG-003: Se eliminaron llamadas `st.success()` y `st.error()` dentro de `get_storage()` decorada con `@st.cache_resource`, reemplazándolas por registro con `logger`.
- BUG-004: Se hizo robusta la generación de nuevos IDs en `avances` usando `a.get("id", 0)` para tolerar registros legacy o incompletos.
- BUG-005: Se estabilizó el orden de creación de `requisitos_rol` usando `sorted(set(codigos))` para evitar resultados no deterministas.
- BUG-006: Se persistió la migración automática de `rol` a `roles` cuando se detectan datos legacy en el JSON cargado desde GitHub.
- BUG-007: Se agregó validación para impedir guardar documentos sin roles asignados desde la pestaña de administración.
- BUG-008: Se corrigió la métrica de “Personas en Alerta” para que use `delta` y `delta_color` de forma coherente en el dashboard.

### Notes
- Estas correcciones mejoran la estabilidad del almacenamiento GitHub, la trazabilidad de datos migrados y la consistencia visual y funcional del sistema de seguimiento de formación del área IIAD.

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0-dev] - 2026-03-14

### Added
- Initial repository setup
- Branch protection rules configured (main branch)
- CHANGELOG.md documentation
- VERSION.txt version tracking
- Metadata module for application metadata

### Initial Setup
- Repositorio privado creado per GSA-I-IIAD-001
- Rama main protegida con Pull Request obligatorio
- Estructura base del repositorio establecida
