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
