# llm-toolkit

`llm-toolkit` es un CLI para preparar proyectos de programación con Codex y herramientas auxiliares de control de contexto, salidas y costos.

El proyecto integra RTK, Caveman, CodeBurn y CodeBurn Guard. Estas herramientas están pensadas para trabajo de programación con Codex.

## Módulos

| Módulo | Rol |
| --- | --- |
| RTK | Compacta salidas de comandos y conserva trazabilidad local en `.rtk/history.db`. |
| Caveman | Compacta respuestas y reportes de Codex para programación. |
| CodeBurn | Observa consumo de tokens, costos, uso histórico y patrones de desperdicio. |
| CodeBurn Guard | Instala hooks de Codex, ejecuta checkpoints automáticos y genera alertas de contexto pesado. |

RTK, Caveman y CodeBurn no se reemplazan entre sí. Cada módulo cubre una parte distinta del flujo.

## Instalación

Instalar desde GitHub con `pipx`:

```powershell
pipx install git+https://github.com/perezemeca/llm-toolkit.git
```

Actualizar desde `main`:

```powershell
pipx install --force "git+https://github.com/perezemeca/llm-toolkit.git@main"
```

## Uso Rápido

Inicializar un proyecto con RTK, Caveman en nivel `lite` y CodeBurn:

```powershell
llm-toolkit init --rtk --caveman lite --codeburn
```

Revisar estado:

```powershell
llm-toolkit doctor
llm-toolkit status
llm-toolkit env
llm-toolkit statusbar
```

El init instala hooks de Codex en `.codex/`, por lo que los checkpoints de Guard quedan automatizados para sesiones de Codex. El comando manual queda disponible para diagnóstico:

```powershell
llm-toolkit guard check --write-alert
```

## Flujo Recomendado En Proyecto Python

Preparar el entorno local en PowerShell:

```powershell
$env:Path = "$PWD\.venv\Scripts;$env:Path"
```

Validar con RTK:

```powershell
rtk pytest -p no:cacheprovider
rtk gain
```

Después de tests, los hooks de Codex ejecutan Guard automáticamente. El comando manual queda disponible para diagnóstico:

```powershell
llm-toolkit guard check --write-alert
```

Si aparece `.llm-toolkit\alerts\CODEX_ALERT.md`, revisar la alerta antes de continuar con más contexto.

Si la alerta dice `Environment STALE`, reiniciar Codex si cambiaron `.codex/`, `AGENTS.md` o skills, y reiniciar PowerShell si hubo reinstalación con `pipx`, cambios de PATH o cambio de versión. Verificar con:

```powershell
where.exe llm-toolkit
llm-toolkit env
```

## Flujo Recomendado En Proyecto Flutter/Dart

`doctor` y `status` detectan proyectos Flutter/Dart mediante `pubspec.yaml`. Para Flutter también reconocen `sdk: flutter`, dependencia `flutter` o estructura típica del proyecto.

Para Flutter:

```powershell
rtk flutter pub get
rtk flutter analyze
rtk flutter test
flutter test --reporter compact
flutter analyze --no-pub
```

Para Dart:

```powershell
rtk dart pub get
rtk dart analyze
rtk dart test
dart test --reporter compact
```

Si RTK trata estos comandos como fallback, usar la salida compacta propia de Flutter/Dart y RTK para git/diffs.

CodeBurn Guard se dispara automáticamente después de `flutter test`, `dart test`, `flutter analyze` y `dart analyze` cuando los hooks de Codex están instalados.

## Comandos Principales

### `llm-toolkit init`

Inicializa integraciones idempotentes en el proyecto actual.

```powershell
llm-toolkit init --rtk
llm-toolkit init --caveman lite
llm-toolkit init --codeburn
llm-toolkit init --rtk --caveman lite --codeburn
```

`--rtk` crea o actualiza el bloque RTK en `AGENTS.md`, prepara la skill `rtk-codex`, crea herramientas auxiliares y configura `.rtk/`.

`--caveman` crea o actualiza el bloque Caveman y la skill `caveman-codex`. El nivel recomendado por defecto es `lite`.

`--codeburn` crea o actualiza el bloque CodeBurn, instala hooks de Codex en `.codex/` y agrega las reglas de CodeBurn Guard en `AGENTS.md`. No instala CodeBurn automáticamente.

La configuración generada usa el feature flag vigente de Codex:

```toml
[features]
hooks = true
```

Si encuentra una configuración legacy con `codex_hooks = true`, `init --codeburn` la migra a `hooks = true` y elimina la clave deprecated para evitar warnings de Codex.

### `llm-toolkit install-rtk`

Instala `rtk.exe` en Windows desde GitHub Releases y lo agrega al `PATH` de usuario si hace falta.

```powershell
llm-toolkit install-rtk
```

### `llm-toolkit install-codeburn`

Verifica `node --version` y `npm --version`. Si ambos existen, ejecuta `npm install -g codeburn` y valida `codeburn --version` o `codeburn status`.

