# Design

## Context

Ver [proposal.md](proposal.md) e [delta spec](specs/deployment-operations/admin-capacity-diagnostics/spec.md). O endpoint atual já entrega `CapacitySnapshot` com schema fechado, `schema_version=1`, enums sanitizados e `Cache-Control: no-store`. O componente `frontend/app/admin/capacity-diagnostics.tsx` mantém somente o snapshot atual em estado React, remove-o em qualquer nova coleta e o apresenta após autenticação administrativa. A mudança deve aproveitar esse objeto sem ampliar a superfície do backend nem criar outra fonte de verdade.

## Goals / Non-Goals

**Goals:**

- Produzir uma representação estável que preserve a semântica técnica suficiente para análise posterior.
- Manter uma única projeção explícita dos campos permitidos, fácil de testar sem acesso ao navegador.
- Diferenciar estado de cópia de estado de coleta e conservar acessibilidade por teclado e leitor de tela.

**Non-Goals:**

- Validar novamente no cliente a autoridade administrativa já aplicada pelo endpoint.
- Criar formato de intercâmbio público, compatibilidade retroativa entre versões arbitrárias ou importação do relatório.
- Adicionar fallback legado de clipboard, arquivo, compartilhamento, telemetria ou retenção do texto.

## Decisions

### 1. Serializador puro no frontend, alimentado pelo snapshot em memória

Extrair os tipos do contrato usados pelo componente e implementar um serializador TypeScript puro ao lado do diagnóstico administrativo. O componente passará diretamente seu `snapshot` atual para o serializador somente no clique. A função não fará `fetch`, não lerá DOM, storage, URL, cookies ou variáveis de ambiente e não terá efeitos colaterais.

Essa separação permite validar o texto exato com teste unitário e impede que a lógica de cópia reconstrua valores a partir da apresentação localizada. Um endpoint de exportação foi rejeitado porque duplicaria autorização, coleta e contrato; serializar o DOM foi rejeitado porque perderia fonte, escopo e valores nulos escondidos na apresentação.

### 2. Markdown canônico com formato `capacity-report/v1`

O relatório será texto UTF-8 com quebras de linha LF e cabeçalho que identifica `capacity-report/v1` e `schema_version`. Seções Markdown terão ordem fixa: coleta, pool da API, PostgreSQL, filas na ordem `media`, `preview_adjustment`, `search`, `index`, `maintenance`, orçamento global, cobertura e limitações. Listas de motivos serão ordenadas para evitar diferença causada pela ordem de origem.

Cada métrica será escrita em uma única linha com chaves estáveis e valores brutos do contrato: `value`, `unit`, `evidence`, `scope`, `source`, `collected_at` e `reason`. `value=null` e o motivo serão escritos explicitamente. Números usarão representação não localizada, timestamps permanecerão em ISO 8601 UTC e enums não serão traduzidos; assim, uma análise não depende de separador decimal ou rótulo visual. Campos booleanos e semântica de espera também serão explícitos.

O serializador enumerará propriedades individualmente e nunca usará `JSON.stringify(snapshot)` nem iteração genérica do objeto recebido. Campos adicionais serão ignorados. Uma representação JSON integral foi rejeitada porque facilitaria copiar campos futuros por acidente; o texto visual localizado foi rejeitado por não ser estável nem completo para análise.

### 3. Clipboard acionado por gesto e feedback independente

O botão **Copiar relatório** aparecerá ao lado de **Atualizar agora** apenas quando `snapshot` existir. No clique, o componente gerará o texto e chamará `navigator.clipboard.writeText` na mesma cadeia do gesto do usuário. Durante a promessa, o botão ficará impedido de iniciar cópias concorrentes; sucesso e falha produzirão mensagem curta em região `aria-live`.

O estado de cópia será limpo quando começar nova coleta, quando o snapshot for removido ou quando o componente desmontar. Recolher e reabrir a seção sem atualizar preserva o mesmo snapshot em memória e permite nova cópia. Falha do clipboard não altera o snapshot nem o estado de erro da coleta. Não haverá fallback com `execCommand`, criação de arquivo ou envio pela rede, pois esses caminhos aumentariam a superfície e teriam comportamento diferente entre navegadores.

### 4. Versões independentes e evolução explícita

`schema_version` descreve o contrato do endpoint; `capacity-report/v1` descreve a forma textual. Qualquer mudança incompatível de nomes, ordem estrutural ou semântica do relatório exigirá nova versão do formato. Adições compatíveis ao endpoint não entram automaticamente no relatório: precisam de revisão da allowlist, da spec e dos testes.

Esse desacoplamento evita que um novo campo do backend seja divulgado implicitamente e permite informar à análise qual projeção foi usada. Não será criado registro central de versões nesta mudança porque há somente um consumidor local e uma versão.

## Risks / Trade-offs

- [Relatório fica desatualizado após algum tempo] → manter os horários originais, o indicador de cache e a ação de atualização manual; copiar nunca altera a aparência de atualidade.
- [Campo novo do endpoint não aparece automaticamente] → comportamento intencional de allowlist; evolução exige revisão explícita do formato.
- [Clipboard bloqueado por permissão ou contexto do navegador] → comunicar falha sem perder o snapshot e permitir nova tentativa pelo mesmo botão.
- [Texto muito extenso para inspeção visual] → formato por seções e uma linha por métrica; sem truncamento, pois a cardinalidade atual é fixa e pequena.
- [Rótulo de sucesso anuncia relatório antigo após atualização] → limpar o estado de cópia antes de invalidar ou substituir o snapshot.

## Migration Plan

1. Implementar o serializador e seus testes unitários, depois integrar o botão e os estados acessíveis ao componente existente.
2. Atualizar a documentação operacional com formato, procedimento de cópia, interpretação e limites de privacidade.
3. Executar testes direcionados, lint, typecheck/build do frontend e validação OpenSpec antes de preparar commit e PR.
4. Publicação ou deploy seguirá o gate próprio de autorização e impacto zero do repositório; esta mudança não exige migration nem configuração.
5. A reversão remove o botão, o serializador e a documentação correspondente, sem tocar endpoint, banco, infraestrutura ou dados.
