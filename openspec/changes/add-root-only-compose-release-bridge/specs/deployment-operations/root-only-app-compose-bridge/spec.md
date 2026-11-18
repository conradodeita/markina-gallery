# Spec Delta

## Purpose

Permite inventariar e operar API/web quando a configuração Compose ativa está em snapshots protegidos do host, sem expor esses arquivos nem perder sua proveniência e recuperação.

## ADDED Requirements

### Requirement: Interface root-only é fixa e restrita
A ponte SHALL exigir UID/GID root e aceitar somente operações, serviços, SHA completo e fingerprints previstos. MUST NOT aceitar shell, caminho de arquivo, comando Docker/Compose arbitrário, stdin operacional ou mutação de serviço fora de `api` e `web`. `nginx` pode ser consultado por ID e receber somente `nginx -t` e `nginx -s reload` do fluxo existente.

#### Scenario: Chamada arbitrária ou sem root
- **WHEN** a chamada contém modo, serviço, argumento ou identidade não permitidos, ou não é executada como root
- **THEN** a ponte recusa antes de ler snapshots, consultar Docker ou alterar estado

#### Scenario: Compose root limitado
- **WHEN** a operação pede build, recreate, start, stop ou exec em serviço/comando fora da tabela fixa
- **THEN** a ponte recusa sem executar Docker Compose

### Requirement: Snapshots Compose preservam proveniência e sigilo
A ponte SHALL obter os caminhos somente dos labels dos containers ativos, limitá-los às raízes persistentes aprovadas e validar arquivo regular, ausência de symlink, proteção de escrita e hash. SHALL ler snapshots sem alterá-los e MUST NOT imprimir seu conteúdo, configuração resolvida, variáveis secretas ou tokens.

#### Scenario: Snapshot inseguro ou divergente
- **WHEN** um caminho escapa das raízes aprovadas, o arquivo ou seus metadados são inseguros, ou o hash muda durante a operação
- **THEN** a operação falha fechada antes de build, troca de imagem ou recriação

### Requirement: Inventário privilegiado é somente leitura e minimizado
A operação de inventário SHALL comprovar uma API e um web, fontes próprias por serviço, imagens, saúde, versão, schema, domínio e portas. O fingerprint SHALL vincular SHA alvo, hashes das fontes, digest semântico e recuperação. A saída SHALL conter apenas campos permitidos; inventário MUST NOT alterar arquivos persistentes, imagens ou containers.

#### Scenario: Cópia temporária privada
- **WHEN** a resolução exige cópias temporárias das fontes e ambiente
- **THEN** elas são verificadas e removidas na saída, sem persistir configuração ou revelar seu conteúdo

#### Scenario: Inventário completo
- **WHEN** os snapshots reproduzem os hashes dos containers e os gates de escopo, versão, saúde, schema e configuração passam
- **THEN** o inventário publica um resumo minimizado e fingerprint reproduzível

#### Scenario: Inventário incompleto
- **WHEN** API/web estão ausentes ou duplicados, Compose não reproduz o label, ou qualquer pré-condição diverge
- **THEN** nenhum fingerprint aprovável é emitido e nenhum estado de produção é alterado

### Requirement: Release root-only exige aprovação vinculada e preserva runtime
A operação mutável SHALL exigir workflow protegido `production`, lock exclusivo e fingerprint idêntico ao inventário recém-calculado. Antes de trocar serviços, SHALL preservar imagens e cópias verificadas dos snapshots originais em estado root-only. O release MUST recriar somente API/web, manter `APP_ENV=production` e `FACIAL_PROCESSING_ENABLED=true` e preservar schema, `.env`, dados, workers e demais serviços.

#### Scenario: Aprovação idêntica
- **WHEN** CI, escopo, lock, SHA e fingerprint correspondem ao inventário aprovado
- **THEN** somente API/web podem ser publicados e snapshots originais permanecem recuperáveis

#### Scenario: Fingerprint ou lock divergente
- **WHEN** estado Compose muda após inventário ou o lock está indisponível
- **THEN** o release aborta antes de build, troca de imagem ou container

### Requirement: Ausência de label exige prova semântica por serviço
Sem `config-hash`, a ponte SHALL comprovar equivalência efetiva entre snapshot e container. MUST NOT sintetizar label nem recriar container só para acrescentar metadados. Divergência ou campo sem contrato de comparação SHALL bloquear fingerprint aprovável.

#### Scenario: Snapshot sem label de hash
- **WHEN** um container API/web não possui o label `config-hash`
- **THEN** comparar ambiente incluindo defaults da imagem, comando/entrypoint, usuário, diretório, healthcheck, labels de aplicação, mounts, redes e políticas Docker com o snapshot do próprio serviço
- **AND** somente o digest da comparação pode sair do processo privilegiado

### Requirement: Rollback é inventariado, aprovado e limitado
O rollback SHALL exigir inventário somente-leitura e aprovação protegida próprios, validar hashes dos snapshots e IDs das imagens preservadas e restaurar somente API/web. Falha de release MUST NOT iniciar rollback automático.

#### Scenario: Rollback aprovado
- **WHEN** o fingerprint recém-inventariado corresponde à aprovação e todos os artefatos de recuperação passam
- **THEN** a ponte restaura API/web com os snapshots e imagens anteriores e valida saúde e endpoints

#### Scenario: Artefato de recuperação inválido
- **WHEN** snapshot, imagem, recibo ou fingerprint diverge
- **THEN** o rollback recusa antes de alterar containers e mantém o diagnóstico minimizado
