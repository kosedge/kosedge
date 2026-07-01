import { redirect } from "next/navigation";
import { getProAccessState } from "@/lib/auth/pro";

export default async function ProRootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const access = await getProAccessState();
  if (access === "unauthenticated") {
    redirect("/auth/signin?callbackUrl=/pro/welcome");
  }
  if (access !== "authorized") {
    redirect("/pricing");
  }
  return <>{children}</>;
}
