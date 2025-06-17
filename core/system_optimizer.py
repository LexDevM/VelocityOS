# core/system_optimizer.py

import subprocess
import re
import os
import shutil
import psutil
import ctypes
from ctypes import wintypes

from .state_manager import StateManager
from .registry_manager import RegistryManager

class SystemOptimizer:
    def __init__(self, state_manager: StateManager, console_logger):
        """
        Inicializa el optimizador del sistema.

        Args:
            state_manager (StateManager): El gestor para guardar y restaurar el estado.
            console_logger (function): Una función callback para imprimir mensajes en la GUI.
        """
        self.state_manager = state_manager
        self.log = console_logger
        self.reg_manager = RegistryManager(console_logger)
        
        self.services_to_manage = [] # Esta lista ahora se llena desde el perfil.
        
        self.gaming_features_keys = {
            "GameDVR_Enabled": {
                "path": r"HKEY_CURRENT_USER\System\GameConfigStore",
                "value_name": "GameDVR_Enabled",
                "disable_value": 0,
                "type": "REG_DWORD"
            },
            "AppCaptureEnabled": {
                "path": r"HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\GameDVR",
                "value_name": "AppCaptureEnabled",
                "disable_value": 0,
                "type": "REG_DWORD"
            }
        }

    def _run_command(self, command, ignore_errors=None):
        """Ejecuta un comando de sistema de forma segura, con opción de ignorar errores esperados."""
        if ignore_errors is None:
            ignore_errors = []
            
        try:
            result = subprocess.check_output(
                command, shell=True, text=True, stderr=subprocess.PIPE, 
                encoding='cp850', creationflags=subprocess.CREATE_NO_WINDOW
            )
            return result.strip()
        except subprocess.CalledProcessError as e:
            if any(err_code in e.stderr for err_code in ignore_errors):
                return ""
            
            cmd_str = ' '.join(command) if isinstance(command, list) else command
            self.log(f"[WARN] El comando '{cmd_str}' falló con un error inesperado: {e.stderr.strip()}")
            return None

    def optimize_power_plan(self):
        """Cambia el plan de energía del sistema a 'Alto Rendimiento' de forma idempotente."""
        self.log("\n[+] Optimizando Plan de Energía...")
        output = self._run_command("powercfg /getactivescheme")
        if output is None:
            self.log("[-] No se pudo obtener el plan de energía actual.")
            return

        match = re.search(r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', output)
        if match:
            current_guid = match.group(1)
            high_perf_guid = "381b4222-f694-41f0-9685-ff5bb260df2e"
            if current_guid != high_perf_guid:
                self.state_manager.save_state('power_plan_guid', current_guid)
                self.log("[INFO] Plan de energía actual guardado.")
                self._run_command(f"powercfg /setactive {high_perf_guid}")
                self.log("[OK] Plan de energía establecido en 'Alto Rendimiento'.")
            else:
                self.log("[OK] El plan de 'Alto Rendimiento' ya estaba activo.")
        else:
            self.log("[-] No se pudo encontrar el GUID del plan actual en la salida.")

    def restore_power_plan(self):
        """Restaura el plan de energía original."""
        self.log("\n[+] Restaurando Plan de Energía...")
        original_guid = self.state_manager.get_state('power_plan_guid')
        if original_guid:
            self._run_command(f"powercfg /setactive {original_guid}")
            self.log("[OK] Plan de energía restaurado al original.")
        else:
            self.log("[-] No se encontró un plan de energía guardado para restaurar.")

    def manage_services(self, action='disable', profile=None):
        """Gestiona servicios basándose en el perfil proporcionado."""
        if not profile or not profile.get('enabled', False):
            self.log("\n[INFO] La gestión de servicios está desactivada en este perfil.")
            return

        services_to_manage = profile.get('list', [])
        if not services_to_manage:
            self.log("\n[INFO] No hay servicios definidos para gestionar en este perfil.")
            return

        log_header = "Desactivando" if action == 'disable' else "Restaurando"
        self.log(f"\n[+] {log_header} servicios según el perfil...")

        if action == 'disable':
            original_states = self.state_manager.get_state('original_service_states', {})
            for service_name in services_to_manage:
                try:
                    service = psutil.win_service_get(service_name)
                    start_type = service.start_type()
                    
                    if service_name not in original_states and start_type != 'disabled':
                        original_states[service_name] = start_type
                        self.log(f"[INFO] Guardando estado de '{service_name}': {start_type}")
                    
                    if service.status() == 'running':
                        self.log(f"[INFO] Deteniendo servicio en ejecución '{service_name}'...")
                        self._run_command(f'sc stop "{service_name}"')
                    
                    if start_type != 'disabled':
                        self._run_command(f'sc config "{service_name}" start= disabled')
                        self.log(f"[OK] Servicio '{service_name}' configurado como deshabilitado.")
                    else:
                        self.log(f"[OK] Servicio '{service_name}' ya estaba deshabilitado.")

                except psutil.NoSuchProcess:
                    self.log(f"[INFO] Servicio '{service_name}' no encontrado. Omitiendo.")
                except Exception as e:
                    self.log(f"[-] Error con el servicio '{service_name}': {e}")
            
            if original_states:
                self.state_manager.save_state('original_service_states', original_states)
        
        elif action == 'restore':
            original_states = self.state_manager.get_state('original_service_states')
            if original_states:
                for service, start_type in original_states.items():
                    self._run_command(f'sc config "{service}" start= {start_type}', ignore_errors=["1060"])
                    self.log(f"[OK] Servicio '{service}' restaurado a '{start_type}'.")
            else:
                self.log("[-] No hay estados de servicios guardados para restaurar.")

    def manage_gaming_features(self, action='disable', profile=None):
        """Gestiona características de juego de Windows basándose en el perfil."""
        if not profile or not profile.get('enabled', False):
            self.log("\n[INFO] La gestión de características de juego está desactivada en este perfil.")
            return

        log_header = "Desactivando" if action == 'disable' else "Restaurando"
        self.log(f"\n[+] {log_header} características de juego de Windows...")
        
        for key_id, props in self.gaming_features_keys.items():
            path, value_name = props["path"], props["value_name"]
            state_key = f"reg_{key_id}"

            if action == 'disable':
                original_value, original_type = self.reg_manager.get_value(path, value_name)
                
                if self.state_manager.get_state(state_key) is None:
                    if original_value is not None:
                        self.state_manager.save_state(state_key, {"value": original_value, "type": original_type})
                        self.log(f"[INFO] Guardando valor de registro de '{value_name}'.")
                    else:
                        self.state_manager.save_state(state_key, "__DELETE__")
                
                self.reg_manager.set_value(path, value_name, props["disable_value"])
                self.log(f"[OK] Característica '{value_name}' desactivada.")
            
            elif action == 'restore':
                saved_state = self.state_manager.get_state(state_key)
                if saved_state is not None:
                    if saved_state == "__DELETE__":
                        self.reg_manager.delete_value(path, value_name)
                        self.log(f"[OK] Valor de registro '{value_name}' eliminado (estado original).")
                    else:
                        self.reg_manager.set_value(path, value_name, saved_state["value"], saved_state["type"])
                        self.log(f"[OK] Característica '{value_name}' restaurada a su valor original.")
                else:
                    self.log(f"[-] No se encontró backup para '{value_name}'.")

    def clean_temp_files(self, profile=None):
        """Limpia archivos temporales si está habilitado en el perfil."""
        if not profile or not profile.get('enabled', False):
            self.log("\n[INFO] La limpieza de archivos temporales está desactivada en este perfil.")
            return

        self.log("\n[+] Limpiando archivos temporales...")
        temp_folders = [os.environ.get('TEMP'), os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Temp')]
        total_deleted_files, total_deleted_size = 0, 0

        for folder in temp_folders:
            if not folder or not os.path.exists(folder): continue
            self.log(f"[INFO] Limpiando directorio: {folder}")
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                try:
                    size = os.path.getsize(file_path)
                    if os.path.isfile(file_path) or os.path.islink(file_path): os.unlink(file_path)
                    elif os.path.isdir(file_path): shutil.rmtree(file_path)
                    total_deleted_files += 1
                    total_deleted_size += size
                except (PermissionError, OSError): self.log(f"[INFO] Omitido (en uso): {os.path.basename(file_path)}")
                except Exception as e: self.log(f"[-] Error inesperado al eliminar {os.path.basename(file_path)}: {e}")
        
        size_mb = total_deleted_size / (1024 * 1024)
        self.log(f"[OK] Limpieza completada. Se eliminaron {total_deleted_files} elementos ({size_mb:.2f} MB liberados).")

    def free_up_ram(self):
        """
        Intenta liberar memoria RAM vaciando el working set de procesos no críticos.
        Esta función es segura y solo apunta a procesos del usuario actual.
        """
        self.log("\n[+] Intentando liberar memoria RAM...")
        
        try:
            current_user = psutil.Process().username()
            system_critical_processes = [
                'csrss.exe', 'wininit.exe', 'services.exe', 'lsass.exe',
                'winlogon.exe', 'svchost.exe', 'smss.exe', 'system', 'registry'
            ]

            mem_before = psutil.virtual_memory().used
            freed_count = 0

            for proc in psutil.process_iter(['pid', 'name', 'username']):
                try:
                    p_info = proc.as_dict(attrs=['pid', 'name', 'username'])
                    # Criterios de seguridad
                    if (p_info['username'] == current_user and
                            p_info['name'].lower() not in system_critical_processes and
                            p_info['pid'] != os.getpid()):
                        
                        PROCESS_ALL_ACCESS = 0x1F0FFF # Permiso completo para abrir el proceso
                        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, p_info['pid'])
                        if handle:
                            # Llamar a la API de Windows para vaciar el working set del proceso
                            ctypes.windll.psapi.EmptyWorkingSet(handle)
                            ctypes.windll.kernel32.CloseHandle(handle)
                            freed_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    # El proceso puede haber terminado o no tenemos permisos, lo ignoramos.
                    continue
            
            # Forzamos una actualización de la memoria para una lectura más precisa
            mem_after = psutil.virtual_memory().used
            freed_mb = (mem_before - mem_after) / (1024 * 1024)

            self.log(f"[OK] Operación completada. Se ha intentado optimizar {freed_count} procesos.")
            if freed_mb > 0:
                self.log(f"[INFO] Memoria liberada aproximadamente: {freed_mb:.2f} MB.")
            else:
                self.log("[INFO] El sistema ya se encontraba en un estado de memoria optimizado.")
                
        except Exception as e:
            self.log(f"[ERROR] Ocurrió un error inesperado al liberar RAM: {e}")