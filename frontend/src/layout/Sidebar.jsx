/* eslint-disable react/prop-types */

import { useState, useMemo, useCallback, useEffect } from "react";
import { useLocation, Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/authContext/useAuth";
import { useProfile } from "../context/profileContext/useProfile";
import Icon from "../components/custom/Icon";
import logoImage2 from "../assets/ekvayu_logo.png";
import UserAvatar from "../components/custom/UserAvatar";
import { Button } from "@/components/ui/button";

import {
  ROLE_ADMIN,
  ROLE_EXPERT,
  ROLE_CUSTOMER_ADMIN,
  ROLE_INTERNAL_EXPERT,
  ROLE_AUDITOR,
  ROLE_USER,
  ROLE_ALL,
} from "@/utils/commonUtils";

const ALL_NAV_ITEMS = [
  {
    id: "dashboard",
    title: "Dashboard",
    description: "Overview & analytics",
    icon: "dashboard",
    path: "/dashboard",
    roles: [ROLE_ALL], // Visible to everyone
  },
  {
    id: "customer-profiles",
    title: "Profile Management",
    description: "Manage users & roles",
    icon: "users",
    path: "/profiles",
    roles: [ROLE_CUSTOMER_ADMIN],
  },
  {
    id: "admin-profiles",
    title: "Profile Management",
    description: "Manage admin users & roles",
    icon: "users",
    roles: [ROLE_ADMIN],
    children: [
      {
        id: "profiles-list",
        title: "Profiles",
        description: "View all profiles",
        icon: "users",
        path: "/profiles",
        roles: [ROLE_ADMIN],
      },
      {
        id: "expert-framework-access",
        title: "Expert Framework Access",
        description: "Manage expert framework access",
        icon: "vpn-key",
        path: "/framework-access",
        roles: [ROLE_ADMIN],
      },
    ],
  },
  {
    id: "customers",
    title: "Customer Management",
    description: "Manage customers & access",
    icon: "building",
    roles: [ROLE_ADMIN],
    children: [
      {
        id: "customer-list",
        title: "Customers",
        description: "View all customers",
        icon: "building",
        path: "/customers",
        roles: [ROLE_ADMIN],
      },
      {
        id: "customer-framework-assignments",
        title: "Framework Assignments",
        description: "Manage framework assignments",
        icon: "assignment",
        path: "/framework-assignments",
        roles: [ROLE_ADMIN],
      },
    ],
  },
  {
    id: "framework",
    title: "Frameworks",
    description: "Explore frameworks",
    icon: "framework",
    path: "/frameworks",
    roles: [ROLE_EXPERT],
  },
  {
    id: "framework-categories",
    title: "Framework Categories",
    description: "Manage framework category",
    icon: "category",
    path: "/framework-categories",
    roles: [ROLE_ADMIN, ROLE_EXPERT],
  },
  {
    id: "deployment-frameworks",
    title: "Deployment Frameworks",
    description: "Manage deployment frameworks",
    icon: "assignment-ind",
    path: "/deployment-frameworks",
    roles: [ROLE_INTERNAL_EXPERT, ROLE_USER, ROLE_AUDITOR, ROLE_CUSTOMER_ADMIN],
  },
  {
    id: "assigned-frameworks",
    title: "Assigned Frameworks",
    description: "Frameworks assigned by admin",
    icon: "assignment",
    path: "/assigned-frameworks",
    roles: [ROLE_CUSTOMER_ADMIN, ROLE_AUDITOR],
  },
  // {
  //   id: "framework-workflow",
  //   title: "Workflow Setup",
  //   description: "Setup framework approval levels",
  //   icon: "git-merge",
  //   path: "/framework-workflow",
  //   roles: [ROLE_CUSTOMER_ADMIN],
  // },
  {
    id: "mcp-server",
    title: "MCP Server",
    description: "Manage mcp server & monitoring",
    icon: "building",
    roles: [ROLE_CUSTOMER_ADMIN, ROLE_AUDITOR],
    children: [
      {
        id: "mcp-server-monitoring",
        title: "MCP Monitoring",
        description: "View monitoring points",
        icon: "activity",
        path: "/mcp-server/monitoring",
        roles: [ROLE_CUSTOMER_ADMIN, ROLE_AUDITOR],
      },
      {
        id: "mcp-server-monitoring-setup",
        title: "MCP Monitoring Setup",
        description: "Configure monitoring points",
        icon: "settings",
        path: "/mcp-server/monitoring-setup",
        roles: [ROLE_CUSTOMER_ADMIN, ROLE_AUDITOR],
      },
    ],
  },
  {
    id: "profile",
    title: "My Profile",
    description: "View & edit your profile",
    icon: "profile",
    path: "/my-profile",
    roles: [ROLE_ALL], // Visible to everyone
  },
];

function Sidebar({ isOpen, setIsOpen }) {
  const [activeMenu, setActiveMenu] = useState(null);
  const { user: authUser } = useAuth();
  const { profile } = useProfile();
  const navigate = useNavigate();
  const location = useLocation();
  const role = authUser?.role || ROLE_EXPERT;

  const customer = profile?.customer ?? null;

  const menuItems = useMemo(() => {
    // List of standard roles. Any role not in this list is treated as a custom role
    const PREDEFINED_ROLES = [
      ROLE_ADMIN,
      ROLE_EXPERT,
      ROLE_CUSTOMER_ADMIN,
      ROLE_INTERNAL_EXPERT,
      ROLE_AUDITOR,
      ROLE_USER,
    ];
    const isCustomRole = !PREDEFINED_ROLES.includes(role);

    // Helper to check if current role can see an item
    const hasAccess = (itemRoles) => {
      if (!itemRoles) return false;
      if (itemRoles.includes("all")) return true; // Visible to everyone
      if (itemRoles.includes(role)) return true; // Exact role match
      if (isCustomRole && itemRoles.includes("other")) return true; // Visible to any custom role
      return false;
    };

    return ALL_NAV_ITEMS.map((item) => {
      // Check if user's role is allowed for the parent
      if (!hasAccess(item.roles)) return null;

      // Filter children by role
      if (item.children) {
        const filteredChildren = item.children.filter((child) =>
          hasAccess(child.roles)
        );
        // Only return parent if there are children available for this role
        if (filteredChildren.length > 0) {
          return { ...item, children: filteredChildren };
        }
        return null;
      }

      return item;
    }).filter(Boolean);
  }, [role]);

  // Auto-expand parent menu if child is active
  // Function to check if a path is active (including child routes)
  const isActive = useCallback(
    (path) => {
      if (!path) return false;

      // Special case for dashboard
      if (path === "/dashboard") {
        return location.pathname === "/" || location.pathname === "/dashboard";
      }

      // Check for exact match or child route match (with trailing slash)
      // This prevents false positives like "/mcp-server/monitoring" matching "/mcp-server/monitoring-setup"
      return (
        location.pathname === path || location.pathname.startsWith(`${path}/`)
      );
    },
    [location.pathname]
  );

  // Auto-expand parent menu if a child item is active on route change
  useEffect(() => {
    const activeParent = menuItems.find((item) =>
      item.children?.some((child) => isActive(child.path))
    );
    setActiveMenu(activeParent ? activeParent.id : null);
  }, [location.pathname, menuItems, isActive]);

  // Check if parent or any of its children are active
  const isParentActive = (item) => {
    if (item.path) {
      // For items with direct path, check if current path starts with it
      return isActive(item.path);
    }
    if (item.children) {
      // For parent items, check if any child is active
      return item.children.some((child) => isActive(child.path));
    }
    return false;
  };

  /* ================= RENDER ================= */
  return (
    <>
      {/* Overlay */}
      {isOpen && (
        <button
          type="button"
          onClick={() => setIsOpen(false)}
          aria-label="Close sidebar"
          className="fixed inset-0 z-40 bg-black/30 backdrop-blur-0.5"
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed left-0 top-0 z-50 h-screen w-85 bg-background flex flex-col shadow-2xl transition-transform duration-300 border-r border-border ${isOpen ? "translate-x-0" : "-translate-x-full"}`}
      >
        {/* ================= HEADER ================= */}
        <div className="relative flex items-center justify-between overflow-hidden bg-linear-to-br from-primary to-primary-2 px-4 py-4">
          <span className="pointer-events-none absolute -top-1/2 -right-1/2 h-[200%] w-[200%] bg-[radial-gradient(circle,rgba(255,255,255,0.1)_0%,transparent_70%)] animate-rotatePattern" />

          <div className="relative z-10 flex items-center gap-3">
            <div className="flex h-14 w-14 items-center justify-center rounded shadow-lg overflow-hidden">
              <img
                src={logoImage2}
                alt="VORA Logo"
                className="h-full w-full object-contain rounded mix-blend-screen"
                style={{
                  filter: "drop-shadow(0 0 5px rgba(255,255,255,0.5))",
                  background: "transparent",
                }}
                loading="lazy"
                decoding="async"
              />
            </div>
            <div>
              <h1 className="text-lg font-extrabold tracking-wide text-white">
                VORA
              </h1>
              <p className="text-xs text-white/90">AI Compliance Platform</p>
              <p className="text-[10px] text-muted-foreground/50 text-center tracking-wide">
                Powered by{" "}
                <span className="font-semibold text-muted-foreground/70">
                  Ekvayu Tech Pvt. Ltd.
                </span>
              </p>
            </div>
          </div>

          <Button
            onClick={() => setIsOpen(false)}
            size="icon"
            className="relative z-10 flex h-8 w-8 items-center justify-center rounded border border-white/30 bg-white/20 text-white transition hover:rotate-90 hover:bg-red-500 cursor-pointer"
          >
            <Icon name="close" size="20px" />
          </Button>
        </div>

        {/* ================= MENU ================= */}
        <div className="flex-1 overflow-y-auto px-3 py-2 sidebar-scroll select-none">
          <div className="flex flex-col gap-1">
            {menuItems.map((item) => (
              <div key={item.id} className="">
                {/* Parent */}
                <button
                  type="button"
                  onClick={() => {
                    if (item.children) {
                      setActiveMenu(activeMenu === item.id ? null : item.id);
                    } else if (item.path) {
                      navigate(item.path);
                      setIsOpen(false);
                    }
                  }}
                  aria-expanded={
                    item.children ? activeMenu === item.id : undefined
                  }
                  className={`group relative flex w-full cursor-pointer items-center gap-3 rounded px-3 py-2 transition-all text-left ${isParentActive(item) ? "border border-primary bg-linear-to-br from-primary/15 to-primary-2/15 shadow-md" : "border border-transparent bg-muted hover:translate-x-1 hover:border-border hover:bg-background"}`}
                >
                  {/* Left accent */}
                  <span
                    className={`absolute left-0 top-1/2 -translate-y-1/2 w-1 rounded-r ${isParentActive(item) ? "h-2/3 bg-linear-to-b from-primary to-primary-2" : "h-0 bg-primary group-hover:h-1/2 transition-all"}`}
                  />

                  {/* Icon */}
                  <div
                    className={`flex h-8 w-8 items-center justify-center rounded border transition ${isParentActive(item) ? "border-primary bg-primary/20 text-primary scale-110" : "border-border bg-muted text-muted-foreground group-hover:text-primary"}`}
                  >
                    <Icon name={item.icon} size="20px" />
                  </div>

                  {/* Text */}
                  <div className="flex flex-1 flex-col">
                    <span
                      className={`text-sm font-semibold ${isParentActive(item) ? "text-primary" : "text-foreground"}`}
                    >
                      {item.title}
                    </span>
                    {item.description && (
                      <span className="text-xs text-muted-foreground">
                        {item.description}
                      </span>
                    )}
                  </div>

                  {/* Arrow */}
                  {item.children && (
                    <div
                      className={`flex h-6 w-6 items-center justify-center rounded border border-border transition ${activeMenu === item.id ? "rotate-180 bg-transparent" : "bg-muted"}`}
                    >
                      <Icon name="chevron-down" size="14px" />
                    </div>
                  )}
                </button>

                {/* Submenu */}
                {item.children && activeMenu === item.id && (
                  <div className="ml-4 mt-1 flex flex-col gap-0.5 border-l-2 border-primary/40 pl-1">
                    {item.children.map((sub) => (
                      <Link
                        key={sub.id}
                        to={sub.path}
                        onClick={() => setIsOpen(false)}
                        className={`group relative flex items-center gap-2 rounded px-2 py-1.5 transition ${isActive(sub.path) ? "bg-primary/20 text-primary border border-primary" : "border border-transparent bg-muted hover:translate-x-1 hover:border-border hover:bg-background"}`}
                      >
                        <span
                          className={`absolute left-0 top-1/2 -translate-y-1/2 w-1 rounded-r ${isActive(sub.path) ? "h-2/3 bg-linear-to-b from-primary to-primary-2" : "h-0 bg-primary group-hover:h-1/2 transition-all"}`}
                        />
                        <div
                          className={`flex h-7 w-7 items-center justify-center rounded border ${isActive(sub.path) ? "border-primary bg-primary/20 text-primary scale-110" : "border-border bg-muted text-muted-foreground group-hover:text-primary"}`}
                        >
                          <Icon name={sub.icon} size="18px" />
                        </div>
                        <span className="text-sm font-medium">{sub.title}</span>
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* ================= CUSTOMER BADGE ================= */}
        {customer && (
          <div className="px-3 py-3 border-t border-border">
            <div
              className="relative flex items-center gap-3 rounded-lg px-3 py-2.5 overflow-hidden"
              style={{
                background:
                  "linear-gradient(135deg, hsl(var(--primary)/0.08), hsl(var(--primary-2, var(--primary))/0.04))",
                border: "1px solid hsl(var(--primary)/0.25)",
                boxShadow: "0 2px 8px hsl(var(--primary)/0.08)",
              }}
            >
              {/* Decorative shimmer */}
              <span className="pointer-events-none absolute -top-1/2 -right-1/4 h-[200%] w-1/2 rotate-12 bg-[radial-gradient(circle,rgba(255,255,255,0.06)_0%,transparent_70%)]" />

              {/* Customer Avatar */}
              <UserAvatar
                user={{ name: customer.name, avatar: customer.avatar }}
                size="lg"
                editable={false}
              />

              {/* Customer Info */}
              <div className="relative z-10 flex flex-col min-w-0">
                <span className="text-sm font-semibold text-foreground truncate leading-tight">
                  {customer.name}
                </span>
                {customer.email && (
                  <span className="text-[11px] text-muted-foreground truncate leading-tight">
                    {customer.email}
                  </span>
                )}
              </div>
            </div>
          </div>
        )}
      </aside>
    </>
  );
}

export default Sidebar;
