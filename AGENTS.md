<!-- LLM-TOOLKIT:RTK:BEGIN -->
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

No versionar `.rtk/`. La base local de RTK debe quedar en `.rtk/history.db`.
<!-- LLM-TOOLKIT:RTK:END -->
