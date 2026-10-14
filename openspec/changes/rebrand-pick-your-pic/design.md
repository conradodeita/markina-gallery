## Context

Ver proposal.md. O nome aparece em layouts compartilhados, auth-entry, metadata/manifesto, tela offline, títulos da API, mensagens de worker/messaging/admin_account e defaults de BrandingSettings. A infraestrutura e os procedimentos usam `markina-gallery`; isso não é marca de apresentação. A logotipo fornecida contém tipografia própria e aparece em uma prancha com diferentes aplicações.

## Goals / Non-Goals

**Goals:** eliminar marca antiga das superfícies padrão atuais, centralizar identidade de produto, preservar arte e comportamento.

**Non-Goals:** novo domínio, renomear repo/Compose/CSS/componentes internos, redesenhar imagem, alterar fonte tipográfica do site para uma fonte inferida da imagem, modificar dados do fotógrafo, enviar mensagens reais ou publicar nesta fase.

## Decisions

1. Centralizar nome e textos derivados em constantes pequenas no frontend e backend. Inventariar ocorrências literais e fragmentadas (MARKINA + Gallery) incluindo assets textuais e exportações. Preferir constantes a substituição cega para distinguir infraestrutura, nomes internos e evidências históricas.
2. Continuar consumindo ativos de branding configurados; conferir proporção/legibilidade nos dois temas com fundo de apoio neutro quando necessário, sem aplicar filtro à arte. A prancha não é asset final: não fazer crop automático nem substituição remota. Caso arquivos individuais sejam necessários e ainda não estejam configurados, solicitar ao proprietário para upload existente.
3. Atualizar somente defaults em código. Valores persistidos antigos podem ser personalizados e serão preservados; documentar como alterar pelo painel. Não atualizar e-mails, WhatsApps, recibos, consentimentos ou mensagens já enfileiradas, nem reprocessar marcas gravadas em fotos. `.env.example` pode receber novo valor de exemplo, mas arquivos de ambiente reais permanecem intactos.
4. Atualizar nome de manifesto/Apple/título mantendo `id`, `scope`, `start_url`, caminho do service worker e nomes de armazenamento técnico. Instalações existentes dependem do ciclo de atualização do navegador/SO, sem promessa de troca instantânea do nome na tela inicial.
5. Atualizar README, títulos e textos de manuais vigentes, mandato/roadmap e contexto OpenSpec para declarar produto Pick-your-Pic e infraestrutura legada markina-gallery. Preservar comandos, caminhos e URLs válidos, nomes de arquivos de instrução, migrations e documentos históricos. Listar explicitamente as ocorrências remanescentes justificadas na validação.

## Risks / Trade-offs

- Marca personalizada antiga no banco → não substituir silenciosamente; mostrar ao proprietário quais configurações devem ser editadas no painel após inventário autorizado.
- Logo escura sobre fundo escuro → validar contraste da aplicação e usar superfície de apoio sem redesenhar a arte; não identificar a fonte a partir de imagem com baixa legibilidade.
- Nome de PWA instalado demora a atualizar → explicar limitação e verificar manifesto servido; não apagar sessões/caches privados como tentativa de forçar atualização.
- Troca indiscriminada rompe operação → testes de estabilidade dos identificadores e varredura classificando produto, configuração, histórico e infraestrutura.

## Migration Plan

Concluir e validar a change de modo escuro/capas antes desta implementação. Sem migration de dados para o rebrand. Testes focados de marca/UI, templates, metadata e branding; lint/build/OpenSpec e inspeção visual. Revisão humana antes de sincronizar/arquivar. Deploy exige plano e confirmação próprios, incluindo migration 0055 e worker opcional se a base ainda não tiver sido publicada. Nenhum recurso remoto é alterado pelo registro desta proposta.
