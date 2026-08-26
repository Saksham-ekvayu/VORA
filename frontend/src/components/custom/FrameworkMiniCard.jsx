/* eslint-disable react/prop-types */

import Icon from "@/components/custom/Icon";
import { Link } from "react-router-dom";

const FrameworkMiniCard = ({ name, description, link }) => {
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
        {link ? (
          <Link
            to={link}
            className="font-medium text-foreground line-clamp-1 hover:underline hover:text-primary"
            title={name}
          >
            {name}
          </Link>
        ) : (
          <span
            className="font-medium text-foreground line-clamp-1"
            title={name}
          >
            {name}
          </span>
        )}

        {description && (
          <span
            className="text-xs text-muted-foreground line-clamp-1 max-w-xs font-semibold"
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
