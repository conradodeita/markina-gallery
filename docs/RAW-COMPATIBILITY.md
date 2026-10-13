# Matriz inicial de compatibilidade RAW

Estado em 12/10/2026. Esta matriz registra suporte declarado pelo projeto upstream; não habilita ingestão em produção nem substitui uma renderização verificada com o corpo de câmera usado pelo fotógrafo.

O lançamento estável mais recente do LightCraft encontrado foi **v0.6.0**, publicado em 11/10/2026. O artefato Linux ARM64 `.deb` tem SHA-256 `834045c5d18d69eca3d13eb313aafe10835baa59bf3ec1d3c2013ca76828f08e`; o artefato Linux x86_64 tem SHA-256 `04aa36f4d9bc4e57d4d3d0a5673261f03d3fcdd13bdd2a1e46b693f7eca03a32`. A imagem dedicada também instala RawTherapee 5.9 pelo pacote Debian Bookworm `5.9-1+b1`. Como a política do pacote remove documentos em `/usr/share/doc`, o build revalida o digest do mesmo `.deb` e extrai seus documentos e licenças de fontes/ativos para `/usr/share/doc/lightcraft/`; também baixa `assets/ATTRIBUTION.md`, `assets/app-icon/LICENSE.txt`, `assets/fonts/OFL-Inter.txt` e `docs/brand/LICENSE-brand.txt` do mesmo tag e confere cada SHA-256. O aviso de copyright do RawTherapee fica em `/usr/share/doc/rawtherapee/copyright`. Esses pins e checksums identificam os motores, não validam qualidade de renderização por câmera.

| Formato | LightCraft | RawTherapee | Gate local |
| --- | --- | --- | --- |
| DNG, CR2/CR3, ARW, NEF/NRW, RAF, RW2/RWL, PEF, ORF | LightCraft declara suporte a esses formatos no projeto; cada variante de compactação e corpo ainda precisa decodificar corretamente na versão pinada. | RawTherapee declara suporte à maioria dos RAWs via LibRaw; o conjunto exato depende da versão/build e do corpo. | Descoberta por motor/versão. Extensão não aprova câmera: a conversão precisa decodificar e produzir dimensões válidas; amostras por corpo documentam fidelidade antes de recomendar um motor. |
| Sony ARW (prioridade atual) | Para a família A7/A7R, há relatos de cor/tonalidade em A7 II, A7R II, A7 III, A7 IV e A7R IV, inclusive referências recentes após o lançamento v0.6.0. | Suporte amplo via LibRaw, mas versão, variante comprimida e corpo precisam ser conferidos no binário pinado. | Família informada pelo proprietário; geração/modelo exato e amostras ainda não estão disponíveis. O gate vale somente para recomendação de qualidade daquela combinação, sem limitar outros fabricantes/formats suportados pelo motor. |

Fontes upstream consultadas:

