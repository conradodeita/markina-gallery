# Design

## Context

A etapa Imagens e o resumo da galeria já exibem prévias de pastas comuns pelo endpoint administrativo. O `Acervo da cliente` lista pastas restritas por cliente, mas o payload não inclui prévia e a abertura é uma linha textual. O backend já protege `/admin/photo-assets/{id}/watermarked-preview` e gera derivados `client_preview` pelo mesmo pipeline para pastas comuns e restritas.

## Goals / Non-Goals

**Goals:** oferecer reconhecimento visual e ação única de abertura por pasta, mantendo o escopo administrativo atual.

**Non-Goals:** definir capa manual, mudar o card da cliente fora do Acervo, modificar acesso público, processamento ou modelos persistidos.

## Decisions

### 1. Prévia vinda da listagem autorizada

Estender a resposta administrativa de pastas restritas com `preview_url`, obtida da primeira foto da própria pasta cujo derivado `client_preview` esteja pronto, como na listagem comum. Não escolher foto de outra pasta nem devolver URL do original. Alternativa considerada: buscar as fotos de cada pasta ao expandir o Acervo; isso exigiria múltiplas chamadas e carregaria uma grade inteira apenas para mostrar a capa.

### 2. Card clicável sem nova mutação

Usar um único botão por pasta, contendo capa ou placeholder, nome, contagem e estado. O botão aciona a função de abertura existente e informa `aria-expanded`; o painel e as fotos só são consultados depois do clique. Reutilizar as classes visuais dos cards comuns onde possível, preservando o layout móvel e nomes longos. O título do resumo muda somente o texto; a lista não muda de público.

### 3. Busca no contexto certo

O resumo já recebe todos os cards de clientes vinculadas na resposta autenticada. Filtrar essa lista localmente por nome e telefone evita chamada a cada tecla e preserva os contadores gerais. Colocar o campo no bloco `Resumo da galeria`, próximo da indicação de clientes vinculadas; o estado vazio aparece no bloco de cards. A busca geral continua encontrando galerias, mas seu backend hoje verifica clientes em `DerivedGallery`, um vínculo legado. Incluir também clientes de `ParentGalleryRegistration`, sem retirar a busca legada, corrige o texto atual e mantém o uso anterior. Alternativa considerada: remover a busca por cliente da página geral; isso perderia a navegação de quem sabe o nome da cliente mas não da galeria.

## Risks / Trade-offs

- [Derivado ainda não pronto] → mostrar placeholder textual sem esconder a pasta.
- [Falha ou revogação da imagem] → preservar nome e ação; a rota administrativa mantém sua própria autorização.
- [Pastas numerosas] → consulta de capa limitada a um derivado por pasta, sem transferir a grade inteira; acompanhar o custo na validação de API.
- [Busca com nome ou telefone formatado] → normalizar caixa, acentos e dígitos no filtro local; backend mantém seu contrato de busca geral e recebe teste com vínculo canônico.

## Migration Plan

Mudança aditiva na resposta da API, sem migration ou tratamento de dados. O frontend antigo ignora o novo campo; o novo frontend funciona com `preview_url` ausente. Reversão de código não altera pastas nem derivados.
