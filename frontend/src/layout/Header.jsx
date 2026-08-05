/* eslint-disable react/prop-types */

import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import UserAvatar from "@/components/custom/UserAvatar";
import { useAuth } from "@/context/authContext/useAuth";
import { useProfile } from "@/context/profileContext/useProfile";
import { useTheme } from "@/context/ThemeContext";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import Icon from "@/components/custom/Icon";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

function Header({ pageTitle, breadcrumbs = [], setIsOpen }) {
  const navigate = useNavigate();
  const { user: authUser, logout } = useAuth();
  const { profile, loading } = useProfile();
  const { toggleTheme, theme } = useTheme();
  const [isPopoverOpen, setIsPopoverOpen] = useState(false);

  const displayUser = profile || authUser;

  return (
    <header className="sticky top-0 z-30 border-b border-border bg-background/80 backdrop-blur -mx-3 px-3">
      <div className="flex items-center justify-between py-1.5">
        {/* LEFT */}
        <div className="flex items-center gap-2">
          <Button
            onClick={() => setIsOpen(true)}
            aria-label="Open sidebar"
            variant="outline"
            size="icon"
            className="flex h-9 w-9 items-center justify-center rounded bg-linear-to-br from-primary to-primary/70"
          >
            <div className="flex flex-col gap-1">
              <span className="h-0.5 w-5 rounded-full bg-white" />
              <span className="h-0.5 w-4 rounded-full bg-white opacity-80" />
              <span className="h-0.5 w-5 rounded-full bg-white" />
            </div>
          </Button>
          <div>
            <h1 className="text-xl font-bold text-foreground capitalize leading-tight">
              {pageTitle}
            </h1>
            {breadcrumbs.length > 0 && (
              <div className="mt-0.5 flex items-center gap-1 text-xs text-muted-foreground">
                {breadcrumbs.map((crumb, index) => (
                  <span key={crumb.label} className="flex items-center gap-1">
                    {crumb.path ? (
                      <button
                        onClick={() => navigate(crumb.path)}
                        className="cursor-pointer font-medium text-primary hover:text-primary/80"
                      >
                        {crumb.label}
                      </button>
                    ) : (
                      <span
                        className={
                          crumb.active
                            ? "text-muted-foreground"
                            : "cursor-pointer text-primary"
                        }
                      >
                        {crumb.label}
                      </span>
                    )}
                    {index < breadcrumbs.length - 1 && (
                      <span className="mx-0.5 text-muted-foreground">/</span>
                    )}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* RIGHT — popover */}
        <Popover open={isPopoverOpen} onOpenChange={setIsPopoverOpen}>
          {loading ? (
            <PopoverTrigger asChild>
              <div className="flex items-center gap-1 rounded border border-border bg-muted/20 p-1 outline-none select-none cursor-wait">
                {/* Avatar skeleton */}
                <Skeleton className="h-8 w-8 rounded" />

                {/* Text skeleton - hidden on mobile */}
                <div className="hidden sm:flex flex-col gap-1">
                  <Skeleton className="h-3.5 w-24" />
                  <Skeleton className="h-3 w-20" />
                </div>

                {/* Chevron */}
                <Icon
                  name="chevron-down"
                  size="14px"
                  className="text-muted-foreground opacity-50"
                />
              </div>
            </PopoverTrigger>
          ) : (
            <div className="flex items-start gap-2 rounded border border-border bg-muted/20 p-1 hover:bg-background hover:shadow-sm transition-all">
              <UserAvatar user={displayUser} />

              <PopoverTrigger asChild>
                <button className="flex items-start gap-2 outline-none select-none cursor-pointer">
                  <div className="text-left">
                    <div className="text-sm font-semibold text-foreground leading-tight">
                      {displayUser?.name}
                    </div>
                    <div className="text-xs text-muted-foreground leading-tight">
                      {displayUser?.email}
                    </div>
                  </div>

                  <Icon
                    name="chevron-down"
                    size="20px"
                    className="text-muted-foreground"
                  />
                </button>
              </PopoverTrigger>
            </div>
          )}

          <PopoverContent align="end" sideOffset={10} className="w-40 p-0">
            <div className="p-1">
              <Button
                variant="ghost"
                size="sm"
                asChild
                className="w-full justify-start gap-2.5"
              >
                <Link to="/my-profile" onClick={() => setIsPopoverOpen(false)}>
                  <Icon
                    name="profile"
                    size="20px"
                    className="text-muted-foreground"
                  />
                  My Profile
                </Link>
              </Button>

              <Button
                variant="ghost"
                size="sm"
                onClick={toggleTheme}
                className="w-full justify-start gap-2.5"
              >
                <Icon
                  name={theme === "dark" ? "sun" : "moon"}
                  size="20px"
                  className="text-muted-foreground"
                />
                {theme === "dark" ? "Light Mode" : "Dark Mode"}
              </Button>
            </div>

            <div className="p-1 border-t border-border">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => logout()}
                className="w-full justify-start gap-2.5 text-red-500 hover:text-red-500 hover:bg-red-500/10"
              >
                <Icon name="power" size="20px" className="text-red-500" />
                Logout
              </Button>
            </div>
          </PopoverContent>
        </Popover>
      </div>
    </header>
  );
}

export default Header;
