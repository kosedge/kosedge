import { redirect } from "next/navigation";

export default async function ProSportPage({
  params,
}: {
  params: Promise<{ sport: string }>;
}) {
  const { sport } = await params;
  redirect(`/pro/${sport}/overview`);
}