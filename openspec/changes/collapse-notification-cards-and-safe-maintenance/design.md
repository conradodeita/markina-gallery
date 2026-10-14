# Design

## Context

Ver proposal.md. EventCard mantém item, busy e mensagens localmente; carga GET acontece na página e PUT somente no submit. Existem sete eventos após a entrega Google Photos. O projeto usa details/summary em Pagamentos, sem componente compartilhado de accordion. Há alterações locais anteriores em backend/app/facial/purge.py, documentos de outras changes e .codex-tmp; não pertencem a esta execução.

## Goals / Non-Goals

**Goals:** controlar apenas apresentação, preservar formulários montados e validar a ausência de requisições ao alternar.

**Non-Goals:** mudar contratos HTTP, schema, transporte, dados, autenticação, dependências ou refatorar módulos. Não executar deploy nem limpar bancos, uploads, volumes ou resíduos de origem incerta.

## Decisions

- Usar details/summary nativo, inicialmente sem open e sem name compartilhado. Cada card abre independentemente, sem novo componente genérico nem estado persistido. Alternativa com React e botão exigiria estado/ARIA adicionais sem benefício aqui.
- Manter form e conteúdo montados dentro de details; preservar IDs contextuais no contêiner e aria-labelledby no formulário. CSS aplica espaçamento no conteúdo e foco no summary; seta decorativa muda conforme open.
- Ajustar testes existentes para abrir explicitamente os cards. Cobrir rascunhos, alternância independente, salvamento e erros; atualizar QA sintético que ainda representa seis eventos.
- Auditoria por lint, buscas e referências; ausência de referência textual isolada não comprova código morto em Next.js, migrations, workers ou scripts operacionais.
- Testes backend usam exclusivamente SQLite novo em diretório temporário e mídia sintética isolada, porque fixtures executam drop_all. Nunca usar o banco padrão do workspace. Docker somente config/build se disponível, sem subir serviços ou montar volumes.
- Extensão de manutenção ao servidor: inventário somente leitura via SSH com host previamente conhecido, sem impressão de credenciais/env. Caches no checkout e containers do projeto podem ser classificados por caminho, tamanho, mounts e camada. Cache Docker compartilhado não pode ser atribuído ao projeto apenas porque aparece como reclaimable; preservar sem prova de exclusividade. Apagar arquivo pertencente à imagem criaria whiteout sem liberar a camada, portanto não executar limpeza cosmética dentro de containers. Antes de qualquer mutação efetiva, aplicar o gate de inventário/plano/aprovação de DEPLOY.md.
- Relato adicional: `order_delivery.record_delivery_notice` produz `/library/purchases#order-UUID`, mas `allowedPushPath` rejeita o caminho, impedindo showNotification e clique. Acrescentar exclusivamente a rota de compras com fragmento opcional `order-UUID` canônico; manter rejeição de queries, URLs externas e fragmentos arbitrários. Validar recebimento e navegação no service worker real executado pelo teste VM. Não mudar backend nem contornar gates de transporte para resolver WhatsApp sem evidência.

## Risks / Trade-offs

- [Renderizadores de teste não reproduzem layout nativo] → verificar navegador quando disponível e manter testes do atributo open e requisições.
- [Links com fragmentos] → preservar o ID do evento no card; o cabeçalho continua acessível no destino.
- [Remover artefato útil] → permitir limpeza somente de caches conhecidos de ferramentas, dentro do workspace, sem links/reparse points; preservar bancos mesmo chamados test.db.
- [Daemon Docker ausente] → registrar bloqueio sem iniciar serviços globais da máquina.

## Migration Plan

Investigação adicional confirmou a mesma rejeição em `backend/app/web_push.py:safe_target`, antes do provedor. Aplicar a mesma allowlist limitada no transporte e no service worker; testar o adaptador real com HTTP falso, sem rede, para evitar que um push_sender inteiramente falso mascare validação de destino novamente.

Sem migration. Implementação e validação locais autorizadas no pedido atual. Rollback consiste em reverter somente o diff desta change. Em 25/09/2026, após confirmar que faltava push, o proprietário solicitou concluir a publicação: commit/push em branch própria e PR para develop. Merge em develop dispara deploy automático e permanece sujeito ao gate operacional; sync/archive ficam para revisão humana posterior.
