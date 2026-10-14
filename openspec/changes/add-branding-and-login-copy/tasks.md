## 1. Dados e segurança

- [x] 1.1 Modelar configurações de marca e validar upload de ativos.
- [x] 1.2 Criar APIs administrativas autorizadas para marca e textos de login.

## 2. Interface

- [x] 2.1 Criar tela administrativa de configuração com preview e fallback.
- [x] 2.2 Aplicar marca, favicon e textos validados na tela de entrada.

## 3. Qualidade

- [x] 3.1 Cobrir autorização, validação, fallback e acessibilidade com testes.
- [x] 3.2 Validar build, OpenSpec e documentação.

## Registro de reconciliação — 2026-08-28

- O commit `669d888` introduz a tabela e migration de configurações, APIs autenticadas de leitura/atualização dos textos de entrada, validação de texto simples, uma tela administrativa inicial e consumo dos textos pela entrada. O teste `test_branding_public_defaults_and_admin_plain_text_update` cobre valores padrão, autorização administrativa e rejeição de script.
- Nenhuma checkbox foi marcada nesta reconciliação: upload, validação e serviço de logo/ícone/favicon ainda não estão implementados; por isso as tarefas 1.1, 1.2, 2.1 e 2.2 permanecem parcialmente atendidas. A cobertura de fallback/acessibilidade e a validação final de build, OpenSpec e documentação também não possuem evidência completa para 3.1 e 3.2.
- A implementação foi concluída nesta rodada: o servidor mantém os ativos em raiz isolada, valida conteúdo por Pillow, MIME, dimensão e tamanho, e só expõe caminhos fixos derivados da configuração. A área administrativa permite enviar cada ativo e indica o fallback; a entrada aplica logo, favicon e `apple-touch-icon`, preservando os textos padrão quando a API falha. As checkboxes foram marcadas com evidência objetiva: `test_branding_public_defaults_and_admin_plain_text_update` e `test_branding_assets_require_admin_and_validate_storage` passaram em banco SQLite temporário; `app/admin/settings/page.test.tsx` e `app/auth-entry.test.tsx` passaram (4 testes); lint focal passou sem erros (2 avisos existentes de `no-img-element`), `tsc --noEmit`, `next build`, `git diff --check` e `openspec validate add-branding-and-login-copy --strict --no-interactive` passaram.
