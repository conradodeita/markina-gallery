## Context

Ver `proposal.md`. O diálogo atual já possui inputs separados para biblioteca e câmera, declaração adulto/menor, consentimento versionado e prazos retornados pelo backend. A mudança deve preservar esse contrato e melhorar somente conteúdo e apresentação, inclusive em navegadores móveis cuja barra altera a altura visível.

## Goals / Non-Goals

**Goals:**

- Organizar o aviso em blocos curtos que expliquem finalidade, retenção, limitações e alternativa manual antes do aceite.
- Tornar o texto infantil específico para pai, mãe ou responsável legal sem substituir o gate de representação do backend.
- Usar os prazos retornados pela disponibilidade facial, evitando valores jurídicos divergentes da configuração efetiva.
- Garantir que o diálogo caiba ou role dentro de `100dvh` em mobile e que suas ações permaneçam alcançáveis.
- Preservar acessibilidade semântica, foco e mensagens de erro.

**Non-Goals:**

- Alterar hipótese legal, aprovar juridicamente o fluxo infantil ou remover os gates de produção existentes.
- Modificar API, banco, auditoria, criptografia, retenção, reconhecimento, ranqueamento ou indexação.
- Solicitar ou processar imagem de documento oficial.
- Reprojetar outras superfícies da Galeria pública.

## Decisions

### 1. Explicar processamento temporário sem usar promessa absoluta de não armazenamento

O texto informará que não existe cadastro biométrico permanente e que a referência é eliminada após o processamento ou no limite informado. Essa formulação corresponde ao ciclo técnico real, no qual o arquivo precisa existir temporariamente para o worker processá-lo.

Alternativa rejeitada: dizer que a foto “não é armazenada”. A frase seria tecnicamente imprecisa durante a janela de processamento.

### 2. Manter confirmação infantil separada do consentimento geral

A seleção `Criança ou adolescente` continuará revelando uma confirmação obrigatória de representação, enquanto o consentimento específico cobre finalidade e tratamento. Isso preserva evidência clara de cada declaração e o bloqueio já aplicado antes do envio.

Alternativa rejeitada: juntar representação, consentimento, termos gerais e outras finalidades em um único texto longo, pois reduz clareza e destaque.

### 3. Recomendar enquadramento “como foto de documento”, sem documento

A orientação usará a comparação apenas para explicar pose frontal e qualidade, acompanhada da frase explícita de que documento oficial não deve ser enviado. Isso atende à necessidade técnica sem ampliar a coleta.

Alternativa rejeitada: pedir “foto do documento”, porque criaria coleta desnecessária e risco de exposição de dados documentais.

### 4. Resolver mobile no próprio componente compartilhado do diálogo

O contêiner facial usará largura fluida limitada pela viewport, altura máxima baseada em `dvh`, rolagem vertical e espaçamento reduzido em breakpoint mobile. A área de ações se reorganizará em uma coluna adequada a toque quando não houver largura suficiente.

Alternativa rejeitada: esconder trechos do aviso em mobile, porque a redução visual não pode retirar informação necessária ao consentimento.

### 5. Validar de forma cirúrgica

Testes do componente verificarão os novos textos, gates e comportamento estrutural. A responsividade será validada com viewport mobile e inspeção visual direcionada; lint, TypeScript e OpenSpec serão executados somente no escopo aplicável.

## Risks / Trade-offs

- [O texto aumenta a altura do diálogo] → usar hierarquia curta e rolagem interna delimitada pela viewport.
- [“Foto de documento” pode ser entendida como solicitação de documento] → escrever expressamente que não é necessário nem permitido enviar documento oficial.
- [Valores padrão divergirem do backend] → renderizar os prazos efetivos informados pela API e usar fallback já existente somente quando ausentes.
- [A melhoria ser confundida com aprovação jurídica] → manter no OpenSpec o gate jurídico/humano independente para produção infantil.

## Migration Plan

1. Publicar a alteração somente no frontend, sem migration ou mudança de dados.
2. Verificar o diálogo em desktop e mobile após o build/deploy de homologação.
3. Em caso de regressão visual, reverter o commit da change; nenhum dado ou job facial precisa ser migrado ou desfeito.
