"use client";

import { createContext, useContext, type ReactNode } from "react";

const BrandingContext = createContext<{ appName: string }>({
  appName: "MiniCourse",
});

export function BrandingProvider({
  appName,
  children,
}: {
  appName: string;
  children: ReactNode;
}) {
  return (
    <BrandingContext.Provider value={{ appName }}>
      {children}
    </BrandingContext.Provider>
  );
}

export function useBranding(): { appName: string } {
  return useContext(BrandingContext);
}
