# Design

## Context

O fluxo disponível, `add-production-web-release-workflow`, publica somente `web` e tem política própria de checkout limpo, SHA, inventário e aprovação. Esta change precisa acrescentar uma execução coordenada sem enfraquecer esses gates e sem usar recursos compartilhados de outros projetos. Ver `proposal.md` e `specs/deployment-operations/spec.md` para motivação e contrato observável.

O Docker Compose pode iniciar e recriar vários serviços numa execução, mas não fornece troca transacional de API e frontend. Os serviços podem ficar temporariamente em versões diferentes durante a atualização. A aplicação atual também depende dos serviços externos ao escopo, que não devem sofrer mutação.

## Goals / Non-Goals

**Goals:**

- Tornar auditável uma única tentativa contendo SHA-alvo, imagens anteriores e imagens-alvo de `api` e `web`, gates, verificações e resultado.
- Garantir que builds falhos ocorram antes de substituir os contêineres ativos.
- Serializar operações web-only e coordenadas no host para evitar releases concorrentes.
- Preservar a possibilidade de rollback para a imagem que cada serviço realmente usava antes, mesmo que as duas imagens anteriores tenham origens distintas.

**Non-Goals:**

- Garantir disponibilidade contínua ou compatibilidade de versões durante toda a troca.
- Alterar Compose, configuração, ambiente, schema ou dados de produção nesta change.
- Automatizar migrations, mudanças de proxy, DNS, firewall, certificados ou recursos de outros projetos.
- Substituir o fluxo web-only em alterações que não requerem API.

## Decisions

1. **Manter a identidade do release e os gates do fluxo existente.** Exigir SHA completo aprovado e alcançável por `origin/main`, checkout limpo, revisão e código de aprovação específico da tentativa. Fazer inventário remoto somente-leitura imediatamente antes da execução, conferindo projeto Compose, serviços, imagem/commit, configurações relevantes, domínio e portas documentadas. Não imprimir valores de segredo. O motivo é impedir publicação de estado local incompleto ou alvo diferente do revisado. Alternativa considerada: aprovar apenas um SHA sem inventário de host; rejeitada porque não comprova o escopo real do host.

   O fluxo exige um SHA-base confiável da API (`app-last-healthy.sha`) e um snapshot imutável das imagens reais dos dois serviços (`app-last-healthy.snapshot`). O marcador web-only existente não prova a origem da imagem da API; não é aceito como baseline da API. O snapshot representa os IDs de runtime efetivos e pode conter uma web-only mais recente que o SHA-base da API. Até que SHA e IDs sejam reconciliados por inventário e aprovados, o fluxo recusa o release.

   Para iniciar de forma verificável, `baseline-inventory` apresenta o estado sem gravações e `baseline` registra SHA/tag somente com código de aprovação recalculado. O proprietário precisa confirmar a origem do SHA da API usando evidência de build/deploy; sem essa evidência, o bootstrap é recusado. Esse passo não muda contêineres e não presume que um hash de configuração comprove a versão do código.

2. **Construir as duas imagens antes de recriar qualquer serviço.** Fixar e registrar os identificadores das imagens construídas para o mesmo SHA. Se um build falhar, encerrar antes da etapa de mutação. A alternativa de construir cada imagem ao atualizar seu serviço foi rejeitada porque poderia deixar o primeiro serviço atualizado e o segundo sem build.

3. **Preservar a imagem de runtime anterior por serviço.** Registrar os identificadores exatos em execução para `api` e `web` sob tags imutáveis por serviço em um snapshot pré-release próprio. Registrar as imagens compiladas em outro snapshot para o SHA alvo. O snapshot pré-release identifica o par real mesmo se uma publicação web-only tiver avançado a web desde o último release coordenado. Não inferir que os dois serviços anteriores vieram do mesmo SHA; não reconstruir imagens para rollback, pois a reconstrução pode não reproduzir os mesmos artefatos. A retenção das tags fica explícita e fora do caminho crítico do release.

4. **Adquirir lock compartilhado no host durante toda a mutação.** O script coordenado e o web-only devem usar o mesmo lock exclusivo do projeto, mantido desde a checagem final pré-mutação até a conclusão ou rollback. Se o host não puder garantir o lock ou identificar operação interrompida, falhar fechado e exigir reconciliação antes de nova execução. Alternativa de lock apenas local foi rejeitada por não serializar operadores ou sessões distintas.

