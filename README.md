# llm-toolkit

`llm-toolkit` es un CLI instalable para preparar proyectos de programación para trabajo con Codex/LLM, RTK y futuras integraciones.

La primera versión implementa RTK-Codex. Caveman queda reservado como estructura futura y no se instala ni configura todavía.

## Instalación desde GitHub

```powershell
pipx install git+https://github.com/perezemeca/llm-toolkit.git
```

## Uso rápido

```powershell
llm-toolkit init --rtk
llm-toolkit doctor
llm-toolkit install-rtk
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

### `llm-toolkit doctor`

Revisa el estado del proyecto: RTK en `PATH`, archivos esperados, frontmatter de la skill, exclusión de `.rtk/`, Git, stack detectado y comandos recomendados.

### `llm-toolkit status`

Alias orientado a estado. Ejecuta la misma revisión básica que `doctor`.

### `llm-toolkit install-rtk`

En Windows descarga `rtk-x86_64-pc-windows-msvc.zip` desde GitHub Releases, extrae `rtk.exe`, lo copia a `%USERPROFILE%\.local\bin`, agrega esa carpeta al `PATH` de usuario si falta y ejecuta `rtk --version`.

## Desarrollo

```powershell
python -m pip install -e ".[dev]"
pytest -p no:cacheprovider
```
