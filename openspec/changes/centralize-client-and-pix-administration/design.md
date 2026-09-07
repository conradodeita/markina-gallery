## Context

Veja `proposal.md` — Why. O backend já expõe criação, busca, edição de nome, troca verificada de telefone e exclusão de clientes, mas a única interface está embutida no editor da galeria. O inventário atual considera qualquer referência um bloqueio, por isso uma cliente sintética com registro, associação e privada sem pedido não pode ser apagada. `PixCheckoutSettings` pertence hoje à Galeria pública, enquanto `SaleOrder` já conserva snapshots PIX; o módulo de segurança administrativo já possui desafios cifrados, reautenticação e entrega de OTP pelo WhatsApp.

## Goals / Non-Goals

**Goals:**

- Reutilizar a identidade canônica e os controles existentes em uma superfície global, sem manter duas implementações divergentes de cliente.
- Tornar removível todo o estado sem valor histórico de uma cliente, com resultado imediato, atômico, idempotente e isolado.
- Introduzir um PIX global versionado, confirmar alterações pelo canal administrativo e preservar pedidos por snapshot.
- Migrar de modo aditivo e fail closed quando os dados PIX legados divergirem.

**Non-Goals:**

- Apagar, reatribuir ou mesclar histórico comercial entre clientes.
- Alterar tabelas globais de preço, regras de galeria, confirmação manual de pagamento ou integrar um provedor financeiro.
- Armazenar chave PIX, OTP ou telefone em auditoria, ou enfraquecer a verificação de troca do telefone da cliente.
- Limpar o cliente sintético de homologação durante a implementação; qualquer operação real dependerá de deploy e confirmação posteriores.

## Decisions

### 1. Diretório global reutiliza os contratos canônicos

A rota visual `/admin/clients` consumirá uma listagem administrativa paginada com busca e agregados em lote: quantidade de Galerias públicas, privadas, pedidos e estado de exclusão. O formulário e diálogo de edição hoje embutidos no editor serão extraídos para componentes compartilhados. A etapa 05 continuará listando todas as clientes retornadas e apenas acrescentará `Já vinculada`, `Vincular`, `Desvincular` e ações da privada.

Alternativa descartada: criar uma segunda API ou uma tabela de contatos separada. Isso permitiria divergência de telefone, duplicação e comportamento diferente entre o diretório e a galeria.

### 2. Dependências são classificadas, não tratadas igualmente

O inventário separará `operational_removable` de `commercial_protected`. A primeira classe inclui sessões, desafios e entregas transitórias, capabilities, registros públicos, memberships, favoritas, comentários, visualizações, seleções sem pedido e buscas/referências faciais transitórias. A segunda inclui pedidos, itens, comunicações de pagamento, pagamentos, entregas e snapshots necessários ao histórico.

Com zero dependências protegidas, a confirmação executará deletes set-based em uma única transação após bloquear a identidade. Privadas sem outro membro ou histórico serão removidas com suas referências; privadas compartilhadas permanecerão e perderão apenas o estado individual da cliente. Galerias públicas, pastas e JPEGs nunca pertencem à exclusão global da cliente. Qualquer corrida que introduza histórico protegido abortará e reclassificará o inventário.

Alternativa descartada: obrigar o fotógrafo a desvincular galeria por galeria. Isso repete o problema relatado e deixa estados transitórios difíceis de descobrir.

### 3. A exclusão é síncrona, mas possui recibo idempotente

Uma pequena tabela aditiva de recibos de lifecycle guardará chave idempotente, UUID alvo sem FK, ator, fingerprint do inventário, estado, contagens e timestamps. A chamada só retorna sucesso depois do commit, permitindo que o item desapareça imediatamente sem polling ou botão `Retomar`. Repetições devolvem o recibo; falhas fazem rollback integral e preservam a cliente.

Alternativa descartada: reutilizar `GalleryLifecycleOperation`. Ela exige uma Galeria pública e representa operações assíncronas sobre um único agregado, enquanto esta exclusão pode abranger várias origens e precisa de confirmação imediata.

### 4. PIX global é versionado por administrador

Será criada uma tabela global com UUID, singleton restrito a `1`, `admin_user_id` único, versão, tipo normalizado, chave/BR Code operacional, recebedor, cidade, instruções, estado `active|unconfigured|review_required` e timestamps UTC. A instalação MVP possui um fotógrafo; o backfill recusa inventário com múltiplos administradores em vez de escolher um proprietário. O checkout lerá somente a versão `active`; o pedido continuará armazenando copia-e-cola/instruções e acrescentará um snapshot JSON de UUID da configuração, versão, recebedor e cidade. O QR é derivado do BR Code congelado, nunca da configuração atual. `PixCheckoutSettings` e seus valores por galeria não serão removidos nesta change para permitir rollback e investigar divergências.

Alternativa descartada: escolher uma galeria como padrão ou manter override por galeria. A primeira escolha seria arbitrária; a segunda contraria a decisão de produto e manteria a duplicação.

### 5. Alteração PIX reutiliza o gate de segurança administrativo

O propósito dos desafios administrativos será ampliado com uma ação de PIX. O primeiro passo exige senha atual e vincula à sessão um fingerprint da configuração proposta, guardando o payload somente no envelope cifrado; o segundo confirma o OTP enviado ao WhatsApp administrativo pronto. A gravação incrementa a versão e audita apenas UUID, versão e resultado. Remover a configuração segue o mesmo fluxo.

