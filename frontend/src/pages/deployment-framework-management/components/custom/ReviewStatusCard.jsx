/* eslint-disable react/prop-types */

import Icon from "@/components/custom/Icon";
import { formatDateWithMonthNameAndTime } from "@/utils/dateFormatter";

const ReviewStatusCard = ({ requestReview }) => {
  if (!requestReview?.assignedExpert) return null;

  if (requestReview.status === "rejected" && requestReview.comments) {
    return (
      <div className="mt-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded p-3">
        <div className="flex gap-3">
          <Icon
            name="x-circle"
            size="20px"
            className="text-red-600 dark:text-red-400 mt-0.5 shrink-0"
          />
          <div className="flex-1">
            <h4 className="text-sm font-semibold text-red-800 dark:text-red-200">
              Framework Rejected
            </h4>
            <div className="flex items-start justify-between mt-1.5 border-t border-red-200 dark:border-red-800/50 pt-1.5">
              <div className="flex flex-col gap-1">
                <p className="text-xs text-red-600 dark:text-red-400">
                  Rejected by:{" "}
                  <span className="font-medium">
                    {requestReview.assignedExpert.name}
                  </span>{" "}
                  ({requestReview.assignedExpert.email})
                </p>
                {requestReview.comments && (
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-red-600 dark:text-red-400">
                      Comment:
                    </span>
                    <span className="text-sm text-red-700 dark:text-red-300 leading-relaxed">
                      {requestReview.comments}
                    </span>
                  </div>
                )}
              </div>
              {requestReview.reviewedAt && (
                <p className="text-xs font-semibold text-red-600 dark:text-red-400">
                  {formatDateWithMonthNameAndTime(requestReview.reviewedAt)}
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (requestReview.status === "approved") {
    return (
      <div className="mt-3 bg-primary/10 border border-primary/30 rounded p-3">
        <div className="flex gap-3">
          <Icon
            name="check-circle"
            size="20px"
            className="text-primary mt-0.5 shrink-0"
          />
          <div className="flex-1">
            <h4 className="text-sm font-semibold text-foreground">
              Review Completed
            </h4>
            <div className="flex items-start justify-between mt-1.5 border-t border-primary/20 pt-1.5">
              <div className="flex flex-col gap-1">
                <p className="text-xs text-muted-foreground">
                  Reviewed by:{" "}
                  <span className="font-medium">
                    {requestReview.assignedExpert.name}
                  </span>{" "}
                  ({requestReview.assignedExpert.email})
                </p>
                {requestReview.comments && (
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-sm text-foreground/80 leading-relaxed italic">
                      "{requestReview.comments}"
                    </span>
                  </div>
                )}
              </div>
              {requestReview.reviewedAt && (
                <p className="text-xs font-semibold text-muted-foreground">
                  {formatDateWithMonthNameAndTime(requestReview.reviewedAt)}
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (requestReview.status === "requested") {
    return (
      <div className="mt-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded p-3">
        <div className="flex gap-3">
          <Icon
            name="clock"
            size="20px"
            className="text-yellow-600 dark:text-yellow-400 mt-0.5 shrink-0"
          />
          <div className="flex-1">
            <h4 className="text-sm font-semibold text-yellow-800 dark:text-yellow-200">
              Framework Requested
            </h4>
            <div className="flex items-start justify-between mt-1.5 border-t border-yellow-200 dark:border-yellow-800/50 pt-1.5">
              <div className="flex flex-col gap-1">
                <p className="text-xs text-yellow-700 dark:text-yellow-300">
                  Requested with:{" "}
                  <span className="font-medium">
                    {requestReview.assignedExpert.name}
                  </span>{" "}
                  ({requestReview.assignedExpert.email})
                </p>
                {requestReview.comments && (
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-yellow-700 dark:text-yellow-300">
                      Comment:
                    </span>
                    <span className="text-sm text-yellow-700 dark:text-yellow-300 leading-relaxed">
                      {requestReview.comments}
                    </span>
                  </div>
                )}
              </div>
              {requestReview.requestedAt && (
                <p className="text-xs font-semibold text-yellow-600 dark:text-yellow-400">
                  {formatDateWithMonthNameAndTime(requestReview.requestedAt)}
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return null;
};

export default ReviewStatusCard;