```powershell
llm-toolkit install-codeburn
```

El comando correcto incluye el prefijo `llm-toolkit`; no usar `install-codeburn` suelto. Este comando no instala Node.

### `llm-toolkit metrics`

Ejecuta métricas locales de CodeBurn.

```powershell
llm-toolkit metrics
llm-toolkit metrics --today
llm-toolkit metrics --month
llm-toolkit metrics --json
```

Si CodeBurn no está instalado, informa cómo instalarlo sin bloquear tareas funcionales.

### `llm-toolkit optimize`

Ejecuta `codeburn optimize` para detectar sesiones con contexto pesado y ahorro potencial.

```powershell
llm-toolkit optimize
```

CodeBurn no valida funcionalidad del código; solo aporta métricas de consumo y contexto.

### `llm-toolkit guard`

CodeBurn Guard ejecuta checkpoints livianos y escribe estado local en `.llm-toolkit/`.

El flujo normal es automático vía hooks instalados por `llm-toolkit init --codeburn`. Los comandos siguientes son herramientas manuales de diagnóstico:

```powershell
llm-toolkit guard check
llm-toolkit guard check --write-alert
llm-toolkit guard start --interval 300 --timeout 30
llm-toolkit guard status
llm-toolkit guard stop
```

`guard check` escribe `.llm-toolkit/state/context_health.json`.

`guard check --write-alert` crea `.llm-toolkit/alerts/CODEX_ALERT.md` si detecta `WARNING` o `CRITICAL`.

`guard start/status/stop` registra una política local de checkpoints sin dejar procesos residentes colgados.

Los hooks versionados viven en:

```text
.codex/config.toml
.codex/hooks.json
.codex/hooks/llm_toolkit_guard_hook.py
```

Guard no bloquea tareas si CodeBurn falla, no está instalado o no tiene datos locales.

### `llm-toolkit env`, `stale` Y `statusbar`

Diagnóstico para trabajar con varias PowerShell y sesiones Codex abiertas:

```powershell
llm-toolkit env
llm-toolkit stale status
llm-toolkit stale check
llm-toolkit stale mark-clean
llm-toolkit statusbar
llm-toolkit statusbar --watch --interval 5
```

`env` muestra rutas y versiones activas de `llm-toolkit`, Codex, RTK y CodeBurn, detectando múltiples rutas o versiones viejas.

`stale mark-clean` guarda un fingerprint de `.codex/`, `AGENTS.md`, skills y código local del toolkit. `stale check/status` advierten si esos archivos o la ruta/versión activa cambiaron después del fingerprint.

`statusbar` imprime una línea compacta, por ejemplo `CTX 73.9% est | WARNING | Guard CRITICAL | Env OK`. El contexto se estima desde el último `token_count` de `~\.codex\sessions`, usando `last_token_usage.input_tokens / model_context_window`; no scrapea ni envía `/status`.

### `llm-toolkit doctor` Y `llm-toolkit status`

Revisan el estado del proyecto, las integraciones disponibles, el bloque CodeBurn en `AGENTS.md` y comandos recomendados.

También reportan `Stack: flutter` o `Stack: dart`, `Flutter en PATH`, `Dart en PATH` y `pubspec.yaml`.

Para CodeBurn Guard, `doctor` y `status` reportan `hooks habilitado` como OK cuando `.codex/config.toml` contiene `hooks = true`. Si solo existe `codex_hooks = true`, lo muestran como legacy/deprecated y sugieren ejecutar `llm-toolkit init --codeburn` para migrar.

```powershell
llm-toolkit doctor
llm-toolkit status
```

## Reglas Operativas

- No usar `rtk ls` en Windows.
- Usar `rtk git ls-files` para listar archivos versionados.
- Usar RTK para compactar salidas de comandos.
- Usar Caveman `lite` para reportes compactos de programación.
- Usar Caveman solo para reportes compactos de programación con Codex cuando se busque reducir tokens.
- CodeBurn no valida funcionalidad del código.
- Guard se activa automáticamente mediante hooks de Codex después de `llm-toolkit init --codeburn`.
- Guard no bloquea tareas si falla CodeBurn.
- Leer `.llm-toolkit\alerts\CODEX_ALERT.md` antes de editar si existe.
- Si la alerta indica `Environment STALE`, no asumir que Codex ya cargó hooks/config/skills actuales.
- Después de `pipx install --force`, cerrar y abrir PowerShell o validar con `where.exe llm-toolkit` y `llm-toolkit env`.
- Versionar `.codex/` cuando contiene hooks/config del proyecto.
- No versionar `.rtk/` ni `.llm-toolkit/`.

## Desarrollo

Instalar en modo editable con dependencias de desarrollo:

```powershell
python -m pip install -e ".[dev]"
```

Ejecutar tests:

```powershell
python -m pytest -p no:cacheprovider --basetemp .rtk\pytest_tmp_py
```
