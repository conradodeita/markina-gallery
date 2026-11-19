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
A ponte SHALL obter as fontes dos labels ativos ou de base privada adotada por operação protegida explícita e vinculada ao runtime exato. MUST NOT aceitar caminhos arbitrários do chamador nem adotar automaticamente um snapshot divergente. SHALL limitar fontes às raízes aprovadas, validar tipo, links, modo e hash, ler sem alterar originais e não imprimir conteúdo ou segredos.

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

### Requirement: Árvore deploy-state permanece privada
Para fontes sob `deploy-state`, cada diretório e arquivo SHALL pertencer a `root` ou ao proprietário do checkout e não conceder permissões a grupo/outros. O arquivo SHALL ser legível pelo proprietário e não executável. Antes de mutação, a ponte SHALL copiar as fontes verificadas para estado privado `root:root` e MUST NOT alterar as originais.

#### Scenario: Snapshot privado pertence ao proprietário autorizado
- **WHEN** a árvore e seus snapshots pertencem a `root` ou ao proprietário do checkout, sem permissões para grupo/outros
- **THEN** a ponte verifica e resolve a fonte sem alterá-la
- **AND** cópias persistentes de recuperação permanecem `root:root` com acesso root-only

#### Scenario: Snapshot tem owner ou modo fora da allowlist
- **WHEN** um arquivo ou diretório da árvore pertence a outro owner ou concede permissões a grupo/outros
- **THEN** a ponte bloqueia o fingerprint e qualquer mutação antes de build ou recriação

### Requirement: Ausência de label exige prova semântica por serviço
Sem `config-hash`, a ponte SHALL comprovar equivalência efetiva entre a fonte selecionada e o container. A fonte SHALL ser o snapshot dos labels ou uma base explicitamente adotada conforme os requisitos abaixo. MUST NOT sintetizar label nem recriar container só para acrescentar metadados. Divergência ou campo sem contrato de comparação SHALL bloquear fingerprint aprovável.

#### Scenario: Snapshot sem label de hash
- **WHEN** um container API/web não possui o label `config-hash`
- **THEN** comparar ambiente incluindo defaults da imagem, comando/entrypoint, usuário, diretório, healthcheck, labels de aplicação, mounts, redes e políticas Docker com o snapshot do próprio serviço
- **AND** somente o digest da comparação pode sair do processo privilegiado

### Requirement: Adoção separa proveniência histórica de reprodução do runtime
Quando fontes históricas divergem, o diagnóstico SHALL preservar e identificar essa divergência. A preparação SHALL traduzir somente campos com contrato explícito do runtime API/web e das imagens fixadas por ID, resolver o modelo com Compose e comparar de forma independente com Docker inspect. SHALL preservar ambiente completo incluindo TOTP, comandos, usuário, mounts, redes e políticas.

#### Scenario: Fonte antiga diverge mas modelo ativo é reproduzível
- **WHEN** o diagnóstico comprova divergência das fontes históricas e o modelo candidato reproduz integralmente ambos os containers
- **THEN** ele pode emitir somente um fingerprint de adoção, distinto do fingerprint de release
- **AND** os snapshots antigos continuam identificados como históricos divergentes, sem alteração ou equivalência fabricada

#### Scenario: Configuração não é reproduzível
- **WHEN** há campo sem contrato, diferença de ambiente, comando, usuário, mount, rede, política ou imagem, ou falta prova independente
- **THEN** a preparação recusa fingerprint de adoção e de release e não persiste uma base ativa

### Requirement: Prova de adoção não altera o runtime
A prova de adoção MUST NOT editar `.env`, gerar/rotacionar credenciais, alterar labels ou executar build, load, tag ou recriação. Cópias temporárias SHALL permanecer privadas e ser removidas ao sair, sem persistir uma base.

#### Scenario: Diagnóstico termina com sucesso ou falha
- **WHEN** a preparação encerra por prova completa ou por qualquer recusa
- **THEN** containers, imagens, configuração persistente e credenciais permanecem intactos e as cópias temporárias são removidas

### Requirement: Políticas Docker da base adotada têm contratos explícitos
A tradução e a prova SHALL tratar `tmpfs` e namespace de cgroup explicitamente, preservando opções e semântica representáveis pelo Compose usado no host. MUST NOT descartar opções desconhecidas ou aceitar HostConfig opaco. Opções não suportadas SHALL bloquear antes de qualquer adoção persistente ou recriação.

#### Scenario: Política representável
- **WHEN** tmpfs ou namespace de cgroup têm opções suportadas e o modelo resolvido reproduz sua semântica
- **THEN** a comparação pode aprovar esse campo, mantendo as demais verificações independentes

#### Scenario: Opção perdida ou desconhecida
- **WHEN** a tradução perde uma opção, muda a semântica ou encontra opção não suportada
- **THEN** a prova falha e não declara compatibilidade por valor default presumido

### Requirement: Base privada exige adoção protegida vinculada ao estado exato
A persistência SHALL exigir revisão/CI do SHA suportado, aprovação protegida `production`, lock comum e fingerprint de adoção recém-recalculado idêntico ao aprovado. O fingerprint SHALL vincular SHA de suporte, IDs dos containers e imagens, modelos, identidades semânticas, fontes históricas, revisão e gates de saúde/schema/configuração facial.

#### Scenario: Adoção aprovada e estável
- **WHEN** a prova completa passa novamente sob lock e corresponde ao fingerprint de adoção aprovado
- **THEN** a ponte persiste modelos e manifesto de proveniência verificados, preserva fontes antigas e ativa o registro root-owned atomicamente
- **AND** não publica a aplicação nem considera aprovado o release subsequente

