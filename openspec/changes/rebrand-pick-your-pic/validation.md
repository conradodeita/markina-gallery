# Validação e continuidade — 14/09/2026

## Implementação

- Dependência modo escuro/capas concluída localmente em 7aab730. Rebrand aplicado em seguida, sem alterar o estado remoto.
- Constantes de apresentação frontend/app/product-brand.ts e backend/app/product_brand.py. Metadata, manifesto (nome e nome curto), Apple title, interface, OTP, assuntos e aviso de e-mail, default novo de marca-d’água e export TXT usam Pick-your-Pic. O worker estático offline é coberto por teste de paridade com a constante.
- BrandLogo compartilhado em entrada/admin/biblioteca: arte enviada, proporção contain, suporte branco nos dois temas, sem texto duplicado nem filtro. Falha de arquivo/API mantém nome textual e não bloqueia navegação. Nenhum redesenho/crop ou upload da prancha enviada.
- Somente defaults foram alterados; valores salvos em banco, mensagens renderizadas existentes, consentimentos, credenciais e imagens não foram migrados. `.env.example` atualizado; nenhum ambiente real editado. OTP só armazena código criptografado e recebe a marca vigente quando o worker gera o texto para envio.

## Evidências

- 37 testes frontend aprovados: product-brand, brand-logo, install-app, theme-control, auth-entry e admin/settings/page, com `--maxWorkers=1`.
- 5 testes backend aprovados: recuperação neutra e troca de e-mail/senha, OTP do worker, entrega de e-mail existente e preservação de marca personalizada. Reexecução do fluxo de troca de e-mail aprovada após adicionar verificação do aviso enviado ao endereço anterior. Provedores falsos/sandbox, sem mensagens reais, banco SQLite temporário exclusivo.
- Next.js build e TypeScript aprovados; lint sem erros, 25 avisos (incluindo img do componente de logo, substituindo o img anterior da entrada). Nenhuma suíte completa local executada.
- OpenSpec estrito válido; git diff --check sem falhas. Diff revisado por área.
- Ruff direcionado nos módulos/testes alterados aprovado após ordenar os cinco blocos de importação que receberam a constante de marca.
- QA local com arte e dados sintéticos: 48 combinações (3 telas × 4 larguras 360/390/768/1440 × dois temas × com/sem logo), sem overflow/erro JS, marca antiga ausente no texto renderizado, logo sem filtro e contain, texto não duplicado. Capturas em .codex-tmp/theme-qa, não versionadas; representações mobile/desktop inspecionadas. Isso verifica o componente, não aprova visualmente uma arte real ainda não publicada.
- Comandos e URLs técnicas nos documentos alterados comparados com versões anteriores: preservados.

## Exceções deliberadas

Sem marca antiga de apresentação em frontend/app (excluindo fixtures de personalização), frontend/public e backend/app. Nomes internos MarkinaButton/MarkinaLink, CSS/pacote, cookies, cabeçalhos X-Markina-*, filas, caminhos e infraestrutura markina-gallery ficam estáveis. Histórico datado, migrations, protótipos/referências e changes anteriores são preservados. A decisão de marca de 22/08 em DECISOES-TECNICAS.md está identificada como supersedida. Specs principais aguardam sincronização após revisão humana.

## Publicação pendente

Não houve push, merge ou deploy nesta execução. A branch contém a base do PR #82, com migration 0055 e atualização coordenada do worker opcional ainda necessárias. Plano anterior: commit c49118d na branch codex/gallery-preview-exposure-and-installable-ui. Inventário atualizado e confirmação operacional são necessários antes de publicar; não declarar paridade antes de conferir SHA/saúde. Nenhum recurso de terceiros foi tocado.

Aplicativos já instalados dependem do ciclo de atualização do navegador/SO. Caso logo/favicon/ícone individuais ainda não tenham sido enviados, usar os uploads existentes em Configurações; a prancha composta é apenas referência. Revisão humana e arquivamento permanecem pendentes, sem tasks locais de implementação restantes.
