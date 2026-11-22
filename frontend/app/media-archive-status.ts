export type MediaArchiveStatus =
  | "available"
  | "archiving"
  | "archived"
  | "restoring"
  | "reconciliation_required"
  | "deleting"
  | "deleted"
  | "unavailable"
  | "expired";

const labels: Record<MediaArchiveStatus, string> = {
  available: "Mídia disponível",
  archiving: "Envio ao arquivo frio em andamento",
  archived: "Arquivada no arquivo frio",
  restoring: "Recuperação em andamento",
  reconciliation_required: "Disponibilidade em conferência",
  deleting: "Remoção da mídia em andamento",
  deleted: "Mídia indisponível",
  unavailable: "Mídia indisponível",
  expired: "Prazo de acesso encerrado",
};

export function mediaArchiveStatusLabel(status: MediaArchiveStatus): string {
  return labels[status];
}

export function folderAccessStatusLabel(folder: {
  status: string;
  media_state?: MediaArchiveStatus;
  access_expires_at?: string | null;
}, at: number): string {
  if (folder.media_state && folder.media_state !== "available") return mediaArchiveStatusLabel(folder.media_state);
  if (folder.status !== "released") return "Preparando prévias";
  if (folder.access_expires_at && Date.parse(folder.access_expires_at) <= at) return labels.expired;
  return "Disponível";
}

export function clientMediaStatusMessage(status: MediaArchiveStatus): string | null {
  switch (status) {
    case "available":
      return null;
    case "archiving":
      return "Esta pasta está sendo enviada ao arquivo frio. As fotos voltarão a ficar disponíveis após a conferência, se necessário.";
    case "archived":
      return "Esta pasta está no arquivo frio. Sua seleção continua salva; fale com o fotógrafo para solicitar a recuperação.";
    case "restoring":
      return "O fotógrafo iniciou a recuperação desta pasta. As fotos voltarão a ficar disponíveis após a conferência.";
    case "reconciliation_required":
      return "A disponibilidade desta pasta está em conferência. Entre em contato com o fotógrafo.";
    case "deleting":
    case "deleted":
      return "Esta mídia não está disponível no momento. Entre em contato com o fotógrafo.";
    case "unavailable":
      return "Esta imagem não está disponível no momento. Entre em contato com o fotógrafo.";
    case "expired":
      return "O prazo desta pasta terminou e as fotos não estão disponíveis no momento.";
  }
}
