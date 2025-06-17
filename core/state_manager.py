# core/state_manager.py
import json
import os
import logging # Usar logging para consistencia

class StateManager:
    """Gestiona el guardado y la restauración del estado del sistema."""
    
    def __init__(self, app_name="VelocityOS"):
        # Usamos AppData\Roaming, que es el lugar estándar para configuraciones que persisten.
        self.backup_dir = os.path.join(os.getenv('APPDATA'), app_name)
        self.backup_file = os.path.join(self.backup_dir, 'backup_state.json')
        os.makedirs(self.backup_dir, exist_ok=True)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.state = self._load_state()

    def _load_state(self):
        """Carga el estado desde el archivo JSON."""
        if os.path.exists(self.backup_file):
            try:
                with open(self.backup_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                self.logger.error(f"No se pudo cargar el archivo de estado: {e}")
                return {}
        return {}

    def save_state(self, key, value):
        """Guarda un valor de configuración específico."""
        self.state[key] = value
        try:
            with open(self.backup_file, 'w') as f:
                json.dump(self.state, f, indent=4)
            self.logger.info(f"Estado guardado: {key} = {value}")
        except IOError as e:
            self.logger.error(f"No se pudo guardar el archivo de estado: {e}")

    def get_state(self, key, default=None):
        """Obtiene un valor de configuración guardado."""
        return self.state.get(key, default)
        
    def backup_exists(self):
        """Verifica si existe un archivo de backup con datos."""
        return bool(self.state)

    def clear_backup(self):
        """Elimina el archivo de backup."""
        if os.path.exists(self.backup_file):
            try:
                os.remove(self.backup_file)
                self.state = {}
                self.logger.info("Backup de estado eliminado.")
            except OSError as e:
                self.logger.error(f"No se pudo eliminar el archivo de backup: {e}")