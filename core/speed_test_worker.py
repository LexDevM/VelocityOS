# core/speed_test_worker.py
import logging
import subprocess
import json
import os
import sys
from PyQt6.QtCore import QThread, pyqtSignal
from utils.resource_path import resource_path

class SpeedTestWorker(QThread):
    """
    Worker de nivel profesional que utiliza el CLI oficial de Ookla Speedtest
    para garantizar la máxima precisión y una selección de servidor fiable.
    """
    status_updated = pyqtSignal(str)
    realtime_progress = pyqtSignal(str, float)
    test_finished = pyqtSignal(dict)
    test_error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(self.__class__.__name__)
        self._is_running = True
        self.process = None

    def run(self):
        try:
            self.logger.info("Iniciando test de velocidad con el CLI oficial de Ookla...")
            
            # Construir la ruta al ejecutable de speedtest de forma robusta
            speedtest_path = resource_path(os.path.join("bin", "speedtest.exe"))
            
            self.logger.info(f"Buscando speedtest.exe en: {speedtest_path}")

            if not os.path.exists(speedtest_path):
                error_msg = f"No se encontró 'speedtest.exe'.\nAsegúrate de que el archivo está en la carpeta 'bin' del proyecto.\nRuta buscada: {speedtest_path}"
                raise FileNotFoundError(error_msg)

            # Comando para ejecutar el test con salida JSON línea por línea
            command = [speedtest_path, "--accept-license", "--accept-gdpr", "-f", "jsonl"]
            
            self.process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            # Leer la salida del proceso línea por línea
            for line in iter(self.process.stdout.readline, ''):
                if not self._is_running:
                    self.process.kill()
                    break
                if not line:
                    break
                
                try:
                    data = json.loads(line)
                    self.parse_cli_output(data)
                except json.JSONDecodeError:
                    self.logger.warning(f"No se pudo decodificar la línea JSON: {line.strip()}")

            # Esperar a que el proceso termine y comprobar si hubo errores
            self.process.wait()
            if self.process.returncode != 0 and self._is_running:
                stderr_output = self.process.stderr.read()
                raise Exception(f"El proceso de speedtest falló con código {self.process.returncode}: {stderr_output}")

        except FileNotFoundError as e:
            self.logger.error(str(e))
            self.test_error.emit(str(e))
        except Exception as e:
            error_msg = f"Error crítico durante el test: {e}"
            self.logger.error(error_msg, exc_info=True)
            self.test_error.emit(error_msg)

    def parse_cli_output(self, data):
        """Decodifica el JSON de cada línea y emite las señales correspondientes."""
        event_type = data.get('type')

        if event_type == 'testStart':
            isp = data.get('isp', 'N/A')
            server = data.get('server', {})
            server_name = server.get('name', 'N/A')
            self.status_updated.emit(f"ISP: {isp} | Conectando a: {server_name}")

        elif event_type == 'ping':
            ping = data.get('ping', {})
            self.status_updated.emit(f"Probando latencia... (Jitter: {ping.get('jitter', 0):.2f} ms)")

        elif event_type == 'download' or event_type == 'upload':
            test_name = event_type
            progress = data.get(test_name, {})
            # La velocidad viene en Bytes por segundo, la convertimos a Mbps
            speed_mbps = (progress.get('bandwidth', 0) * 8) / 1_000_000
            self.realtime_progress.emit(test_name, speed_mbps)
            if progress.get('progress') == 0: # Al inicio de la fase
                 self.status_updated.emit(f"Midiendo velocidad de {test_name}...")

        elif event_type == 'result':
            self.status_updated.emit("¡Test completado!")
            self.test_finished.emit(data)

    def stop(self):
        self.logger.info("Solicitando la detención del SpeedTestWorker...")
        self._is_running = False
        if self.process and self.process.poll() is None: # Si el proceso sigue vivo
            try:
                self.process.kill()
            except Exception as e:
                self.logger.error(f"Error al intentar detener el proceso de speedtest: {e}")