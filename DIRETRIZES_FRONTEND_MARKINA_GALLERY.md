# Markina Gallery — Diretrizes de Frontend e UX

Este documento orienta o Claude Code a desenhar e implementar o frontend completo da Markina Gallery. Ele é uma diretriz de produto e experiência, não um catálogo de templates nem uma autorização para transformar o sistema em um CMS genérico.

O protótipo visual aprovado está em [`docs/frontend-reference/stitch-export/`](docs/frontend-reference/stitch-export/). Ele é apenas referência visual/funcional: o código exportado não pode ser copiado diretamente. A implementação deve seguir a arquitetura oficial, as specs OpenSpec e as regras deste documento.

## 1. Definição do produto

A Markina Gallery é uma plataforma operacional de fotografia com duas superfícies:

1. **Área administrativa do fotógrafo**: CRM, eventos, galerias, fotos, clientes, seleções, pedidos, pagamentos, entregas, mensagens, armazenamento e pendências.
2. **Área do cliente/responsável**: acesso à galeria autorizada, busca/resultado privado quando aplicável, seleção, carrinho, checkout, pedido e entregas.

Ela possui características de um CMS apenas no sentido de administrar conteúdo estruturado — galerias, pastas, fotos, capas, textos e configurações comerciais. **Não é um CMS completo de website.**

## 2. O que o fotógrafo pode personalizar

O fotógrafo pode configurar por galeria:

- cor principal ou cor de destaque;
- tipografia do título/nome da galeria, escolhida de uma lista segura de fontes;
- foto de capa;
- template de organização das fotos, limitado aos layouts suportados pelo produto;
- ordem e visibilidade de pastas/fotos;
- texto de informação de venda;
- preço e faixas de quantidade;
- prazo, resolução, download e proteção visual;
- marca d’água, linhas diagonais e aviso de direitos autorais.

Também pode configurar identidade global simples: logo, nome da marca, favicon e cores-base.

## 3. O que não deve existir

Não implementar:

- construtor de páginas arrastável;
- dezenas de templates de website;
- editor livre de HTML/CSS/JavaScript;
- publicação de blog, landing pages ou portfólio dentro do MVP;
- personalização independente de cada componente visual pelo fotógrafo;
- configurações que permitam quebrar contraste, acessibilidade ou hierarquia de navegação;
- visual diferente e arbitrário para cada cliente.

O frontend deve parecer um produto coeso da Markina Gallery. A personalização altera identidade e organização da galeria, não a estrutura fundamental da aplicação.

## 4. Direção visual

- Estética moderna, editorial e fotográfica, inspirada em produtos como Wfolio, Pic-Time e Pixieset sem copiar suas interfaces.
- Imagens são o elemento dominante; controles devem ser discretos e claros.
- Interface limpa, com bom uso de espaço, tipografia legível e estados visuais fortes.
- Cores configuradas pelo fotógrafo devem ser aplicadas com tokens CSS e passar por validação de contraste.
- Priorizar uma experiência premium sem sacrificar velocidade em aparelhos intermediários.
- Estados de sistema devem ser explícitos: carregando, vazio, erro, pendente, ativo, expirado, pago, em edição, entregue.

## 5. Portal do cliente — princípio de poucos passos

O cliente não deve precisar compreender a estrutura interna do sistema. A jornada principal é:

```text
Abrir galeria → identificar-se por OTP → navegar no escopo autorizado → ampliar → selecionar → revisar carrinho → pagar → acompanhar entrega
```

Regras de UX:

- capa e informações sem fotografia identificável podem ocorrer sem login quando a galeria permitir;
- nenhuma prévia fotográfica é entregue antes do login; o backend aplica os modos `standard`, `invite_only` e `collective_protected`;
- a biblioteca apresenta separadamente Galerias públicas autorizadas, galerias privadas derivadas e histórico comercial;
- coração/check seleciona; ampliar é ação separada;
- contador e total estimado ficam visíveis após autenticação;
- carrinho mostra miniaturas, quantidade, faixa de preço alcançada e próxima faixa;
- cliente pode voltar à galeria antes de confirmar o pagamento;
- fotos já pagas para aquele cliente ficam claramente marcadas e indisponíveis para recompra;
- pedidos e entregas continuam acessíveis depois da expiração da seleção.

