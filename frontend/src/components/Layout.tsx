import { NavLink, Outlet } from "react-router-dom";
import {
  BookOpen,
  Wrench,
  GitCompareArrows,
  FlaskConical,
  Play,
  MessageSquareText,
  EyeOff,
  BarChart3,
  Download,
} from "lucide-react";

const NAV_ITEMS = [
  { to: "/", icon: BookOpen, label: "Scenarios" },
  { to: "/scaffolds", icon: Wrench, label: "Scaffolds" },
  { to: "/counterfactual", icon: GitCompareArrows, label: "Counterfactual" },
  { to: "/experiments", icon: FlaskConical, label: "Experiments" },
  { to: "/runner", icon: Play, label: "Runner" },
  { to: "/responses", icon: MessageSquareText, label: "Responses" },
  { to: "/coding", icon: EyeOff, label: "Blind Coding" },
  { to: "/analysis", icon: BarChart3, label: "Analysis" },
  { to: "/export", icon: Download, label: "Export" },
];

export default function Layout() {
  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="fixed left-0 top-0 h-screen w-64 flex flex-col z-40"
        style={{
          background: "rgba(15, 23, 42, 0.85)",
          backdropFilter: "blur(20px)",
          borderRight: "1px solid rgba(148, 163, 184, 0.08)",
        }}
      >
        {/* Logo Area */}
        <div className="p-5 pb-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center gradient-accent">
              <FlaskConical size={18} className="text-white" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-surface-50 leading-tight">
                Bias Research
              </h1>
              <span className="text-[0.6875rem] text-surface-500 font-medium">
                LLM NPC Testbed
              </span>
            </div>
          </div>
        </div>

        {/* Divider */}
        <div className="mx-4 h-px bg-surface-700/50" />

        {/* Nav Links */}
        <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
          {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 group ${
                  isActive
                    ? "bg-accent-500/15 text-accent-400"
                    : "text-surface-400 hover:text-surface-200 hover:bg-surface-700/40"
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <Icon
                    size={18}
                    className={`transition-colors ${
                      isActive ? "text-accent-400" : "text-surface-500 group-hover:text-surface-300"
                    }`}
                  />
                  <span>{label}</span>
                  {isActive && (
                    <div className="ml-auto w-1.5 h-1.5 rounded-full bg-accent-400" />
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-surface-700/50">
          <div className="text-[0.6875rem] text-surface-600 text-center">
            Gender Bias Research v1.0
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 ml-64">
        <div className="p-8 max-w-7xl mx-auto">
          <div className="page-enter">
            <Outlet />
          </div>
        </div>
      </main>
    </div>
  );
}
