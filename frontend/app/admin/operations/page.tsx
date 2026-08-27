import { redirect } from "next/navigation";

export default async function LegacyOperationsPage({
  searchParams,
}: {
  searchParams: Promise<{ parent_gallery_id?: string }>;
}) {
  const { parent_gallery_id: parentGalleryId } = await searchParams;
  if (parentGalleryId) {
    redirect(`/admin/galleries/sources/${parentGalleryId}/edit/imagens`);
  }
  redirect("/admin/galleries");
}
