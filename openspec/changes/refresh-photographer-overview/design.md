# Design

## Context

Referência visual aprovada no Google Stitch: projeto Pick your Pic — Visual Redesign `14942044356996446740`, tela Visão Geral Dourado Claro `5e4c66ed48ca4027b89852acba9d7018`. A variante escura `57bdcac29d814bd48c3c3e6ff6a44bec` orienta a paleta correspondente. A composição usa barra lateral de 264 px, cabeçalho de 64 px, fundo contínuo quente, corpo com cinco métricas em 3+2, três etapas de publicação e cartões recentes em pares. No celular, navegação recolhível e conteúdo em uma coluna.

## Goals / Non-Goals

Reconstruir a composição da rota `/admin` e manter seus fluxos autenticados. Preservar os componentes de aparência, sessão e links com permissões existentes. As demais rotas mantêm a apresentação atual até o seu incremento. A lista de Galerias, a criação, edição e upload, o cliente móvel, o checkout e pagamentos serão validados em incrementos definidos separadamente.

## Decisions

- Encapsular a composição em um módulo CSS, com Plus Jakarta Sans e subconjunto de Material Symbols distribuídos localmente e acompanhados das licenças OFL e Apache 2.0. A estrutura reutiliza a navegação administrativa, a sessão e as variantes de aparência. O filtro do cabeçalho leva à busca existente em Galerias; a Visão Geral não introduz índice global.
- Priorizar a sequência hero, indicadores, prática de publicação, galerias, seleções e carteira. Preservar as cinco métricas já oferecidas pela aplicação e manter a carteira após a operação recente.
- Preservar os destinos reais dos links, as permissões de console e monitor, as ações de instalar aplicativo, notificações da sessão e saída. O tema completo continua disponível junto ao perfil.
- Usar aparência sem capa para as galerias recentes. A projeção atual não fornece capa, imagem ou data da galeria. A composição não cria solicitação por cartão e não incorpora dados, capas ou ações demonstrativas do protótipo.

### Mapa tela, resposta e estados

| Região | Origem e campos | Estado e ação |
| --- | --- | --- |
| Admissão ao painel e sessão | `GET /api/auth/destination` (`destination`) e `GET /api/auth/identity` (`role`, `identity`) pelos componentes existentes | Redirecionamento e escopo seguem a sessão atual. O menu de conta carrega a identidade autorizada. |
| Endereço da marca | `GET /api/admin/onboarding/address` (`base_domain,hostname,state,choice_complete,suggested_prefix,public_url`) pelo aviso existente | Escolha pendente ou erro de consulta aparecem no aviso próprio. Conta com escolha concluída mantém a tela livre do aviso. |
| Indicadores operacionais | `GET /api/admin/validation-summary` · `counts.parent_galleries`, `clients`, `folders_with_active_imports`, `photos_in_folders_with_active_imports`, `folders_released`; `storage.photo_count`, `bytes`, `available` | Carregamento e erro do resumo; armazenamento indisponível quando a medição não responde. |
| Galerias recentes | Mesmo resumo · `recent_galleries[].id,name,active,event_name` | Lista vazia ou cartões com estado ativo/bloqueado e link para `/admin/galleries/sources/{id}`. A projeção não inclui capa. |
| Seleções em andamento | Mesmo resumo · `recent_selections[].scope_id,client,gallery,parent_gallery,selected_count,selection_started_at`; a resposta inclui `last_selected_at`, sem renderização no cartão | Lista vazia ou seleção com horário local e atalho à seleção correspondente em Vendas e pagamentos. |
| Carteira e movimentações | `GET /api/admin/credits/wallet` · `wallet.mode,available_credits,reserved_credits,pending_operations,recent_consumed_credits,recent_period_days,can_upload_content`; `entries[].id,type,delta,source_reference,description,created_at` | Carregando, disponível, ilimitado, sem movimentações, saldo insuficiente ou indisponível. A falha da carteira preserva indicadores e atalhos do resumo. |
| Prática e ações de publicação | Dicas fixas, URLs `/admin/galleries` e `/admin/galleries/new` | Criação e consulta usam rotas existentes. A busca direciona ao filtro da lista, que consulta `GET /api/admin/parent-galleries/overview?query=...`. |

## Risks / Trade-offs

O cabeçalho e a navegação aparecem em tamanhos diferentes conforme a janela, com um único menu de navegação ativo e foco visível. Sem resumo autorizado disponível a estrutura visual permanece acessível, e o conteúdo informa carregamento ou erro. Preferências de movimento reduzido e tema são preservadas.
