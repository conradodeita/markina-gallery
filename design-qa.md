# Revisão visual — Vendas e pagamentos

## Escopo e evidência

- Fonte de verdade: implementação anterior preservada em baseline temporário e identidade definida em `frontend/app/globals.css` / `frontend/app/ui-kit.tsx`; mandato humano exige reutilizar tokens e capacidades existentes.
- Não existe imagem/mockup independente selecionado como alvo nesta tarefa. Não foi capturada a interface anterior em viewport idêntica para uma comparação visual normalizada.
- Implementação: capturas em `C:/Users/Conrado/Documents/Photo Delivery/.codex-tmp/sales-visual-qa/`.
- Viewports CSS: 390 × 950, 768 × 950, 1440 × 950; densidade 1; temas claro/escuro, acabamento silver. Full-page tem altura variável; lightbox corresponde ao viewport.
- Estados: listagem recolhida, pedido expandido e modal. Dados e imagens de teste sintéticos, APIs interceptadas; não são fotos de cliente nem evidência de fidelidade de imagem real.
- Inspeção realizada: listagem mobile claro/escuro, desktop claro, detalhe desktop escuro, detalhe mobile e lightbox mobile. A matriz automatizada completa tem seis cenários aprovados e 18 capturas.
- Comparação conjunta fonte/implementação: indisponível por falta de referência visual anterior/independente; não se declara comparação lado a lado nem fidelidade pixel a pixel.

## Superfícies verificadas e limites

| Superfície | Evidência da implementação | Limite |
|---|---|---|
| Tipografia | Família herdada do sistema; títulos, valores, nomes longos e nomes dos arquivos inspecionados. | Sem comparação tipográfica com screenshot anterior. |
| Layout e espaçamento | Detalhe em duas colunas no desktop e uma no mobile; sem overflow horizontal nos seis cenários, inclusive detalhes. | Capturas full-page em scroll podem exibir barras aderentes no meio da composição; isso não demonstra deslocamento do layout em uso. |
| Cores e tokens | Tokens existentes; claro/escuro legíveis na inspeção; bordas, superfícies, badges e botões reutilizados. | Sem auditoria completa de contraste/WCAG ou matriz dos demais acabamentos. |
| Imagens | 64 px sem deformação; modal contém imagem ativa; carga diferida verificada em navegador e autorização testada no backend. | Imagem sintética valida geometria/carga, não nitidez/crop de acervo real. |
| Conteúdo | Título, filtros, quantidades, totais, status e áreas Fotos/Pagamento/Entrega presentes; sem novo vocabulário financeiro persistido. | Casos operacionais ricos são cobertos pelos componentes/testes existentes; a fixture visual não contém todo o histórico real. |

## Histórico de correções

- [P1, resolvido] Shift+Tab no primeiro controle do dialog permitia saída de foco para a interface do navegador. Adicionado ciclo explícito por Tab/Shift+Tab, regressão unitária, novo build e repetição da matriz de seis cenários com foco/scroll aprovados.
- O script falhou ao localizar Exibir por correspondência exata. Ajustado somente o localizador; repetição completa aprovada. Não era falha funcional da página.
- Capturas de detalhe repetidas a partir do topo para facilitar leitura da composição com barras aderentes.

## Interações verificadas

Nenhuma imagem antes da expansão; miniaturas lazy; modal na top layer; uma imagem ampliada ativa; setas; foco contido; Escape, botão e clique externo; restauração de scroll/foco/expansão; exportação filtrada; seleção automática sem duplicidade; histórico vazio e Estatísticas 404. Nenhum `pageerror` nos cenários. Decisões financeiras e entregas reais não foram acionadas na revisão visual.

## Resultado

**QA funcional local:** aprovado na matriz descrita. Nenhum achado visual P0/P1/P2 aberto nas capturas inspecionadas.

**Aceite comparativo de design:** a equivalência pixel a pixel não pode ser medida sem fonte visual independente/anterior em condições equivalentes. O proprietário informou “revisado e autorizado” e autorizou a publicação. A aprovação cobre o redesenho revisado; não representa comparação pixel a pixel nem auditoria WCAG completa.

final result: passed

## Continuação após integração na `main` atual

- Nova execução do `frontend/scripts/payments-visual-qa.cjs` com Playwright 1.61.0 e Edge headless, APIs e conteúdo sintéticos: seis combinações concluídas em 390, 768 e 1440 px nos temas claro/escuro; 18 capturas em `%TEMP%/sales-visual-qa-current/`, com `report.json` aprovado.
- Cobertura confirmada: listagem, pedido expandido e lightbox; sem overflow horizontal; navegação por teclado, foco contido/restaurado, Escape, botão e clique externo; filtro/exportação; histórico de acervo vazio; rota Estatísticas 404; nenhum `pageerror`.
- Para o contrato atualizado do `SessionBoundary`, o script usa `localhost` e intercepta `/api/auth/destination` com destino sintético `/admin`. O Next dev bloqueou chunks de `127.0.0.1` como origem cruzada; somente o script de QA foi ajustado, sem alteração de configuração da aplicação.
- O navegador registrou falha local de proxy no endpoint de favicon da marca porque a API não estava rodando na porta 8000; os cenários passaram e não dependeram desse recurso.
- Capturas representativas do checkpoint: `payments-1440-light.png`, `details-390-light.png`, `lightbox-390-light.png` no diretório temporário acima. A aprovação humana informada no chat autoriza avançar à publicação; como não há screenshot anterior normalizada, ainda não se declara equivalência pixel a pixel.

## Checklist de continuação

- [x] Reutilizar tokens/UI Kit existentes.
- [x] Validar desktop/mobile e temas claro/escuro com dados sintéticos.
- [x] Corrigir foco e repetir checks.
- [x] Registrar limites e evidências no relatório técnico e OpenSpec.
- [x] Obter aceite visual humano ou referência comparável para concluir avaliação de fidelidade.
- [ ] Validar acervo real/ambiente autenticado e casos PostgreSQL quando o ambiente apropriado estiver disponível.
