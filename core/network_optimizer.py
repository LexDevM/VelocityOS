# core/network_optimizer.py

import winreg
from .state_manager import StateManager
from .registry_manager import RegistryManager

class NetworkOptimizer:
    def __init__(self, state_manager: StateManager, reg_manager: RegistryManager, console_logger):
        """
        Inicializa el optimizador de red.

        Args:
            state_manager (StateManager): El gestor para guardar y restaurar el estado.
            reg_manager (RegistryManager): El gestor para interactuar con el registro.
            console_logger (function): Una función callback para imprimir mensajes en la GUI.
        """
        self.state_manager = state_manager
        self.reg_manager = reg_manager
        self.log = console_logger
        # Claves de registro para desactivar el Algoritmo de Nagle.
        self.nagle_keys = {
            "TcpAckFrequency": 1,
            "TCPNoDelay": 1
        }

    def _get_network_interface_guids(self):
        """
        Encuentra los GUID de todas las interfaces de red físicas y virtuales
        enumerando las claves del registro de Windows. Es el método más fiable.
        """
        interface_guids = []
        # La clase de dispositivo para adaptadores de red tiene este GUID maestro.
        net_class_guid = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e972-e325-11ce-bfc1-08002be10318}"
        
        try:
            # Abrimos la clave maestra que contiene todas las interfaces.
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, net_class_guid) as key:
                i = 0
                while True:
                    try:
                        # Iteramos sobre las sub-claves numéricas (0000, 0001, 0002, etc.).
                        subkey_name = winreg.EnumKey(key, i)
                        
                        # Dentro de cada sub-clave, el valor 'NetCfgInstanceId' contiene el GUID que necesitamos.
                        with winreg.OpenKey(key, subkey_name) as subkey:
                            try:
                                guid, _ = winreg.QueryValueEx(subkey, "NetCfgInstanceId")
                                interface_guids.append(guid)
                            except FileNotFoundError:
                                pass # Esta sub-clave no es una interfaz de red válida, la ignoramos.
                        i += 1
                    except OSError:
                        # Se lanza cuando EnumKey no encuentra más sub-claves.
                        break
        except Exception as e:
            self.log(f"[ERROR-REG] No se pudo enumerar las interfaces de red: {e}")

        # Devolvemos una lista de GUIDs únicos para evitar duplicados.
        return list(set(interface_guids))

    def manage_nagle_algorithm(self, action='disable', profile=None):
        """Desactiva o restaura el Algoritmo de Nagle basándose en el perfil."""
        if not profile or not profile.get('enabled', False):
            self.log("\n[INFO] La optimización del Algoritmo de Nagle está desactivada en este perfil.")
            return

        log_header = "Desactivando" if action == 'disable' else "Restaurando"
        self.log(f"\n[+] {log_header} Algoritmo de Nagle para baja latencia...")
        
        interface_guids = self._get_network_interface_guids()
        if not interface_guids:
            self.log("[-] No se pudieron encontrar interfaces de red para optimizar.")
            return

        self.log(f"[INFO] Encontradas {len(interface_guids)} interfaces de red para analizar.")
        
        for guid in interface_guids:
            reg_path = fr"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces\{guid}"
            
            for key_name, disable_value in self.nagle_keys.items():
                state_key = f"nagle_{guid}_{key_name}"

                if action == 'disable':
                    # 1. Guardar el estado original del valor del registro.
                    original_value, original_type = self.reg_manager.get_value(reg_path, key_name)
                    
                    if self.state_manager.get_state(state_key) is None:
                        if original_value is not None:
                            self.state_manager.save_state(state_key, {"value": original_value, "type": original_type})
                        else:
                            self.state_manager.save_state(state_key, "__DELETE__")
                    
                    # 2. Establecer el valor optimizado.
                    self.reg_manager.set_value(reg_path, key_name, disable_value)

                elif action == 'restore':
                    # 1. Recuperar el estado original guardado.
                    saved_state = self.state_manager.get_state(state_key)
                    if saved_state is not None:
                        if saved_state == "__DELETE__":
                            self.reg_manager.delete_value(reg_path, key_name)
                        else:
                            self.reg_manager.set_value(reg_path, key_name, saved_state["value"], saved_state["type"])
        
        if action == 'disable':
            self.log(f"[OK] Tweaks de red aplicados a {len(interface_guids)} interfaces.")
        elif action == 'restore':
            self.log(f"[OK] Tweaks de red restaurados en {len(interface_guids)} interfaces.")