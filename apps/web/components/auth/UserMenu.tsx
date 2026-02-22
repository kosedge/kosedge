// apps/web/components/auth/UserMenu.tsx
"use client";

import { signOut, useSession } from "next-auth/react";
import Link from "next/link";
import { useState } from "react";

export default function UserMenu() {
  const { data: session, status } = useSession();
  const [isOpen, setIsOpen] = useState(false);

  if (status === "loading") {
    return <div className="h-10 w-10 rounded-full bg-white/10 animate-pulse" />;
  }

  if (!session) {
    return (
      <div className="flex items-center gap-3">
        <Link
          href="/auth/signin"
          className="px-4 py-2 text-sm font-semibold rounded-lg border border-kos-gold/45 text-kos-gold hover:bg-kos-gold/10 transition"
        >
          Sign In
        </Link>
        <Link
          href="/auth/signup"
          className="px-4 py-2 text-sm font-semibold rounded-lg bg-kos-gold text-black hover:brightness-110 transition"
        >
          Sign Up
        </Link>
      </div>
    );
  }

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 border border-white/12 hover:bg-white/10 transition"
      >
        {session.user.image ? (
          <img
            src={session.user.image}
            alt={session.user.name || "User"}
            className="h-8 w-8 rounded-full"
          />
        ) : (
          <div className="h-8 w-8 rounded-full bg-kos-gold flex items-center justify-center text-black font-bold text-sm">
            {session.user.name?.[0]?.toUpperCase() ||
              session.user.email[0].toUpperCase()}
          </div>
        )}
        <span className="text-sm font-medium text-gray-200 hidden sm:inline">
          {session.user.name || session.user.email}
        </span>
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute right-0 mt-2 w-48 bg-black/95 border border-white/12 rounded-xl shadow-xl z-50 overflow-hidden">
            <div className="p-3 border-b border-white/10">
              <p className="text-sm font-semibold text-gray-200">
                {session.user.name || "User"}
              </p>
              <p className="text-xs text-gray-400 truncate">
                {session.user.email}
              </p>
            </div>
            <div className="p-1">
              <Link
                href="/pro/welcome"
                className="block px-3 py-2 text-sm text-gray-300 hover:bg-white/10 rounded-lg transition"
                onClick={() => setIsOpen(false)}
              >
                Pro Dashboard
              </Link>
              <Link
                href="/pro"
                className="block px-3 py-2 text-sm text-gray-300 hover:bg-white/10 rounded-lg transition"
                onClick={() => setIsOpen(false)}
              >
                Account Settings
              </Link>
              <button
                onClick={() => {
                  setIsOpen(false);
                  signOut({ callbackUrl: "/" });
                }}
                className="w-full text-left px-3 py-2 text-sm text-red-400 hover:bg-white/10 rounded-lg transition"
              >
                Sign Out
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
