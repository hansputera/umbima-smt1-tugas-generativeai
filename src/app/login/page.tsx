import Image from "next/image";
import { LoginForm } from "./login-form";
import { getAppBranding, logoSrc } from "@/lib/branding";

export const dynamic = "force-dynamic";

export default async function LoginPage() {
  const branding = await getAppBranding();
  const brandLogo = logoSrc(branding);
  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas p-4">
      <div className="w-full max-w-[400px] rounded-lg border border-border bg-white p-6 shadow-menu">
        <div className="flex items-center gap-2">
          {brandLogo ? (
            <Image
              src={brandLogo}
              alt=""
              width={28}
              height={28}
              unoptimized
              aria-hidden
              className="size-7 rounded-[4px] object-contain"
            />
          ) : (
            <span
              className="size-2.5 rounded-full bg-accent"
              aria-hidden
            />
          )}
          <span className="font-heading text-[18px] leading-none font-extrabold">
            {branding.app_name}
          </span>
        </div>
        <h1 className="mt-5">Masuk</h1>
        <p className="mt-1 text-[14px] text-muted">
          Selamat datang! Masuk untuk melanjutkan.
        </p>
        <LoginForm />
      </div>
    </div>
  );
}
