/* eslint-disable react/prop-types */

import PhoneInput, { getCountryCallingCode } from "react-phone-number-input";
import "react-phone-number-input/style.css";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const CustomInput = ({ className, ...props }) => {
  return (
    <Input
      className={cn(
        "rounded-none border-none bg-transparent px-2 py-0 h-auto w-full min-w-0 shadow-none focus-visible:ring-0 focus-visible:ring-offset-0 outline-none text-base md:text-sm dark:bg-transparent",
        className
      )}
      {...props}
    />
  );
};

const CountrySelect = (props) => {
  const {
    value,
    onChange,
    disabled,
    options,
    iconComponent: FlagComponent,
  } = props;

  const handleValueChange = (newValue) => {
    onChange(newValue === "ZZ" ? undefined : newValue);
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger disabled={disabled} asChild>
        <button
          type="button"
          className="flex h-7 w-auto items-center gap-1 border-none bg-transparent px-0 py-0 shadow-none focus:ring-0 focus:ring-offset-0 disabled:opacity-50 [&>svg]:size-3 cursor-pointer outline-none"
        >
          <FlagComponent country={value} label={value} />
          <span className="text-muted-foreground/50 text-[10px]">▼</span>
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        className="max-h-75 w-64 overflow-y-auto"
        align="start"
      >
        {options.map((option) => {
          const optValue = option.value || "ZZ";
          return (
            <DropdownMenuItem
              key={optValue}
              onClick={() => handleValueChange(optValue)}
              className="flex items-center gap-2 cursor-pointer"
            >
              <FlagComponent country={option.value} label={option.label} />
              <span className="flex-1 truncate text-sm">{option.label}</span>
              {option.value && (
                <span className="text-muted-foreground text-xs font-mono">
                  +{getCountryCallingCode(option.value)}
                </span>
              )}
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

export default function PhoneInputField({
  value,
  onChange,
  disabled = false,
  id,
  className,
}) {
  return (
    <PhoneInput
      international
      defaultCountry="IN"
      value={value || undefined}
      onChange={onChange}
      disabled={disabled}
      id={id}
      autoComplete="off"
      inputComponent={CustomInput}
      countrySelectComponent={CountrySelect}
      className={cn(
        "flex w-full items-center rounded border border-input bg-transparent dark:bg-input/30 px-3 py-1 shadow-xs transition-[color,box-shadow] h-9",
        "focus-within:border-ring focus-within:ring-ring/50 focus-within:ring-[3px]",
        "has-disabled:cursor-not-allowed has-disabled:opacity-50",
        className
      )}
    />
  );
}
