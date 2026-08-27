# Homologação — interface original de galerias

## Escopo

- Dashboard e navegação administrativa autoral.
- Acervos-fonte, galerias privadas, ajustes, clonagem e exclusão segura.
- Pastas/lotes em preparação, upload JPEG, processamento, liberação e bloqueio posterior.
- Biblioteca, rodadas liberadas, grade protegida, estados de compra, seleção, favoritos, comentários e histórico da cliente.

## Evidências locais

- `ruff check backend/app backend/tests`: aprovado.
- `pytest backend/tests -q`: 32 aprovados; 4 avisos de depreciação do adaptador SQLite do Python 3.12.
- `npm run lint`: sem erros; 6 avisos não bloqueantes relacionados a prévias autenticadas e navegações antigas.
- `npm test`: 11 aprovados.
- `npm run build`: aprovado, incluindo TypeScript e geração das rotas.
- `openspec validate launch-original-gallery-interface --strict`: aprovado.

## Inventário e impacto zero

- Projeto alvo: somente `markina-gallery` em `/opt/markina-gallery`.
- Compose obrigatório: `--env-file docker/.env.homolog -p markina-gallery -f docker/docker-compose.yml`.
- Domínio alvo: `https://markina-homolog.duckdns.org`.
- Proxy: preservar `npm-network` e alias `markina-homolog-nginx`.
- ClearBudget em `/home/ubuntu/docker/clearbudget`: fora do escopo; nenhum container, volume, rede, imagem ou banco será alterado.
- Não executar prune, `compose down`, remoção de volume ou comando Docker global.

## Dados e roteiro sintéticos

1. Criar cliente sintética, acervo e galeria privada vazia.
2. Criar pasta em preparação e enviar JPEGs sem dados reais de crianças.
3. Confirmar progresso e prévias administrativas.
4. Liberar a pasta para a galeria privada e confirmar bloqueio de novos uploads.
5. Entrar como cliente sintética e validar biblioteca, estados, seleção, favorito, comentário e expiração.
6. Confirmar que outra cliente não acessa a galeria nem seus metadados.

## Rollback

- Registrar commit implantado e imagem anterior antes do deploy.
- Em falha, restaurar somente a imagem anterior do `markina-gallery` e reaplicar o Compose obrigatório sem derrubar o projeto.
- Banco só será restaurado se rollback de código não bastar, usando backup exclusivo do Markina.
