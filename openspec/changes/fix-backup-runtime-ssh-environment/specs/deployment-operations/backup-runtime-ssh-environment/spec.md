## ADDED Requirements

### Requirement: Canal SSH do ambiente protegido de backup

O job de operação SHALL resolver sua configuração SSH no ambiente protegido `production`, verificar a identidade do destino em relação ao inventário e usar uma credencial vinculada ao wrapper de comandos fixos. A leitura posterior SHALL usar o mesmo canal validado. A instalação SHALL preservar os gates de SHA, CI, fingerprint, pacote e aprovação de ambiente.

#### Scenario: Configuração ausente ou destino divergente

- **WHEN** a configuração obrigatória está ausente ou host, porta ou usuário divergem do inventário
- **THEN** o workflow MUST abortar antes do download ou da chamada SSH e emitir diagnóstico fixo sem valores secretos

#### Scenario: Credencial restrita a verificar

- **WHEN** a associação entre a credencial de produção e o wrapper de backup não foi comprovada
- **THEN** uma leitura protegida SHALL comprovar o canal antes de qualquer tentativa mutável e o workflow MUST NOT usar credencial genérica como fallback

#### Scenario: Falha na chamada de instalação

- **WHEN** a chamada SSH de instalação termina sem sucesso
- **THEN** o workflow SHALL registrar uma categoria fixa para falha de transporte, recusa estruturada do instalador ou outra falha remota, e MUST NOT publicar a saída bruta da chamada

#### Scenario: Alias lib64 padrão do venv ARM64

- **WHEN** o Python cria `venv/lib64` como link relativo para o diretório real irmão `lib` dentro da árvore privada de staging
- **THEN** o instalador SHALL preservar somente esse alias esperado após validar metadados e destino; links divergentes, alvos inseguros e outros links na árvore MUST ser recusados
