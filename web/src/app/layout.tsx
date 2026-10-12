import type { Metadata } from "next";
import type { ReactNode } from "react";

import { ToastProvider } from "@/components/ui";

import "./globals.css";

export const metadata: Metadata = {
  title: { default: "EMS", template: "%s · EMS" },
  description: "EMS - one workspace for your people, work, clients and revenue.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <ToastProvider>{children}</ToastProvider>
      </body>
    </html>
  );
}
