## Context

As rotas atuais já validam autenticação, propriedade exclusiva de galerias, prévias protegidas e interações privadas, mas apresentam páginas compactas e operações desconectadas. A proposta e as delta specs desta mudança definem a experiência observável; este documento fixa como ela será entregue sem criar dados simulados nem ampliar acesso a fotos.

## Goals / Non-Goals

**Goals:**

- Consolidar um design system interno pequeno, com tokens e componentes reutilizáveis para as duas superfícies do produto.
- Organizar a área administrativa em navegação persistente, dashboard e fluxos de galeria/pasta orientados por APIs autenticadas.
- Representar pasta como lote com estado e tornar a liberação um comando explícito, auditável e idempotente.
- Construir a experiência de cliente a partir de respostas privadas, com prioridade para celular e visualização de fotos protegidas.
- Preparar dados sintéticos e roteiro de homologação apenas quando os dois fluxos estiverem completos.

**Non-Goals:**

- Não criar construtor de páginas, editor livre de estilo, templates de terceiros ou cópia do sistema de referência.
- Não implementar pagamento, carrinho comercial final, PIX, WhatsApp, entrega, biometria, indexação facial ou sincronização Drive.
- Não publicar acervo-fonte, servir originais ou usar dados reais de crianças em homologação.

## Decisions

### Casca visual única e componentes por domínio

Será criada uma casca administrativa com navegação, cabeçalho de contexto e área de conteúdo, e uma casca separada e mobile-first para a cliente. Os componentes de base (botões, campos, cartões, badges, diálogo de confirmação, estados vazios/erro, grade e visualizador) usarão tokens CSS da Markina e serão compostos nas páginas, em vez de concentrar toda a interface em arquivos de página. Isso permite aparência coesa sem introduzir biblioteca visual externa ou CMS.

Alternativa descartada: usar páginas de demonstração independentes. Elas incentivariam mocks, duplicariam autorização e não permitiriam validar o produto entregue.

### Backend como fonte de estado e contratos específicos

Cada tela buscará seu resumo, lista ou detalhe por API autenticada. Quando uma resposta existente não for suficiente, o backend exporá contrato pequeno e paginado para a tela, sem URL de original, telefone em listas indevidas ou dados de outra cliente. Estados de upload e liberação serão retornados pelo backend; o browser guardará somente estado efêmero de interação.

Alternativa descartada: montar o dashboard no cliente a partir de listas completas. Isso degrada desempenho, amplia dados transferidos e pode vazar informações operacionais.

### Pasta como lote imutável após liberação

Uma nova entidade ou extensão de modelo de pasta terá identificação, nome exibido, ordem, estado `preparing | released | failed`, contagens e timestamps. O upload associa JPEGs somente a uma pasta em preparação. A liberação verifica que o lote está apto, associa somente referências autorizadas às galerias privadas de destino e impede incluir fotos posteriores naquela pasta. Uma nova pasta será usada para nova rodada.

Alternativa descartada: permitir anexar fotos silenciosamente a uma pasta liberada. Isso cria ambiguidade para cliente e fotógrafo e contraria a regra de negócio aprovada.

### Previews e ações sensíveis

O admin poderá ver prévias administrativas por rota protegida; a cliente continuará recebendo somente derivados protegidos. Exclusão, bloqueio, liberação e remoção de lote exigirão confirmação acessível e resposta de sucesso/erro do backend. A página nunca assumirá que a ação deu certo antes da resposta.

### Entrega em incrementos verificáveis

A implementação seguirá a ordem: contratos de pasta e liberação; design system/casca; área do fotógrafo; experiência da cliente; testes e homologação. Cada incremento manterá páginas utilizáveis, mas somente após todos os critérios desta mudança a interface será apresentada à proprietária para validação final.

### Exclusão administrativa com preservação de histórico

O backend decide se uma pasta ou galeria pode ser removida. Pastas vazias ou em preparação sem vínculos podem ser excluídas; uma pasta liberada exige não possuir referências privadas. Galerias privadas só podem ser excluídas sem fotos, seleções ou pedidos. Compra confirmada torna a exclusão indisponível: o fotógrafo poderá congelar ou bloquear o acesso, preservando histórico e auditoria.

## Risks / Trade-offs

- [Upload de JPEG grande no navegador] → validar tipo/tamanho no backend, expor progresso por arquivo e nunca transmitir URL do original de volta à interface.
- [Pasta liberada sem referência privada suficiente] → validar destinos e retornar bloqueio explicável antes de alterar visibilidade.
- [Componentes visuais atrasarem a operação] → começar por fluxos de galeria/pasta e reutilizar os componentes nas áreas restantes.
- [Dados operacionais vazarem no dashboard] → contratos administrativos e de cliente separados, com testes de autorização e de ausência de campos sensíveis.
- [Validação humana ocorrer antes de estar pronta] → publicar roteiro de homologação somente após lint, testes, build e os dois fluxos completos.

## Migration Plan

1. Adicionar migration somente aditiva para pastas/lotes e seus vínculos, preservando galerias, fotos e pedidos existentes.
2. Publicar contratos e interfaces sem conceder acesso a pasta não liberada; manter rollback por imagem anterior, pois a migration não remove registros.
3. Executar testes automatizados e validação com dados sintéticos locais.
4. Apresentar inventário e plano de impacto zero, obter aprovação explícita e implantar somente o projeto `markina-gallery` em homologação.
5. Se ocorrer falha, restaurar a imagem anterior do projeto; restaurar banco apenas se a mudança de código não resolver, usando backup exclusivo do Markina.
