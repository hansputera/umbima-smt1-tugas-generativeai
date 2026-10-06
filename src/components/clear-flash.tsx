"use client";

import { useEffect } from "react";

export function ClearFlash({ name }: { name: string }) {
  useEffect(() => {
    document.cookie = `${name}=; Path=/; Max-Age=0`;
  }, [name]);
  return null;
}
