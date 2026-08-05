/* eslint-disable react/prop-types */

import Icon from "@/components/custom/Icon";
import UserAvatar from "@/components/custom/UserAvatar";
import { formatDateWithMonthNameAndTime } from "@/utils/dateFormatter";

const UserMiniCard = ({
  name,
  email,
  date,
  avatar,
  icon = "user",
  isSelf = false,
  isEmailVerified,
  isRequestPending = false,
}) => {
  if (isSelf) {
    return (
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded bg-linear-to-br from-green-100 to-green-50 dark:from-green-900/30 dark:to-green-800/20 flex items-center justify-center text-green-600 dark:text-green-400 border border-green-200 dark:border-green-800">
          <Icon name="user-check" size="18px" />
        </div>
        <div>
          <span className="font-semibold text-foreground block whitespace-nowrap">
            Self Created
          </span>
          <span className="text-xs text-muted-foreground whitespace-nowrap">
            User Registration
          </span>
        </div>
      </div>
    );
  }

  if (isRequestPending) {
    return (
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded bg-linear-to-br from-yellow-100 to-yellow-50 dark:from-yellow-900/30 dark:to-yellow-800/20 flex items-center justify-center text-yellow-600 dark:text-yellow-400 border border-yellow-200 dark:border-yellow-800">
          <Icon name={icon} size="18px" />
        </div>
        <div>
          <span className="font-semibold text-yellow-600 dark:text-yellow-400 block whitespace-nowrap">
            {name}
          </span>
          <span className="text-xs text-yellow-600 dark:text-yellow-400 whitespace-nowrap">
            {email}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 min-w-0">
      {avatar ? (
        <UserAvatar user={{ name, avatar }} className="rounded shrink-0" />
      ) : (
        <div className="w-8 h-8 rounded bg-linear-to-br from-primary/20 to-primary/10 flex items-center justify-center text-primary border border-primary/20 shrink-0">
          <Icon name={icon} size="16px" />
        </div>
      )}

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span
            className="font-semibold text-foreground truncate block capitalize"
            title={name}
          >
            {name}
          </span>
          {isEmailVerified !== undefined && (
            <span
              className={`w-2 h-2 rounded-full cursor-pointer shrink-0 ${isEmailVerified ? "bg-green-500" : "bg-yellow-500"}`}
              title={
                isEmailVerified
                  ? "Email verified"
                  : "Email verification pending"
              }
            />
          )}
        </div>
        {email && (
          <span className="text-xs text-muted-foreground truncate block">
            {email}
          </span>
        )}
        {date && (
          <span className="text-[11px] text-muted-foreground truncate block">
            {formatDateWithMonthNameAndTime(date)}
          </span>
        )}
      </div>
    </div>
  );
};

export default UserMiniCard;
