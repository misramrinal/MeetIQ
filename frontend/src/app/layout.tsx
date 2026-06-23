"use client";

import "./globals.css";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import { useState } from "react";
import Sidebar from "@/components/layout/Sidebar";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        retry: 1,
      },
    },
  }));

  return (
    <html lang="en">
      <head>
        <title>MeetMind — Meeting Intelligence</title>
        <meta name="description" content="Multimodal meeting intelligence platform" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body>
        <QueryClientProvider client={queryClient}>
          <div className="flex h-screen overflow-hidden bg-gray-50">
            <Sidebar />
            <main className="flex-1 overflow-y-auto">
              {children}
            </main>
          </div>
          <Toaster position="top-right" richColors />
        </QueryClientProvider>
      </body>
    </html>
  );
}
