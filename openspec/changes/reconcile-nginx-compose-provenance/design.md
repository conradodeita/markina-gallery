# Design

## Context

Ver `proposal.md`. Em 29/10/2026, consultas SSH somente-leitura aos metadados do projeto encontraram 13 serviços ativos. Apenas o Nginx contém fonte Compose ausente: o arquivo RAW aposentado, com histórico Git disponível. Fontes da API/web/workers existem. O Nginx `ee8973e6551e`, criado em 18/10, está saudável, sem restarts, na rede `markina-gallery_internal`, com publicação `127.0.0.1:8080 → 80/tcp` e montagem em `/etc/nginx/conf.d/default.conf`. A imagem é `sha256:96868d9fa38f469a86d2f25787e43ee9ad330339d30be260aa9f5a338bb03751`.

O modelo diagnóstico construído em memória com as cinco fontes ainda existentes é recusado pela validação normal do Compose. A resolução com `--no-consistency`, usada exclusivamente para diagnóstico, encontrou `face-gemma-index-worker` sem imagem/build. A imagem e a montagem do Nginx coincidem com o modelo, mas o hash Compose diverge do rótulo ativo `96dd77fe8c7e5742f7513ba31fe58bc3091c9aa5ade7398e27d35a636483b8a8`. Isso não prova equivalência operacional. O release 0090 contém escrita/restauração temporária de `nginx.conf`; arquivos efetivamente carregados e seu backup devem ser comparados antes de recriação. HTTPS `/healthz` respondeu 200 nesta investigação.

## Goals / Non-Goals

- Preparar origem persistente e reproduzível para o Nginx e eliminar a dependência operacional de fontes aposentadas.
- Preservar todos os comportamentos efetivos do proxy próprio e comprovar o conjunto de propriedades necessário antes de publicar.
- Não restaurar RAW/Gemma, mudar integração financeira, migrar APP_ENV, alterar schema ou operar o proxy externo.
- Não transformar `--no-consistency` em caminho de aprovação ou release.

## Decisions

1. Produzir candidato dedicado ao Nginx com configuração persistente, fora de diretórios temporários, sem serviços opcionais aposentados. Recuperar a origem histórica como evidência em memória/arquivo protegido; não reintroduzir o Compose RAW no checkout ativo. Simplesmente ignorar o arquivo no coletor foi rejeitado por perder proveniência.
2. Comparar semanticamente candidato, imagem imutável e container: imagem, comando/entrypoint, variáveis necessárias sem impressão de valores, políticas de restart/health/logging/recursos, portas, montagens e bytes carregados, redes/aliases e demais propriedades operacionais. Investigar cada diferença; hash divergente ou campo desconhecido bloqueia. Defaults devem ser resolvidos com a versão Compose instalada. Candidato passa validação normal sem `--no-consistency`.
3. Não recriar antes de guardar configuração efetiva, origem, imagem, inventário completo e recuperação reproduzível em armazenamento protegido. Backup não depende do arquivo RAW ausente. Recibos públicos contêm somente hashes, estados e metadados permitidos.
4. Executar por procedimento protegido com fingerprint revalidado e trava exclusiva. A operação alcança apenas Nginx do projeto, com imagem local já existente e sem build/pull/dependências. Todos os outros containers e configurações devem manter os mesmos fingerprints; não iniciar nem remover serviços aposentados ou outros projetos.
5. A revisão desta proposta libera preparação/implementação local; o plano remoto final exige revisão específica com candidato, recuperação, impacto e snapshot atuais. A autorização anterior da transição APP_ENV não é usada como aprovação de um candidato de proxy ainda não validado.
6. As recusas do wrapper antes do módulo operacional usam uma allowlist de códigos constantes. Erros brutos de comandos de identidade/proveniência e entradas recebidas não são exibidos; códigos não reconhecidos são reduzidos a uma recusa genérica. Assim, uma guarda pode ser diagnosticada sem expor valores ou contornar a condição.

## Risks / Trade-offs

- [Perda de ajuste presente na camada gravável do Nginx] → inventariar arquivos carregados e comparar backups antes da recriação; não confiar somente na imagem/montagem.
- [Interrupção breve do ingresso] → janela informada no plano, readiness e HTTPS, recuperação imediata com imagem/configuração anteriores; não prometer zero interrupção.
- [Overlays antigos reativarem serviços aposentados] → modelo dedicado validado e alvo único sem dependências; verificar ausência de RAW/Gemma antes/depois.
- [Configuração conter segredo ou caminho sensível] → armazenamento externo protegido e logs somente de hashes/categorias; não versionar dumps de inspect ou arquivos do host.
- [A correção Compose não resolver todos os bloqueios APP_ENV] → repetir o coletor oficial após a publicação; não antecipar prontidão de credenciais.

## Migration Plan

1. Completar inventário e investigação das diferenças; produzir candidato e recuperação verificáveis com fixtures e comparação somente-leitura real.
2. CI focalizado, revisão e integração; não disparar novas suítes opcionais nem push apenas de relatos intermediários.
3. Apresentar plano atual com domínio, porta, serviços, imagem, fingerprint, indisponibilidade esperada e restauração. Aguardar aprovação específica antes de qualquer escrita remota.
4. Revalidar snapshot/trava, persistir backup e fontes, atualizar somente Nginx, verificar configuração/saúde/HTTPS e igualdade dos demais containers.
5. Em falha, recuperar Nginx anterior sem restaurar banco ou alterar tráfego de outros projetos. Se recuperação não for comprovada, parar e registrar o incidente.
6. Repetir inventário APP_ENV oficial; manter os gates e aprovações próprios das duas changes financeiras.
