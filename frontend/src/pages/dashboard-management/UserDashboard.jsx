/* eslint-disable react/prop-types */

import { useEffect, useState } from "react";
import { useAuth } from "@/context/authContext/useAuth";
import { getRoleLabel } from "@/utils/commonUtils";

export default function UserDashboard() {
  const { user } = useAuth();
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  return (
    <div className="space-y-4 my-4">
      {/* Welcome Message with Live Clock */}
      <div className="rounded border border-border bg-card px-4 py-3">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-base font-semibold text-foreground">
              Welcome, {user?.name},
              <span className="text-sm">
                ({user?.role && getRoleLabel(user.role)})
              </span>{" "}
              👋
            </h2>
            <p className="text-xs text-muted-foreground">
              System overview for today.
            </p>
          </div>
          <div className="text-right hidden sm:block">
            <p className="text-[10px] font-medium text-foreground">
              {currentTime.toLocaleDateString("en-US", {
                weekday: "long",
                month: "long",
                day: "numeric",
                year: "numeric",
              })}
            </p>
            <p className="text-xs text-muted-foreground font-mono">
              {currentTime.toLocaleTimeString("en-US", {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
                hour12: true,
              })}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
