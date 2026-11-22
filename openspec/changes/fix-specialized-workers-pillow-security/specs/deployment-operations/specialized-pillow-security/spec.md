## ADDED Requirements

### Requirement: Correção isolada de Pillow nos seis especializados
O operador SHALL preparar Pillow13.0.0 para os seis workers especializados inventariados, derivando cada candidato do ID ativo anterior e alterando somente Pillow. Python, demais distribuições, fontes, pesos/modelos e binários fotográficos MUST permanecer idênticos. Atualizar o manifest SHALL NOT provar publicação.

#### Scenario: Deriva de outro componente
- **WHEN** a comparação encontra mudança de outra distribuição, Python, código ou modelo
- **THEN** o candidato é recusado e nenhum serviço ativo é substituído

### Requirement: Compatibilidade com entradas sintéticas
Os candidatos SHALL passar pip check e contratos de JPEG/EXIF/conversão/resize/normalização/proteção com padrões sem pessoas. O ensaio SHALL permanecer offline e separado de filas/dados reais. Diferenças de qualidade/formato/pixels SHALL ser avaliadas antes da publicação, sem enfraquecer assertivas para liberar o build.

#### Scenario: Peso ou foto real necessário
- **WHEN** uma validação exigir novo download de peso/modelo ou dado biométrico real
- **THEN** essa etapa é bloqueada para autorização específica e os ensaios sintéticos independentes continuam

### Requirement: Release Pillow pontual e recuperável
A aplicação SHALL exigir inventário, CI, aprovação e lock exclusivos; pausar/drenar escritores, suspender temporariamente restart policies e parar legados identificados somente ociosos, sem SIGKILL. SHALL substituir somente os seis serviços e restaurar políticas/configuração dos demais. MUST NOT executar migration, excluir dados ou alterar infraestrutura de terceiros.

#### Scenario: Parada ou saúde falha
- **WHEN** parada não é comprovada ou o candidato não fica saudável
- **THEN** o procedimento não avança e recupera as imagens/configurações anteriores sem alterar o banco, mantendo explícito que a correção de segurança não foi concluída

### Requirement: Prova efetiva e continuidade financeira
O fechamento SHALL conferir Pillow13.0.0 nos seis processos ativos e preservar schema, histórico financeiro, filas e acervo. SHALL registrar a avaliação de licença/formatos/recursos e manter a publicação Mercado Pago separada até renovar seu inventário/gates.

#### Scenario: Manifest corrigido e container antigo
- **WHEN** o arquivo declara13.0.0 mas algum processo ainda carrega12.3.0
- **THEN** a publicação permanece incompleta e o relatório identifica o serviço pendente
