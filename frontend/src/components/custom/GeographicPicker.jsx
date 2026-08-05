/* eslint-disable react/prop-types */

import * as React from "react";
import { Check, ChevronsUpDown } from "lucide-react";
import { Country, State, City } from "country-state-city";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

export function GeographicPicker({
  type = "country",
  countryCode,
  stateCode,
  value,
  onSelect,
  placeholder = "Select...",
  disabled = false,
}) {
  const [open, setOpen] = React.useState(false);
  const [searchQuery, setSearchQuery] = React.useState("");

  const data = React.useMemo(() => {
    try {
      if (type === "country") {
        return Country.getAllCountries().map((c) => ({
          label: c.name,
          value: c.name,
          code: c.isoCode,
        }));
      }
      if (type === "state" && countryCode) {
        return State.getStatesOfCountry(countryCode).map((s) => ({
          label: s.name,
          value: s.name,
          code: s.isoCode,
        }));
      }
      if (type === "city" && countryCode && stateCode) {
        return City.getCitiesOfState(countryCode, stateCode).map((c) => ({
          label: c.name,
          value: c.name,
        }));
      }
      return [];
    } catch (e) {
      console.error("Error fetching geographic data:", e);
      return [];
    }
  }, [type, countryCode, stateCode]);

  const filteredData = React.useMemo(() => {
    if (!searchQuery) return data.slice(0, 100); // Initial limit for performance
    return data
      .filter((item) =>
        item.label.toLowerCase().includes(searchQuery.toLowerCase())
      )
      .slice(0, 50); // Limit results for search performance
  }, [data, searchQuery]);

  const selectedItem = data.find((item) => item.value === value);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="w-full justify-between font-normal text-muted-foreground truncate"
          disabled={disabled}
        >
          {value ? selectedItem?.label || value : placeholder}
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent
        className="w-(--radix-popover-trigger-width) p-0"
        align="start"
        onWheel={(e) => e.stopPropagation()}
      >
        <Command shouldFilter={false}>
          <CommandInput
            placeholder={`Search ${type}...`}
            value={searchQuery}
            onValueChange={setSearchQuery}
          />
          <CommandList>
            <CommandEmpty>No {type} found.</CommandEmpty>
            <CommandGroup>
              {filteredData.map((item) => (
                <CommandItem
                  key={`${item.value}-${item.code || ""}`}
                  value={item.value}
                  onSelect={() => {
                    onSelect(item);
                    setOpen(false);
                    setSearchQuery("");
                  }}
                >
                  <Check
                    className={cn(
                      "mr-2 h-4 w-4",
                      value === item.value ? "opacity-100" : "opacity-0"
                    )}
                  />
                  {item.label}
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
