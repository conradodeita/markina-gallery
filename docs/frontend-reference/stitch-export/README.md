# Markina Gallery — Referência visual e protótipo

Este diretório contém uma exportação do Google Stitch/AI Studio usada **somente como referência visual, de UX e de prototipagem** para o Markina Gallery.

## Regra obrigatória para o Claude Code

Não copiar este código diretamente para a aplicação oficial.

Não copiar componentes, estado, mocks, dados, URLs, dependências ou estrutura de pastas deste protótipo como arquitetura de produção. O executor deve seguir a arquitetura oficial definida em:

1. `INSTRUCOES_EXECUTOR_CLAUDE_CODE.md`;
2. `ROADMAP_ARQUITETURA.md`;
3. `DIRETRIZES_FRONTEND_MARKINA_GALLERY.md`;
4. specs e changes vigentes em `openspec/`.

Este export serve para consultar composição visual, hierarquia, espaçamento, componentes, fluxos e estados. Ao implementar, o Claude Code deve reconstruir a interface dentro do stack oficial (Next.js, TypeScript, Tailwind e APIs reais), respeitando autenticação, permissões, OpenSpec, segurança e regras de negócio.

## O que é apenas simulação

Os dados, usuários, pedidos, valores, códigos PIX, links de WhatsApp, links do Google Photos, resultados faciais e imagens são fictícios. Este protótipo não confirma pagamentos, não processa biometria, não envia mensagens e não entrega arquivos reais.

Qualquer afirmação de criptografia, exclusão biométrica, proteção contra captura de tela ou entrega em alta resolução deve ser tratada como intenção de UX, nunca como implementação de segurança.

## Restrições de produto

- Não transformar o sistema em CMS ou page builder.
- Não adicionar loja de impressões, molduras, álbuns físicos ou produtos fora do MVP.
- Pré-visualizações devem permanecer protegidas por marca d’água/linhas configuradas.
- Downloads de originais só podem existir após pagamento confirmado e entrega autorizada.
- Reconhecimento facial permanece sujeito ao spike técnico, privacidade e aprovação OpenSpec.
- A área administrativa deve ser protegida por autenticação real; nunca por um botão ou rota pública.

## Execução local

O código pode ser executado apenas para inspeção visual. Ele não deve ser usado como serviço de produção e não deve compartilhar a porta ou volumes do projeto Docker oficial. Use uma porta temporária e um projeto Compose isolado se precisar executar o protótipo.

## Fonte visual

A versão anterior está em `../stitch-export-v1/` para comparação. A versão atual deste diretório é a referência visual aprovada até nova revisão.
