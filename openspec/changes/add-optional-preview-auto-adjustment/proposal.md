## Why

O fotógrafo deseja melhorar automaticamente a apresentação dos JPEGs na vitrine, preservando o original e a edição final externa. A avaliação precisa ser reversível: desligar o módulo restaura a prévia convencional sem reprocessar fotos nem desfazer outras funcionalidades.

## What Changes

- Módulo opcional de ajuste de prévias, desligado por padrão, com chave administrativa persistida e efeito nas próximas requisições, sem deploy.
- Motor substituível; primeira integração com RawTherapee CLI e perfil moderado. IA permanece candidata para comparação posterior, sem prometer qualidade ou capacidade ainda não medidas.
- Trabalhos duráveis independentes da indexação facial, com limites, retentativa explícita, progresso e fallback para a prévia convencional.
- Derivado tratado separado, com proteção aplicada depois do ajuste, preservando original, prévia convencional e entrada facial.
- Controles administrativos de ativação, processamento de galeria existente e comparação antes/depois. Nenhuma nova etapa para o cliente.
- Procedimento de desativação e higienização exclusivo do módulo.

## Capabilities

### New Capabilities

- `media-storage/optional-preview-adjustment`: geração, seleção, operação e reversão de prévias ajustadas.

### Modified Capabilities

Nenhuma. As garantias de autorização, metadados e proteção de `media-storage/protected-previews` continuam aplicáveis às duas versões.

## Impact

Backend de mídia e entrega autenticada, duas tabelas aditivas, worker opcional, configuração administrativa e testes focados. RawTherapee fica na imagem exclusiva do worker; API e processamento convencional não ganham essa dependência. Após a implementação local, o proprietário autorizou push, merge e deploy em homologação com o módulo desligado. A publicação segue o inventário operacional; ativação sobre fotos reais e aceitação estética permanecem separadas.

## Non-goals

Editar originais/entregas, importar RAW, gerar ou reconstruir rostos, alterar busca facial, treinar modelos, enviar imagens a terceiros ou aplicar tratamento retroativo automático ao ativar.
