# core/monitor.py

import time
import logging
import psutil

# --- Importaciones seguras para librerías de GPU ---
try:
    import pynvml
    PYNVML_AVAILABLE = True
except ImportError:
    PYNVML_AVAILABLE = False

try:
    from pyadl import ADLManager
    PYADL_AVAILABLE = True
except ImportError:
    PYADL_AVAILABLE = False

from PyQt6.QtCore import QThread, pyqtSignal

class SystemMonitor(QThread):
    """
    Un hilo de monitoreo agnóstico a la marca de la GPU.
    Detecta si hay una GPU NVIDIA o AMD y utiliza la librería correspondiente.
    """
    system_data_updated = pyqtSignal(dict)
    gpu_detected = pyqtSignal(str) # Señal para informar a la GUI qué GPU se encontró

    UPDATE_INTERVAL = 1  # segundos

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(self.__class__.__name__)
        self._is_running = True
        
        self.gpu_brand = "NONE"
        self.gpu_device = None # Almacenará el 'handle' de pynvml o el 'device' de pyadl
        
        # La inicialización de la GPU ahora se hace en el constructor
        # para que la señal 'gpu_detected' se emita al principio.
        self._initialize_gpu()

    def _initialize_gpu(self):
        """
        Intenta inicializar primero NVIDIA, y si falla, intenta con AMD.
        Emite una señal con la marca de la GPU detectada.
        """
        # 1. Intentar con NVIDIA
        if PYNVML_AVAILABLE:
            try:
                pynvml.nvmlInit()
                self.gpu_device = pynvml.nvmlDeviceGetHandleByIndex(0)
                self.gpu_brand = "NVIDIA"
                self.logger.info("NVML inicializado. GPU NVIDIA detectada.")
                self.gpu_detected.emit("NVIDIA")
                return
            except pynvml.NVMLError:
                self.logger.warning("No se detectó una GPU NVIDIA. Buscando AMD...")
        
        # 2. Si NVIDIA falla, intentar con AMD
        if PYADL_AVAILABLE:
            try:
                adl_devices = ADLManager.getInstance().getDevices()
                if adl_devices:
                    self.gpu_device = adl_devices[0] # Usamos la primera GPU AMD encontrada
                    self.gpu_brand = "AMD"
                    self.logger.info("ADL inicializado. GPU AMD detectada.")
                    self.gpu_detected.emit("AMD")
                    return
            except Exception as e:
                # La librería PyADL puede lanzar excepciones genéricas si los drivers no responden.
                self.logger.error(f"Error al inicializar PyADL para AMD: {e}")

        # 3. Si ambos fallan
        self.logger.warning("No se detectó una GPU NVIDIA o AMD compatible para el monitoreo.")
        self.gpu_detected.emit("NONE")

    def _get_gpu_stats(self):
        """Devuelve una tupla (uso, temperatura) de la GPU según la marca detectada."""
        usage, temp = 0, 0
        if not self.gpu_device:
            return usage, temp
            
        try:
            if self.gpu_brand == "NVIDIA":
                utilization = pynvml.nvmlDeviceGetUtilizationRates(self.gpu_device)
                usage = utilization.gpu
                temp = pynvml.nvmlDeviceGetTemperature(self.gpu_device, pynvml.NVML_TEMPERATURE_GPU)
            
            elif self.gpu_brand == "AMD":
                usage = self.gpu_device.getCurrentUsage()
                temp = self.gpu_device.getCurrentTemperature()

        except Exception as e:
            self.logger.warning(f"Error temporal al leer datos de la GPU {self.gpu_brand}: {e}")
            # Si falla la lectura, reseteamos el dispositivo para un posible reintento futuro
            self.gpu_device = None
            self.gpu_brand = "NONE"
            self.gpu_detected.emit("NONE") # Informar a la GUI del fallo
        
        return usage, temp

    def run(self):
        """
        El bucle principal del hilo. Recopila datos y los emite a intervalos regulares.
        """
        self.logger.info("Hilo de monitoreo iniciado.")
        while self._is_running:
            gpu_usage, gpu_temp = self._get_gpu_stats()
            
            data = {
                'cpu_usage': psutil.cpu_percent(),
                'ram_usage': psutil.virtual_memory().percent,
                'gpu_usage': gpu_usage,
                'gpu_temp': gpu_temp,
            }
            
            self.system_data_updated.emit(data)
            time.sleep(self.UPDATE_INTERVAL)
        
        self.logger.info("Bucle de monitoreo finalizado.")

    def stop(self):
        """
        Detiene el bucle del hilo de forma segura y limpia los recursos.
        """
        self.logger.info("Deteniendo el hilo de monitoreo...")
        self._is_running = False
        
        # Limpieza de recursos de la librería de NVIDIA
        if self.gpu_brand == "NVIDIA" and PYNVML_AVAILABLE:
            try:
                pynvml.nvmlShutdown()
                self.logger.info("NVML cerrado correctamente.")
            except pynvml.NVMLError as e:
                self.logger.error(f"Error al cerrar NVML: {e}")