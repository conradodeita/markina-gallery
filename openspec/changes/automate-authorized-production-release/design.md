# Design

## Context

O CI da PR #300 dividiu o backend, mas o workflow manual ainda roda toda a matriz por despacho. O fluxo 0090 usa prévia somente leitura, fingerprint exato, aprovação de ambiente e recolhe o inventário sob lock. Uma mudança na main invalida o SHA de suporte durante esse release.

## Goals / Non-Goals

**Goals:** evitar repetição da mesma CI e pedidos redundantes de autorização em operações já autorizadas, sem dispensar evidência ou revalidação.

**Non-Goals:** autorizar operações futuras fora do escopo solicitado, enfraquecer proteção de ambiente, ignorar falhas, apagar recursos, alterar terceiros, fazer downgrade automático ou substituir inventário atual por evidência antiga.

## Decisions

- O verificador read-only seleciona o run mais recente do workflow CI, evento push na main e SHA exato de suporte; exige conclusão success e sucesso dos jobs obrigatórios aplicáveis, inclusive agregador. Rejeita ausência, paginação incompleta, tentativa mais recente falha/pendente, jobs ausentes/skipped, SHA divergente e falhas de API. O candidato de produto mantém seu próprio gate de CI, distinto do SHA de suporte.
- Integração ao workflow manual separado `preview-migration-0090-authorized.yml` é limitada ao wrapper, preflight e release 0090. Push e PR continuam com validações completas ou classificadas como hoje; preservar nomes dos checks e todos os gates existentes. A credencial GitHub terá somente `actions: read` e `contents: read`. As etapas de instalação, inventário e release são iguais às do workflow revisado; o checkbox `authorization_confirmed` expressa autorização vigente, e `production` continua exigindo revisão independente. Um executor autorizado pode efetivar essa revisão em nome do proprietário, sem criar nova permissão para outras operações.
- O inventário é apresentado antes da etapa mutável e seu fingerprint passa automaticamente para a operação seguinte quando a autorização vigente cobre exatamente o ambiente, escopo e impacto apresentado. O executor recolhe e compara o fingerprint sob lock antes da mutação, falhando se houver mudança. O environment production permanece habilitado; a aprovação pode ser exercida pela conta autorizada, sem novo pedido de autorização em cada etapa já abrangida.
- SHA de suporte e CI são fixados até terminar a execução; uma alteração da main ou resultado mais recente não verde interrompe. Os relatórios identificam origem, SHA, run, fingerprint e ações. Uma falha após DDL requer diagnóstico; não restaurar dados nem fazer downgrade automaticamente.
- A execução 0090 atual mantém seu procedimento e gate existentes até sua conclusão ou bloqueio reconciliado. O protótipo local e testes podem avançar, mas nenhum merge que mude a main interromperá o inventário pendente.

## Risks / Trade-offs

- [Run reexecutado ou check omitido] → selecionar a tentativa mais recente e verificar conclusão dos jobs por nome.
- [Estado muda entre consulta e deploy] → fingerprint fresco sob lock, SHA de main atual e recusa antes da mutação.
- [Interpretação de autorização] → escopo explícito, ambiente e impacto apresentados; não ampliar a operações ou terceiros não autorizados.
- [Alinhamento com main em release] → PR e integração somente depois da reconciliação do fluxo em andamento.
