/* eslint-disable react/prop-types */

import Icon from "@/components/custom/Icon";

const FrameworkMiniCard = ({ name, description }) => {
  return (
    <div className="flex items-center gap-2">
      <div className="">
        <div
          className="w-8 h-8 rounded
        bg-primary/10 dark:bg-primary/20
        flex items-center justify-center
        border border-primary/20 dark:border-primary/30"
        >
          <Icon
            name="shield"
            size="16px"
            className="text-primary dark:text-primary/80"
          />
        </div>
      </div>

      <div className="flex flex-col">
        <span className="font-medium text-foreground line-clamp-1" title={name}>
          {name}
        </span>
        {description && (
          <span
            className="text-xs text-muted-foreground line-clamp-1 max-w-xs"
            title={description}
          >
            {description}
          </span>
        )}
      </div>
    </div>
  );
};

export default FrameworkMiniCard;
