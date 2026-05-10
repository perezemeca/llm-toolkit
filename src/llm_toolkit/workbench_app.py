from __future__ import annotations

import sys
from pathlib import Path

from .caveman import validate_level
from .statusbar import build_statusbar_line
from .workbench_config import load_config, remember_project, save_config, update_defaults
from .workbench_launcher import (
    WORKBENCH_V2_MAIN_AREAS,
    build_project_selection_plan,
    codex_available,
    diagnostic_commands,
    ensure_project_dir,
    inspect_project,
    launch_plan,
    read_alert_text,
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
            QComboBox,
            QDialog,
            QFileDialog,
            QGroupBox,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QMainWindow,
            QMessageBox,
            QPlainTextEdit,
            QPushButton,
            QSplitter,
            QVBoxLayout,
            QWidget,
        )
    except ImportError as exc:
        raise RuntimeError(PYSIDE_INSTALL_MESSAGE) from exc
    return {
        "QApplication": QApplication,
        "QComboBox": QComboBox,
        "QDialog": QDialog,
        "QFileDialog": QFileDialog,
        "QGroupBox": QGroupBox,
        "QHBoxLayout": QHBoxLayout,
        "QLabel": QLabel,
        "QLineEdit": QLineEdit,
        "QMainWindow": QMainWindow,
        "QMessageBox": QMessageBox,
        "QProcess": QProcess,
        "QTimer": QTimer,
        "QPlainTextEdit": QPlainTextEdit,
        "QPushButton": QPushButton,
        "QSplitter": QSplitter,
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


def _build_main_window(
    qt: dict[str, object],
    project: str | None,
    auto_init: bool,
    auto_guard: bool,
    caveman_level: str,
    open_statusbar: bool,
):
    QMainWindow = qt["QMainWindow"]
    QWidget = qt["QWidget"]
    QVBoxLayout = qt["QVBoxLayout"]
    QHBoxLayout = qt["QHBoxLayout"]
    QGroupBox = qt["QGroupBox"]
    QLabel = qt["QLabel"]
    QLineEdit = qt["QLineEdit"]
    QPushButton = qt["QPushButton"]
    QPlainTextEdit = qt["QPlainTextEdit"]
    QComboBox = qt["QComboBox"]
    QFileDialog = qt["QFileDialog"]
    QMessageBox = qt["QMessageBox"]
    QDialog = qt["QDialog"]
    QProcess = qt["QProcess"]
    QTimer = qt["QTimer"]
    QSplitter = qt["QSplitter"]
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
            self.auto_init = self.config.auto_init
            self.auto_guard = self.config.auto_guard
            self.caveman_level = self.config.default_caveman_level
            self.processes: list[object] = []
            self.opened_terminal_project: str | None = None
            self.setWindowTitle("LLM Toolkit Workbench")
            self.resize(1120, 680)

            root = QWidget()
            layout = QVBoxLayout(root)
            self.setCentralWidget(root)

            topbar = QHBoxLayout()
            self.recent_combo = QComboBox()
            self.recent_combo.addItem("Recientes", "")
            for item in self.config.recent_projects:
                self.recent_combo.addItem(item, item)
            self.recent_combo.activated.connect(self.select_recent_index)
            self.project_edit = QLineEdit()
            self.project_edit.setPlaceholderText("Ruta del proyecto")
            if project:
                self.project_edit.setText(str(Path(project).expanduser()))
            elif self.config.last_project:
                self.project_edit.setText(self.config.last_project)
            browse_btn = QPushButton("Buscar...")
            browse_btn.clicked.connect(self.browse_project)
            self.diagnostic_btn = QPushButton("Diagnóstico")
            self.diagnostic_btn.clicked.connect(self.show_diagnostics)
            self.alert_btn = QPushButton("Alerta")
            self.alert_btn.clicked.connect(self.show_alert)
            self.refresh_btn = QPushButton("↻")
            self.refresh_btn.setToolTip("Actualizar estado")
            self.refresh_btn.clicked.connect(self.refresh_state)
            topbar.addWidget(QLabel("Recientes"))
            topbar.addWidget(self.recent_combo, 1)
            topbar.addWidget(QLabel("Proyecto"))
            topbar.addWidget(self.project_edit, 3)
            topbar.addWidget(browse_btn)
            topbar.addWidget(self.diagnostic_btn)
            topbar.addWidget(self.alert_btn)
            topbar.addWidget(self.refresh_btn)
            layout.addLayout(topbar)

            splitter = QSplitter(Qt.Horizontal)
            self.codex_output = self._terminal_panel(WORKBENCH_V2_MAIN_AREAS[0], "Codex se abre en el proyecto después de Guard.")
            self.shell_output = self._terminal_panel(WORKBENCH_V2_MAIN_AREAS[1], "PowerShell queda lista con PATH de .venv si existe.")
            splitter.addWidget(self.codex_output["box"])
            splitter.addWidget(self.shell_output["box"])
            splitter.setSizes([560, 560])
            layout.addWidget(splitter, 1)

            self.statusbar_label = QLabel("CTX n/d | Guard n/d | Env n/d | Alert no")
            self.statusbar_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            layout.addWidget(self.statusbar_label)

            self.project_edit.editingFinished.connect(self.project_selected)
            self.status_timer = QTimer(self)
            self.status_timer.setInterval(5000)
            self.status_timer.timeout.connect(self.refresh_statusbar)
            self.status_timer.start()
            QTimer.singleShot(0, self.project_selected)

        def _terminal_panel(self, title: str, placeholder: str) -> dict[str, object]:
            box = QGroupBox(title)
            panel = QVBoxLayout(box)
            output = QPlainTextEdit()
            output.setReadOnly(True)
            output.setPlaceholderText(placeholder)
            panel.addWidget(output)
            return {"box": box, "output": output}

        def _append(self, panel: dict[str, object], message: str) -> None:
            panel["output"].appendPlainText(message.rstrip())

        def log_codex(self, message: str) -> None:
            self._append(self.codex_output, message)

        def log_shell(self, message: str) -> None:
            self._append(self.shell_output, message)

        def warn(self, message: str) -> None:
            QMessageBox.warning(self, "LLM Toolkit Workbench", message)

        def ask_create(self, path: Path) -> bool:
            answer = QMessageBox.question(
                self,
                "Crear proyecto",
                f"La carpeta no existe:\n{path}\n\n¿Querés crearla?",
            )
            return answer == QMessageBox.Yes

        def current_project(self) -> Path | None:
            text = self.project_edit.text().strip()
            if not text:
                return None
            return Path(text).expanduser().resolve()

        def browse_project(self) -> None:
            selected = QFileDialog.getExistingDirectory(self, "Seleccionar proyecto", self.project_edit.text() or str(Path.home()))
            if selected:
                self.project_edit.setText(selected)
                self.project_selected()

        def select_recent_index(self, index: int) -> None:
            path = self.recent_combo.itemData(index)
            if path:
                self.project_edit.setText(path)
                self.project_selected()

        def remember_current_project(self, project_path: Path) -> None:
            self.config = remember_project(self.config, project_path)
            save_config(self.config)
            self.recent_combo.blockSignals(True)
            self.recent_combo.clear()
            self.recent_combo.addItem("Recientes", "")
            for item in self.config.recent_projects:
                self.recent_combo.addItem(item, item)
            self.recent_combo.blockSignals(False)

        def ensure_project(self) -> Path | None:
            project_path = self.current_project()
            if project_path is None:
                return None
            if not project_path.exists():
                if not self.ask_create(project_path):
                    return None
                ensure_project_dir(project_path)
            self.remember_current_project(project_path)
            return project_path

        def project_selected(self) -> None:
            project_path = self.ensure_project()
            if project_path is None:
                self.refresh_statusbar()
                return
            plan = build_project_selection_plan(
                project_path,
                caveman_level=self.caveman_level,
                auto_init=self.auto_init,
                auto_guard=self.auto_guard,
            )
            if plan.git_message:
                self.log_shell(plan.git_message)
            if plan.init_args:
                self.run_cli(list(plan.init_args), self.log_shell)
            if plan.guard_args:
                self.run_cli(list(plan.guard_args), self.log_codex)
            self.refresh_state()
            self.open_terminal_pair(plan.terminal_plans, project_path)

        def open_terminal_pair(self, plans: tuple[object, object], project_path: Path) -> None:
            project_key = str(project_path)
            if self.opened_terminal_project == project_key:
                return
            if codex_available():
                launch_plan(plans[0])
                self.log_codex("Codex CLI abierto con Guard previo.")
            else:
                self.log_codex("Codex no está en PATH; panel preparado, apertura pendiente.")
            launch_plan(plans[1])
            self.log_shell("PowerShell manual abierta con comandos recomendados.")
            self.opened_terminal_project = project_key

        def refresh_state(self) -> None:
            project_path = self.current_project()
            if project_path is None:
                self.alert_btn.setEnabled(False)
                self.refresh_statusbar()
                return
            state = inspect_project(project_path)
            self.alert_btn.setEnabled(state.alert_path is not None)
            self.refresh_statusbar()

        def refresh_statusbar(self) -> None:
            project_path = self.current_project()
            if project_path is None:
                self.statusbar_label.setText("CTX n/d | Guard n/d | Env n/d | Alert no")
                return
            try:
                self.statusbar_label.setText(build_statusbar_line(project_path, include_rtk=True))
            except Exception:
                self.statusbar_label.setText("CTX n/d | Guard n/d | Env n/d")

        def run_cli(self, args: list[str], logger) -> None:
            project_path = self.current_project()
            if project_path is None:
                return
            process = QProcess(self)
            process.setProgram("llm-toolkit")
            process.setArguments(args)
            process.setWorkingDirectory(str(project_path))
            process.readyReadStandardOutput.connect(lambda: logger(bytes(process.readAllStandardOutput()).decode(errors="replace")))
            process.readyReadStandardError.connect(lambda: logger(bytes(process.readAllStandardError()).decode(errors="replace")))
            process.finished.connect(lambda code, _status: (logger(f"[fin] llm-toolkit {' '.join(args)} -> {code}"), self.refresh_state()))
            self.processes.append(process)
            logger(f"> llm-toolkit {' '.join(args)}")
            process.start()

        def show_alert(self) -> None:
            project_path = self.current_project()
            if project_path is None:
                return
            content = read_alert_text(project_path)
            if content is None:
                self.warn("No hay alerta activa.")
                return
            self.show_text_dialog("Alerta CodeBurn Guard", content)

        def show_diagnostics(self) -> None:
            project_path = self.ensure_project()
            if project_path is None:
                return
            dialog = QDialog(self)
            dialog.setWindowTitle("Diagnóstico / Comandos")
            dialog.resize(840, 560)
            layout = QVBoxLayout(dialog)
            text = QPlainTextEdit()
            text.setReadOnly(True)
            commands = list(diagnostic_commands())
            text.setPlainText("Comandos recomendados:\n" + "\n".join("llm-toolkit " + " ".join(command) for command in commands) + "\n")
            layout.addWidget(text)
            close_btn = QPushButton("Cerrar")
            close_btn.clicked.connect(dialog.accept)
            layout.addWidget(close_btn)

            def run_next(index: int = 0) -> None:
                if index >= len(commands):
                    return
                args = list(commands[index])
                process = QProcess(dialog)
                process.setProgram("llm-toolkit")
                process.setArguments(args)
                process.setWorkingDirectory(str(project_path))
                process.readyReadStandardOutput.connect(
                    lambda: text.appendPlainText(bytes(process.readAllStandardOutput()).decode(errors="replace").rstrip())
                )
                process.readyReadStandardError.connect(
                    lambda: text.appendPlainText(bytes(process.readAllStandardError()).decode(errors="replace").rstrip())
                )
                process.finished.connect(
                    lambda code, _status: (text.appendPlainText(f"[fin] llm-toolkit {' '.join(args)} -> {code}\n"), run_next(index + 1))
                )
                self.processes.append(process)
                text.appendPlainText(f"\n> llm-toolkit {' '.join(args)}")
                process.start()

            QTimer.singleShot(0, run_next)
            dialog.exec()

        def show_text_dialog(self, title: str, content: str) -> None:
            dialog = QDialog(self)
            dialog.setWindowTitle(title)
            dialog.resize(760, 520)
            layout = QVBoxLayout(dialog)
            text = QPlainTextEdit()
            text.setReadOnly(True)
            text.setPlainText(content)
            layout.addWidget(text)
            close_btn = QPushButton("Cerrar")
            close_btn.clicked.connect(dialog.accept)
            layout.addWidget(close_btn)
            dialog.exec()

    return WorkbenchWindow()
