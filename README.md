# llm-toolkit

`llm-toolkit` es un CLI instalable para preparar proyectos de programación para trabajo con Codex/LLM, RTK, Caveman, CodeBurn y futuras integraciones.

La primera versión implementa RTK-Codex. Caveman queda reservado como estructura futura y no se instala ni configura todavía.
La integración Caveman-Codex es opcional y está limitada a reportes compactos de programación con Codex.
La integración CodeBurn es opcional y sirve para observar consumo de tokens, costos, uso histórico y patrones de desperdicio.

## Instalación desde GitHub

```powershell
pipx install git+https://github.com/perezemeca/llm-toolkit.git
```

## Uso rápido

```powershell
llm-toolkit init --rtk
llm-toolkit init --caveman
llm-toolkit init --codeburn
llm-toolkit init --rtk --caveman --codeburn
llm-toolkit doctor
llm-toolkit install-rtk
llm-toolkit install-codeburn
llm-toolkit metrics
llm-toolkit optimize
llm-toolkit guard check --write-alert
llm-toolkit status
```

## Qué hace `init --rtk`

- Detecta si el directorio actual tiene Git.
- Detecta stack Python, Node, Rust, Go, .NET o `unknown`.
- Crea o actualiza `AGENTS.md` con un bloque RTK idempotente.
- Crea `.agents/skills/rtk-codex/SKILL.md` con frontmatter válido.
- Crea `tools/codex_rtk_env.ps1` como script manual opcional.
- Crea `.rtk/` y configura RTK para usar `.rtk/history.db`.
- Evita versionar `.rtk/` usando `.git/info/exclude` si hay Git o `.gitignore` si no hay Git.
- Muestra comandos recomendados según el stack detectado.

## Preparación recomendada para Codex en PowerShell

Antes de trabajar en un proyecto con entorno virtual local:

```powershell
$env:Path = "$PWD\.venv\Scripts;$env:Path"
```

Luego usar RTK para las inspecciones habituales:

```powershell
rtk git status
rtk git diff --stat
rtk git diff --name-only
rtk git ls-files
rtk gain
```

Si el proyecto tiene pytest instalado:

```powershell
rtk pytest -p no:cacheprovider
```

## Comandos

### `llm-toolkit init --rtk`

Inicializa RTK-Codex en el proyecto actual.

### `llm-toolkit init --caveman`

Inicializa Caveman-Codex en el proyecto actual. El nivel por defecto es `lite`.

Niveles disponibles:

```powershell
llm-toolkit init --caveman lite
llm-toolkit init --caveman full
llm-toolkit init --caveman ultra
```

Alternativa explícita:

```powershell
llm-toolkit init --caveman --caveman-level full
```

### `llm-toolkit init --rtk --caveman`

Inicializa ambas integraciones. RTK compacta salidas de comandos; Caveman compacta reportes del agente.

### `llm-toolkit init --codeburn`

Agrega o actualiza el bloque CodeBurn en `AGENTS.md`. No instala CodeBurn automáticamente y no bloquea tareas funcionales si no hay datos de sesiones locales.

### `llm-toolkit init --rtk --caveman --codeburn`

Inicializa las tres integraciones. RTK compacta salidas de comandos, Caveman compacta reportes del agente y CodeBurn observa consumo y costos.

### `llm-toolkit doctor`

Revisa el estado del proyecto: RTK en `PATH`, archivos esperados, frontmatter de skills, exclusión de `.rtk/`, Git, stack detectado, Caveman, CodeBurn y comandos recomendados.

### `llm-toolkit status`

Alias orientado a estado. Ejecuta la misma revisión básica que `doctor`.

### `llm-toolkit install-rtk`

En Windows descarga `rtk-x86_64-pc-windows-msvc.zip` desde GitHub Releases, extrae `rtk.exe`, lo copia a `%USERPROFILE%\.local\bin`, agrega esa carpeta al `PATH` de usuario si falta y ejecuta `rtk --version`.

### `llm-toolkit install-codeburn`

Verifica `node --version` y `npm --version`. Si ambos existen, ejecuta `npm install -g codeburn` y valida `codeburn --version` o `codeburn status`. No instala Node.

El comando del toolkit incluye el prefijo `llm-toolkit`: usar `llm-toolkit install-codeburn`, no `install-codeburn` suelto.

### `llm-toolkit metrics`

Ejecuta `codeburn status`. Variantes:

```powershell
llm-toolkit metrics --today
llm-toolkit metrics --month
llm-toolkit metrics --json
```

Si CodeBurn no está instalado, informa `CodeBurn no está instalado. Ejecutar llm-toolkit install-codeburn.`

### `llm-toolkit optimize`

Ejecuta `codeburn optimize`. Si falla o no hay datos locales de sesiones, reporta el error sin bloquear la tarea.

### `llm-toolkit guard check`

Ejecuta un chequeo liviano con CodeBurn y escribe `.llm-toolkit/state/context_health.json`. Si CodeBurn no está instalado o no tiene datos, informa `UNKNOWN` sin bloquear.

```powershell
llm-toolkit guard check
llm-toolkit guard check --write-alert
```

Con `--write-alert`, si detecta `WARNING` o `CRITICAL`, crea `.llm-toolkit/alerts/CODEX_ALERT.md` con la regla de contexto fresco.

### `llm-toolkit guard start/status/stop`

Registra o desactiva una política local de checkpoints sin dejar procesos residentes colgados.

```powershell
llm-toolkit guard start --interval 300 --timeout 30
llm-toolkit guard status
llm-toolkit guard stop
```

## Desarrollo

```powershell
python -m pip install -e ".[dev]"
pytest -p no:cacheprovider
```
