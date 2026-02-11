import { redirect } from "next/navigation";

export default function SportHubIndex({ params }: { params: { sport: string } }) {
  redirect(`/pro/${params.sport}/overview`);
}