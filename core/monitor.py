# core/monitor.py

import time
import logging
import psutil
import subprocess
import re

try:
    import pynvml
    PYNVML_AVAILABLE = True
except ImportError:
    PYNVML_AVAILABLE = False
    # No usamos print aquí; dejaremos que el logger lo maneje si se configura
    # print("[Monitor] La librería 'pynvml' no está instalada. El monitoreo de GPU NVIDIA estará desactivado.")

from PyQt6.QtCore import QThread, pyqtSignal

class SystemMonitor(QThread):
    """
    Un hilo de monitoreo robusto y profesional que recopila datos del sistema
    (CPU, RAM, GPU y Red) y los emite a través de una señal de Qt.
    """
    # La señal que emitirá un diccionario con los datos del sistema.
    system_data_updated = pyqtSignal(dict)

    # Constantes para la configuración del monitor
    UPDATE_INTERVAL = 1  # segundos
    PING_TARGET = "1.1.1.1" # Servidor de Cloudflare, una opción fiable y rápida para el ping

    def __init__(self, parent=None):
        """
        Inicializa el hilo de monitoreo.
        Args:
            parent (QObject, optional): El objeto padre en la jerarquía de Qt.
        """
        super().__init__(parent)
        self.logger = logging.getLogger(self.__class__.__name__)
        self._is_running = True
        self.gpu_handle = self._initialize_gpu()
        
        # Inicializar contadores de red para el primer cálculo de velocidad
        self.last_net_io = psutil.net_io_counters()

    def _initialize_gpu(self):
        """
        Inicializa la librería NVML de NVIDIA de forma segura.
        Devuelve el handle de la GPU si está disponible, de lo contrario None.
        """
        if not PYNVML_AVAILABLE:
            self.logger.warning("Librería 'pynvml' no encontrada. El monitoreo de GPU NVIDIA estará desactivado.")
            return None
        
        try:
            pynvml.nvmlInit()
            # Asumimos que la GPU principal es el dispositivo 0.
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            self.logger.info("NVML inicializado. GPU NVIDIA detectada y lista para monitoreo.")
            return handle
        except pynvml.NVMLError as e:
            self.logger.warning(f"No se pudo inicializar NVML o detectar una GPU NVIDIA: {e}")
            return None

    def _get_ping(self):
        """Ejecuta un comando ping y parsea la latencia. Devuelve -1 si falla."""
        try:
            # -n 1 (Windows) / -c 1 (Linux/macOS) envía solo un paquete.
            # -w 1000 (Windows) / -W 1 (Linux/macOS) establece un timeout de 1000ms.
            command = ["ping", "-n", "1", "-w", "1000", self.PING_TARGET]
            # La salida de ping puede estar en otro idioma, pero el formato "time=Xms" suele ser consistente.
            output = subprocess.check_output(command, stderr=subprocess.STDOUT, universal_newlines=True, creationflags=subprocess.CREATE_NO_WINDOW)
            
            match = re.search(r"tiempo[=<](\d+)", output) # Para español: "tiempo=Xms" o "tiempo<Xms"
            if not match:
                match = re.search(r"time[=<](\d+)", output) # Para inglés: "time=Xms" or "time<Xms"
            
            if match:
                return int(match.group(1))
        except (subprocess.CalledProcessError, FileNotFoundError):
            # El ping falló (sin conexión) o el comando no se encontró
            return -1
        return -1

    def run(self):
        """
        El bucle principal del hilo. Se ejecuta cuando se llama a .start().
        Recopila datos y los emite a intervalos regulares.
        """
        self.logger.info("Hilo de monitoreo iniciado.")
        while self._is_running:
            # --- Lectura de Red ---
            current_net_io = psutil.net_io_counters()
            elapsed_time = self.UPDATE_INTERVAL # Asumimos que el tiempo de ejecución del código es despreciable
            
            bytes_sent = current_net_io.bytes_sent - self.last_net_io.bytes_sent
            bytes_recv = current_net_io.bytes_recv - self.last_net_io.bytes_recv
            
            upload_speed = bytes_sent / elapsed_time
            download_speed = bytes_recv / elapsed_time
            
            self.last_net_io = current_net_io
            
            # --- Recopilación de todos los datos en un diccionario ---
            data = {
                'cpu_usage': psutil.cpu_percent(),
                'ram_usage': psutil.virtual_memory().percent,
                'gpu_usage': 0,
                'gpu_temp': 0,
                'ping': self._get_ping(),
                'upload_speed': upload_speed,
                'download_speed': download_speed
            }

            if self.gpu_handle:
                try:
                    utilization = pynvml.nvmlDeviceGetUtilizationRates(self.gpu_handle)
                    data['gpu_usage'] = utilization.gpu
                    data['gpu_temp'] = pynvml.nvmlDeviceGetTemperature(self.gpu_handle, pynvml.NVML_TEMPERATURE_GPU)
                except pynvml.NVMLError as e:
                    self.logger.warning(f"Error temporal al leer datos de la GPU: {e}")
            
            # Emitimos la señal con los datos recolectados para que la GUI los reciba.
            self.system_data_updated.emit(data)
            
            # Esperamos el intervalo definido antes de la siguiente lectura.
            time.sleep(self.UPDATE_INTERVAL)
        
        self.logger.info("Bucle de monitoreo finalizado.")

    def stop(self):
        """
        Detiene el bucle del hilo de forma segura y limpia los recursos.
        """
        self.logger.info("Deteniendo el hilo de monitoreo...")
        self._is_running = False
        if PYNVML_AVAILABLE and self.gpu_handle:
            try:
                pynvml.nvmlShutdown()
                self.logger.info("NVML cerrado correctamente.")
            except pynvml.NVMLError as e:
                self.logger.error(f"Error al cerrar NVML: {e}")