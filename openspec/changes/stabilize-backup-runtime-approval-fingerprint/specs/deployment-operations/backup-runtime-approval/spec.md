# Spec Delta

> **Registro histórico — contrato de runtime aposentado em 25/11/2026.** Os requisitos abaixo descrevem a fingerprint do runtime global removido pela PR #436 (`eff4d504`); não são contrato para reimplementação. A retirada remanescente está em `retire-platform-backup-runtime`, e a nova prova está em `prove-open-source-backup-and-recovery`. Preserve a fingerprint genérica independente que ainda é usada pelos workflows de suporte compartilhados.

## Purpose

Define como uma aprovação humana de instalação do runtime de backup permanece vinculada ao host e ao estado operacional pretendidos, enquanto precondições voláteis de espaço são reavaliadas no momento da operação protegida.

## ADDED Requirements

### Requirement: Fingerprint de aprovação estável do runtime

A instalação protegida SHALL vincular a aprovação a uma fingerprint versionada que represente identidade do host, serviços/containers e estado operacional relevante, schema, bindings opacos de configuração e identidade/capacidade total dos filesystems fixos medidos. O vínculo da conexão autorizada, SHA/CI e hash do pacote SHALL ser verificado separadamente no mesmo fluxo; a fingerprint MUST NOT incluir leituras voláteis de espaço usado ou disponível.

#### Scenario: Capacidade varia sem mudança de identidade
- **WHEN** a nova coleta mantém todos os campos vinculados iguais e somente os bytes usados/livres ou a porcentagem de uso do filesystem variam
- **THEN** a fingerprint estável SHALL continuar igual, e a operação SHALL seguir sujeita às precondições atuais de capacidade

#### Scenario: Identidade operacional muda
- **WHEN** host, a conexão protegida revalidada, SHA/CI, pacote, container, schema, configuração protegida, filesystem de destino ou estado operacional relevante divergir da aprovação
- **THEN** o fluxo MUST abortar antes de transferir o pacote ou iniciar qualquer escrita persistente dos arquivos de instalação no host

#### Scenario: Aprovação antiga ou formato desconhecido
- **WHEN** a operação recebe fingerprint integral legada, versão desconhecida, valor inválido ou aprovação sem correspondência ao contrato versionado atual
- **THEN** o fluxo MUST abortar e exigir novo inventário e aprovação, sem reinterpretar ou converter a aprovação antiga

### Requirement: Capacidade atual bloqueia instalação sem margem segura

A operação de instalação SHALL validar capacidade dos filesystems de destino antes da primeira escrita persistente e imediatamente antes da troca ativa, sob o lock comum; cada filesystem MUST permanecer abaixo do limite operacional de 75% de uso e dispor da margem calculada para staging, instalação e preservação do runtime anterior.

#### Scenario: Capacidade suficiente na coleta e na mutação
- **WHEN** cada leitura atual confirma uso inferior a 75%, espaço livre suficiente conforme o pacote verificado e cópias/rollback preservados, e as demais precondições passam
- **THEN** a operação pode avançar com a fingerprint estável aprovada

#### Scenario: Espaço insuficiente ou não verificável
- **WHEN** algum filesystem ultrapassa o limite, não comporta o staging/instalação/rollback estimados, não pode ser medido ou muda para condição insegura antes da troca ativa
- **THEN** a operação MUST abortar antes da próxima escrita ou troca, preservar os artefatos anteriores e emitir somente diagnóstico sanitizado

#### Scenario: Expansão do pacote excede o bound suportado
- **WHEN** os wheels são inválidos, falham na leitura/CRC, ou a expansão descomprimida agregada excede 8 GiB
- **THEN** a operação MUST abortar antes da primeira escrita persistente de instalação e emitir somente diagnóstico sanitizado

### Requirement: Inventário distingue aprovação de capacidade corrente

O inventário SHALL apresentar separadamente a fingerprint estável de aprovação e as leituras atuais de capacidade de `/var/lib`, `/opt/pyp-backup-runtime` e `/etc/systemd/system`, sem expor identidade de containers, device/mountpoint, segredos ou metadados brutos.

#### Scenario: Revisão humana do inventário
- **WHEN** o inventário read-only termina com sucesso
- **THEN** o operador recebe a fingerprint versionada, bytes totais/usados/livres e percentual atual por filesystem de destino, além do resultado das precondições, com saída sanitizada

#### Scenario: Precondições revalidadas mudam
- **WHEN** a fingerprint estável permanece igual mas capacidade ou outra precondição operacional deixa de passar no preflight final ou sob lock
- **THEN** a etapa mutável MUST ser bloqueada, sem tratar a aprovação estável como autorização para ignorar a condição corrente
