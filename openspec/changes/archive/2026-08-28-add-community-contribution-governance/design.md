## Context

O repositório Markina Gallery tornou-se público e já possui CI, OpenSpec obrigatório e branches de integração. Não há ainda instruções externas de contribuição, código de conduta ou modelos que orientem a abertura de issues e pull requests. Consulte `proposal.md` para a motivação.

## Goals / Non-Goals

**Goals:**

- Dar a contribuidoras e contribuidores um fluxo único, verificável e acolhedor para fork, issue e pull request.
- Proteger o produto e a infraestrutura por orientações explícitas sobre OpenSpec, testes, privacidade, segurança e revisão humana.
- Reduzir triagem repetitiva usando modelos curtos e campos que revelem escopo, validação e impacto.

**Non-Goals:**

- Não conceder acesso de escrita, acesso a homologação, secrets, banco de dados ou produção a colaboradores externos.
- Não automatizar a aceitação de pull requests nem escolher uma licença sem decisão da proprietária.
- Não substituir `AGENTS.md`, as specs OpenSpec ou os controles de CI existentes.

## Decisions

### Documentação em arquivos padrão do GitHub

Usar `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` e `.github` para que o GitHub os apresente naturalmente a pessoas que abrem issues ou pull requests. O guia referencia, sem duplicar, as regras técnicas de `AGENTS.md` e OpenSpec.

Alternativa descartada: concentrar regras apenas no README. Ela não oferece orientação contextual durante issue/PR e mistura apresentação do produto com governança.

### Contribuição via fork e pull request para `develop`

Colaboradores externos trabalham em fork e abrem PR para `develop`; nenhuma contribuição presume permissão de push ou deploy. O modelo exige uma change OpenSpec para alteração de comportamento e evidências de validação.

Alternativa descartada: permitir branches diretamente no repositório principal. Isso amplia desnecessariamente a superfície de escrita e dificulta separar trabalho externo de mudanças operacionais.

### Triagem focada em segurança e escopo

Os modelos perguntarão por impacto em privacidade, dados, segurança, migrations e deploy, e indicarão que segredos e dados pessoais nunca devem ser enviados. O código de conduta estabelece comunicação respeitosa e uma via privada para reportes de segurança.

Alternativa descartada: formulário excessivamente detalhado. Ele elevaria a barreira para pequenas correções e não substituiria a revisão técnica.

## Risks / Trade-offs

- [Documentação desatualizada] → referenciar fontes de verdade do repositório em vez de reproduzir decisões técnicas.
- [Issue com vulnerabilidade ou dado pessoal] → orientar reporte privado e remover modelos que incentivem publicar conteúdo sensível.
- [Contribuições grandes sem escopo] → exigir proposta OpenSpec antes da implementação e permitir que mantenedores fechem/redirecionem PRs fora do roadmap.
- [Ausência de licença] → informar claramente que a licença é pendência humana e não declarar permissões jurídicas não aprovadas.
