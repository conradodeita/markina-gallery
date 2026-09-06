## ADDED Requirements

### Requirement: Prévia facial limitada ao conjunto já autorizado

O sistema SHALL montar candidatos faciais somente com fotos cuja prévia de cliente já esteja pronta e autorizada para aquela sessão na Galeria pública e pertença ao snapshot congelado da consulta. O endpoint de prévia SHALL repetir a autorização normal por requisição e SHALL NOT aceitar resultado facial como capacidade de acesso.

#### Scenario: Referência aponta para foto não autorizada

- **WHEN** um resultado vencido, adulterado ou inconsistente contém foto fora do conjunto atualmente autorizado
- **THEN** o backend omite a candidata e nega a prévia sem revelar existência, caminho ou metadados

### Requirement: Separação entre mídia e material biométrico

Originais, prévias internas limpas, prévias protegidas, referências temporárias e embeddings SHALL usar ciclos e autorizações separados. Embeddings e classificação técnica SHALL usar uma prévia interna sem marca d'água derivada do original; essa variante SHALL NOT ser servida ou incorporada ao navegador da cliente. O navegador SHALL receber somente a prévia protegida, IDs opacos, banda pública `best|other`, posição e progresso agregado necessários ao filtro; SHALL NOT receber referência armazenada, vetor, indicadores técnicos brutos, similaridade, landmarks, caixa facial, caminho interno, variante limpa ou modelo.

#### Scenario: Cliente consulta resultado

- **WHEN** a cliente carrega ou atualiza o bloco de possíveis fotos
- **THEN** a resposta contém apenas referências autorizadas, ordem e estado de expiração, sem artefato biométrico

#### Scenario: Foto é indexada e classificada

- **WHEN** a prévia interna limpa e a prévia protegida da foto estão prontas sob uma política facial ativa
- **THEN** o worker calcula embeddings e qualidade exclusivamente a partir da variante limpa, enquanto toda rota e marcação da cliente continuam apontando somente para a variante protegida

### Requirement: Aviso de tentativa de cópia na apresentação da cliente

A apresentação da cliente SHALL manter a marca d'água na imagem visível e SHALL abrir um diálogo acessível de direitos autorais quando interceptar menu de contexto, cópia, arraste ou captura de tela detectável pelo navegador. O diálogo SHALL mencionar a Lei nº 9.610/98, artigo 79, solicitar que a imagem não seja copiada ou compartilhada sem autorização e oferecer fechamento claro. A interface SHALL NOT afirmar que consegue impedir toda captura ou download fora dos eventos controláveis pelo navegador. A prévia administrativa SHALL NOT exibir esse diálogo como se o fotógrafo fosse uma cliente.

#### Scenario: Cliente tenta abrir opções de download

- **WHEN** a cliente aciona o menu de contexto, copia ou arrasta uma prévia protegida
- **THEN** a ação padrão é cancelada e um diálogo explica a proteção autoral, sem revelar nem carregar a variante interna limpa

#### Scenario: Fotógrafo revisa a apresentação administrativa

- **WHEN** o fotógrafo interage com a prévia pelo painel administrativo
- **THEN** os controles administrativos continuam funcionais e o diálogo destinado à cliente não é exibido

### Requirement: Proteção visual global configurável

O fotógrafo SHALL poder configurar globalmente texto, tipografia, cor, tamanho, transparência, orientação, posição em uma grade de nove pontos, sombra e uma camada opcional de linhas diagonais transversais. A interface SHALL mostrar uma prévia responsiva antes do salvamento. O servidor SHALL validar os limites, persistir a configuração e reprocessar somente as prévias protegidas; originais e prévias internas de análise facial SHALL permanecer inalterados.

O texto SHALL continuar repetido pela imagem para reduzir recortes triviais, com a grade de posição definindo o alinhamento principal do padrão. As linhas de segurança SHALL usar a cor e uma opacidade proporcional à marca, sem substituir o texto.

#### Scenario: Fotógrafo salva proteção em camadas

- **WHEN** o fotógrafo escolhe texto, 60% de transparência, posição inferior central, sombra e linhas transversais
- **THEN** a prévia ao vivo representa esses controles e o processamento seguinte grava texto e linhas somente em `client_preview`

#### Scenario: Proteção global é alterada após uploads

- **WHEN** o fotógrafo salva uma configuração visual válida
- **THEN** as prévias protegidas são reenfileiradas e o índice facial baseado na variante interna limpa não é invalidado pela mudança de marca d'água

### Requirement: Exclusão do índice acompanha a origem

Excluir ou retirar uma foto da finalidade facial SHALL eliminar todos os seus embeddings e candidatos temporários, mesmo quando mídia comercial histórica precisar permanecer. Reprocessar a prévia SHALL reindexar somente se a política facial continuar ativa e válida.

#### Scenario: Galeria pública excluída com privada preservada

- **WHEN** a origem pública é excluída e fotos selecionadas permanecem em privada ou histórico
- **THEN** o índice facial e os resultados da origem são eliminados sem apagar a mídia e os snapshots que devam sobreviver comercialmente
