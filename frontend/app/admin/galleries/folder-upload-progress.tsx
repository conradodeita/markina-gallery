import { CreditUploadFeedback, type CreditWalletSnapshot, type PhotoCreditItem } from "../credits/credit-upload-status";

export type { CreditWalletSnapshot, PhotoCreditStatus } from "../credits/credit-upload-status";

export type FolderUpload = {
  folderId: string; folderName: string;
  phase: "uploading" | "success" | "error";
  current: number; total: number; progress?: number; filename?: string; waiting?: boolean;
};

export function FolderUploadProgress({ uploads, wallet, walletState, creditItems, onVerifyPending }: {
  uploads: Record<string, FolderUpload>;
  wallet: CreditWalletSnapshot | null;
  walletState: "loading" | "ready" | "failed";
  creditItems: PhotoCreditItem[];
  onVerifyPending: () => void;
}) {
  const batches = Object.values(uploads);
  if (!batches.length) return null;
  return <div className="folder-upload-progress" aria-label="Progresso dos uploads">
    {batches.map((upload) => <div key={upload.folderId} className={`upload-status upload-status--${upload.phase}`} role="status">
      <small>Pasta {upload.folderName}</small>
      <strong>{upload.phase === "uploading" ? `Enviando foto ${upload.current} de ${upload.total}` : upload.phase === "success" ? `Upload concluído · ${upload.current} de ${upload.total} fotos` : `Upload interrompido · ${upload.current} de ${upload.total} fotos enviadas`}</strong>
      {upload.phase === "uploading" ? <progress aria-label={`Progresso do upload em ${upload.folderName}`} value={upload.progress ?? upload.current} max={upload.total} /> : null}
      {upload.filename ? <span>{upload.filename}</span> : null}
      {upload.waiting && upload.phase === "uploading" ? <small>Aguardando o processamento liberar espaço para continuar o envio.</small> : null}
    </div>)}
    <CreditUploadFeedback wallet={wallet} walletState={walletState} items={creditItems}
      visible={batches.some((upload) => upload.phase === "uploading")} onVerifyPending={onVerifyPending} />
  </div>;
}
