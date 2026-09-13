# Validação e continuidade

Branch: `codex/gallery-preview-exposure-and-installable-ui`. Implementação autorizada pelo proprietário; nenhuma operação remota executada nesta evolução.

## Evidências locais

- Backend: 23 testes direcionados do módulo/exposição aprovados, mais um teste independente de despacho do worker entre duas galerias (24 casos); 3 avisos de depreciação preexistentes. Incluem preservação pela migration 0055, isolamento de galerias, corrida durante exposição, fonte limpa e resultado reproduzível, fallback, acesso privado e limpeza delimitada. Teste de migration repetido após desabilitar o singleton legado: aprovado.
- Frontend: 25 testes painel/Configurações/layout e 54 testes editor/PWA aprovados (79 casos distintos). Após orientação final de preto/amarelo/cinza/bege, 18 testes PWA/layout/contraste repetidos e aprovados. Texto escuro sobre amarelo supera 7:1; links/textos principais superam 4,5:1 contra branco.
- Build Next.js final aprovado com manifesto e rotas PNG. Ruff, ESLint direcionado, Typecheck e OpenSpec estrito aprovados. O estado do navegador é assinado com `useSyncExternalStore`, sem efeito com estado síncrono. Cadeia Alembic completa até `20260913_0055` em banco SQLite temporário, sem modificar bancos existentes.
- Chromium local com API simulada, em 390/768/1440 px: dashboard, etapa 04 e biblioteca sem overflow/erro JavaScript; nova paleta visualmente inspecionada e botão administrativo amarelo verificado por estilo computado. Popup iOS abre/fecha ao clique. Manifesto standalone, PNGs reais com dimensões 180/192/512, worker ativo, CacheStorage vazio e navegação offline neutra aprovados. Capturas sintéticas locais não são adicionadas ao Git.
- Não foi executada suíte completa local nem teste de carga. Suítes obrigatórias do CI permanecem intactas.
- Lint ampliado aos arquivos de integração: zero erros; sete avisos preexistentes de imagens `<img>` e parâmetros não usados nos testes do editor. Servidor local de QA parado ao concluir; arquivos sintéticos e banco temporário não integram o commit.

## Operação

A API e o worker mudam de configuração global para configuração por galeria. Antes de qualquer publicação, inventariar somente Markina, apresentar subdomínio/portas e plano sem impacto em terceiros. Parar exclusivamente `preview-adjustment-worker` antigo antes da migration e publicar/reconstruir o worker no mesmo SHA da API. O pipeline base não atualiza automaticamente esse worker; não declarar paridade sem verificar ambos. Galerias existentes preservam flag/intensidade/geração com exposição zero. A migration não agenda fotos.

Depois da cópia, a migration desliga o singleton legado para que o worker antigo falhe fechado se reiniciado por engano. Essa proteção não substitui a atualização coordenada. Documentação operacional em `docs/MODULO-AJUSTE-DE-PREVIAS.md` e `docs/APLICATIVO-INSTALAVEL.md`.

## Revisão humana

A comparação estética em fotos escolhidas e a instalação real nos aparelhos do proprietário seguem como validação humana. A prova automatizada usa dados simulados e não comprova qualidade em fotografias reais. Sem sincronização de specs principais ou arquivamento antes dessa revisão.

## Referências técnicas

- [PWA no Next.js](https://nextjs.org/docs/app/guides/progressive-web-apps).
- [ImageResponse](https://nextjs.org/docs/app/api-reference/functions/image-response).
- [Instalação contextual](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/How_to/Trigger_install_prompt).