- [LightCraft README](https://github.com/storytold/lightcraft): formatos RAW declarados e aviso de desenvolvimento alpha.
- [LightCraft releases](https://github.com/storytold/lightcraft/releases): v0.6.0 e data do lançamento consultados.
- [LightCraft roadmap](https://github.com/storytold/lightcraft/blob/main/ROADMAP.md): detalhes de decodificação ARW.
- [LightCraft issue #461](https://github.com/storytold/lightcraft/issues/461): caso Sony A200 reportado como incompatível.
- [LightCraft issue #197](https://github.com/storytold/lightcraft/issues/197): relato de cor em Sony ILCE-6000.
- [LightCraft issue #515](https://github.com/storytold/lightcraft/issues/515): compila relatos recentes de vários corpos A7/A7R.
- [LightCraft issue #631](https://github.com/storytold/lightcraft/issues/631): relato recente de variação tonal em Sony ILCE-7RM4.
- [RawTherapee release notes](https://github.com/RawTherapee/RawTherapee/blob/dev/RELEASE_NOTES.txt): suporte declarado a formatos RAW Sony e limites de suporte.

## Primeiro alvo e compatibilidade geral

O proprietário informou **Sony A7/A7R** como primeira família para avaliação, sem geração ou corpo exato. Isso prioriza um futuro ensaio, mas não limita o produto: configurações e seletores usam a lista de formatos do motor escolhido e não possuem allowlist de fabricante/corpo. A decodificação por arquivo confirma se a variante é realmente aceita. Ainda não há ARW local autorizado para comparação estética reproduzível, então não se recomenda um motor como padrão. Quando amostras forem disponibilizadas, armazenar fora do Git e registrar hash, variante, versões/digests, dimensões/orientação e resultado sanitizado por versão.

Cada RAW pode ter até **256 MiB**, portanto arquivos acima de 47 MB são aceitos. O Nginx aplica `260m` somente à rota autenticada de fontes de foto e transmite o corpo em streaming; a API aplica o limite estrito de 256 MiB e quotas adicionais. As demais rotas conservam o limite geral de 32 MB, e o endpoint JPEG continua limitado a 25 MiB pela API.

No schema multi-tenant integrado, a migration RAW é `20261014_0078`, descendente de `20261012_0077_provider_payment_correction`. A migration `20261014_0079` materializa defaults independentes para pastas públicas já existentes. Configuração de motor e cache de releases pertencem a cada tenant; jobs persistidos incluem `tenant_id` e chave composta para a foto. O worker revalida o owner ativo antes da conversão. A cadeia completa exige PostgreSQL porque a revisão 0070 recusa SQLite no preflight; os testes locais específicos das migrations usam schema descartável com as tabelas relevantes.

## Prévia do cliente e dados móveis

O JPEG final `client_preview`, com marca-d'água e eventual ajuste de prévia, tem teto rígido de **250.000 bytes**. A codificação tenta qualidades JPEG 90, 85, 80 e 75; se necessário, reduz as dimensões progressivamente até caber no teto e registra as dimensões finais. No fluxo com análise facial, a prévia começa em até 1980 × 1980 px; sem análise, segue os limites dimensionais convencionais de até 1600 × 3200 px. A redução de resolução só ocorre quando a compressão não é suficiente.

Esse teto não se aplica ao JPEG high-res temporário usado na análise facial, à miniatura de 480 px nem ao `admin_preview`. O limite é por `client_preview`; não representa um teto para a transferência total da galeria. Carregar somente imagens visíveis e usar miniaturas antes das prévias continua sendo importante para o consumo móvel.

Builds locais do worker verificados em 12/10/2026: linux/amd64 `sha256:2d39e7d71dd249d8a2acc90042f5b5d9b6660a56bca058f26c55534cbac76dc7`; linux/arm64 `sha256:7c9a48c679e960a6bd4253c1d1883f764ec0aa509811e4b3634055b9ff05d0f9`. São manifests locais ainda não publicados; uma publicação deverá referenciar o digest exato da imagem aprovada para cada arquitetura.

## Construção e verificação do worker

O worker é opcional e fica separado da imagem da API. Em Linux ARM64 ou x86_64, a imagem `raw-development-worker` confere o SHA-256 do pacote LightCraft antes da instalação e fixa RawTherapee 5.9 no pacote do sistema. A configuração por fotógrafo permanece desativada por padrão. O job de deploy em homologação usa `--raw-development-enabled true` para incluir o overlay, construir e iniciar o worker antes da API; esse argumento não modifica `.env` nem habilita o processamento para nenhum fotógrafo. Para omitir o worker, use `--raw-development-enabled false`. Para avaliar nova versão, atualize em conjunto `LIGHTCRAFT_VERSION` e o checksum correspondente em `backend/Dockerfile.raw-development`, construa a imagem e confira `lightcraft-cli --version` e `rawtherapee-cli --version`; a API só anuncia o motor se a variável de versão de runtime estiver configurada no override do worker/API. A atualização do painel apenas consulta releases, nunca baixa ou instala programas.

Exemplo local de build e verificação (não inicia serviços):

```powershell
docker buildx build --platform linux/amd64 --load `
  -t markina-gallery-raw-development:0.6.0-amd64 `
  -f backend/Dockerfile.raw-development backend
docker buildx build --platform linux/arm64 --load `
  -t markina-gallery-raw-development:0.6.0-arm64 `
  -f backend/Dockerfile.raw-development backend
docker image inspect --format '{{.Id}} {{.Os}}/{{.Architecture}}' `
  markina-gallery-raw-development:0.6.0-amd64 `
  markina-gallery-raw-development:0.6.0-arm64
docker compose -p markina-gallery `
  -f docker/docker-compose.yml `
  -f docker/docker-compose.raw-development.yml config --quiet
```

Registre os digests resultantes por arquitetura, os checksums upstream, as versões reportadas pelos dois executáveis e o resultado do render sintético antes de aprovar uma atualização. Para testar uma versão nova, construa sob uma tag nova e aponte o ambiente de avaliação para essa tag/digest; mantenha o último digest aprovado disponível para rollback. A consulta no painel não muda o motor ativo. Ative a ingestão somente depois da avaliação e aceite humano; o caminho JPEG continua disponível se o módulo RAW for desligado.

Em falha individual, o worker aplica no máximo duas tentativas durante a retenção temporária de até 24 horas. Estado `reupload_required` significa que o staging expirou ou as tentativas se esgotaram; o fotógrafo precisa reenviar o RAW. Não copie a fonte para backup/Drive e não use os RAWs na restauração de derivados: preserve apenas proveniência permitida e os JPEGs derivados. Antes de rollout/rollback em qualquer ambiente compartilhado, identifique os serviços e volumes do projeto e siga o plano de impacto zero. A futura publicação de homologação deve usar o gate protegido `homolog`, inventário scoped do `markina-gallery`, backup lógico e migrations aditivas 0078/0079; não publicar em produção nem ativar RAW por fotógrafo sem validação controlada.
