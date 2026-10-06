"use client";

import { useActionState } from "react";
import { login, type ActionState } from "@/lib/actions/auth";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/field";

export function LoginForm() {
  const [state, formAction, pending] = useActionState<ActionState, FormData>(
    login,
    undefined,
  );

  return (
    <form action={formAction} className="mt-6 flex flex-col gap-4">
      <Field label="Email" htmlFor="email">
        <Input
          id="email"
          name="email"
          type="email"
          autoComplete="email"
          placeholder="nama@contoh.com"
          required
        />
      </Field>

      <Field label="Kata sandi" htmlFor="password" error={state?.error}>
        <Input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
        />
      </Field>

      <Button type="submit" variant="primary" disabled={pending}>
        {pending ? "Masuk..." : "Masuk"}
      </Button>
    </form>
  );
}
