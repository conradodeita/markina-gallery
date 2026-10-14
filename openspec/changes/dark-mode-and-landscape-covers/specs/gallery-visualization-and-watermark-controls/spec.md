## ADDED Requirements

### Requirement: Novas capas exclusivamente horizontais

O sistema SHALL aceitar novos uploads e substituições de capa somente em JPEG com largura maior que altura após normalizar a orientação EXIF. A validação SHALL ocorrer no servidor antes de gravar/substituir o arquivo, selecionar a nova capa ou agendar processamento. O frontend SHALL comunicar a exigência na etapa 03 e apresentar o erro sem perder a capa anterior. Capas já cadastradas SHALL ser preservadas até substituição; imagens comuns do acervo SHALL continuar aceitando outras orientações.

#### Scenario: Capa horizontal válida
- **WHEN** o admin envia JPEG cuja largura visual é maior que a altura
- **THEN** o upload segue o processamento existente e mantém a imagem fora das pastas de conteúdo

#### Scenario: Arquivo vertical ou quadrado
- **WHEN** o admin envia capa cuja largura visual é menor ou igual à altura, inclusive via API direta
- **THEN** o sistema recusa com mensagem de orientação horizontal, preserva a capa anterior e não cria job nem grava a fonte inválida

#### Scenario: Orientação EXIF
- **WHEN** os pixels codificados e a orientação visual indicada por EXIF diferem
- **THEN** a aceitação considera a imagem após aplicar a orientação, não apenas os números brutos do arquivo

### Requirement: Capa limpa e responsiva com título

O sistema SHALL mostrar a capa sem marca-d'água ou grade na etapa 03, visualizações administrativas e galerias autorizadas do cliente, mantendo título, fonte, cor e posição configurados. A capa SHALL ocupar a largura disponível preservando a proporção e mostrando a fotografia inteira, sem distorção ou cortes automáticos para forçar orientação vertical no celular. A nova aparência SHALL NOT reintroduzir capas em telas que já não as exibem, como conferência do pedido.

#### Scenario: Mobile e desktop
- **WHEN** a galeria é aberta em telas de diferentes larguras
- **THEN** a capa mantém proporção, imagem completa e título adaptado à área disponível, sem overflow

#### Scenario: Configuração do título
- **WHEN** o fotógrafo altera a tipografia ou posição do título
- **THEN** a prévia mantém a foto limpa e reflete as configurações sem alterar a proteção do acervo
