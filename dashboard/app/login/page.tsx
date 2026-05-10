"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { setAuthToken } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

  const login = async () => {
    if (!apiBaseUrl) {
      setError("Set NEXT_PUBLIC_API_BASE_URL in the dashboard env.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const body = new URLSearchParams();
      body.set("username", email);
      body.set("password", password);

      const response = await fetch(`${apiBaseUrl}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
          "ngrok-skip-browser-warning": "true"
        },
        body
      });

      if (!response.ok) {
        throw new Error("Invalid credentials.");
      }

      const payload = (await response.json()) as { access_token: string };
      setAuthToken(payload.access_token);
      router.push("/monitor");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed.");
    } finally {
      setLoading(false);
    }
  };

  const register = async () => {
    if (!apiBaseUrl) {
      setError("Set NEXT_PUBLIC_API_BASE_URL in the dashboard env.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${apiBaseUrl}/auth/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "ngrok-skip-browser-warning": "true"
        },
        body: JSON.stringify({ email, password, role: "viewer" })
      });

      if (!response.ok) {
        throw new Error("Registration failed.");
      }

      await login();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 grid-glow opacity-60" />
      <div className="mx-auto flex min-h-screen w-full max-w-xl flex-col gap-8 px-6 pb-20 pt-16">
        <header className="flex items-center justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.4em] text-sky/70">
              Hawk Eye
            </p>
            <h1 className="font-display text-3xl text-fog">
              Operator sign-in
            </h1>
          </div>
          <Link href="/" className="text-xs uppercase tracking-widest text-fog/60">
            Home
          </Link>
        </header>

        <div className="glass rounded-3xl p-8">
          <div className="flex flex-col gap-4 text-sm text-fog/70">
            <label className="flex flex-col gap-2">
              <span className="text-xs uppercase tracking-widest text-fog/50">
                Email
              </span>
              <input
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className="rounded-2xl border border-fog/10 bg-coal px-4 py-2 text-fog"
              />
            </label>
            <label className="flex flex-col gap-2">
              <span className="text-xs uppercase tracking-widest text-fog/50">
                Password
              </span>
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="rounded-2xl border border-fog/10 bg-coal px-4 py-2 text-fog"
              />
            </label>
            {error ? <p className="text-xs text-ember">{error}</p> : null}
            <div className="flex flex-wrap gap-3">
              <button
                onClick={login}
                disabled={loading}
                className="rounded-full bg-sky px-5 py-2 text-xs uppercase tracking-widest text-ink disabled:opacity-60"
              >
                Sign in
              </button>
              <button
                onClick={register}
                disabled={loading}
                className="rounded-full border border-fog/20 px-5 py-2 text-xs uppercase tracking-widest text-fog/70 disabled:opacity-60"
              >
                Create account
              </button>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
