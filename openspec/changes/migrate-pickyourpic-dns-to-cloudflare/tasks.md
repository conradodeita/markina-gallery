# Tasks

## 1. Preparação preservadora

- [x] 1.1 Conferir zona autenticada, DNSSEC e referência DNS/HTTPS/Oracle somente por leitura; registrar inventário e limites em migration-plan.md.
- [x] 1.2 Documentar spec, plano de impacto zero, recuperação e avaliação proporcional de refatoração; conferir coerência com a decisão vigente.
- [x] 1.3 Preparar zona Cloudflare Free pendente, com os dois registros DNS-only e TTL 3600; registrar nameservers e comparar respostas diretas com o inventário (quatro consultas corretas, tabela persistida e estado pending).
- [x] 1.4 Confirmar procedimento do Registro.br para DS anterior, caches e limites da preservação da zona/chaves, sem salvar troca; registrar fontes oficiais e validar os artefatos com OpenSpec strict.

## 2. Transição pública autorizada

Operação aceita no painel às 16:45 BRT de 05/11/2026; Registro.br impôs aproximadamente duas horas de transição. 18:45 BRT era o primeiro horário de conferência, não uma garantia de propagação. As tasks 2.2–2.4 foram concluídas com evidência datada em `migration-plan.md`; a revisão de integração está registrada na task 3.1.

- [x] 2.1 Apresentar plano concreto e receber aprovação operacional, incluindo confirmação específica para eventual suspensão temporária do DNSSEC; resposta expressa de 05/11/2026 registrada no plano.
- [x] 2.2 Executar somente a sequência DNSSEC/delegação aprovada após verificar pré-condições, compatibilidade e caches; registrar respostas e horários sem parar serviços. Sequência enviada e aceita em 05/11/2026; em 07/11/2026, resolvers independentes retornavam a delegação Cloudflare. A janela sem DS foi temporária e autorizada; a reativação e validação constam na task 2.4. Ver `migration-plan.md`, seções de retomada e validação final. Nenhum serviço foi parado.
- [x] 2.3 Confirmar nova autoridade, A/TTL e HTTPS de markina em resolvers independentes; registrar divergências e smoke autorizado sem transação real. Em 07/11/2026, 1.1.1.1 e Google DoH/8.8.8.8 retornaram os NS Cloudflare; os A raiz/markina e as respostas dos dois NS autoritativos preservaram `132.145.193.169`, TTL 3600; `markina` respondeu HTTPS 200 com TLS válido e a raiz manteve o 404 de referência. Ver `migration-plan.md`, seção “Retomada pública — 07/11/2026”.
- [x] 2.4 Ativar DNSSEC Cloudflare e publicar o DS correspondente com autorização aplicável; comprovar cadeia válida e ausência de SERVFAIL em resolvers validadores. Registro.br, Cloudflare DoH e Google DoH confirmaram DS 2371 13 2; ambos validadores públicos retornaram `AD=true` para DS e A raiz/markina, sem SERVFAIL observado. HTTPS markina 200 e raiz 404 histórico, ambos com TLS válido. Ver `migration-plan.md`, seção “Validação DNSSEC final — 07/11/2026”.

## 3. Revisão de integração

- [x] 3.1 Revisar evidências finais, escopo/diff e limitações, confirmar preservação dos serviços e executar validação OpenSpec strict; deixar curinga/proxy/provisionamento SaaS explicitamente em escopo posterior. Change exclusivamente operacional/documental: sem diff de código, `.env`, Oracle ou dados. `openspec validate migrate-pickyourpic-dns-to-cloudflare --strict` passou após a revisão. Curinga, proxy e provisionamento SaaS permanecem fora desta change.

## Workflow follow-up

- Sincronizar spec principal e arquivar somente após revisão humana.
