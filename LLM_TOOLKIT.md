# LLM Toolkit

Este repositorio contiene el CLI `llm-toolkit`.

## Alcance actual

- RTK-Codex implementado.
- Caveman-Codex opcional para reportes compactos de programación con Codex.
- CodeBurn opcional para observabilidad de tokens, costos, uso histórico y patrones de desperdicio.
- CodeBurn Guard opcional para checkpoints y alertas de contexto pesado.
- Env/Stale/Statusbar para detectar rutas viejas, sesiones Codex no recargadas y estado compacto.
- Sin dependencias a proyectos específicos.

## Contrato de uso

Los archivos que genera `llm-toolkit init --rtk` deben ser idempotentes: ejecutar el comando varias veces no debe duplicar bloques ni romper configuraciones existentes.

Los archivos que genera `llm-toolkit init --caveman` también deben ser idempotentes y deben mantener Caveman limitado al modo compacto de programación con Codex.

Los archivos que genera `llm-toolkit init --codeburn` también deben ser idempotentes. CodeBurn no reemplaza RTK ni Caveman: solo aporta métricas y no debe usarse para validar funcionalidad del código.

CodeBurn Guard se activa automáticamente mediante hooks de Codex instalados en `.codex/` por `llm-toolkit init --codeburn`. Escribe estado local en `.llm-toolkit/`, no debe versionarse y no debe bloquear tareas funcionales si CodeBurn falla o no está instalado.

Antes de editar, si existe `.llm-toolkit\alerts\CODEX_ALERT.md`, leerlo. Si indica `Environment STALE`, no asumir que Codex ya cargó hooks/config/skills actuales. Reiniciar Codex si cambiaron `.codex/`, `AGENTS.md` o skills; reiniciar PowerShell si hubo reinstalación con pipx, cambios de PATH o cambio de versión; verificar con `llm-toolkit env`.

Después de `pipx install --force`, las PowerShell abiertas pueden seguir usando una ruta o versión vieja. Cerrar y abrir terminal, o verificar con:

```powershell
where.exe llm-toolkit
llm-toolkit env
```

`.codex/config.toml` debe usar el feature flag vigente:

```toml
[features]
hooks = true
```

Si existe `codex_hooks = true`, `llm-toolkit init --codeburn` debe migrarlo a `hooks = true`, eliminar la clave deprecated y preservar otras claves existentes.

El contenido visible para usuarios, mensajes de ayuda y documentación debe mantenerse en español.

## CodeBurn

Instalación opcional:

```powershell
llm-toolkit install-codeburn
```

Inicialización del bloque de instrucciones:

```powershell
llm-toolkit init --codeburn
llm-toolkit init --rtk --caveman --codeburn
```

Esto crea o actualiza:

```text
.codex/config.toml
.codex/hooks.json
.codex/hooks/llm_toolkit_guard_hook.py
```

Uso:

```powershell
llm-toolkit metrics
llm-toolkit metrics --today
llm-toolkit metrics --month
llm-toolkit metrics --json
llm-toolkit optimize
llm-toolkit guard check --write-alert
llm-toolkit guard start --interval 300 --timeout 30
llm-toolkit guard status
llm-toolkit guard stop
llm-toolkit env
llm-toolkit stale status
llm-toolkit stale mark-clean
llm-toolkit statusbar
```

Los comandos `guard` manuales son herramientas de diagnóstico; el flujo normal se dispara por hooks de Codex.

`llm-toolkit doctor` y `llm-toolkit status` deben aceptar `hooks = true` como OK. Si detectan solo `codex_hooks = true`, deben reportarlo como legacy/deprecated y sugerir migración con `llm-toolkit init --codeburn`.

`llm-toolkit env` diagnostica rutas/versiones activas. `llm-toolkit stale` compara un fingerprint de `.codex/`, `AGENTS.md`, skills y código local. `llm-toolkit statusbar` imprime CTX estimado desde `last_token_usage`, Guard y Env/Stale.

## Flutter/Dart

`llm-toolkit doctor` y `llm-toolkit status` detectan `pubspec.yaml` y reportan Flutter/Dart en PATH.

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

Si RTK ejecuta Flutter/Dart como fallback, usar la salida compacta propia de Flutter/Dart y RTK para git/diffs.
