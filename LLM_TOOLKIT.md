# LLM Toolkit

Este repositorio contiene el CLI `llm-toolkit`.

## Alcance actual

- RTK-Codex implementado.
- Caveman-Codex opcional para reportes compactos de programación con Codex.
- CodeBurn opcional para observabilidad de tokens, costos, uso histórico y patrones de desperdicio.
- CodeBurn Guard opcional para checkpoints y alertas de contexto pesado.
- Sin dependencias a proyectos específicos.

## Contrato de uso

Los archivos que genera `llm-toolkit init --rtk` deben ser idempotentes: ejecutar el comando varias veces no debe duplicar bloques ni romper configuraciones existentes.

Los archivos que genera `llm-toolkit init --caveman` también deben ser idempotentes y deben mantener Caveman fuera de tesis, documentación académica, FEA, simulación, cinemática y explicaciones técnicas extensas.

Los archivos que genera `llm-toolkit init --codeburn` también deben ser idempotentes. CodeBurn no reemplaza RTK ni Caveman: solo aporta métricas y no debe usarse para validar funcionalidad del código.

CodeBurn Guard escribe estado local en `.llm-toolkit/`, no debe versionarse y no debe bloquear tareas funcionales si CodeBurn falla o no está instalado.

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
```
