---
name: rtk-codex
description: Usar RTK con Codex para inspeccionar, validar y resumir trabajo en proyectos locales.
---

# RTK-Codex

## Preparación

En PowerShell, antes de trabajar con un entorno virtual local:

```powershell
$env:Path = "$PWD\.venv\Scripts;$env:Path"
```

## Reglas de uso

- Usar `rtk git status` para revisar el estado inicial.
- Usar `rtk git diff --stat` y `rtk git diff --name-only` para entender cambios.
- Usar `rtk git ls-files` para listar archivos versionados cuando haya Git.
- Usar `rtk pytest -p no:cacheprovider` si el proyecto tiene pytest instalado.
- Usar `rtk gain` al inicio o al cierre para revisar ahorro de tokens.
- No versionar `.rtk/`.
- No ejecutar `commit`, `push`, `merge` ni `rebase` salvo pedido explícito del usuario.

## Sin Git

Si el proyecto no tiene `.git`, no recomendar comandos `rtk git ...`. Usar solo comandos RTK aplicables al stack detectado y `rtk gain`.
