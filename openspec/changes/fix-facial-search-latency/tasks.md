## 1. Diagnóstico e regressão

- [x] 1.1 Delimitar falha com inventário e estados sanitizados somente de leitura. Evidência: consulta real 376,77 s, índice completo, quatro claims, timeout e log de lease expirado; versão checkout/container conferida por SHA256, commit 3b15529.
- [x] 1.2 Registrar teste sintético de regressão para snapshot pontual, revogação e fingerprint, demonstrando falha antes da correção. Teste inicial com oito fotos falhou: 99 leituras de snapshot, contra orçamento máximo de quatro leituras integrais; resultado funcional permaneceu correto. Negativos de revogação/fingerprint serão completados na task 2.1.

## 2. Implementação

- [x] 2.1 Substituir recarga integral por verificação pontual do snapshot e renovar lease/progresso durante comparação; validar contratos e isolamento. Testes focados: 6 aprovados em 22,79 s, Ruff aprovado; oito fotos geram no máximo quatro leituras integrais. Negativos verificam foto indisponível, prévia falha, pasta oculta, índice falho e fingerprint divergente sem modificar o snapshot. Regressões region/tenant anteriores: 26 aprovados; precisam repetir com a paginação final.
- [x] 2.2 Limitar leitura/vetorização por lote e preservar ordenação/deduplicação; validar múltiplos lotes e volume. Nove regressões aprovadas em 94,91 s; teste sintético 2.691 fotos/10.531 rostos usou 83 páginas de até 128 rostos, 2.691 candidatas deduplicadas, progresso por foto e menos de 20 entidades ORM retidas. Comparação local isolada: 57,42 s; não inclui callback completo de autorização do worker nem representa latência Oracle.
- [x] 2.3 Condensar as consultas redundantes de revalidação sem cache de autorização; validar equivalência de gates, revogação/cancelamento durante a comparação e medir novamente. Engine/tenant/regressão: 30 aprovados; worker/região/regressão: 38 aprovados; cancelamento/lease/publicação: 12 regressões aprovadas; nove negativos adicionais de público/versão aprovados. Comparação isolada sintética passou de 57,42 s para 7,14–7,94 s no Windows, sem callback completo do worker; não é latência de produção.
- [ ] 2.4 Exibir o contador real de fotos comparadas e impedir que o arredondamento indique conclusão antecipada; cobrir porcentagens próximas de 100% e conclusão exata.

## 3. Validação e operação

- [x] 3.1 Executar testes relevantes, lint, validação OpenSpec e revisão do diff; registrar resultados e limitações. Ruff, diff-check e OpenSpec estrito aprovados para o backend; nova alteração da interface aguarda a suíte CI descrita em validation.md. Nenhuma alteração de schema, configuração de runtime, segredo ou acervo integra o diff.
- [x] 3.2 Apresentar inventário/portas/plano de impacto e obter aprovação explícita de implantação limitada ao worker de busca. Inventário e plano em deployment-plan.md; proprietário autorizou push, merge e deploy nesta conversa.
- [ ] 3.3 Após aprovação, implantar sem alterar dados/configurações de segredo, conferir integridade/saúde e busca real autenticada; registrar duração e rollback.

## Bloqueios

Não executar reset, limpeza de homologação, purge manual, migration ou reindexação. Sync/archive dependem de revisão humana.