5. **Atualizar somente `api` e `web`, de forma sequencial e registrada.** Usar comandos Compose explicitamente limitados a esses dois serviços, com o projeto e arquivo Compose confirmados no inventário. A API será substituída primeiro, seguida de sua healthcheck, depois web e suas verificações; a janela mista permanece possível. Se qualquer validação falhar, parar a promoção e apresentar o rollback conjunto, que requer aprovação específica. Não usar `compose down`, prune ou comandos globais. Alternativa de recriar todos os serviços foi rejeitada por exceder o escopo autorizado.

6. **Fechar o estado do release somente após validação conjunta.** Executar healthchecks de ambos os serviços e smoke checks HTTPS contra o domínio confirmado pelo inventário. Registrar SHA, imagens antes/depois, horários, comandos e resultados sem secrets. Em falha, manter tentativa como malsucedida e imagens de rollback até que o operador conclua uma restauração ou reconciliação. O procedimento web-only adquire o mesmo lock, mas mantém sua validação e mutação exclusiva de `web`.

7. **Recusar migration ou mudança de configuração de infraestrutura.** Se o diff do SHA aprovado contiver migrations ou mudanças de Compose/configuração de ambiente, não usar esta automação. Exigir change e plano separado com inventário, plano de impacto e aprovação próprios. Isso evita ampliar silenciosamente o blast radius.

## Risks / Trade-offs

- [Janela de incompatibilidade entre API e frontend durante a troca] → Atualizar API primeiro, validar e depois atualizar web; informar interrupção possível na aprovação; não declarar zero downtime.
- [Build da imagem resultar em configuração diferente da esperada] → Registrar SHA e identidade das imagens; conferir serviço/projeto e healthchecks antes de seguir.
- [Lock permanecer após interrupção do processo] → Usar lock liberado pelo sistema operacional quando a sessão termina; detectar estado de tentativa não finalizada e exigir reconciliação, sem remover lock ou contêiner por suposição.
- [Imagem de rollback removida ou disco insuficiente] → Verificar espaço e existência das imagens antes da mutação; não iniciar se não for possível preservar ambas; retenção posterior explícita e auditável.
- [Smoke check não cobrir fluxos autenticados] → Tratar smoke checks como saúde básica da implantação, sem afirmar que substituem validação funcional autenticada ou CI.
- [Scripts divergirem quanto aos gates ou escopo] → Compartilhar a política de lock e as validações comuns, revisar o web-only e testar ambos os caminhos; mudanças ficam cobertas por esta mesma change.
- [Ausência de histórico de versão conjunto da API e web] → Exigir reconciliação e aprovação humana do baseline antes de liberar; nunca inferir o SHA da API pelo histórico web-only.

## Migration Plan

1. Implementar e revisar a automação e runbook coordenados sem acesso de escrita ao servidor.
2. Validar localmente políticas de recusa, builds, lock, identidade dos artefatos, healthchecks, smoke checks e rollback, usando fixtures/mocks ou ambiente isolado.
3. Revisar se o procedimento web-only adquire o lock comum e continua restrito a `web`.
4. Antes do primeiro release coordenado, executar inventário de baseline, confirmar por evidência a origem do SHA-base da API e aprovar o registro dos IDs reais de ambos os serviços. Se a origem da API não puder ser comprovada, manter o fluxo bloqueado.
5. Antes de qualquer publicação real, obter aprovação humana após apresentar inventário remoto atualizado, SHA completo, domínio, portas, serviços e plano de impacto. A aprovação geral desta change não substitui o gate por execução definido no procedimento.
6. Em execução aprovada, construir os dois artefatos, registrar estado anterior, atualizar e validar os serviços; em falha, aguardar aprovação de rollback e restaurar ambos os identificadores anteriores.
7. Não executar migrations nem alterações de configuração/infraestrutura nesta sequência.

## Open Questions

Nenhuma questão em aberto altera o contrato ou a abordagem. Valores de inventário, nomes exatos de healthchecks e rotas HTTPS devem ser confirmados em modo somente-leitura durante a implementação e novamente antes de eventual execução; não são presumidos como estado atual de produção.
