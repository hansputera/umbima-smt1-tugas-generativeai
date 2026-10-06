import type { ReactNode } from "react";

export function Table({ children }: { children: ReactNode }) {
  return (
    <div className="w-full max-lg:overflow-x-auto">
      <table className="w-full border-collapse text-left text-[13px]">
        {children}
      </table>
    </div>
  );
}

export function Tr({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <tr
      className={`border-b border-border odd:bg-canvas transition-colors hover:bg-row-hover ${className}`}
    >
      {children}
    </tr>
  );
}

export function Th({
  children,
  className = "",
}: {
  children?: ReactNode;
  className?: string;
}) {
  return (
    <th
      className={`whitespace-nowrap border-b border-border bg-white px-3 py-2 text-left text-[13px] font-semibold text-ink ${className}`}
    >
      {children}
    </th>
  );
}

export function Td({
  children,
  className = "",
  colSpan,
}: {
  children?: ReactNode;
  className?: string;
  colSpan?: number;
}) {
  return (
    <td
      colSpan={colSpan}
      className={`px-3 py-2.5 align-middle text-[13px] ${className}`}
    >
      {children}
    </td>
  );
}
