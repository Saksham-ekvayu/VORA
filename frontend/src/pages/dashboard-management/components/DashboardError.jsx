/* eslint-disable react/prop-types */

import Icon from "@/components/custom/Icon";
import { Button } from "@/components/ui/button";

export default function DashboardError({ error, onRetry }) {
  return (
    <div className="flex items-center justify-center min-h-[calc(100vh-180px)]">
      <div className="text-center p-8 rounded border border-border bg-card max-w-md w-full">
        <div className="w-16 h-16 bg-red-500/10 rounded flex items-center justify-center mx-auto mb-4">
          <Icon name="error" size="36px" className="text-red-500" />
        </div>
        <p className="text-base font-medium text-destructive mb-6">
          {error || "We couldn't retrieve your dashboard data at this time."}
        </p>
        <div className="flex justify-center">
          <Button onClick={onRetry} variant="outline" className="px-8 gap-2">
            <Icon name="refresh" size="16px" /> Retry
          </Button>
        </div>
      </div>
    </div>
  );
}
