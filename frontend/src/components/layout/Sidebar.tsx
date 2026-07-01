"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  Brain,
  LayoutDashboard,
  Video,
  Search,
  CheckSquare,
  Lightbulb,
  Upload,
  PanelLeftClose,
  PanelLeftOpen,
  ExternalLink,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { BACKEND_URL } from "@/lib/api";
import ThemeToggle from "@/components/theme/ThemeToggle";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/meetings", label: "Meetings", icon: Video },
  { href: "/upload", label: "Upload", icon: Upload },
  { href: "/search", label: "Search", icon: Search },
  { href: "/actions", label: "Action Items", icon: CheckSquare },
  { href: "/decisions", label: "Decisions", icon: Lightbulb },
];

const STORAGE_KEY = "meetiq-sidebar-collapsed";

export default function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    try {
      setCollapsed(localStorage.getItem(STORAGE_KEY) === "1");
    } catch {
      /* ignore */
    }
  }, []);

  const toggle = () => {
    setCollapsed((c) => {
      const next = !c;
      try {
        localStorage.setItem(STORAGE_KEY, next ? "1" : "0");
      } catch {
        /* ignore */
      }
      return next;
    });
  };

  return (
    <aside
      className={cn(
        "flex-shrink-0 flex flex-col h-full border-r border-line bg-panel/70 backdrop-blur-xl transition-all duration-300",
        collapsed ? "w-[74px]" : "w-64"
      )}
    >
      {/* Brand */}
      <div className="flex items-center gap-3 px-4 h-16 border-b border-line">
        <div className="w-10 h-10 flex-shrink-0 bg-gradient-to-br from-blue-500 to-cyan-400 rounded-2xl flex items-center justify-center shadow-glow">
          <Brain className="w-5 h-5 text-white" />
        </div>
        {!collapsed && (
          <div className="min-w-0">
            <p className="text-fg font-bold text-base leading-tight truncate">MeetIQ</p>
            <p className="text-subtle text-xs truncate">Meeting intelligence</p>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1.5 overflow-y-auto">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const isActive =
            href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              title={collapsed ? label : undefined}
              className={cn(
                "group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all",
                collapsed && "justify-center",
                isActive
                  ? "bg-gradient-to-r from-blue-600/90 to-cyan-500/90 text-white shadow-glow"
                  : "text-muted hover:text-fg hover:bg-panel-2"
              )}
            >
              <Icon className="w-[18px] h-[18px] flex-shrink-0" />
              {!collapsed && <span className="truncate">{label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-3 pb-4 space-y-3">
        <div
          className={cn(
            "flex items-center gap-2",
            collapsed ? "flex-col" : "justify-between"
          )}
        >
          <ThemeToggle compact={collapsed} />
          <button
            onClick={toggle}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            className="btn-ghost px-2 py-2"
          >
            {collapsed ? (
              <PanelLeftOpen className="w-[18px] h-[18px]" />
            ) : (
              <PanelLeftClose className="w-[18px] h-[18px]" />
            )}
          </button>
        </div>

        {!collapsed && (
          <div className="card-2 px-4 py-3">
            <p className="text-fg text-xs font-semibold">MeetIQ v1.0</p>
            <a
              href={`${BACKEND_URL}/docs`}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-1 inline-flex items-center gap-1 text-subtle hover:text-accent text-xs transition-colors"
            >
              API Docs <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        )}
      </div>
    </aside>
  );
}
