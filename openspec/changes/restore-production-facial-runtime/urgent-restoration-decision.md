# Decisão para restauração urgente — 02/11/2026

**ÚLTIMA DECISÃO, SUBSTITUTIVA:** o proprietário determinou “o mais importante é ligar o reconhecimento facial para todos independente de estar Calibrado ou não”. A decisão substitui a escolha anterior de manter medição antes da ativação. A pasta de teste não será liberada aos demais clientes; o ensaio posterior usará o cliente de teste do proprietário. Modo e controles estão especificados no início de `design.md`; nenhuma medição será declarada aprovada sem resultado.

**Esclarecimento subsequente:** o proprietário configurará o vínculo do cliente de teste pela UI existente. Não acrescentar regra de acesso, restrição de pasta ou funcionalidade nova para esse ensaio. Resultados e eventual calibração posterior serão fornecidos pelo proprietário se necessários.

## Autorização operacional recebida

O proprietário determinou resolver as pendências técnicas e seguir para ativação em produção, usando uma galeria ativa existente. A autorização substitui a limitação anterior de execução somente local para esta restauração. A recusa de transferir o backup real para o PC permanece válida; qualquer ensaio de restauração deve permanecer no servidor, isolado da base ativa.

## Estado confirmado nesta retomada

- API e worker mantêm os digests saudáveis pós-30/10; schema `20261026_0090`.
- Há seis galerias ativas com política facial ativa, modelo YuNet/SFace anterior e limiar 750; nenhuma galeria nova é necessária.
- Não há qualquer registro em `facial_calibration_approval` nem em `facial_rollout`.
- As diferenças de camada dos containers são caminhos de diretórios de mounts e ancestrais; é necessário provar o tipo e conteúdo subjacente antes de classificá-los como scaffolding descartável.
- Host ARM64 nativo com aproximadamente 20 GiB de RAM disponível e 137 GiB de disco livre no checkpoint.

## Preparação autorizada e delimitada

Preparar imagens candidatas e suporte isolado, sem trocar os consumidores ativos; ensaios usam containers próprios, recursos limitados, sem portas públicas ou banco de aplicação. O destino publicado permanece `https://markina.pickyourpic.com.br`, Nginx em `127.0.0.1:8080`. A operação eventual afeta somente API, worker e os três workers faciais; não tem migration e preserva imagens/configurações anteriores, Mercado Pago, banco, mídia e serviços de outros projetos.

## Decisão ainda necessária sobre a calibração

**Decisão recebida:** o proprietário escolheu explicitamente “Manter exigência de medição antes de ativar”. A alternativa abaixo foi rejeitada e SHALL NOT ser implementada. O proprietário considera desnecessária a preparação local porque a busca já operava; a medição pode permanecer no servidor, mas o resultado anterior não fornece ground truth nem autoriza fabricar aprovação. A localização de corpus anotado ainda não foi fornecida.

O código exige medição aprovada em produção. A autorização de ativação e o uso anterior das fotos não comprovam precisão ou aprovação de grupos. Registrar uma linha de aprovação sem medição seria evidência falsa.

Alternativa proposta, ainda NÃO aprovada nem implementada: permitir uma exceção explícita de restauração para a galeria existente autorizada, com política ativa anterior ao corte, os mesmos modelos/limiar e índices preservados; registrar o aceite da exceção separadamente de calibração. Preservar OTP, vínculo, consentimento, versões, isolamento, retenção e rollout explícito. Não declarar calibração aprovada; não ampliar a novas galerias por essa exceção. Uma medição real continua pendente para encerrar a exceção e expandir o escopo.

Essa alternativa muda um requisito do runtime e requer decisão explícita do proprietário antes do código. Até essa decisão, a fase de ativação continua recusando a ausência da medição, enquanto a preparação independente avança.
