"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "./ThemeProvider";
import { cn } from "@/lib/utils";

export default function ThemeToggle({
  className,
  compact = false,
}: {
  className?: string;
  compact?: boolean;
}) {
  const { theme, setTheme } = useTheme();
  const isDark = theme === "dark";

  if (compact) {
    return (
      <button
        onClick={() => setTheme(isDark ? "light" : "dark")}
        title={isDark ? "Switch to light mode" : "Switch to dark mode"}
        aria-label="Toggle theme"
        className={cn("btn-ghost px-2 py-2", className)}
      >
        {isDark ? <Sun className="w-[18px] h-[18px]" /> : <Moon className="w-[18px] h-[18px]" />}
      </button>
    );
  }

  return (
    <div
      role="group"
      aria-label="Theme"
      className={cn(
        "inline-flex items-center gap-1 rounded-xl border border-line bg-panel-2 p-1",
        className
      )}
    >
      <button
        onClick={() => setTheme("light")}
        aria-pressed={!isDark}
        title="Light mode"
        className={cn(
          "inline-flex items-center justify-center rounded-lg h-7 w-7 transition-colors",
          !isDark ? "bg-accent text-accent-fg shadow-sm" : "text-muted hover:text-fg"
        )}
      >
        <Sun className="w-4 h-4" />
      </button>
      <button
        onClick={() => setTheme("dark")}
        aria-pressed={isDark}
        title="Dark mode"
        className={cn(
          "inline-flex items-center justify-center rounded-lg h-7 w-7 transition-colors",
          isDark ? "bg-accent text-accent-fg shadow-sm" : "text-muted hover:text-fg"
        )}
      >
        <Moon className="w-4 h-4" />
      </button>
    </div>
  );
}
