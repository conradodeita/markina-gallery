## Context

O backend já possui entidades e autorizações de galeria derivada. A mudança cria uma camada de operação visual, mantendo o backend como fonte de autorização.

## Decisions

### Fluxo administrativo em etapas

O fotógrafo cria cliente, acervo, fotos e galeria derivada em telas pequenas e sequenciais. Seletores usam APIs administrativas autorizadas; UUIDs não são digitados manualmente.

### Cliente recebe somente dados derivados

Biblioteca e galeria usam endpoints da própria sessão. Nenhuma página aceita path de arquivo ou apresenta dados do acervo-mãe.

### Interfaces estritamente backend-driven

Frontend somente apresenta respostas de APIs autenticadas e solicita ações ao backend. Permissões, prazo, disponibilidade de mídia, status de importação e transições comerciais não podem ser inferidos, simulados ou autorizados pelo estado local do browser. Dados fictícios são permitidos apenas em testes automatizados isolados.

### Importação explícita e assíncrona

O envio aceita JPEG, exibe processamento e depende do worker para prévias. Falhas ficam visíveis ao fotógrafo sem liberar o original.

## Risks / Trade-offs

- Muitos arquivos em um navegador → importar em lotes e comunicar processamento; não criar upload de RAW.
- Formulários longos → dividir em etapas e preservar erros próximos ao campo.
