## CodeBurn

CodeBurn se usa para observabilidad de tokens y costo en sesiones locales de agentes de programación, especialmente Codex.

No reemplaza RTK ni Caveman:

- RTK compacta salidas de comandos.
- Caveman compacta respuestas y reportes de Codex.
- CodeBurn mide consumo, costo, uso histórico y patrones de desperdicio.

Comandos recomendados:

```powershell
codeburn status
codeburn today
codeburn month
codeburn report -p 30days
codeburn report --format json
codeburn optimize
codeburn compare
codeburn yield
```

Si no hay datos de sesiones locales, no bloquear la tarea.

No usar CodeBurn para validar funcionalidad del código; solo para métricas.

## CodeBurn Guard

La optimización se activa automáticamente mediante Codex hooks instalados por:

```powershell
llm-toolkit init --codeburn
```

La configuración de Codex generada usa:

```toml
[features]
hooks = true
```

Si existe `codex_hooks = true`, ejecutar `llm-toolkit init --codeburn` para migrar al flag vigente y eliminar el warning deprecated.

Al inicio de una tarea de programación con Codex, revisar si existe:

```powershell
.llm-toolkit\alerts\CODEX_ALERT.md
```

Después de ejecutar tests o análisis soportados (`flutter analyze`, `dart analyze`), los hooks ejecutan automáticamente:

```powershell
llm-toolkit guard check --write-alert
```

No depender de que el usuario ejecute `guard check` manualmente. Los comandos manuales quedan disponibles para diagnóstico.

Si existe alerta `WARNING` o `CRITICAL`, aplicar regla de contexto fresco:

- iniciar un hilo nuevo o limpiar contexto si la tarea sigue siendo pesada;
- usar solo el objetivo actual, archivos relevantes, salida fallida y restricciones vigentes;
- restatar el contexto de trabajo en menos de 10 bullets antes de editar.

Si la alerta indica `Environment STALE`:

- no asumir que hooks/config/skills actuales ya fueron cargados por Codex;
- reiniciar Codex si cambiaron `.codex/`, `AGENTS.md` o skills;
- reiniciar PowerShell si hubo reinstalación con pipx, cambios de PATH o cambio de versión;
- verificar con `llm-toolkit env`.

Después de reinstalar `llm-toolkit` con `pipx install --force`, las PowerShell abiertas pueden seguir usando una versión/ruta vieja. Cerrar y abrir terminal, o verificar con:

```powershell
where.exe llm-toolkit
llm-toolkit env
```

CodeBurn Guard no bloquea tareas funcionales si CodeBurn falla o no está instalado.
