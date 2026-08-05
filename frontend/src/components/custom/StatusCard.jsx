/* eslint-disable react/prop-types */

import Icon from "@/components/custom/Icon";
import { formatDateWithMonthNameAndTime } from "@/utils/dateFormatter";
import { getStatusVisual } from "@/utils/commonUtils";

const StatusCard = ({ item, time = false, width = "w-fit" }) => {
  if (!item?.status) {
    return (
      <div
        className={`flex items-center gap-1.5 px-2 py-1 bg-muted/40 rounded border border-border/40 h-7 ${width} max-w-full`}
      >
        <div className="w-4 h-4 rounded bg-gray-500/10 flex items-center justify-center text-gray-500 shrink-0">
          <Icon name="minus" size="10px" />
        </div>
        <span className="text-[9px] font-bold text-muted-foreground truncate uppercase">
          Not started
        </span>
      </div>
    );
  }

  const { status, timestamp } = item;
  const statusKey = String(status || "").toLowerCase();

  const config = getStatusVisual(statusKey);

  return (
    <div
      className={`flex items-center gap-1.5 px-2 py-1 ${config.bgColor} ${config.borderColor} border rounded h-7 ${width} max-w-full`}
    >
      <div
        className={
          "w-4 h-4 rounded bg-background/50 flex items-center justify-center shrink-0"
        }
      >
        <Icon name={config.icon} size="10px" className={config.iconColor} />
      </div>
      <div className="flex flex-col min-w-0">
        <span className={`text-[11px] font-medium ${config.labelColor}`}>
          {config.label}
        </span>
        {time && timestamp ? (
          <span className="text-[8px] text-muted-foreground truncate normal-case font-medium">
            {formatDateWithMonthNameAndTime(timestamp)}
          </span>
        ) : null}
      </div>
    </div>
  );
};

export default StatusCard;