Alternativa descartada: salvar diretamente por sessão autenticada. O roadmap classifica mudança de PIX como ação sensível e exige confirmação pelo WhatsApp validado.

### 6. A etapa 02 perde a escrita PIX e preserva o restante

O contrato de vendas passará a conter uma visão somente leitura do PIX global (`status`, `version`, recebedor, QR e instruções) e uma capability de checkout. O `PUT` da etapa rejeitará campos PIX novos e atualizará apenas preço, preset, mensagem, prazo, favoritas e comentários. Sem PIX ativo, salvar/avançar permanece possível, mas checkout é recusado sem perder seleção e a UI direciona para Configurações.

Alternativa descartada: impedir a criação ou edição da galeria inteira sem PIX. Isso acoplaria preparação do acervo a uma integração comercial corrigível posteriormente.

### 7. Backfill canônico e fail closed

A migration criará as estruturas e agrupará configurações legadas não vazias por BR Code canônico e instruções normalizadas. Zero grupos deixa `unconfigured`; um grupo cria a versão global; mais de um grupo ou qualquer registro inválido cria somente `review_required`, com contagem de grupos válidos, nunca elegendo um recebedor. Não se persistem novos fingerprints das chaves: a contagem e o estado são suficientes para orientar a revisão. Pedidos e snapshots existentes não serão recalculados. O downgrade remove apenas as estruturas novas e recusa executar se houver desafios PIX, preservando sua auditabilidade; nesse caso deve-se reverter somente a aplicação.

## Risks / Trade-offs

- [Cliente com muitas interações torna a exclusão síncrona lenta] → deletes set-based, índices de `client_id`, timeout explícito e teste de volume sintético; qualquer falha faz rollback.
- [Uma privada contém estado administrativo útil sem compra] → a confirmação apresenta inventário e consequência; privada compartilhada é preservada e a privada exclusiva é removida somente junto da cliente confirmada.
- [PIX legado divergente interrompe novos checkouts] → estado fail closed, aviso no dashboard/etapa 02 e seleção explícita em Configurações; pedidos existentes permanecem utilizáveis pelo snapshot.
- [Configuração PIX em claro é necessária para montar pagamento] → restringir leitura a admin/checkout autorizado, nunca logar valor e auditar somente fingerprints/versão; segredos de criptografia continuam fora do banco comum.
- [OTP administrativo indisponível impede corrigir PIX] → manter a versão ativa anterior e expor diagnóstico do canal; nenhuma alteração parcial é aplicada.

## Migration Plan

1. Adicionar configuração PIX global, snapshot complementar e novo propósito de desafio em `20260906_0046`, sem remover colunas ou registros existentes. O recibo de exclusão de clientes permanece em tarefa própria, fora da entrega PIX solicitada em 2026-09-06.
2. Executar backfill canônico do PIX e validar os estados `unconfigured`, `active` e `review_required` em banco limpo e banco com configurações iguais/divergentes.
3. Publicar backend compatível que ainda leia snapshots/pedidos antigos, depois a nova interface de Clientes, Configurações e etapa 02.
4. Verificar migração no head, autorização, auditoria, checkout antigo/novo e rollback em PostgreSQL descartável antes de qualquer deploy.
5. Em homologação autorizada, testar somente clientes e pagamentos sintéticos; excluir o contato sintético relatado apenas por uma confirmação humana posterior na nova interface.
6. Rollback da aplicação restaura a leitura por galeria porque os dados legados não foram removidos; antes de reabrir novos checkouts, conferir seus recebedores legados, que não acompanham alterações globais posteriores. O downgrade estrutural é recusado quando há desafios PIX ou snapshots globais em pedidos: ambos devem permanecer auditáveis. Sem esses dados, o downgrade conserva todos os registros e campos comerciais legados.

## Estado da entrega PIX — 2026-09-07

O recorte PIX desta change está implementado e publicado em homologação no SHA funcional `07aa6dffdcbeb70e3a0f7eba91cc66dfaa150961`, pelo run verde `34073819354` e deployment `6300430858`. A migration `20260906_0046` está no head remoto. O painel global em `Configurações`, a confirmação por senha e OTP administrativo, a leitura somente na etapa 02 e o snapshot imutável por pedido estão presentes; a configuração por galeria permanece apenas como legado preservado para compatibilidade e rollback, sem servir de origem para novos checkouts.

O inventário posterior confirmou zero clientes, galerias, fotos e pedidos após a limpeza autorizada, com administrador, configurações e pareamento WhatsApp preservados. `/healthz` e `/api/health` responderam HTTP 200. A paridade é funcional: o commit posterior `9bb077fb1de2b78c76d8674aee09cdcbeb473c34` contém somente evidências OpenSpec e não exige nova publicação da aplicação.

Esta confirmação não concluiu a change inteira naquele momento. Em 2026-09-07, o diretório global e o lifecycle de exclusão de clientes das seções 3 e 4 foram implementados localmente, com migration aditiva de recibo, integrações sintéticas, interface compartilhada com a etapa 05 e validação ampla. O SHA de homologação citado acima ainda contém apenas o recorte PIX; o lifecycle de clientes SHALL NOT ser considerado disponível remotamente antes de um novo deploy autorizado, da migration `20260907_0047` e da verificação humana prevista em 7.6.

As specs não devem ser sincronizadas nem a change arquivada antes desse aceite. A evidência histórica red/green estrita de todos os testes PIX em 1.3 também permanece não comprovada e não deve ser inferida das regressões atualmente verdes.
