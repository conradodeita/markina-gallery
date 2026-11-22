# Proposal

## Why

Os runtimes da API e do worker em produção reportam versões diferentes do `main` remoto atual (`6af538ecd5c46da7691fa973c33869f263945a25`). A API usa `74f61300e7a818d1605afda3db1d07574c443110`; o worker usa `c1944189761799be96eeeb921cad9906484d8b09`. O `main` é a base de implementação e não deve retroceder. A divergência é uma fronteira de compatibilidade a registrar, não autorização para alterar o runtime.

## What Changes

- Conferir todos os 144 módulos Python carregados pela API e pelo worker, classificar as diferenças contra `main`, e integrar somente mudanças necessárias para preservar contratos efetivos, sem substituir o `main` por uma revisão anterior.
- Registrar a proveniência, hashes, decisões e evidências sem dados de clientes ou segredos.
- Validar somente com testes locais/sintéticos e dependências compatíveis, sem modificar serviços ou banco remoto.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

Nenhuma. A change trata de reconciliação interna de código sem introduzir ou alterar contrato funcional do produto; `skip_specs: true` está configurado.

## Impact

Somente documentação de reconciliação, testes locais existentes e registro de continuidade. Não inclui alteração de módulos de runtime, migrations, configuração externa, deploy ou tráfego a provedores reais. A diferença entre worker e `main` inclui nove módulos e fica como gate de compatibilidade de qualquer release futura.
