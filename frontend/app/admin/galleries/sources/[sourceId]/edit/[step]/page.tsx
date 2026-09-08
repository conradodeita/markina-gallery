import { redirect } from "next/navigation";

import GalleryEditor from "../gallery-editor";

const validSteps = new Set(["ajustes", "vendas", "detalhes", "imagens", "clientes"]);

export default async function GalleryEditorPage({
  params,
}: {
  params: Promise<{ sourceId: string; step: string }>;
}) {
  const { sourceId, step } = await params;
  if (!validSteps.has(step)) {
    redirect(`/admin/galleries/sources/${sourceId}/edit/ajustes`);
  }
  return <GalleryEditor sourceId={sourceId} step={step} />;
}
