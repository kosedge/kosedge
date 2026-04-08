// apps/web/app/auth/error/page.tsx
import Link from "next/link";

export default function AuthErrorPage({
  searchParams,
}: {
  searchParams: { error?: string };
}) {
  const error = searchParams.error;

  const errorMessages: Record<string, string> = {
    Configuration: "There is a problem with the server configuration.",
    AccessDenied: "You do not have permission to sign in.",
    Verification:
      "The verification token has expired or has already been used.",
    Default: "An error occurred during authentication.",
  };

  const message = errorMessages[error || "Default"] || errorMessages.Default;

  return (
    <div className="min-h-screen bg-[#070A0F] text-gray-100 font-inter relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-44 left-1/2 h-[520px] w-[900px] -translate-x-1/2 rounded-full bg-kos-gold/12 blur-3xl animate-pulse-slow" />
        <div className="absolute inset-0 bg-gradient-to-b from-black/60 via-transparent to-black/70" />
      </div>

      <main className="relative z-10 flex min-h-screen items-center justify-center px-5 py-16">
        <div className="w-full max-w-md">
          <div className="bg-black/30 border border-white/12 rounded-2xl p-8 backdrop-blur-xl shadow-xl text-center">
            <h1 className="text-4xl font-bebas tracking-tight text-red-400 mb-4">
              Authentication Error
            </h1>
            <p className="text-gray-300 mb-6">{message}</p>
            <div className="flex flex-col gap-3">
              <Link
                href="/auth/signin"
                className="rounded-xl bg-kos-gold px-6 py-3 font-bold text-black hover:brightness-110 transition shadow-lg shadow-kos-gold/25"
              >
                Try Again
              </Link>
              <Link
                href="/"
                className="text-sm text-gray-400 hover:text-gray-300"
              >
                ← Back to home
              </Link>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
