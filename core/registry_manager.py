# core/registry_manager.py
import winreg

class RegistryManager:
    """Una clase de utilidad para interactuar de forma segura con el Registro de Windows."""

    def __init__(self, log_function):
        self.log = log_function
        self.hkey_map = {
            "HKEY_CURRENT_USER": winreg.HKEY_CURRENT_USER,
            "HKEY_LOCAL_MACHINE": winreg.HKEY_LOCAL_MACHINE,
        }

    def _parse_path(self, full_path):
        """Divide una ruta completa (ej. 'HKLM\\Path\\To\\Key') en HKEY y sub_key."""
        parts = full_path.split('\\', 1)
        hkey_str = parts[0].upper().replace("HKCU", "HKEY_CURRENT_USER").replace("HKLM", "HKEY_LOCAL_MACHINE")
        
        if hkey_str not in self.hkey_map:
            raise ValueError(f"HKEY no válido: {hkey_str}")
            
        return self.hkey_map[hkey_str], parts[1]

    def get_value(self, key_path, value_name):
        """
        Obtiene un valor del registro.
        Devuelve (valor, tipo) o (None, None) si no existe.
        """
        try:
            hkey, sub_key = self._parse_path(key_path)
            with winreg.OpenKey(hkey, sub_key, 0, winreg.KEY_READ) as key:
                value, value_type = winreg.QueryValueEx(key, value_name)
                return value, value_type
        except FileNotFoundError:
            return None, None
        except Exception as e:
            self.log(f"[ERROR-REG] No se pudo leer el valor '{value_name}' en '{key_path}': {e}")
            return None, None

    def set_value(self, key_path, value_name, value, value_type=winreg.REG_DWORD):
        """
        Establece un valor en el registro. Crea la clave si no existe.
        """
        try:
            hkey, sub_key = self._parse_path(key_path)
            # AKEY_ALL_ACCESS da todos los permisos necesarios
            with winreg.CreateKeyEx(hkey, sub_key, 0, winreg.KEY_ALL_ACCESS) as key:
                winreg.SetValueEx(key, value_name, 0, value_type, value)
            return True
        except Exception as e:
            self.log(f"[ERROR-REG] No se pudo establecer el valor '{value_name}' en '{key_path}': {e}")
            return False
            
    def delete_value(self, key_path, value_name):
        """Elimina un valor del registro."""
        try:
            hkey, sub_key = self._parse_path(key_path)
            with winreg.OpenKey(hkey, sub_key, 0, winreg.KEY_ALL_ACCESS) as key:
                winreg.DeleteValue(key, value_name)
            return True
        except FileNotFoundError:
            # Si no existe, consideramos la operación un éxito.
            return True
        except Exception as e:
            self.log(f"[ERROR-REG] No se pudo eliminar el valor '{value_name}' de '{key_path}': {e}")
            return False