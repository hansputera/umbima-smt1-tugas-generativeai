import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary";

export function buttonClass(variant: Variant = "secondary"): string {
  const base =
    "inline-flex cursor-pointer items-center justify-center gap-2 rounded-md border px-3 py-1.5 text-[14px] font-medium leading-normal transition-colors disabled:pointer-events-none disabled:opacity-50";
  const look =
    variant === "primary"
      ? "border-transparent bg-accent text-white hover:bg-accent-hover"
      : "border-border bg-white text-ink hover:bg-canvas";
  return `${base} ${look}`;
}

export function Button({
  variant = "secondary",
  className = "",
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  children: ReactNode;
}) {
  return (
    <button className={`${buttonClass(variant)} ${className}`} {...props}>
      {children}
    </button>
  );
}
