# LLM Toolkit

Este repositorio contiene el CLI `llm-toolkit`.

## Alcance actual

- RTK-Codex implementado.
- Caveman reservado para una etapa futura.
- Sin dependencias a proyectos específicos.

## Contrato de uso

Los archivos que genera `llm-toolkit init --rtk` deben ser idempotentes: ejecutar el comando varias veces no debe duplicar bloques ni romper configuraciones existentes.

El contenido visible para usuarios, mensajes de ayuda y documentación debe mantenerse en español.
