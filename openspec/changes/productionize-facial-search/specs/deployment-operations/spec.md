## ADDED Requirements

### Requirement: Deploy preserva o estado facial autorizado do ambiente

O deploy SHALL detectar e validar o estado facial autorizado do ambiente antes de trocar código. Quando o recurso estiver desligado, o `face-worker` SHALL permanecer inativo; quando estiver persistentemente habilitado fora de uma janela temporária de benchmark, o deploy SHALL atualizar e reiniciar o `face-worker` com o mesmo gate, chaves, modelos e limites, verificar healthchecks e manter rollback isolado. Produção MUST permanecer desligada até a ativação protegida prevista na capability de runtime facial de produção.

#### Scenario: Upgrade com homologação facial persistente

- **WHEN** homologação está autorizada com `FACIAL_PROCESSING_ENABLED=true` e sem benchmark privado ativo
- **THEN** o deploy preserva a flag, atualiza API, worker de mídia e `face-worker`, confirma o mesmo estado efetivo nos processos e não exige trailer temporário de pausa/retomada

#### Scenario: Estado facial inconsistente

- **WHEN** a flag, o profile, as chaves, os modelos ou o estado efetivo dos processos divergem antes ou depois do deploy
- **THEN** a operação falha fechada, não amplia o rollout e restaura somente a versão saudável da Markina quando o rollback for comprovadamente seguro

#### Scenario: Alias explícito do ambiente de homologação

- **WHEN** o host identifica homologação como `APP_ENV=homologation` e as credenciais faciais correspondem exatamente a esse valor
- **THEN** o rollout canonicaliza somente esse alias para `homolog`, preserva tokens e registros operacionais estáveis e continua recusando ambiente ou credencial divergente

#### Scenario: Rótulo interno staging no host fixo de homologação

- **WHEN** o inventário do projeto, checkout, portas e subdomínio fixos de homologação comprova `APP_ENV=staging`
- **THEN** o operador protegido preserva `staging` como ambiente interno distinto, deriva a confirmação interna correspondente e mantém a autorização humana vinculada ao Environment `homolog`, sem criar alias global

### Requirement: Ferramentas de benchmark fora do caminho de produção

Scripts, tokens, manifestos, janelas e relatórios criados exclusivamente para o benchmark privado SHALL NOT controlar o runtime, o deploy comum ou a autorização de produção. A evidência agregada histórica MAY permanecer arquivada pelo prazo documentado, sem fotos, PII, vetores ou scores.

#### Scenario: Benchmark encerrado e higienizado

- **WHEN** a prova de limpeza do lote privado for concluída
- **THEN** os modos temporários deixam de participar dos workflows normais e sua remoção não altera o contrato de indexação, busca, retenção ou rollback do produto

### Requirement: Ativação e rollback zero-impact em produção

A ativação de produção SHALL exigir SHA integral aprovado, inventário imediatamente anterior, backup restrito, migrations aditivas, modelos verificados, gates humanos registrados, escopo inicial do rollout e confirmação explícita. A operação SHALL alterar somente recursos `markina-gallery`, manter PostgreSQL e Redis sem portas públicas, manter o `face-worker` sem porta e preservar proxy, firewall, DNS, certificados, containers, imagens, redes e volumes de terceiros.

#### Scenario: Ativação inicial aprovada

- **WHEN** o proprietário autoriza a etapa inicial de produção com todos os gates verdes
- **THEN** a operação habilita somente o escopo permitido, confirma migrations, containers, portas, healthchecks, métricas e rollback antes de receber consultas reais

#### Scenario: Rollback de produção

- **WHEN** o operador aciona rollback por falha funcional, segurança, privacidade ou capacidade
- **THEN** novas operações faciais param, referências temporárias são eliminadas, seleção manual permanece disponível e nenhum recurso externo à Markina é alterado
