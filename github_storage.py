"""Módulo para almacenar datos en GitHub.

Permite guardar y leer datos persistentes (JSON) en un repositorio GitHub,
utilizando la API de GitHub como base de datos.

Versión: 1.0.0
GSA-I-IIAD-001 Compliance
"""

import json
import base64
import streamlit as st
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class GitHubStorage:
    """Almacenamiento persistente usando GitHub API."""
    
    def __init__(self, owner: str = None, repo: str = None, token: str = None):
        """Inicializar cliente de GitHub.
        
        Args:
            owner: Propietario del repositorio (ej: IIAD-LANIA)
            repo: Nombre del repositorio
            token: Token de autenticación de GitHub
        """
        self.owner = owner or st.secrets.get("GITHUB_OWNER", "IIAD-LANIA")
        self.repo = repo or st.secrets.get("GITHUB_REPO", "iiad-lania-programa_entrenamiento")
        self.token = token or st.secrets.get("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
        self.data_dir = "data/registros"
        
        if not self.token:
            logger.error("Token de GitHub no configurado")
            raise ValueError("GITHUB_TOKEN no configurado en secretos de Streamlit")
    
    @property
    def headers(self) -> Dict[str, str]:
        """Headers para las solicitudes a la API de GitHub."""
        return {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
        }
    
    def verificar_conexion(self) -> bool:
        """Verificar que el token es válido."""
        try:
            url = f"{self.base_url}/user"
            response = requests.get(url, headers=self.headers, timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error verificando conexión: {e}")
            return False
    
    def guardar_registro(self, nombre: str, data: Dict[str, Any]) -> bool:
        """Guardar un registro JSON en GitHub.
        
        Args:
            nombre: Nombre identificador del registro
            data: Diccionario con los datos a guardar
            
        Returns:
            True si se guardó correctamente, False si hubo error
        """
        try:
            timestamp = datetime.now().isoformat().replace(":", "-")
            filename = f"{nombre}_{timestamp}.json"
            filepath = f"{self.data_dir}/{filename}"
            
            # Agregar metadatos
            record = {
                "timestamp": datetime.now().isoformat(),
                "nombre": nombre,
                "data": data
            }
            
            content_json = json.dumps(record, indent=2, ensure_ascii=False)
            encoded_content = base64.b64encode(content_json.encode()).decode()
            
            # Preparar payload
            url = f"{self.base_url}/repos/{self.owner}/{self.repo}/contents/{filepath}"
            payload = {
                "message": f"feat(registro): Guardar {nombre} - {timestamp}",
                "content": encoded_content,
                "branch": "main"
            }
            
            response = requests.put(url, json=payload, headers=self.headers, timeout=10)
            
            if response.status_code in [201, 200]:
                logger.info(f"Registro guardado: {filepath}")
                return True
            elif response.status_code == 401:
                logger.error("Token de GitHub inválido o expirado")
                return False
            else:
                logger.error(f"Error GitHub {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error guardando registro: {e}")
            return False
    
    def leer_archivo(self, filepath: str) -> Optional[Dict]:
        """Leer un archivo JSON de GitHub.
        
        Args:
            filepath: Ruta del archivo en el repositorio
            
        Returns:
            Diccionario con los datos, o None si hay error
        """
        try:
            url = f"{self.base_url}/repos/{self.owner}/{self.repo}/contents/{filepath}"
            response = requests.get(url, headers=self.headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                decoded = base64.b64decode(data['content']).decode()
                return json.loads(decoded)
            elif response.status_code == 404:
                logger.warning(f"Archivo no encontrado: {filepath}")
                return None
            else:
                logger.error(f"Error leyendo archivo: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error leyendo archivo: {e}")
            return None
    
    def listar_registros(self, prefijo: str = "") -> List[Dict]:
        """Listar todos los registros guardados.
        
        Args:
            prefijo: Prefijo para filtrar registros
            
        Returns:
            Lista de archivos encontrados
        """
        try:
            url = f"{self.base_url}/repos/{self.owner}/{self.repo}/contents/{self.data_dir}"
            response = requests.get(url, headers=self.headers, timeout=5)
            
            if response.status_code == 200:
                files = response.json()
                if prefijo:
                    files = [f for f in files if f['name'].startswith(prefijo)]
                return files
            elif response.status_code == 404:
                logger.info(f"Directorio no existe: {self.data_dir}")
                return []
            else:
                logger.error(f"Error listando registros: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error listando registros: {e}")
            return []
    
    def actualizar_archivo_maestro(self, data: Dict[str, Any]) -> bool:
        """Actualizar archivo maestro con índice de todos los registros.
        
        Args:
            data: Datos a guardar en el archivo maestro
            
        Returns:
            True si se guardó correctamente
        """
        try:
            filepath = f"{self.data_dir}/index.json"
            
            # Leer archivo existente
            existing = self.leer_archivo(filepath) or {"records": []}
            
            # Agregar nuevo registro
            existing["records"].append({
                "timestamp": datetime.now().isoformat(),
                **data
            })
            
            # Actualizar última modificación
            existing["last_updated"] = datetime.now().isoformat()
            
            content_json = json.dumps(existing, indent=2, ensure_ascii=False)
            encoded_content = base64.b64encode(content_json.encode()).decode()
            
            # Obtener SHA del archivo existente si existe
            url = f"{self.base_url}/repos/{self.owner}/{self.repo}/contents/{filepath}"
            sha_response = requests.get(url, headers=self.headers, timeout=5)
            sha = None
            if sha_response.status_code == 200:
                sha = sha_response.json()['sha']
            
            # Preparar payload
            payload = {
                "message": f"feat(index): Actualizar índice de registros",
                "content": encoded_content,
                "branch": "main"
            }
            
            if sha:
                payload["sha"] = sha
            
            response = requests.put(url, json=payload, headers=self.headers, timeout=10)
            
            return response.status_code in [201, 200]
            
        except Exception as e:
            logger.error(f"Error actualizando archivo maestro: {e}")
            return False


# Función de conveniencia para Streamlit
@st.cache_resource
def get_storage() -> GitHubStorage:
    """Obtener instancia de almacenamiento GitHub con caché."""
    try:
        storage = GitHubStorage()
        if storage.verificar_conexion():
            st.success("✅ Conectado a GitHub")
            return storage
        else:
            st.error("❌ Error conectando a GitHub. Token inválido.")
            return None
    except Exception as e:
        st.error(f"❌ Error inicializando almacenamiento: {e}")
        return None
