import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { getProAccessState } from "@/lib/auth/pro";
import { isPublicProPath } from "@/lib/pro-public-paths";

export default async function ProRootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = (await headers()).get("x-pathname");
  // Soft-launch docs (e.g. NFL launch notes) stay open without Pro wall.
  if (!isPublicProPath(pathname)) {
    const access = await getProAccessState();
    if (access === "unauthenticated") {
      redirect("/auth/signin?callbackUrl=/pro/welcome");
    }
    if (access !== "authorized") {
      redirect("/pricing");
    }
  }
  return <>{children}</>;
}
