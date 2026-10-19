# Proposal

## Por que

O inventário anterior foi feito num checkout antigo e deixou de fora o runtime especializado de EmbeddingGemma. A `main` atual tem gerenciamento de dependências por ecossistema, mas necessita de uma rotina consolidada para candidatos, avisos de segurança, itens especializados e incertezas de produção.

## O que muda

- Reconciliar o inventário a partir da `main` atual, preservando a distinção entre container existente, runtime pronto e modelo realmente usado.
- Integrar política de atualização de dependências externas ao OpenSpec e ao `AGENTS.md`.
- Habilitar Dependabot em ciclos semanais e agrupados para npm, Python, imagens Docker e GitHub Actions, sem automerge; usar alertas de segurança nativos em sua cadência própria.
- Gerar um relatório semanal GitHub Actions, sem notificação quando não houver candidatos/alertas, e com estado explícito de consulta indisponível/falha.
- Registrar proveniência, riscos, compatibilidade, licença e validações humanas necessárias para serviços críticos e motores especializados.

## Fora de escopo

- Atualizar qualquer versão de produção, modelo, imagem ou segredo.
- Consultar ou alterar Oracle, fazer deploy/migration, modificar dados de cliente, habilitar serviços pagos ou contornar configurações/permissões do GitHub.
- Criar PRs automáticos de atualização para pesos/modelos de IA, engines faciais ou motores fotográficos que exijam avaliação especializada.
- Automerge ou merge deste PR sem aprovação/revisões requeridas.
