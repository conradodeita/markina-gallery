## Context

Candidato: branch `codex/unified-client-cart-and-pix`, baseada em `235d2ff6e17fe666f63754df92f829c9d9fdb4f5`. Migration aditiva `20260919_0057` → `20260920_0058`. Registrar o SHA final da PR antes da publicação. Esta change não foi implantada e não altera secrets ou arquivos `.env`.

## Inventário e impacto

Inventário local consultado em 20/09/2026: três containers Evolution existentes (API v2.3.7, PostgreSQL 15 e Redis 7), sem publicação de porta adicional. Foram preservados. A validação desta change usa apenas `markina-gallery-unified-pix-test`, PostgreSQL 17, porta restrita `127.0.0.1:55458`, bancos descartáveis `markina_unified_test` e `markina_unified_migration_test`. Preview local em `127.0.0.1:3132`; dados e imagens sintéticos, sem corpus facial ou envio externo.

Último inventário remoto registrado em `../persist-device-push-choice/deployment.md`: checkout `/opt/markina-gallery`, SHA base acima, revisão 0057, 13 serviços do projeto `markina-gallery`, entrada `127.0.0.1:8080`, subdomínio `markina-homolog.duckdns.org`. Esse registro é referência anterior, não uma inspeção remota desta execução. Antes do deploy autorizado, revalidar SHA, saúde, revisão, portas, mounts e identidade dos containers de terceiros (Firefly, Nginx Proxy Manager e Portainer).

Plano de impacto restrito: usar somente o workflow existente de homologação e o projeto/Compose Markina. Nenhuma alteração de DNS, certificados, firewall, proxy compartilhado, volume ou container de terceiros; nenhuma porta nova no Oracle. Preservar configurações de push, high-res e branding. Não usar prune, down, limpeza de banco, restore ou migration destrutiva. A indisponibilidade transitória dos serviços próprios durante sua recriação deve ser acompanhada pelos healthchecks existentes; impacto zero aqui significa preservar integralmente os outros projetos.

## Sequência de publicação e rollback

1. Revisar diff e migration, obter CI verde no SHA da PR e autorização aplicável de homologação. Quando somente CI estiver pendente, parar e aguardar retorno do proprietário; sem polling ou automação.
2. Revalidar inventário e apresentar este plano atualizado. Manter gates do GitHub Environment; uma interação exclusiva do proprietário não pode ser contornada por SSH.
3. Usar backup pré-deploy e registro `last-healthy.sha` do fluxo existente. Aplicar 0058 e publicar API, workers e web compatíveis como um único candidato. Não executar migrations no banco real durante testes locais.
4. O script `scripts/deploy-homolog.sh` já bloqueia rollback automático quando o schema mudou (`MIGRATION_CHANGED` / `SCHEMA_ROLLBACK_UNSAFE`). Após 0058, corrigir adiante ou usar somente binário compatível com agrupamentos. A migration também recusa downgrade quando existe qualquer `payment_group`. Não voltar à versão 0057 depois de escrita agrupada, nem apagar grupos para viabilizar downgrade.
5. Conferir saúde, SHA local/servidor/imagens, revisão 0058, volumes de branding, canais e terceiros. Falhas de transporte não devem desfazer o registro financeiro. Registrar URLs/execução de CI e evidências de paridade, sem expor credenciais.

## Cenários de aceite

- Cliente A: selecionar fotos em duas galerias, com duas pastas em uma delas. Navegar entre Galerias, Carrinho e Compras; repetir após logout/login e em outro navegador. Seleção e contador devem vir da mesma identidade no servidor.
- Abrir Carrinho diretamente na revisão, ver nomes/pastas/fotos, subtotais e somente um total/PIX/QR/Informar pagamento. A listagem de galerias não pode duplicar cards de carrinho.
- Alterar seleção em outra aba e tentar informar a revisão anterior: conflito e nova conferência obrigatória. Uma resposta de rede incerta deve permitir repetição sem criar outra comunicação.
- Informar pagamento: congelar todos os integrantes e consumir apenas suas seleções. Confirmar, corrigir silenciosamente e recusar pelo admin, incluindo atalho filtrado por uma galeria; conferir alcance explícito e todos os estados.
- Ver grupo uma vez no histórico, com fotos/entregas individuais e compra antiga separada. Criar seleção nova sem modificar a compra anterior. Cliente B não pode consultar ou comunicar pagamentos de A.
- Expirar uma galeria ou retirar preço: mostrar impedimento sem total parcial pagável; permitir remoção explícita. Configuração PIX ausente bloqueia início. Mudança global mantém PIX já iniciado; snapshot legado divergente oferece recuperação pelo link do pedido anterior. Código de valor fixo incompatível bloqueia combinação.
- Em mobile e desktop, testar teclado, foco ao abrir/fechar prévias, leitor de tela real, safe area e botão de pagamento visível acima da navegação. A validação automatizada local não substitui o aceite em dispositivo real, OTP nem confirmação bancária manual.

## Gates pendentes

Deploy e aceite humano desta change ainda não executados. Sincronização das specs principais e arquivamento ficam após essa revisão, conforme `AGENTS.md`. A implementação local continua independente desses gates.