#### Scenario: Estado muda ou escrita fica incompleta
- **WHEN** um container, imagem, fonte ou configuração muda, falta aprovação/lock, ou falha a persistência/verificação
- **THEN** a operação não ativa a nova base nem substitui o registro anterior e mantém diagnóstico minimizado

### Requirement: Base adotada preserva sigilo e estado operacional
A base e cópias históricas SHALL ser imutáveis em raiz fixa `root:root`, diretórios `0700` e arquivos `0600`; conteúdo privado MUST NOT sair do host. A operação SHALL preservar containers, imagens, serviços vizinhos, `.env` e valores de credenciais.

#### Scenario: Base privada é persistida
- **WHEN** a operação aprovada grava e verifica os modelos e fontes de recuperação
- **THEN** somente o estado privado da ponte é acrescido, sem mudança dos serviços, credenciais ou originais e sem conteúdo privado nos logs/artifacts

### Requirement: Registro de base permanece verificável durante release e rollback
O inventário SHALL selecionar base adotada somente por registro root-owned em localização fixa e validar metadados, hashes, IDs e identidade semântica a cada uso. Base selecionada inválida SHALL falhar sem fallback silencioso. Ausência de registro SHALL manter o fluxo original por labels. Release e rollback SHALL preservar fontes/identidades anteriores e vincular o novo estado somente após prova e saúde, sem reaproveitar aprovação de adoção como aprovação de deploy.

#### Scenario: Base adulterada ou obsoleta
- **WHEN** manifesto, modelo, registro, permissão, container ou imagem diverge da identidade adotada
- **THEN** o inventário bloqueia fingerprint aprovável e não escolhe outra fonte automaticamente

#### Scenario: Publicação ou recuperação troca containers
- **WHEN** release ou rollback separadamente aprovado conclui a troca e comprova o estado saudável
- **THEN** o registro passa a vincular os IDs/fontes verificados desse estado e preserva os anteriores para recuperação
- **AND** falha parcial permanece bloqueada para recuperação explícita, sem declarar publicação saudável

### Requirement: Recuperação parcial usa somente a transição preservada
Antes de recriação, a ponte SHALL preservar registro root-only da transição com SHA, aprovação, manifesto anterior, modelos candidatos e hashes. Somente `rollback-inventory`/`rollback`, com marcador interrompido do mesmo SHA, SHALL poder comprovar a combinação de estados anteriores/candidatos. Cada serviço SHALL corresponder integralmente a um modelo e imagem preservados. Inventário normal MUST NOT usar essa exceção.

#### Scenario: API candidata e web anterior após interrupção
- **WHEN** a base está obsoleta pela troca parcial e os dois serviços correspondem aos modelos/imagens da transição preservada
- **THEN** o inventário explícito identifica recuperação, vincula IDs atuais e prova da transição ao novo fingerprint e aguarda aprovação própria antes de rollback

#### Scenario: Transição inválida ou runtime não pertence à operação
- **WHEN** falta marcador, SHA, hash, modelo ou serviço, ou a imagem/configuração não corresponde a estado anterior nem candidato
- **THEN** a recuperação recusa fingerprint e mutação, sem adotar estado arbitrário nem alterar a base

### Requirement: Allowlist Git limita a origem do instalador
O instalador SHALL aceitar somente as formas HTTPS e SSH exatas documentadas nos cenários. Origem divergente SHALL ser recusada antes de qualquer escrita privilegiada.

#### Scenario: Origem HTTPS ou SSH URI exata
- **WHEN** `origin` é `https://github.com/conradodeita/markina-gallery.git` ou `ssh://github.com/conradodeita/markina-gallery.git` e `origin/main` corresponde ao SHA suportado
- **THEN** o instalador continua as verificações fixas de checkout, lock, backup e invariância

#### Scenario: Forma SCP exata do OpenSSH
- **WHEN** `origin` é `git@github.com:conradodeita/markina-gallery.git` e `origin/main` corresponde ao SHA suportado
- **THEN** o instalador reconhece o mesmo repositório sem alterar `origin`

#### Scenario: Origem divergente
- **WHEN** `origin` contém outro host, caminho, protocolo, usuário ou credenciais
- **THEN** o instalador recusa antes de qualquer escrita privilegiada e preserva a configuração do host

### Requirement: Instalador preserva a origem e exige revisão suportada
O instalador SHALL validar que `origin/main` corresponde ao SHA suportado e MUST NOT reescrever a configuração Git do host.

#### Scenario: Revisão principal suportada
- **WHEN** `origin/main` corresponde ao SHA completo suportado
- **THEN** o instalador mantém a origem configurada e continua para as demais verificações

#### Scenario: Revisão principal divergente
- **WHEN** `origin/main` não corresponde ao SHA suportado
- **THEN** o instalador recusa antes de qualquer escrita privilegiada

### Requirement: Rollback é inventariado, aprovado e limitado
O rollback SHALL exigir inventário somente-leitura e aprovação protegida próprios, validar hashes dos snapshots e IDs das imagens preservadas e restaurar somente API/web. Falha de release MUST NOT iniciar rollback automático.

#### Scenario: Rollback aprovado
- **WHEN** o fingerprint recém-inventariado corresponde à aprovação e todos os artefatos de recuperação passam
- **THEN** a ponte restaura API/web com os snapshots e imagens anteriores e valida saúde e endpoints

#### Scenario: Artefato de recuperação inválido
- **WHEN** snapshot, imagem, recibo ou fingerprint diverge
- **THEN** o rollback recusa antes de alterar containers e mantém o diagnóstico minimizado
