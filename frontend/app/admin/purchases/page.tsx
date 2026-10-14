import { redirect } from "next/navigation";

export default function LegacyPurchasesPage() {
  redirect("/admin/payments");
}
