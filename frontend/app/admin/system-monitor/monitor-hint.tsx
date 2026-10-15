import styles from "./monitor.module.css";

const hints = {
  "Estado geral": "É o resumo dos sinais disponíveis. CPU mostra quanto o servidor está trabalhando; memória e disco mostram espaço disponível. Atenção ou Crítico pedem conferir os alertas. Dados parciais ou antigos exigem cautela; Saudável não é garantia de capacidade máxima.",
  "Filas, uploads e processamento": "Na fila são trabalhos aguardando; em processamento são trabalhos iniciados. Acompanhe se as pendências diminuem. Uma fila pode crescer durante muitos uploads. Um sinal antigo de processamento não confirma que o serviço parou: confira os alertas e o progresso.",
  "Servidor e armazenamento": "Mostra uso do servidor, rede, disco e arquivos cadastrados. Pouco espaço livre pede atenção antes de enviar mais fotos. Inventário parcial é apenas a parte verificada. Não coletado significa que não há medida disponível; não significa zero.",
  "Fotógrafos e clientes": "Expanda um fotógrafo para ver seus clientes. Para fotógrafos e clientes, verde indica interação confirmada há pouco; vermelho indica ausência de sessão válida. Atividade anterior, sessão aberta sem interação recente e dados desconhecidos ficam neutros. As cores refletem a última consulta, não presença física. Atualize a árvore para conferir de novo.",
  "Incidentes e alertas": "São condições observadas que persistiram além do limite configurado. Um alerta ajuda a encontrar o que conferir, mas não prova sozinho a causa ou uma queda do sistema. Recuperado significa que novas medidas confirmaram melhora. Use o relatório técnico para pedir análise.",
  "Capacidade e filas": "Consultar diagnóstico faz uma leitura pontual das conexões e filas; Atualizar consulta novamente. Copiar relatório permite compartilhar essa leitura com o suporte. Esse retrato não determina quantos usuários o sistema suporta nem sua capacidade máxima.",
};

export function MonitorHint({ title }: { title: keyof typeof hints }) {
  return <details className={styles.hint}>
    <summary aria-label={`Como interpretar: ${title}`}>Como interpretar</summary>
    <p>{hints[title]}</p>
  </details>;
}
