# core/gpu_optimizer.py

import wmi

class GpuOptimizer:
    def __init__(self, console_logger):
        """
        Inicializa el optimizador de GPU.

        Args:
            console_logger (function): Una función callback para imprimir mensajes en la GUI.
        """
        self.log = console_logger
        try:
            self.wmi_connection = wmi.WMI()
        except wmi.x_wmi as e:
            self.log(f"[ERROR] No se pudo inicializar WMI. La detección de GPU no funcionará: {e}")
            self.wmi_connection = None

    def detect_gpu(self):
        """
        Detecta la marca de la GPU principal (NVIDIA o AMD) usando WMI.
        Devuelve 'NVIDIA', 'AMD', o 'UNKNOWN'.
        """
        if not self.wmi_connection:
            self.log("[WARN] Conexión WMI no disponible. Saltando detección de GPU.")
            return "UNKNOWN"
            
        try:
            # Consultamos todos los controladores de video del sistema
            for video_controller in self.wmi_connection.Win32_VideoController():
                # El nombre del adaptador suele contener la marca
                adapter_name = video_controller.Name.upper()
                if "NVIDIA" in adapter_name:
                    self.log("[INFO] GPU NVIDIA detectada.")
                    return "NVIDIA"
                if "AMD" in adapter_name or "RADEON" in adapter_name:
                    self.log("[INFO] GPU AMD detectada.")
                    return "AMD"
                if "INTEL" in adapter_name:
                    # Podríamos añadir soporte para Intel en el futuro, por ahora lo ignoramos
                    continue
        except Exception as e:
            self.log(f"[ERROR] No se pudo detectar la GPU a través de WMI: {e}")
        
        self.log("[WARN] No se detectó una GPU NVIDIA o AMD principal.")
        return "UNKNOWN"

    def get_recommendations(self, gpu_brand):
        """
        Devuelve una tupla (título, texto_recomendacion) según la marca de la GPU.
        """
        if gpu_brand == "NVIDIA":
            title = "Recomendaciones para NVIDIA Control Panel"
            text = (
                "Para un rendimiento competitivo máximo, te recomendamos aplicar estos ajustes manualmente en el Panel de Control de NVIDIA:\n\n"
                "1. En 'Controlar la configuración 3D' -> 'Configuración de programa', selecciona tu juego.\n"
                "2. Ajusta lo siguiente:\n"
                "   - **Modo de baja latencia:** Ultra\n"
                "   - **Modo de control de energía:** Preferir rendimiento máximo\n"
                "   - **Sincronización vertical:** Desactivada\n"
                "   - **Filtrado de texturas - Calidad:** Alto rendimiento\n\n"
                "Puedes abrir el panel haciendo clic derecho en el escritorio."
            )
            return title, text
        
        if gpu_brand == "AMD":
            title = "Recomendaciones para AMD Software: Adrenalin Edition"
            text = (
                "Para un rendimiento competitivo máximo, te recomendamos aplicar estos ajustes manualmente en AMD Software:\n\n"
                "1. En la pestaña 'Juegos' -> 'Gráficos', selecciona un perfil (ej. 'eSports').\n"
                "2. Ajusta lo siguiente:\n"
                "   - **Radeon Anti-Lag:** Activado\n"
                "   - **Radeon Boost:** Activado\n"
                "   - **Espera la sincronización vertical:** Desactivada, a menos que se especifique lo contrario\n"
                "   - **Calidad de filtrado de texturas:** Rendimiento\n\n"
                "Puedes abrir el software desde el menú Inicio o la bandeja del sistema."
            )
            return title, text
            
        return None, None