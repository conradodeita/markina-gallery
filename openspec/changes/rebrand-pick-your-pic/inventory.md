# Inventário de marca — 14/09/2026

A dependência dark-mode-and-landscape-covers foi concluída/validada localmente no commit 7aab730, sem publicação. A aprovação de implementação permite seguir o rebrand, não libera deploy.

| Categoria | Substituições / tratamento |
| --- | --- |
| Produto frontend | Entrada, cabeçalhos admin/cliente (inclusive MARKINA + Gallery fragmentado), account-action, galerias, estatísticas, configurações, prévias, validation-ui, metadata, manifesto e offline: Pick-your-Pic. |
| Produto backend | Título API, assunto/corpo de recuperação/verificação administrativa, OTP nos adaptadores/worker, nome amigável do export e defaults novos de marca-d’água. |
| Arte | Logo obtida por /branding e uploads de logo/favicon/app-icon são preservados. Prancha enviada não será recortada/redesenhada nem publicada automaticamente. |
| Personalização | Valores persistidos de mensagens, marca-d’água, nomes, consentimentos e fotos permanecem intactos. Atualização de defaults em código não substitui banco ou arquivos. |
| Documentação vigente | README, instruções, roadmap, diretrizes e manuais operacionais correntes, contexto OpenSpec: novo produto com indicação explícita de infraestrutura legada. |
| Histórico | Migrations, changes arquivadas, atas/evidências datadas, commits e referências históricas não são renomeados. |
| Identificadores técnicos | Manter markina-gallery, domínio homolog, URLs, caminhos de documentos, pacote npm, Compose, cookies, cabeçalhos X-Markina-*, queues, storage, service worker /markina-sw.js, nomes internos MarkinaButton/MarkinaLink e prefixos CSS. |

Nenhuma substituição em massa de banco, secret ou ambiente real; .env.example é somente exemplo versionado. Mensagens já renderizadas/enfileiradas permanecem como estão; novas mensagens padrão usam a nova marca.
