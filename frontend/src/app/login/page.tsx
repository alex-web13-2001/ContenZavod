"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/authStore";
import { CzInput, CzButton } from "@/components/ui-system";
import { Mail, Lock } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuthStore();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    // Fallback for browser autofill: read values from DOM if React state is empty
    let loginEmail = email;
    let loginPassword = password;
    if (!loginEmail || !loginPassword) {
      const form = e.currentTarget;
      const emailInput = form.querySelector<HTMLInputElement>('input[type="email"]');
      const passInput = form.querySelector<HTMLInputElement>('input[type="password"]');
      if (emailInput && !loginEmail) loginEmail = emailInput.value;
      if (passInput && !loginPassword) loginPassword = passInput.value;
    }

    if (!loginEmail || !loginPassword) {
      setError("Введите email и пароль");
      setLoading(false);
      return;
    }

    try {
      await login(loginEmail, loginPassword);
      router.push("/");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Ошибка входа");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100dvh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "20px",
        background: `
          radial-gradient(ellipse 80% 60% at 50% 0%, hsl(var(--cz-primary) / 0.08), transparent),
          radial-gradient(ellipse 60% 40% at 80% 100%, hsl(var(--cz-accent) / 0.06), transparent),
          hsl(var(--cz-bg-root))
        `,
      }}
    >
      <div
        className="animate-page-in"
        style={{
          width: "100%",
          maxWidth: "400px",
          padding: "40px 32px",
          backgroundColor: `hsl(var(--cz-bg-surface) / 0.8)`,
          backdropFilter: "blur(20px)",
          border: `1px solid hsl(var(--cz-border-subtle))`,
          borderRadius: "var(--cz-radius-xl)",
          boxShadow: "var(--cz-shadow-lg)",
        }}
      >
        {/* Logo */}
        <div style={{ textAlign: "center", marginBottom: "32px" }}>
          <div
            style={{
              width: "56px",
              height: "56px",
              margin: "0 auto 16px",
              borderRadius: "var(--cz-radius-lg)",
              background: "linear-gradient(135deg, hsl(var(--cz-primary)), hsl(var(--cz-accent)))",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "white",
              fontSize: "22px",
              fontWeight: 700,
              boxShadow: "0 4px 20px hsl(var(--cz-primary) / 0.3)",
            }}
          >
            CZ
          </div>
          <h1
            style={{
              fontSize: "24px",
              fontWeight: 700,
              color: `hsl(var(--cz-text-primary))`,
              letterSpacing: "-0.02em",
            }}
          >
            ContenZavod
          </h1>
          <p
            style={{
              fontSize: "14px",
              color: `hsl(var(--cz-text-muted))`,
              marginTop: "6px",
            }}
          >
            Войдите для доступа к платформе
          </p>
        </div>

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {error && (
            <div
              className="animate-fade-in"
              style={{
                padding: "12px 16px",
                fontSize: "13px",
                color: `hsl(var(--cz-error))`,
                backgroundColor: `hsl(var(--cz-error) / 0.08)`,
                border: `1px solid hsl(var(--cz-error) / 0.15)`,
                borderRadius: "var(--cz-radius-md)",
              }}
            >
              {error}
            </div>
          )}

          <CzInput
            label="Email"
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            icon={<Mail size={18} />}
            autoComplete="email"
            name="email"
          />

          <CzInput
            label="Пароль"
            type="password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            icon={<Lock size={18} />}
            autoComplete="current-password"
            name="password"
          />

          <CzButton type="submit" loading={loading} fullWidth size="lg">
            Войти
          </CzButton>
        </form>
      </div>
    </div>
  );
}
