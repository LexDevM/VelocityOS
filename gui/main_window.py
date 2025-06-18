# gui/main_window.py

import json
import os
import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QTextEdit, QLabel, QTabWidget, QProgressBar, QGroupBox, 
    QScrollArea, QFrame, QCheckBox, QComboBox, QFormLayout
)
from PyQt6.QtGui import QIcon, QFont, QPixmap
from PyQt6.QtCore import Qt, QSize, QTimer

from core.state_manager import StateManager
from core.system_optimizer import SystemOptimizer
from core.registry_manager import RegistryManager
from core.network_optimizer import NetworkOptimizer
from core.gpu_optimizer import GpuOptimizer
from utils import os_detector, startup_manager
from utils.resource_path import resource_path
from core.monitor import SystemMonitor
from core.speed_test_worker import SpeedTestWorker

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VelocityOS")
        self.setWindowIcon(QIcon(resource_path("assets/icons/velocityos.ico")))
        self.setMinimumSize(800, 720)

        # --- Backend Logic Initialization ---
        app_path = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(sys.argv[0])
        self.startup_manager = startup_manager.StartupManager("VelocityOS", app_path)
        self.state_manager = StateManager()
        
        # El widget de la consola DEBE crearse antes de que cualquier módulo de backend lo use
        self.console_output = QTextEdit() 

        self.reg_manager = RegistryManager(self.log_to_console)
        self.system_optimizer = SystemOptimizer(self.state_manager, self.log_to_console)
        self.network_optimizer = NetworkOptimizer(self.state_manager, self.reg_manager, self.log_to_console)
        self.gpu_optimizer = GpuOptimizer(self.log_to_console)

        # --- GUI State Variables ---
        self.profiles = self._load_profiles()
        self.selected_profile_name = None
        self.selected_profile_id_for_settings = None
        self.gpu_brand_detected = "UNKNOWN"

        # --- Main Layout: Tabs ---
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.optimization_tab = QWidget()
        self.monitor_tab = QWidget()
        self.settings_tab = QWidget()
        self.tabs.addTab(self.optimization_tab, QIcon(resource_path("assets/icons/sliders.png")), "Optimización")
        self.tabs.addTab(self.monitor_tab, QIcon(resource_path("assets/icons/monitor.png")), "Monitor")
        self.tabs.addTab(self.settings_tab, QIcon(resource_path("assets/icons/settings.png")), "Ajustes")
        self.tabs.setIconSize(QSize(24, 24))

        # --- Setup Tabs ---
        self.setup_optimization_tab()
        self.setup_monitor_tab()
        self.setup_settings_tab()
        
        # --- Start Monitoring Thread ---
        self.monitor_thread = SystemMonitor(self)
        self.monitor_thread.system_data_updated.connect(self.update_monitor_data)
        self.monitor_thread.start()
        
        # --- Initial State ---
        self.update_button_states()
        self.log_to_console("Bienvenido a VelocityOS.")
        if not self.profiles:
            self.log_to_console("[ADVERTENCIA] No se cargó ningún perfil. La funcionalidad de optimización estará desactivada.")
        else:
            self.log_to_console("Selecciona un perfil para comenzar.")

    def setup_optimization_tab(self):
        main_layout = QVBoxLayout(self.optimization_tab)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_content_widget = QWidget()
        content_layout = QVBoxLayout(scroll_content_widget)
        content_layout.setContentsMargins(0, 10, 0, 10)
        content_layout.setSpacing(15)
        
        profile_group = QGroupBox("1. Selecciona tu Perfil de Optimización")
        profile_layout = QVBoxLayout()
        self.profile_buttons_layout = QHBoxLayout()
        self.profile_buttons = {}
        profile_icons = {"competitive": resource_path("assets/icons/rocket.png"), "balanced": resource_path("assets/icons/shield.png")}
        for profile_id, profile_data in self.profiles.items():
            icon_path = profile_icons.get(profile_id, resource_path("assets/icons/zap.png"))
            button = QPushButton(QIcon(icon_path), f"  {profile_data['name']}")
            button.setIconSize(QSize(20, 20))
            button.setCheckable(True)
            button.clicked.connect(lambda checked, p_id=profile_id: self.select_profile(p_id))
            self.profile_buttons_layout.addWidget(button)
            self.profile_buttons[profile_id] = button
        self.profile_description_label = QLabel("Selecciona un perfil para ver su descripción.")
        self.profile_description_label.setObjectName("DescriptionLabel")
        self.profile_description_label.setWordWrap(True)
        self.profile_description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.profile_description_label.setMinimumHeight(60)
        profile_layout.addLayout(self.profile_buttons_layout)
        profile_layout.addWidget(self.profile_description_label)
        profile_group.setLayout(profile_layout)
        
        actions_group = QGroupBox("2. Aplica la Optimización o Reviértela")
        actions_layout = QHBoxLayout()
        self.optimize_button = QPushButton(QIcon(resource_path("assets/icons/zap.png")), " Optimizar Ahora")
        self.optimize_button.setObjectName("OptimizeButton")
        self.optimize_button.setIconSize(QSize(20, 20))
        self.restore_button = QPushButton(QIcon(resource_path("assets/icons/rotate-ccw.png")), " Revertir Cambios")
        self.restore_button.setIconSize(QSize(20, 20))
        actions_layout.addWidget(self.optimize_button)
        actions_layout.addWidget(self.restore_button)
        actions_group.setLayout(actions_layout)
        self.optimize_button.clicked.connect(self.run_optimization)
        self.restore_button.clicked.connect(self.run_restore)
        
        console_group = QGroupBox("Registro de Actividad")
        console_layout = QVBoxLayout()
        console_layout.addWidget(self.console_output)
        console_group.setLayout(console_layout)
        
        self.gpu_recommendations_group = QGroupBox("Recomendaciones Adicionales para GPU")
        gpu_layout = QVBoxLayout()
        self.gpu_recommendations_label = QLabel("Aquí aparecerán recomendaciones...")
        self.gpu_recommendations_label.setWordWrap(True)
        gpu_layout.addWidget(self.gpu_recommendations_label)
        self.gpu_recommendations_group.setLayout(gpu_layout)
        self.gpu_recommendations_group.setVisible(False)
        
        content_layout.addWidget(profile_group)
        content_layout.addWidget(actions_group)
        content_layout.addWidget(console_group)
        content_layout.addWidget(self.gpu_recommendations_group)
        content_layout.addStretch()
        
        scroll_area.setWidget(scroll_content_widget)
        main_layout.addWidget(scroll_area)

    def setup_monitor_tab(self):
        layout = QVBoxLayout(self.monitor_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        speed_test_group = QGroupBox("Test de Velocidad de Red (por Ookla®)")
        st_main_layout = QVBoxLayout()
        st_numbers_layout = QHBoxLayout()
        download_panel = QVBoxLayout()
        download_title = QLabel("⬇️ DESCARGA Mbps")
        download_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.st_download_realtime_label = QLabel("0.00")
        self.st_download_realtime_label.setFont(QFont("Segoe UI", 36, QFont.Weight.Bold))
        self.st_download_realtime_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        download_panel.addWidget(download_title)
        download_panel.addWidget(self.st_download_realtime_label)
        upload_panel = QVBoxLayout()
        upload_title = QLabel("⬆️ SUBIDA Mbps")
        upload_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.st_upload_realtime_label = QLabel("0.00")
        self.st_upload_realtime_label.setFont(QFont("Segoe UI", 36, QFont.Weight.Bold))
        self.st_upload_realtime_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        upload_panel.addWidget(upload_title)
        upload_panel.addWidget(self.st_upload_realtime_label)
        st_numbers_layout.addLayout(download_panel)
        st_numbers_layout.addLayout(upload_panel)
        st_controls_layout = QHBoxLayout()
        self.speed_test_button = QPushButton(QIcon(resource_path("assets/icons/zap.png")), " Iniciar Test")
        self.speed_test_button.setIconSize(QSize(20, 20))
        self.speed_test_button.clicked.connect(self.start_speed_test)
        self.speed_test_status_label = QLabel("Haz clic para iniciar el test de diagnóstico.")
        self.speed_test_status_label.setObjectName("DescriptionLabel")
        st_controls_layout.addWidget(self.speed_test_button)
        st_controls_layout.addWidget(self.speed_test_status_label, 1)
        self.st_final_results_label = QLabel("Ping: -- | ISP: -- | Servidor: --")
        self.st_final_results_label.setObjectName("DescriptionLabel")
        st_main_layout.addLayout(st_numbers_layout)
        st_main_layout.addLayout(st_controls_layout)
        st_main_layout.addWidget(self.st_final_results_label)
        speed_test_group.setLayout(st_main_layout)

        monitoring_group = QGroupBox("Monitoreo y Acciones Rápidas")
        monitoring_layout = QVBoxLayout()
        self.cpu_progress = QProgressBar()
        self.ram_progress = QProgressBar()
        self.gpu_progress = QProgressBar()
        monitoring_layout.addWidget(QLabel("Uso de CPU:"))
        monitoring_layout.addWidget(self.cpu_progress)
        monitoring_layout.addSpacing(10)
        monitoring_layout.addWidget(QLabel("Uso de RAM:"))
        monitoring_layout.addWidget(self.ram_progress)
        monitoring_layout.addSpacing(10)
        monitoring_layout.addWidget(QLabel("Uso de GPU (NVIDIA):"))
        monitoring_layout.addWidget(self.gpu_progress)
        monitoring_layout.addSpacing(15)
        self.free_ram_button = QPushButton(QIcon(resource_path("assets/icons/zap.png")), " Liberar Memoria RAM")
        self.free_ram_button.setIconSize(QSize(20, 20))
        self.free_ram_button.clicked.connect(self.run_free_ram)
        monitoring_layout.addWidget(self.free_ram_button)
        monitoring_group.setLayout(monitoring_layout)
        
        layout.addWidget(speed_test_group)
        layout.addWidget(monitoring_group)
        layout.addStretch()

    def setup_settings_tab(self):
        layout = QVBoxLayout(self.settings_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        app_settings_group = QGroupBox("Ajustes Generales de la Aplicación")
        app_settings_layout = QFormLayout()
        self.startup_checkbox = QCheckBox("Iniciar VelocityOS con Windows")
        self.startup_checkbox.setChecked(self.startup_manager.is_enabled())
        self.startup_checkbox.toggled.connect(self.toggle_startup)
        app_settings_layout.addRow(self.startup_checkbox)
        app_settings_group.setLayout(app_settings_layout)
        profile_settings_group = QGroupBox("Personalización de Perfiles")
        profile_settings_layout = QVBoxLayout()
        self.profile_selector = QComboBox()
        if self.profiles:
            self.profile_selector.addItems([p['name'] for p in self.profiles.values()])
        self.profile_selector.currentIndexChanged.connect(self.populate_profile_settings)
        self.profile_options_layout = QFormLayout()
        self.profile_options_widgets = {}
        profile_settings_layout.addWidget(QLabel("Selecciona un perfil para editar:"))
        profile_settings_layout.addWidget(self.profile_selector)
        profile_settings_layout.addSpacing(10)
        profile_settings_layout.addLayout(self.profile_options_layout)
        save_layout = QHBoxLayout()
        self.save_feedback_label = QLabel("")
        self.save_feedback_label.setStyleSheet("color: #a6e3a1; font-weight: bold;")
        save_button = QPushButton(QIcon(resource_path("assets/icons/save.png")), " Guardar Cambios del Perfil")
        save_button.setIconSize(QSize(20, 20))
        save_button.clicked.connect(self.save_profile_settings)
        save_layout.addStretch()
        save_layout.addWidget(self.save_feedback_label)
        save_layout.addSpacing(10)
        save_layout.addWidget(save_button)
        profile_settings_layout.addLayout(save_layout)
        profile_settings_group.setLayout(profile_settings_layout)
        layout.addWidget(app_settings_group)
        layout.addWidget(profile_settings_group)
        layout.addStretch()
        if self.profiles:
            self.populate_profile_settings(0)

    def _load_profiles(self):
        profiles = {}
        try:
            config_dir = resource_path("config")
            if not os.path.exists(config_dir):
                self.log_to_console(f"[ERROR-FATAL] ¡El directorio de perfiles no existe! Ruta buscada: {config_dir}")
                return profiles
            for filename in os.listdir(config_dir):
                if filename.endswith(".json"):
                    file_path = os.path.join(config_dir, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            profile = json.load(f)
                            profiles[profile['id']] = profile
                    except json.JSONDecodeError as e:
                        self.log_to_console(f"[ERROR-FATAL] El archivo de perfil '{filename}' tiene un error de sintaxis: {e}")
                    except KeyError:
                        self.log_to_console(f"[ERROR-FATAL] El archivo de perfil '{filename}' no tiene una clave 'id'.")
        except Exception as e:
            self.log_to_console(f"[CRITICAL-ERROR] No se pudo procesar la carpeta de perfiles: {e}")
        return profiles

    def run_free_ram(self):
        self.free_ram_button.setEnabled(False)
        self.free_ram_button.setText("Liberando...")
        self.tabs.setCurrentWidget(self.optimization_tab)
        QApplication.processEvents()
        self.system_optimizer.free_up_ram()
        self.free_ram_button.setText(" Liberar Memoria RAM")
        self.free_ram_button.setEnabled(True)

    def toggle_startup(self, checked):
        if self.startup_manager.set_startup(checked): self.log_to_console(f"[INFO] Inicio con Windows {'activado' if checked else 'desactivado'}.")
        else:
            self.log_to_console("[ERROR] No se pudo modificar el registro para el inicio con Windows.")
            self.startup_checkbox.blockSignals(True)
            self.startup_checkbox.setChecked(not checked)
            self.startup_checkbox.blockSignals(False)

    def populate_profile_settings(self, index):
        while self.profile_options_layout.rowCount() > 0: self.profile_options_layout.removeRow(0)
        self.profile_options_widgets.clear()
        if not self.profiles: return
        selected_name = self.profile_selector.itemText(index)
        profile_id = next((pid for pid, pdata in self.profiles.items() if pdata['name'] == selected_name), None)
        if not profile_id: return
        self.selected_profile_id_for_settings = profile_id
        profile_opts = self.profiles[profile_id]['optimizations']
        option_map = {"power_plan": "Cambiar Plan de Energía a Alto Rendimiento", "services": "Desactivar Servicios Innecesarios", "gaming_features": "Desactivar Funciones de Juego de Windows (Game Bar)", "nagle_algorithm": "Aplicar Tweaks de Red (Baja Latencia)", "temp_files": "Limpiar Archivos Temporales"}
        for key, text in option_map.items():
            if key in profile_opts:
                checkbox = QCheckBox(text)
                is_enabled = profile_opts[key]
                if isinstance(is_enabled, dict): is_enabled = is_enabled.get('enabled', False)
                checkbox.setChecked(is_enabled)
                self.profile_options_layout.addRow(checkbox)
                self.profile_options_widgets[key] = checkbox

    def save_profile_settings(self):
        if not self.selected_profile_id_for_settings: return
        profile_id = self.selected_profile_id_for_settings
        profile_data = self.profiles[profile_id]
        for key, checkbox in self.profile_options_widgets.items():
            if key in profile_data['optimizations']:
                if isinstance(profile_data['optimizations'][key], dict): profile_data['optimizations'][key]['enabled'] = checkbox.isChecked()
                else: profile_data['optimizations'][key] = checkbox.isChecked()
        try:
            config_dir = resource_path("config")
            file_path = os.path.join(config_dir, f"{profile_id}.json")
            with open(file_path, 'w', encoding='utf-8') as f: json.dump(profile_data, f, indent=4, ensure_ascii=False)
            self.log_to_console(f"[INFO] Ajustes del perfil '{profile_data['name']}' guardados.")
            self.save_feedback_label.setText("¡Guardado!")
            self.save_feedback_label.setStyleSheet("color: #a6e3a1; font-weight: bold;")
            QTimer.singleShot(2500, lambda: self.save_feedback_label.setText(""))
        except Exception as e:
            self.log_to_console(f"[ERROR] No se pudo guardar el archivo del perfil: {e}")
            self.save_feedback_label.setText("¡Error!")
            self.save_feedback_label.setStyleSheet("color: #f38ba8; font-weight: bold;")
            QTimer.singleShot(2500, lambda: self.save_feedback_label.setText(""))

    def start_speed_test(self):
        self.speed_test_button.setEnabled(False)
        self.st_download_realtime_label.setText("0.00")
        self.st_upload_realtime_label.setText("0.00")
        self.st_final_results_label.setText("Ping: -- | ISP: -- | Servidor: --")
        self.speed_test_status_label.setStyleSheet("color: #cdd6f4;")
        self.speed_test_worker = SpeedTestWorker(self)
        self.speed_test_worker.status_updated.connect(self.update_speed_test_progress)
        self.speed_test_worker.realtime_progress.connect(self.update_realtime_speed)
        self.speed_test_worker.test_finished.connect(self.display_speed_test_results)
        self.speed_test_worker.test_error.connect(self.handle_speed_test_error)
        self.speed_test_worker.start()

    def update_speed_test_progress(self, message): self.speed_test_status_label.setText(message)
    def update_realtime_speed(self, test_type, speed_mbps):
        if test_type == "download": self.st_download_realtime_label.setText(f"{speed_mbps:.2f}")
        elif test_type == "upload": self.st_upload_realtime_label.setText(f"{speed_mbps:.2f}")

    def display_speed_test_results(self, results):
        self.speed_test_button.setEnabled(True)
        self.speed_test_status_label.setText("¡Test completado! Resultados finales mostrados.")
        download_info, upload_info, ping_info, server_info, isp_info = results.get('download', {}), results.get('upload', {}), results.get('ping', {}), results.get('server', {}), results.get('client_isp', 'N/A')
        final_download, final_upload, ping, jitter = (download_info.get('bandwidth', 0) * 8) / 1_000_000, (upload_info.get('bandwidth', 0) * 8) / 1_000_000, ping_info.get('latency', 0), ping_info.get('jitter', 0)
        self.st_download_realtime_label.setText(f"{final_download:.2f}")
        self.st_upload_realtime_label.setText(f"{final_upload:.2f}")
        self.st_final_results_label.setText(f"Ping: {ping:.2f} ms | Jitter: {jitter:.2f} ms | ISP: {isp_info} | Servidor: {server_info.get('name', 'N/A')}")

    def handle_speed_test_error(self, error_message):
        self.speed_test_button.setEnabled(True)
        self.speed_test_status_label.setText(f"Error: {error_message}")
        self.speed_test_status_label.setStyleSheet("color: #f38ba8;")
        
    def update_monitor_data(self, data):
        self.cpu_progress.setValue(int(data['cpu_usage']))
        self.ram_progress.setValue(int(data['ram_usage']))
        self.gpu_progress.setValue(int(data['gpu_usage']))
        self.gpu_progress.setFormat(f"{int(data['gpu_usage'])}% ({data['gpu_temp']}°C)")

    def log_to_console(self, message):
        if hasattr(self, 'console_output') and self.console_output:
            self.console_output.append(message)
            QApplication.processEvents()
            
    def show_gpu_recommendations(self):
        self.gpu_brand_detected = self.gpu_optimizer.detect_gpu()
        title, text = self.gpu_optimizer.get_recommendations(self.gpu_brand_detected)
        if title and text:
            self.gpu_recommendations_group.setTitle(title)
            self.gpu_recommendations_label.setText(text)
            self.gpu_recommendations_group.setVisible(True)
            self.log_to_console(f"\n[INFO] Se han generado recomendaciones para tu GPU {self.gpu_brand_detected}.")

    def closeEvent(self, event):
        self.monitor_thread.stop()
        if hasattr(self, 'speed_test_worker') and self.speed_test_worker.isRunning():
            self.speed_test_worker.stop()
        event.accept()

    def select_profile(self, profile_id):
        profile_data = self.profiles[profile_id]
        self.selected_profile_name = profile_data['name']
        self.profile_description_label.setText(profile_data['description'])
        for pid, button in self.profile_buttons.items():
            if pid != profile_id: button.setChecked(False)
        self.update_button_states()

    def update_button_states(self):
        has_backup = self.state_manager.backup_exists()
        self.restore_button.setEnabled(has_backup)
        self.optimize_button.setEnabled(not has_backup and self.selected_profile_name is not None)
        for button in self.profile_buttons.values(): button.setEnabled(not has_backup)

    def run_optimization(self):
        if not self.selected_profile_name:
            self.log_to_console("[ERROR] No se ha seleccionado ningún perfil.")
            return
        profile_id = next((pid for pid, pdata in self.profiles.items() if pdata['name'] == self.selected_profile_name), None)
        if not profile_id: return
        opts = self.profiles[profile_id]['optimizations']
        self.console_output.clear()
        self.log_to_console(f"=== INICIANDO OPTIMIZACIÓN CON PERFIL: {self.selected_profile_name} ===")
        if opts.get('power_plan', False): self.system_optimizer.optimize_power_plan()
        self.system_optimizer.manage_services('disable', opts.get('services'))
        self.system_optimizer.manage_gaming_features('disable', opts.get('gaming_features'))
        self.network_optimizer.manage_nagle_algorithm('disable', opts.get('nagle_algorithm'))
        self.system_optimizer.clean_temp_files(opts.get('temp_files'))
        self.log_to_console("\n=== OPTIMIZACIÓN COMPLETADA ===")
        self.log_to_console("Se recomienda reiniciar el equipo para que todos los cambios surtan efecto.")
        self.update_button_states()
        self.show_gpu_recommendations()

    def run_restore(self):
        self.console_output.clear()
        self.log_to_console("=== INICIANDO RESTAURACIÓN ===")
        self.system_optimizer.restore_power_plan()
        self.system_optimizer.manage_services(action='restore')
        self.system_optimizer.manage_gaming_features(action='restore')
        self.network_optimizer.manage_nagle_algorithm(action='restore')
        self.log_to_console("\n[INFO] La limpieza de archivos temporales es una acción permanente.")
        self.state_manager.clear_backup()
        self.log_to_console("\n=== RESTAURACIÓN COMPLETADA ===")
        self.gpu_recommendations_group.setVisible(False)
        self.selected_profile_name = None
        for button in self.profile_buttons.values(): button.setChecked(False)
        self.profile_description_label.setText("Selecciona un perfil para ver su descripción.")
        self.update_button_states()