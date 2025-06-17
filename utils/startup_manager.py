# utils/startup_manager.py
import winreg
import sys
import os

class StartupManager:
    """Gestiona la entrada de la aplicación en el inicio de Windows."""
    
    def __init__(self, app_name, app_path):
        # La clave del registro para las aplicaciones de inicio del usuario actual
        self.key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        self.app_name = app_name
        # Asegurarse de que la ruta esté entre comillas para manejar espacios
        self.app_path = f'"{app_path}"'

    def _get_key(self, access):
        return winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.key_path, 0, access)

    def is_enabled(self):
        """Comprueba si la aplicación ya está configurada para iniciarse con Windows."""
        try:
            with self._get_key(winreg.KEY_READ) as key:
                winreg.QueryValueEx(key, self.app_name)
            return True
        except FileNotFoundError:
            return False
        except Exception:
            return False

    def set_startup(self, enable: bool):
        """Activa o desactiva el inicio con Windows."""
        try:
            if enable:
                with self._get_key(winreg.KEY_WRITE) as key:
                    winreg.SetValueEx(key, self.app_name, 0, winreg.REG_SZ, self.app_path)
            else:
                with self._get_key(winreg.KEY_WRITE) as key:
                    winreg.DeleteValue(key, self.app_name)
            return True
        except Exception as e:
            print(f"Error al configurar el inicio con Windows: {e}")
            return False