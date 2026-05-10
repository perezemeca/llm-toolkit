# LLM Toolkit

Este proyecto fue preparado con `llm-toolkit`.

## Integraciones

- RTK-Codex: activo.
- Caveman-Codex: opcional para reportes compactos de programación con Codex.
- CodeBurn Guard: opcional para alertas de contexto y entorno.
- Env/Stale/Statusbar: diagnóstico de rutas, sesiones stale y contexto estimado.

## Uso recomendado

```powershell
$env:Path = "$PWD\.venv\Scripts;$env:Path"
rtk gain
llm-toolkit env
llm-toolkit statusbar
```

Si existe `.llm-toolkit\alerts\CODEX_ALERT.md`, leerlo antes de editar. Si indica `Environment STALE`, no asumir que Codex ya cargó hooks/config/skills actuales; reiniciar Codex si cambiaron `.codex/`, `AGENTS.md` o skills, y reiniciar PowerShell si hubo reinstalación con pipx, cambios de PATH o cambio de versión.

Después de `pipx install --force`, las PowerShell abiertas pueden seguir usando una ruta o versión vieja. Cerrar y abrir terminal, o verificar con:

```powershell
where.exe llm-toolkit
llm-toolkit env
```

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
