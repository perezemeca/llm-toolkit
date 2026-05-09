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

<!-- LLM-TOOLKIT:CAVEMAN:BEGIN -->
## Caveman-Codex

Caveman es un modo opcional para reportes de programación con Codex. No reemplaza RTK: RTK compacta salidas de comandos y Caveman compacta respuestas del agente.

- Uso permitido: solo programación con Codex.
- Nivel configurado: lite
- Nivel por defecto: lite.

Reportes compactos:

- archivos modificados;
- cambios realizados;
- tests ejecutados;
- resultado;
- riesgos;
- próximos pasos.

No usar Caveman para:

- tesis;
- documentación académica;
- FEA;
- simulación;
- cinemática;
- explicaciones técnicas extensas.
<!-- LLM-TOOLKIT:CAVEMAN:END -->

<!-- LLM-TOOLKIT:CODEBURN:BEGIN -->
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
<!-- LLM-TOOLKIT:CODEBURN:END -->
