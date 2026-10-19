# Design

## Context

O repositório usa OpenSpec `spec-driven`, `AGENTS.md` na raiz e configuração com contexto e orientação de apply. O CLI instalado é 1.14.1; o CI fixa 1.14.0. A autorização permite apenas instruções/documentação, sem executar a manutenção do código agora. Ver motivação em `proposal.md`.

## Goals / Non-Goals

**Goals:** uma fonte permanente, aplicação no fluxo OpenSpec e fora dele, e verificação proporcional com resultado sem remoções válido.

**Non-Goals:** automação de exclusões, auditoria geral, refatoração funcional, alteração dos gates existentes ou atualização de ferramentas/workflows.

## Decisions

1. `docs/CONTINUOUS-REFACTORING.md` será a fonte da política; `AGENTS.md` SHALL exigir sua leitura/aplicação em qualquer implementação. Referências curtas evitam copiar blocos sujeitos a divergência.
2. Usar somente campos suportados: `context` para alcance permanente, `rules.proposal` para impacto no código existente, `rules.tasks` para verificação rastreável e `operations.apply.guidance` para implementação e fechamento. Não inventar `rules.verify`: a revisão final integra tasks/apply.
3. Confirmar parsing e saída efetiva de instructions em 1.14.1 e 1.14.0. Essas instruções orientam executores; não são uma análise estática ou gate automático que prove ausência de código morto.
4. Preservar integralmente as convenções existentes. A manutenção SHALL respeitar contratos, compatibilidade, tenants e autorizações de áreas sensíveis. Uma oportunidade arriscada é registrada separadamente; sem oportunidade segura, nenhuma remoção é exigida.
5. `skip_specs: true` segue o precedente de tooling do repositório: nenhum requisito de produto muda. Não sincronizar/arquivar specs funcionais nem criar capacidades artificiais para esta política.

## Risks / Trade-offs

- Avaliação virar auditoria geral → limitar componentes e consumidores diretamente relacionados, sem quota de remoções ou varredura ampla obrigatória.
- Remoção inferida de busca textual vazia → exigir referências dinâmicas, integrações, scripts, testes, histórico e contratos; incerteza preserva o código.
- Instruções divergirem → política única e referências curtas, sem alterar as prioridades de segurança vigentes.
- Promessa de execução automática rígida → explicitar que o CLI injeta orientações e o executor as aplica/valida; não há robô de exclusão nem mudança em runtime.

## Migration Plan

Publicar somente documentos/configuração por PR em main. Integrar apenas com checks/revisões/proteções satisfeitos e classificador sem operações remotas. A política vale para próximas implementações; não dispara refatoração retroativa ou operação de ambiente. Uma eventual reversão documental requer fluxo Git normal, sem force push.
