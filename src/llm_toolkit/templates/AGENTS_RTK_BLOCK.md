## RTK-Codex

Antes de ejecutar comandos del proyecto en PowerShell, preparar el entorno local si existe `.venv`:

```powershell
$env:Path = "$PWD\.venv\Scripts;$env:Path"
```

Usar RTK para inspecciones y validación cuando esté disponible:

```powershell
rtk git status
rtk git diff --stat
rtk git diff --name-only
rtk git ls-files
rtk gain
```

Si el proyecto tiene pytest instalado, preferir:

```powershell
rtk pytest -p no:cacheprovider
```

Si el proyecto es Flutter/Dart, usar comandos específicos cuando correspondan:

```powershell
rtk flutter pub get
rtk flutter analyze
rtk flutter test
flutter test --reporter compact
flutter analyze --no-pub

rtk dart pub get
rtk dart analyze
rtk dart test
dart test --reporter compact
```

Si RTK ejecuta Flutter/Dart como fallback, usar la salida compacta propia de Flutter/Dart y RTK para git/diffs.

No versionar `.rtk/`. La base local de RTK debe quedar en `.rtk/history.db`.
