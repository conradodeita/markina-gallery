import { AuthEntry } from "./auth-entry";

export default async function Home({ searchParams }: {
  searchParams: Promise<{ access_token?: string | string[]; return_to?: string | string[] }>;
}) {
  const params = await searchParams;
  const accessToken = typeof params.access_token === "string" ? params.access_token : "";
  const returnTo = typeof params.return_to === "string" ? params.return_to : "";
  return <AuthEntry key={accessToken} initialInvitation={{ accessToken, returnTo }} />;
}