## 6. Portal do cliente — telas e estados

Implementar progressivamente:

- entrada da galeria/capa;
- login OTP ou convite;
- tela única de entrada com contexto `Cliente` ou `Fotógrafo`;
- fluxo administrativo de e-mail, senha e TOTP;
- biblioteca do responsável;
- galeria com pastas e grade;
- visualizador ampliado;
- seleção/carrinho;
- checkout PIX;
- detalhe do pedido;
- minhas entregas.

Para evento coletivo, não mostrar grade pública do acervo. O fluxo de busca facial, quando habilitado após o spike, leva a uma sessão de resultado privada, com consentimento e revisão/ativação conforme as specs de privacidade.

## 7. Área administrativa — princípio de operação rápida

O painel deve ser mais funcional que decorativo. O fotógrafo deve localizar uma pendência e agir em poucos cliques.

Dashboard inicial:

- pagamentos informados;
- clientes pendentes de ativação;
- pedidos em edição;
- entregas aguardando link;
- galerias próximas da expiração;
- falhas de importação/mensagem;
- uso do disco e estimativa de capacidade.

Entidades principais do menu:

- Dashboard;
- Clientes/responsáveis;
- Pessoas fotografadas;
- Eventos e bibliotecas;
- Galerias e pastas;
- Fotos/importações;
- Pedidos e pagamentos;
- Entregas;
- Tags e pendências;
- Mensagens;
- Armazenamento;
- Configurações.

O painel deve oferecer busca, filtros persistentes, ações em massa e histórico contextual. Evitar tabelas gigantes sem filtros e sem estados visuais.

## 8. Componentes e padrões obrigatórios

Criar um design system interno pequeno e consistente:

- tokens de cor, tipografia, espaçamento, borda e sombra;
- Button, Input, Select, Dialog, Drawer, Toast, Badge, Tabs, Table, Card, EmptyState, ConfirmDialog;
- GalleryGrid, PhotoCard, PhotoViewer, SelectionBar, CartSummary, StatusBadge, Timeline, UploadProgress;
- componentes acessíveis por teclado e leitor de tela;
- estados de foco, erro, carregamento e desabilitado;
- confirmação explícita para exclusão, pagamento, entrega e ações em massa.

Não espalhar decisões visuais diretamente em páginas. Componentes e tokens devem permitir evolução sem criar um CMS.

## 9. Responsividade e desempenho

- Mobile-first real; a maior parte dos clientes usará smartphone.
- Grade de 2 colunas no celular e 4 ou mais no desktop, respeitando proporções.
- Carregamento lazy, thumbnails responsivas, placeholders e paginação/infinite scroll controlado.
- Visualizador ampliado deve manter navegação simples por toque, teclado e swipe.
- Não carregar originais nem imagens maiores que a resolução configurada.
- Administração deve funcionar em desktop e tablet; telas de operação críticas não podem depender apenas de hover.

## 10. Critérios de aceite frontend

- Um cliente novo consegue selecionar a primeira foto, autenticar via OTP e chegar ao carrinho sem instruções externas.
- O cliente entende visualmente quais fotos estão selecionadas, pagas, indisponíveis ou entregues.
- O fotógrafo identifica as pendências principais na primeira tela e resolve ações em massa sem navegar por várias telas.
- Alterar cor, tipografia, capa ou layout suportado de uma galeria não quebra contraste, responsividade ou navegação.
- Nenhuma tela oferece edição livre de página ou template fora do conjunto definido pelo produto.
- O frontend não expõe acervo coletivo antes de uma sessão privada autorizada.
- Loading, vazio, erro, expiração, pagamento, edição e entrega têm estados visuais claros.
- Testes de componentes e fluxos principais cobrem seleção, carrinho, checkout, estados de pedido e permissões.

## 11. Regra para o executor

Antes de criar qualquer tela, o Claude Code deve ler este documento e a spec OpenSpec do domínio correspondente. Se uma decisão de interface não estiver definida, deve propor a solução no change OpenSpec antes de implementá-la. Não criar novas opções de customização apenas para “deixar mais flexível” sem aprovação do proprietário.
