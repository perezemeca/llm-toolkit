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

Después de ejecutar tests, los hooks ejecutan automáticamente:

```powershell
llm-toolkit guard check --write-alert
```

No depender de que el usuario ejecute `guard check` manualmente. Los comandos manuales quedan disponibles para diagnóstico.

Si existe alerta `WARNING` o `CRITICAL`, aplicar regla de contexto fresco:

- iniciar un hilo nuevo o limpiar contexto si la tarea sigue siendo pesada;
- usar solo el objetivo actual, archivos relevantes, salida fallida y restricciones vigentes;
- restatar el contexto de trabajo en menos de 10 bullets antes de editar.

CodeBurn Guard no bloquea tareas funcionales si CodeBurn falla o no está instalado.
