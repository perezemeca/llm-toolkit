# LLM Toolkit

Este proyecto fue preparado con `llm-toolkit`.

## Integraciones

- RTK-Codex: activo.
- Caveman-Codex: opcional para reportes compactos de programación con Codex.

## Uso recomendado

```powershell
$env:Path = "$PWD\.venv\Scripts;$env:Path"
rtk gain
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
