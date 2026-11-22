## ADDED Requirements

### Requirement: Prévia facial limitada ao conjunto já autorizado

O sistema SHALL montar candidatos faciais somente com fotos cuja prévia de cliente já esteja pronta e autorizada para aquela sessão na Galeria pública e pertença ao snapshot congelado da consulta. O endpoint de prévia SHALL repetir a autorização normal por requisição e SHALL NOT aceitar resultado facial como capacidade de acesso.

#### Scenario: Referência aponta para foto não autorizada

- **WHEN** um resultado vencido, adulterado ou inconsistente contém foto fora do conjunto atualmente autorizado
- **THEN** o backend omite a candidata e nega a prévia sem revelar existência, caminho ou metadados

### Requirement: Separação entre mídia e material biométrico

Originais, prévias limpas, prévias protegidas, referências e embeddings SHALL manter acesso e retenção separados. Análise facial usa derivado limpo, nunca entregue à cliente; respostas ao navegador incluem somente prévia protegida e metadados mínimos para resultados e progresso, sem artefatos biométricos ou caminhos internos.

#### Scenario: Cliente consulta resultado

- **WHEN** a cliente carrega ou atualiza o bloco de possíveis fotos
- **THEN** a resposta contém referências autorizadas, banda `best|other`, posição, expiração e progresso agregado; não inclui referência, vetor, score, landmarks, caixa facial, caminho interno, prévia limpa, modelo ou indicador técnico bruto

#### Scenario: Foto é indexada e classificada automaticamente

- **WHEN** a prévia interna limpa e a prévia protegida da foto estão prontas em ambiente facial habilitado
- **THEN** o sistema garante a política interna sem ação do fotógrafo e o worker calcula embeddings e qualidade exclusivamente a partir da variante limpa, enquanto toda rota e marcação da cliente continuam apontando somente para a variante protegida

### Requirement: Aviso de tentativa de cópia na apresentação da cliente

A prévia da cliente SHALL manter a marca d'água e abrir diálogo acessível sobre direitos em tentativas de cópia detectáveis pelo navegador; deve permitir fechar e não prometer impedir toda captura/download. A prévia administrativa SHALL manter seus controles sem mostrar mensagem dirigida à cliente.

#### Scenario: Cliente tenta abrir opções de download

- **WHEN** a cliente aciona menu de contexto, cópia, arraste ou captura de tela detectável pelo navegador
- **THEN** a interface cancela eventos controláveis e abre diálogo acessível que cita a Lei nº 9.610/98, artigo 79, pede que a imagem não seja copiada/compartilhada sem autorização e oferece fechamento; não promete impedir capturas fora do navegador nem carrega a variante limpa

#### Scenario: Fotógrafo revisa a apresentação administrativa

- **WHEN** o fotógrafo interage com a prévia pelo painel administrativo
- **THEN** os controles administrativos continuam funcionais e o diálogo destinado à cliente não é exibido

### Requirement: Proteção visual global configurável

O fotógrafo SHALL configurar texto e estilo globais da marca d'água: tipografia, cor, tamanho, transparência, orientação, grade de nove posições, sombra e linhas diagonais opcionais. UI SHALL pré-visualizar; servidor SHALL validar, salvar e reprocessar só prévias protegidas. Texto se repete; linhas usam cor/opacidade proporcionais, sem substituir o texto; originais e derivados limpos permanecem intactos.

#### Scenario: Fotógrafo salva proteção em camadas

- **WHEN** o fotógrafo escolhe texto, tipografia, cor, tamanho, transparência, orientação, posição inferior central, sombra e linhas diagonais
- **THEN** a prévia responsiva repete o texto alinhado pela grade; linhas usam a cor e opacidade proporcional. Só a prévia protegida é reprocessada, sem mudar original ou derivado facial limpo

#### Scenario: Proteção global é alterada após uploads

- **WHEN** o fotógrafo salva uma configuração visual válida
- **THEN** as prévias protegidas são reenfileiradas e o índice facial baseado na variante interna limpa não é invalidado pela mudança de marca d'água

### Requirement: Exclusão do índice acompanha a origem

Excluir ou retirar uma foto da finalidade facial SHALL eliminar todos os seus embeddings e candidatos temporários, mesmo quando mídia comercial histórica precisar permanecer. Reprocessar a prévia SHALL reindexar somente se a política facial continuar ativa e válida.

#### Scenario: Galeria pública excluída com privada preservada

- **WHEN** a origem pública é excluída e fotos selecionadas permanecem em privada ou histórico
- **THEN** o índice facial e os resultados da origem são eliminados sem apagar a mídia e os snapshots que devam sobreviver comercialmente
