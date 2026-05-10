from __future__ import annotations

import os
import sys
from pathlib import Path

from .caveman import validate_level
from .doctor import build_report
from .statusbar import build_statusbar_line
from .workbench_config import load_config, remember_project, save_config, update_defaults
from .workbench_launcher import (
    codex_available,
    codex_plan,
    ensure_project_dir,
    folder_plan,
    inspect_project,
    launch_plan,
    launch_plans,
    manual_powershell_plan,
    statusbar_plan,
    workbench_three_panel_plans,
)


PYSIDE_INSTALL_MESSAGE = (
    "PySide6 no está instalado. Instalar con:\n"
    "python -m pip install -e .[gui]\n"
    "o, si usa pipx:\n"
    "pipx inject llm-toolkit PySide6"
)


def _import_qt():
    try:
        from PySide6.QtCore import QProcess, QTimer, Qt
        from PySide6.QtWidgets import (
            QApplication,
            QCheckBox,
            QComboBox,
            QFileDialog,
            QGridLayout,
            QGroupBox,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QListWidget,
            QMainWindow,
            QMessageBox,
            QPushButton,
            QPlainTextEdit,
            QVBoxLayout,
            QWidget,
        )
    except ImportError as exc:
        raise RuntimeError(PYSIDE_INSTALL_MESSAGE) from exc
    return {
        "QApplication": QApplication,
        "QCheckBox": QCheckBox,
        "QComboBox": QComboBox,
        "QFileDialog": QFileDialog,
        "QGridLayout": QGridLayout,
        "QGroupBox": QGroupBox,
        "QHBoxLayout": QHBoxLayout,
        "QLabel": QLabel,
        "QLineEdit": QLineEdit,
        "QListWidget": QListWidget,
        "QMainWindow": QMainWindow,
        "QMessageBox": QMessageBox,
        "QProcess": QProcess,
        "QTimer": QTimer,
        "QPlainTextEdit": QPlainTextEdit,
        "QPushButton": QPushButton,
        "QVBoxLayout": QVBoxLayout,
        "QWidget": QWidget,
        "Qt": Qt,
    }


def run_workbench(
    *,
    project: str | None = None,
    auto_init: bool = True,
    auto_guard: bool = True,
    caveman_level: str = "lite",
    open_statusbar: bool = True,
) -> int:
    qt = _import_qt()
    QApplication = qt["QApplication"]
    app = QApplication.instance() or QApplication(sys.argv)
    window = _build_main_window(qt, project, auto_init, auto_guard, caveman_level, open_statusbar)
    window.show()
    return app.exec()


def main() -> None:
    try:
        raise SystemExit(run_workbench())
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc


def _build_main_window(qt: dict[str, object], project: str | None, auto_init: bool, auto_guard: bool, caveman_level: str, open_statusbar: bool):
    QMainWindow = qt["QMainWindow"]
    QWidget = qt["QWidget"]
    QVBoxLayout = qt["QVBoxLayout"]
    QHBoxLayout = qt["QHBoxLayout"]
    QGridLayout = qt["QGridLayout"]
    QGroupBox = qt["QGroupBox"]
    QLabel = qt["QLabel"]
    QLineEdit = qt["QLineEdit"]
    QPushButton = qt["QPushButton"]
    QPlainTextEdit = qt["QPlainTextEdit"]
    QListWidget = qt["QListWidget"]
    QComboBox = qt["QComboBox"]
    QCheckBox = qt["QCheckBox"]
    QFileDialog = qt["QFileDialog"]
    QMessageBox = qt["QMessageBox"]
    QProcess = qt["QProcess"]
    QTimer = qt["QTimer"]
    Qt = qt["Qt"]

    class WorkbenchWindow(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.config = update_defaults(
                load_config(),
                caveman_level=validate_level(caveman_level),
                auto_init=auto_init,
                auto_guard=auto_guard,
            )
            self.open_statusbar = open_statusbar
            self.processes: list[object] = []
            self.setWindowTitle("LLM Toolkit Workbench")
            self.resize(980, 680)

            root = QWidget()
            layout = QVBoxLayout(root)
            self.setCentralWidget(root)

            project_row = QHBoxLayout()
            self.project_edit = QLineEdit()
            self.project_edit.setPlaceholderText("Ruta del proyecto")
            if project:
                self.project_edit.setText(str(Path(project).expanduser()))
            elif self.config.last_project:
                self.project_edit.setText(self.config.last_project)
            browse_btn = QPushButton("Buscar...")
            browse_btn.clicked.connect(self.browse_project)
            last_btn = QPushButton("Abrir último proyecto")
            last_btn.clicked.connect(self.open_last_project)
            project_row.addWidget(QLabel("Proyecto"))
            project_row.addWidget(self.project_edit, 1)
            project_row.addWidget(browse_btn)
            project_row.addWidget(last_btn)
            layout.addLayout(project_row)

            options_row = QHBoxLayout()
            self.level_combo = QComboBox()
            self.level_combo.addItems(["lite", "full", "ultra"])
            self.level_combo.setCurrentText(self.config.default_caveman_level)
            self.auto_init_check = QCheckBox("Auto init")
            self.auto_init_check.setChecked(self.config.auto_init)
            self.auto_guard_check = QCheckBox("Auto guard")
            self.auto_guard_check.setChecked(self.config.auto_guard)
            self.wt_check = QCheckBox("Windows Terminal")
            self.wt_check.setChecked(self.config.use_windows_terminal)
            options_row.addWidget(QLabel("Caveman"))
            options_row.addWidget(self.level_combo)
            options_row.addWidget(self.auto_init_check)
            options_row.addWidget(self.auto_guard_check)
            options_row.addWidget(self.wt_check)
            options_row.addStretch(1)
            layout.addLayout(options_row)

            middle = QHBoxLayout()
            recent_box = QGroupBox("Proyectos recientes")
            recent_layout = QVBoxLayout(recent_box)
            self.recent_list = QListWidget()
            self.recent_list.addItems(list(self.config.recent_projects))
            self.recent_list.itemDoubleClicked.connect(lambda item: self.select_recent(item.text()))
            recent_layout.addWidget(self.recent_list)
            middle.addWidget(recent_box, 1)

            status_box = QGroupBox("Estado")
            status_layout = QGridLayout(status_box)
            self.status_labels = {}
            for row, name in enumerate(("Stack detectado", "Toolkit / doctor", "Env", "Stale", "Guard", "CTX estimado")):
                label = QLabel("n/d")
                label.setTextInteractionFlags(Qt.TextSelectableByMouse)
                self.status_labels[name] = label
                status_layout.addWidget(QLabel(name), row, 0)
                status_layout.addWidget(label, row, 1)
            middle.addWidget(status_box, 2)
            layout.addLayout(middle, 1)

            self.alert_btn = QPushButton("Ver alerta")
            self.alert_btn.clicked.connect(self.open_alert)
            self.alert_btn.setVisible(False)
            layout.addWidget(self.alert_btn)

            buttons = QGridLayout()
            actions = [
                ("Inicializar Toolkit", self.initialize_toolkit),
                ("Doctor", lambda: self.run_cli(["doctor"])),
                ("Guard Check", lambda: self.run_cli(["guard", "check", "--write-alert"])),
                ("Statusbar", lambda: self.run_cli(["statusbar"])),
                ("Abrir Codex", self.open_codex),
                ("Abrir PowerShell", self.open_powershell),
                ("Abrir Workbench 3 paneles", self.open_three_panel),
                ("Abrir carpeta", self.open_folder),
                ("Refrescar estado", self.refresh_state),
            ]
            for index, (text, handler) in enumerate(actions):
                btn = QPushButton(text)
                btn.clicked.connect(handler)
                buttons.addWidget(btn, index // 3, index % 3)
            layout.addLayout(buttons)

            self.output = QPlainTextEdit()
            self.output.setReadOnly(True)
            self.output.setPlaceholderText("Salida breve de comandos")
            layout.addWidget(self.output, 1)

            self.project_edit.editingFinished.connect(self.persist_current_project)
            self.level_combo.currentTextChanged.connect(self.persist_options)
            self.auto_init_check.toggled.connect(self.persist_options)
            self.auto_guard_check.toggled.connect(self.persist_options)
            self.wt_check.toggled.connect(self.persist_options)
            self.refresh_state()
            QTimer.singleShot(0, self.run_initial_checks)

        def log(self, message: str) -> None:
            self.output.appendPlainText(message.rstrip())

        def current_project(self) -> Path | None:
            text = self.project_edit.text().strip()
            if not text:
                self.warn("Indicá una carpeta de proyecto.")
                return None
            return Path(text).expanduser().resolve()

        def warn(self, message: str) -> None:
            QMessageBox.warning(self, "LLM Toolkit Workbench", message)

        def ask_create(self, path: Path) -> bool:
            answer = QMessageBox.question(
                self,
                "Crear proyecto",
                f"La carpeta no existe:\n{path}\n\n¿Querés crearla?",
            )
            return answer == QMessageBox.Yes

        def browse_project(self) -> None:
            selected = QFileDialog.getExistingDirectory(self, "Seleccionar proyecto", self.project_edit.text() or str(Path.home()))
            if selected:
                self.project_edit.setText(selected)
                self.persist_current_project()
                self.refresh_state()

        def open_last_project(self) -> None:
            if not self.config.last_project:
                self.warn("No hay último proyecto guardado.")
                return
            self.project_edit.setText(self.config.last_project)
            self.refresh_state()

        def select_recent(self, path: str) -> None:
            self.project_edit.setText(path)
            self.persist_current_project()
            self.refresh_state()

        def persist_options(self) -> None:
            self.config = update_defaults(
                self.config,
                caveman_level=self.level_combo.currentText(),
                use_windows_terminal=self.wt_check.isChecked(),
                auto_init=self.auto_init_check.isChecked(),
                auto_guard=self.auto_guard_check.isChecked(),
            )
            save_config(self.config)

        def persist_current_project(self) -> None:
            project_path = self.project_edit.text().strip()
            if not project_path:
                return
            self.config = remember_project(self.config, project_path)
            self.persist_options()
            self.recent_list.clear()
            self.recent_list.addItems(list(self.config.recent_projects))

        def ensure_project(self) -> Path | None:
            project_path = self.current_project()
            if project_path is None:
                return None
            if not project_path.exists():
                if not self.ask_create(project_path):
                    return None
                ensure_project_dir(project_path)
            self.persist_current_project()
            return project_path

        def refresh_state(self) -> None:
            project_path = self.project_edit.text().strip()
            if not project_path:
                return
            state = inspect_project(project_path)
            self.alert_btn.setVisible(state.alert_path is not None)
            self.alert_btn.setProperty("alert_path", str(state.alert_path) if state.alert_path else "")
            self.status_labels["Stack detectado"].setText(", ".join(state.stacks) if state.stacks else "unknown")
            self.status_labels["Toolkit / doctor"].setText("inicializado" if state.initialized else "sin inicializar")
            if not state.has_git:
                self.status_labels["Toolkit / doctor"].setText(
                    self.status_labels["Toolkit / doctor"].text() + " | Git no detectado; git init manual"
                )
            try:
                report = build_report(state.path)
                self.status_labels["Env"].setText(f"{report.env.level}: {report.env.message}")
                self.status_labels["Stale"].setText(f"{report.stale.level}: {report.stale.message}")
                guard_check = next((check for check in report.checks if check.name == "automatización CodeBurn Guard"), None)
                self.status_labels["Guard"].setText(guard_check.detail if guard_check else "n/d")
            except Exception as exc:
                self.status_labels["Env"].setText(f"n/d: {exc}")
                self.status_labels["Stale"].setText("n/d")
                self.status_labels["Guard"].setText("n/d")
            try:
                self.status_labels["CTX estimado"].setText(build_statusbar_line(state.path, include_rtk=False))
            except Exception as exc:
                self.status_labels["CTX estimado"].setText(f"n/d: {exc}")

        def run_cli(self, args: list[str]) -> None:
            project_path = self.ensure_project()
            if project_path is None:
                return
            process = QProcess(self)
            process.setProgram("llm-toolkit")
            process.setArguments(args)
            process.setWorkingDirectory(str(project_path))
            process.readyReadStandardOutput.connect(lambda: self.log(bytes(process.readAllStandardOutput()).decode(errors="replace")))
            process.readyReadStandardError.connect(lambda: self.log(bytes(process.readAllStandardError()).decode(errors="replace")))
            process.finished.connect(lambda code, _status: (self.log(f"[fin] llm-toolkit {' '.join(args)} -> {code}"), self.refresh_state()))
            self.processes.append(process)
            self.log(f"> llm-toolkit {' '.join(args)}")
            process.start()

        def initialize_toolkit(self) -> None:
            self.run_cli(["init", "--rtk", "--caveman", self.level_combo.currentText(), "--codeburn"])

        def run_initial_checks(self) -> None:
            project_path = self.project_edit.text().strip()
            if not project_path or not Path(project_path).exists():
                return
            state = inspect_project(project_path)
            if self.auto_init_check.isChecked() and not state.initialized:
                self.initialize_toolkit()
            if self.auto_guard_check.isChecked():
                self.run_cli(["guard", "check", "--write-alert"])

        def open_codex(self) -> None:
            project_path = self.ensure_project()
            if project_path is None:
                return
            if not codex_available():
                self.warn("Codex no está en PATH. Instalá o agregá Codex al PATH antes de abrirlo.")
                return
            launch_plan(codex_plan(project_path))
            self.log("Codex abierto en una PowerShell externa.")

        def open_powershell(self) -> None:
            project_path = self.ensure_project()
            if project_path is None:
                return
            stacks = inspect_project(project_path).stacks
            launch_plan(manual_powershell_plan(project_path, stacks))
            self.log("PowerShell manual abierta.")

        def open_three_panel(self) -> None:
            project_path = self.ensure_project()
            if project_path is None:
                return
            if not codex_available():
                self.warn("Codex no está en PATH. El panel de Codex no se puede iniciar.")
                return
            state = inspect_project(project_path)
            plans = workbench_three_panel_plans(
                project_path,
                prefer_windows_terminal=self.wt_check.isChecked(),
                include_statusbar=self.open_statusbar,
                stacks=state.stacks,
            )
            launch_plans(plans)
            self.log("Workbench externo abierto.")

        def open_folder(self) -> None:
            project_path = self.ensure_project()
            if project_path is None:
                return
            launch_plan(folder_plan(project_path))

        def open_alert(self) -> None:
            alert = self.alert_btn.property("alert_path")
            if not alert:
                return
            if os.name == "nt":
                os.startfile(str(alert))
            else:
                self.log(str(alert))

    return WorkbenchWindow()
