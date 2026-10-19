# External dependency monitoring Specification

## ADDED Requirements

### Requirement: Monitoramento de imagens Docker e Docker Compose

O projeto SHALL monitorar imagens declaradas em Dockerfiles de `/backend` e `/frontend` pelo ecossistema Docker e imagens declaradas no Compose base e overlays de `/docker` pelo ecossistema Docker Compose. A configuração MUST apontar cada ecossistema ao diretório que contém seus manifests, conservar um limite de um PR ordinário por entrada e MUST NOT habilitar automerge.

#### Scenario: Dependabot verifica Compose e overlays

- **WHEN** Dependabot processa a entrada de `/docker`
- **THEN** SHALL localizar o manifesto base e todos os overlays Compose suportados presentes no diretório, sem falhar por ausência de Dockerfile ou manifesto Kubernetes

#### Scenario: Dockerfiles seguem monitorados

- **WHEN** Dependabot verifica imagens dos runtimes backend e frontend
- **THEN** SHALL continuar usando o ecossistema Docker nas entradas `/backend` e `/frontend`

#### Scenario: Verificação não integra atualizações

- **WHEN** Dependabot detecta uma versão elegível em qualquer manifesto Compose
- **THEN** SHALL propor uma PR ordinária sujeita ao limite e à revisão humana; MUST NOT integrar automaticamente a atualização
