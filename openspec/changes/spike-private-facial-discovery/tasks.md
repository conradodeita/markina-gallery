## 1. Preparação segura

- [x] 1.1 Definir dataset sintético/anonimizado de 500–1.000 JPEGs, identidades ficcionais, cenários de qualidade, métricas e ambiente efêmero isolado; verificar inventário e limpeza sem dados no Git ou homologação.
- [x] 1.2 Pesquisar e registrar licença comercial de código/pesos e compatibilidade ARM de YuNet + SFace e dos concorrentes elegíveis; excluir candidatos sem cadeia de licença verificável.

## 2. Avaliação

- [x] 2.1 Implementar harness isolado para indexação em background e consulta por filtro, comprovando isolamento por evento, referência de rosto único e ausência de criação de galeria/seleção/vínculo.
- [x] 2.2 Medir cobertura, precisão, falsos positivos/negativos, latência, throughput e consumo de CPU/memória/disco por candidato, versão e limiar em evento único; registrar evidência reproduzível e limitações do hardware.
- [x] 2.3 Documentar base legal da indexação, consentimento da consulta, menores, retenção, exclusão automática/manual, revogação, auditoria e quando a revisão humana continua obrigatória.

## 3. Decisão

- [x] 3.1 Produzir relatório sem dados biométricos com decisão aprovar/ajustar/rejeitar cada candidato e o rollout futuro; verificar que contém critérios, resultados agregados e riscos residuais.
- [x] 3.2 Validar OpenSpec em modo estrito, executar a limpeza do ambiente efêmero e registrar que nenhuma migration, rota, interface ou funcionalidade cliente foi habilitada.
