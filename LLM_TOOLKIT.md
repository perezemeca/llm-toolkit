# LLM Toolkit

Este repositorio contiene el CLI `llm-toolkit`.

## Alcance actual

- RTK-Codex implementado.
- Caveman-Codex opcional para reportes compactos de programación con Codex.
- Sin dependencias a proyectos específicos.

## Contrato de uso

Los archivos que genera `llm-toolkit init --rtk` deben ser idempotentes: ejecutar el comando varias veces no debe duplicar bloques ni romper configuraciones existentes.

Los archivos que genera `llm-toolkit init --caveman` también deben ser idempotentes y deben mantener Caveman fuera de tesis, documentación académica, FEA, simulación, cinemática y explicaciones técnicas extensas.

El contenido visible para usuarios, mensajes de ayuda y documentación debe mantenerse en español.
