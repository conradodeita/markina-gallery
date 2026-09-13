## Why

O diálogo atual de envio da referência facial não descreve com precisão suficiente o tratamento temporário realizado pelo sistema e apresenta excesso de conteúdo em telas pequenas. A cliente responsável precisa compreender, antes do aceite, a finalidade restrita à galeria, a eliminação automática, as limitações do resultado e como escolher uma referência adequada.

## What Changes

- Reformular o diálogo como aviso e consentimento específico para a busca facial, sem apresentá-lo como contrato ou prometer ausência absoluta de armazenamento durante o processamento.
- Explicar em linguagem curta que a foto e sua representação biométrica são temporárias, restritas àquela galeria, eliminadas após o processamento ou no prazo máximo informado e que o resultado não confirma identidade.
- Manter a busca opcional e informar que a seleção manual continua disponível.
- Para referência de criança ou adolescente, apresentar declaração destacada de que a cliente é pai, mãe ou responsável legal e autoriza especificamente o tratamento temporário.
- Recomendar uma foto frontal, nítida, bem iluminada, com apenas um rosto e aparência semelhante a foto de documento, sem solicitar nem induzir o envio de documento oficial.
- Reorganizar o diálogo para mobile, com conteúdo rolável dentro da viewport, ações acessíveis e sem sobreposição ou corte.
- Cobrir o conteúdo, os estados adulto/menor e a responsividade com testes direcionados, sem alterar o pipeline facial, a retenção, a API ou o banco.

## Capabilities

### New Capabilities

- `privacy-biometric/facial-consent-experience`: define a informação, o consentimento específico, a orientação de qualidade da referência e a apresentação responsiva do diálogo de busca facial da cliente.

### Modified Capabilities

Nenhuma capability consolidada é modificada; o runtime facial ainda está documentado em mudanças ativas e esta change isola o contrato de experiência e transparência da cliente.

## Impact

- Frontend da Galeria pública, especialmente `frontend/app/public-galleries/facial-search-panel.tsx` e estilos compartilhados do diálogo facial.
- Testes direcionados do componente e, se disponível, validação visual em viewport mobile.
- Sem mudança de endpoint, schema, migration, retenção configurada, indexação administrativa, reconhecimento ou autorização de acesso.
- O texto é uma implementação técnica de transparência e consentimento; a aprovação jurídica/humana de produção para fluxo infantil permanece um gate separado.
