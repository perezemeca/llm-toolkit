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

Al inicio de una tarea de programación con Codex, revisar si existe:

```powershell
.llm-toolkit\alerts\CODEX_ALERT.md
```

Después de ejecutar tests o en un checkpoint de programación, ejecutar:

```powershell
llm-toolkit guard check --write-alert
```

Si el guard informa `WARNING` o `CRITICAL`, aplicar regla de contexto fresco:

- iniciar un hilo nuevo o limpiar contexto si la tarea sigue siendo pesada;
- usar solo el objetivo actual, archivos relevantes, salida fallida y restricciones vigentes;
- restatar el contexto de trabajo en menos de 10 bullets antes de editar.

CodeBurn Guard no bloquea tareas funcionales si CodeBurn falla o no está instalado.
