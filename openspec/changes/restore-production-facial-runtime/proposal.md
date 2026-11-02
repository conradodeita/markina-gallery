# Proposal: Restaurar o runtime facial em produção

> **Escopo atualizado por decisão expressa em 02/11/2026:** restauração geral autorizada sem exigir calibração prévia, preservando políticas, modelos/limiares e controles de acesso. Usar modo operacional auditável e configuração explícita, com exigência de calibração habilitada por padrão no código. Nenhuma aprovação de medição será inventada. A medição posterior usará uma pasta restrita ao cliente de teste do proprietário.

## Why

A transição ambiental de 30/10/2026 preservou os índices e desligou a busca facial; o proprietário solicitou expressamente sua reativação. A API atual não contém OpenCV, NumPy ou o cache de modelos exigido para ligar a flag, e os workers preservados pertencem ao contexto anterior de `staging`, portanto a retomada exige preparação compatível com o ambiente `production` atual.

## What Changes

- Preparar um operador próprio para restaurar um runtime facial desligado, distinto do operador de manutenção que exige runtime já ativo e schema `0082`.
- Identificar fontes, imagens, módulos, configuração e schema atuais por fingerprint; preservar o patch saudável da API e impedir inclusão do desenvolvimento SaaS não publicado.
- Preparar imagens ARM64 com dependências e modelos faciais fixados e verificados; manter YuNet/SFace, limiares, chaves e retenção existentes, sujeitos à revisão da configuração real.
- Validar primeiro em ambiente isolado sem banco, rede ou mídia de produção; preparar uma etapa `dark` que não processe galerias reais.
- Habilitar `FACIAL_PROCESSING_ENABLED=true` somente após os gates técnicos e as evidências de calibração, uso autorizado e escopo exigidas pelo contrato vigente, sem criar aprovação fictícia para satisfazer o código.
- Delimitar a etapa inicial por rollout explícito: o runtime atual admite galerias sem registro como compatibilidade legada depois da calibração; o modo de restauração deverá impedir exposição fora da allowlist, inclusive para galerias criadas durante o canary.
- Registrar fases, evidências, pendências e recuperação por serviço, sem parar bancos, proxy ou outros projetos e sem alteração de schema.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `deployment-operations`: acrescentar restauração protegida do runtime facial desligado após transição ambiental, com compatibilidade da versão atual, preparação sem tráfego real e recuperação delimitada.

O comportamento de busca e os gates da change `productionize-facial-search`, com as revisões posteriores de consentimento e referências, permanecem a base do produto. Esta proposta não substitui os gates por simples autorização da flag.

## Impact

- Operação: futuro operador e testes, manifests protegidos por digest, imagens ARM64 de API/worker e três workers faciais, inventário e recibo de fases. Os caminhos finais de código serão definidos na implementação revisada.
- Destino: somente projeto `markina-gallery` no host autorizado, `https://markina.pickyourpic.com.br`, Nginx em `127.0.0.1:8080`; nenhum serviço facial publica porta.
- Dados: schema atual `20261026_0090`, 14.267 embeddings observados apenas por contagem, sete políticas ativas e nenhum job facial ativo. Sem migration, exclusão, reindexação geral ou alteração financeira implícitas.
- Continuidade: o desenvolvimento SaaS continua na worktree atual; o pacote operacional deverá partir da versão saudável observada e de uma base Git limpa revisada. Nenhum diff local não publicado será levado a produção.
- Refatoração: reutilizar verificação de modelos, configuração e infraestrutura de operação onde forem compatíveis. Não flexibilizar o operador antigo, seus schemas fixos ou seus gates para fazê-lo aceitar um estado que ele não suporta.
- Aprovações e limites: autorização de reativação recuperada do chat “Investigue busca facial em produção”. Em 02/11 o proprietário confirmou que o acervo real já foi usado no reconhecimento e dispensou documento jurídico adicional para a retomada. Não foi apresentada métrica de calibração; o gate técnico do runtime permanece a reconciliar com evidência verdadeira. Falta revisão deste novo desenho operacional. Evidência atual em `investigation.md`.
