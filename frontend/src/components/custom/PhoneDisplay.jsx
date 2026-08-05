/* eslint-disable react/prop-types */

import { parsePhoneNumber } from "react-phone-number-input";
import flags from "react-phone-number-input/flags";
import Icon from "./Icon";
import { cn } from "@/lib/utils";

/**
 * PhoneDisplay Component
 * Displays a phone number with its country flag.
 *
 * @param {string} value - The phone number to display (e.g., "917618274722")
 * @param {string} className - Optional additional CSS classes
 */
export default function PhoneDisplay({ value, className }) {
  if (!value)
    return <span className={cn("text-muted-foreground", className)}>N/A</span>;

  const phoneWithPlus = value.startsWith("+") ? value : `+${value}`;
  const phoneNumber = (() => {
    try {
      return parsePhoneNumber(phoneWithPlus);
    } catch {
      return null;
    }
  })();

  const country = phoneNumber?.country;
  const Flag = country ? flags[country] : null;

  return (
    <div className={cn("flex items-center gap-1", className)}>
      {Flag ? (
        <div className="w-5 flex shrink-0 items-center justify-center overflow-hidden">
          <Flag />
        </div>
      ) : (
        <Icon
          name="phone"
          size="14px"
          className="text-muted-foreground shrink-0"
        />
      )}
      <span className="text-foreground truncate">+{value}</span>
    </div>
  );
}
