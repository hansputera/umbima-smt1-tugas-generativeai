import type { ReactNode } from "react";

export function Field({
  label,
  htmlFor,
  error,
  hint,
  children,
}: {
  label: string;
  htmlFor?: string;
  error?: string | null;
  hint?: string | null;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={htmlFor} className="text-[14px] font-medium leading-snug text-ink">
        {label}
      </label>
      {children}
      {error ? (
        <p className="text-[13px] leading-snug text-danger">{error}</p>
      ) : hint ? (
        <p className="text-[13px] leading-snug text-muted">{hint}</p>
      ) : null}
    </div>
  );
}

export const inputClass =
  "h-9 w-full rounded border border-border bg-white px-3 text-[16px] text-ink placeholder:text-faint cursor-text";

export const selectClass =
  "h-9 w-full rounded border border-border bg-white px-2.5 text-[16px] text-ink cursor-pointer";

export const textareaClass =
  "w-full rounded border border-border bg-white px-3 py-2 text-[16px] text-ink placeholder:text-faint cursor-text";

export function Input(props: React.ComponentPropsWithRef<"input">) {
  const { className = "", ...rest } = props;
  return <input className={`${inputClass} ${className}`} {...rest} />;
}

export function Textarea(props: React.ComponentPropsWithRef<"textarea">) {
  const { className = "", ...rest } = props;
  return <textarea className={`${textareaClass} ${className}`} {...rest} />;
}

export function Select(props: React.ComponentPropsWithRef<"select">) {
  const { className = "", children, ...rest } = props;
  return (
    <select className={`${selectClass} ${className}`} {...rest}>
      {children}
    </select>
  );
}
