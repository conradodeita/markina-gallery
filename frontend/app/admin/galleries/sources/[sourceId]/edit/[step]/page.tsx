import { redirect } from "next/navigation";

import GalleryEditor from "../gallery-editor";

const validSteps = new Set(["ajustes", "vendas", "detalhes", "imagens", "clientes"]);

export default async function GalleryEditorPage({
  params,
  searchParams,
}: {
  params: Promise<{ sourceId: string; step: string }>;
  searchParams: Promise<{ folder?: string | string[] }>;
}) {
  const { sourceId, step } = await params;
  const query = await searchParams;
  if (!validSteps.has(step)) {
    redirect(`/admin/galleries/sources/${sourceId}/edit/ajustes`);
  }
  return <GalleryEditor key={step} sourceId={sourceId} step={step} initialFolderId={typeof query.folder === "string" ? query.folder : ""} />;
}
