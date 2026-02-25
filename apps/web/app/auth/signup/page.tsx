// apps/web/app/auth/signup/page.tsx
"use client";

import { useState } from "react";
import { signIn } from "next-auth/react";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function SignUpPage() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      // Register user
      const res = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, name: name || undefined }),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.error || "Registration failed");
        setLoading(false);
        return;
      }

      // Auto sign in after registration
      const result = await signIn("credentials", {
        email,
        password,
        redirect: false,
      });

      if (result?.error) {
        setError("Account created but sign in failed. Please try signing in.");
        setLoading(false);
        return;
      }

      router.push("/pro/welcome");
      router.refresh();
    } catch (err) {
      setError("An error occurred. Please try again.");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#070A0F] text-gray-100 font-inter relative overflow-hidden">
      {/* Background FX */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-44 left-1/2 h-[520px] w-[900px] -translate-x-1/2 rounded-full bg-kos-gold/12 blur-3xl animate-pulse-slow" />
        <div className="absolute top-24 -left-40 h-[520px] w-[520px] rounded-full bg-kos-green/10 blur-3xl animate-pulse-slow" />
        <div className="absolute inset-0 bg-gradient-to-b from-black/60 via-transparent to-black/70" />
      </div>

      <main className="relative z-10 flex min-h-screen items-center justify-center px-5 py-16">
        <div className="w-full max-w-md">
          <div className="bg-black/30 border border-white/12 rounded-2xl p-8 backdrop-blur-xl shadow-xl">
            <div className="mb-8 text-center">
              <h1 className="text-4xl font-bebas tracking-tight text-kos-gold">
                Sign Up
              </h1>
              <p className="mt-2 text-sm text-gray-400">
                Create your Kos Edge account
              </p>
            </div>

            {error && (
              <div className="mb-4 rounded-lg bg-red-500/20 border border-red-500/50 p-3 text-sm text-red-300">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label
                  htmlFor="name"
                  className="block text-sm font-medium text-gray-300 mb-2"
                >
                  Name (optional)
                </label>
                <input
                  id="name"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full rounded-lg bg-white/5 border border-white/12 px-4 py-3 text-white placeholder-gray-500 focus:border-kos-gold/50 focus:outline-none focus:ring-2 focus:ring-kos-gold/20"
                  placeholder="Your name"
                />
              </div>

              <div>
                <label
                  htmlFor="email"
                  className="block text-sm font-medium text-gray-300 mb-2"
                >
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="w-full rounded-lg bg-white/5 border border-white/12 px-4 py-3 text-white placeholder-gray-500 focus:border-kos-gold/50 focus:outline-none focus:ring-2 focus:ring-kos-gold/20"
                  placeholder="you@example.com"
                />
              </div>

              <div>
                <label
                  htmlFor="password"
                  className="block text-sm font-medium text-gray-300 mb-2"
                >
                  Password
                </label>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={8}
                  className="w-full rounded-lg bg-white/5 border border-white/12 px-4 py-3 text-white placeholder-gray-500 focus:border-kos-gold/50 focus:outline-none focus:ring-2 focus:ring-kos-gold/20"
                  placeholder="At least 8 characters"
                />
                <p className="mt-1 text-xs text-gray-500">
                  Must be at least 8 characters long
                </p>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full rounded-xl bg-kos-gold px-6 py-3 font-bold text-black hover:brightness-110 transition shadow-lg shadow-kos-gold/25 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? "Creating account..." : "Sign Up"}
              </button>
            </form>

            <div className="mt-6 text-center text-sm text-gray-400">
              Already have an account?{" "}
              <Link
                href="/auth/signin"
                className="text-kos-gold hover:text-kos-gold/80 font-semibold"
              >
                Sign in
              </Link>
            </div>

            <div className="mt-4 text-center">
              <Link
                href="/"
                className="text-xs text-gray-500 hover:text-gray-400"
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
