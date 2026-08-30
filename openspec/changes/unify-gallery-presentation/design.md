## Context

O produto já possui contratos separados para a operação da galeria-mãe e para a galeria privada derivada. A composição atual da prévia do fotógrafo é uma página técnica independente, enquanto a cliente usa outra estrutura. A decisão confirmada é compartilhar a visualização, não os privilégios.

## Goals / Non-Goals

**Goals:**

- Fazer capa, navegação de pastas, grade de prévias e visualizador terem a mesma hierarquia visual para os dois papéis.
- Priorizar fotografia, legibilidade, responsividade e estados explícitos.
- Preservar contratos backend-driven e proteção de prévias.

**Non-Goals:**

- Expor fotos em preparação à cliente, tornar a galeria pública ou alterar permissões.
- Criar novo template livre, checkout, pagamentos, entrega ou controles de edição de imagem.
- Copiar código, mocks ou componentes do export do Stitch.

## Decisions

### Superfície compartilhada com adaptadores por papel

Será extraído um componente de apresentação que receba um modelo visual mínimo: identidade da galeria, capa protegida, pastas ordenadas, fotos permitidas, estado e ações declaradas. A prévia do fotógrafo e a galeria da cliente fornecerão esse modelo a partir de seus próprios contratos autenticados.

A composição será igual: cabeçalho/hero, contexto da galeria, seletor ou trilha de pastas, grade de fotos e visualizador. A cliente verá somente pastas liberadas e fotos atribuídas à sua galeria derivada. A prévia do fotógrafo poderá mostrar o escopo administrativo permitido, sempre sinalizado como prévia e sem alterar conteúdo ou autorização.

Alternativa descartada: redirecionar o fotógrafo para uma sessão de cliente. Isso exigiria OTP e não permitiria pré-visualizar com segurança o estado administrativo.

### Estados e acessibilidade

Ausência de capa, pasta sem fotos, carregamento e erro usarão componentes de estado consistentes. O visualizador manterá foco, fechamento por teclado e textos alternativos; controles exclusivos de cliente não aparecerão na prévia do fotógrafo.

### Responsividade e mídia

A grade será mobile-first, com duas colunas em telas estreitas e expansão progressiva no desktop. As imagens usarão somente prévias protegidas devolvidas pelo backend, com `object-fit: contain` onde necessário para não cortar enquadramentos.

### Proteção visual global e apresentação por galeria

Marca-d’água e demais controles de proteção visual pertencem à identidade operacional do fotógrafo, não a uma galeria isolada. Eles serão configurados em **Configurações**, em um painel curto e acessível, e serão a fonte única usada na entrega de prévias protegidas de todas as galerias. A alteração de configuração deverá ser refletida nas prévias protegidas servidas após sua persistência, sem expor originais nem exigir que o fotógrafo replique valores galeria a galeria.

O editor da galeria não oferecerá controles locais de texto, fonte, cor, tamanho ou direção da marca-d’água. Ele preservará os campos próprios da galeria, como capa/título quando aplicáveis, e manterá a **Organização** das pastas como escolha explícita daquela galeria. A interface separará esses assuntos para não sugerir que uma alteração global afeta apenas a galeria aberta.

Alternativa descartada: adicionar campos de CSS, posicionamento livre ou templates arbitrários. Isso conflita com a personalização controlada do produto e inviabiliza garantia de contraste e responsividade.

## Risks / Trade-offs

- [Diferença entre contratos de galeria-mãe e derivada] → criar adaptadores pequenos e testar que a estrutura não infere autorização no navegador.
- [Prévia administrativa parecer acesso de cliente] → manter rótulo de modo fotógrafo e separar ações por papel.
- [Galeria sem capa ou sem fotos] → fornecer estados visuais intencionais, sem cards vazios genéricos.
- [Prévia sem mídia disponível] → manter a configuração utilizável e apresentar um estado de prévia que explica o próximo passo, sem simular fotografia.

## Migration Plan

1. Criar componente compartilhado e adaptadores sem alterar contratos de autorização.
2. Centralizar os controles de proteção visual em Configurações e retirar os controles locais de marca-d’água do editor de galeria, preservando a organização de pastas por galeria.
3. Cobrir desktop e mobile com testes de componente para ambos os papéis e para a configuração global.
4. Validar em homologação com dados sintéticos e sessão de fotógrafo e cliente.
5. Publicar somente após lint, typecheck, build e validação OpenSpec.
