## Context

A autenticação unificada possui migration Alembic, variáveis documentadas e testes locais. O servidor de homologação poderá hospedar outros projetos, portanto nenhuma ação externa está autorizada antes de um inventário e de aprovação explícita do proprietário.

## Goals / Non-Goals

**Goals:**

- Produzir um plano executável, auditável e de impacto zero para homologar a autenticação.
- Definir os gates de inventário, segredos, migration, smoke test e rollback.
- Separar por completo dados e integrações de homologação e produção.

**Non-Goals:**

- Fazer deploy, criar recursos em servidor, alterar DNS, proxy, firewall ou certificados.
- Configurar WhatsApp real, SMTP ou credenciais reais.
- Promover a autenticação diretamente para produção.

## Decisions

### Decisão: inventário antes de qualquer mutação

O primeiro passo de aplicação será exclusivamente leitura: containers, Compose, redes, volumes, serviços e portas. O inventário define os dados que serão apresentados para aprovação; não serão assumidos porta, subdomínio ou proxy disponíveis.

### Decisão: homologação isolada por projeto e ambiente

Todos os recursos usarão o projeto Compose `markina-gallery`, arquivos de ambiente externos ao Git e serviços exclusivos. Essa separação reduz o risco de colisão com aplicações existentes e evita reutilizar banco, Redis ou segredos de produção.

### Decisão: entrada privada pelo Proxy Manager sem usar a rede do ClearBudget

O Proxy Manager executa em container e não alcança `127.0.0.1` do host. A Markina manterá a porta de diagnóstico limitada ao loopback e conectará somente seu serviço `nginx` à rede externa existente `npm-network`, usando o alias exclusivo `markina-homolog-nginx`. O Proxy Manager receberá apenas um host novo para `markina-homolog.duckdns.org`, encaminhado para esse alias na porta `80`, com certificado próprio. Nenhum container da Markina será conectado a `clearbudget_default`, e nenhum serviço, host, rede, volume ou configuração existente será alterado, reiniciado ou removido.

### Decisão: migration explícita e reversível

A migration Alembic será executada como operação deliberada antes do início da API. A versão anterior saudável e o backup serão confirmados antes de qualquer upgrade, para permitir rollback do projeto sem executar comandos globais de Docker.

## Risks / Trade-offs

- [Servidor sem porta ou subdomínio disponível] → interromper após o inventário e solicitar uma escolha do proprietário.
- [Segredo real não fornecido] → manter o ambiente não publicável; nunca usar valores de exemplo.
- [Falha de migration ou smoke test] → não expor tráfego externo e retornar a versão anterior da Markina Gallery.
- [Adaptador WhatsApp ainda sandbox] → homologar o restante do fluxo e registrar que o envio real requer mudança/aprovação de integração separada.
- [Proxy compartilhado] → criar somente um host novo, após backup e aprovação explícita; se o alias não responder, interromper sem mudar hosts existentes ou expor porta pública.

## Migration Plan

1. Coletar inventário somente-leitura e apresentar plano de impacto zero.
2. Após aprovação, preparar diretório, variáveis e recursos isolados de homologação.
3. Construir a versão do commit aprovado, realizar backup e aplicar `alembic upgrade head`.
4. Subir exclusivamente o Compose `markina-gallery`, executar healthchecks e smoke tests.
5. Em falha, parar/retornar apenas os serviços da Markina Gallery conforme o checklist; nunca usar prune ou comandos globais.

## Open Questions

- Qual servidor, subdomínio e porta o proprietário disponibilizará para homologação? Esta informação será coletada antes da aplicação e pode bloquear o plano sem alterar seus critérios de segurança.
