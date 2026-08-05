/* eslint-disable react/prop-types */

import Icon from "@/components/custom/Icon";
import SearchInput from "@/components/custom/SearchInput";
import { capitalizeFirst } from "@/utils/commonUtils";
import { ScrollArea } from "@/components/ui/scroll-area";

/**
 * Reusable section sidebar button.
 *
 * Props:
 *   section    – { id, name }
 *   isActive   – boolean
 *   count      – number shown in the badge
 *   onClick    – () => void
 */
export function SectionButton({ section, isActive, count, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex flex-col p-2.5 rounded border text-left cursor-pointer transition-all duration-200 ${
        isActive
          ? "bg-primary/5 border-primary shadow-sm"
          : "bg-card border-border hover:bg-muted/30"
      }`}
    >
      <div className="flex items-center justify-between gap-2 w-full">
        <div className="flex items-center gap-2">
          <span
            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
              isActive
                ? "bg-primary text-primary-foreground"
                : "bg-primary/10 text-primary"
            }`}
          >
            {section.id}
          </span>
          <span
            className={`font-semibold text-xs leading-relaxed ${
              isActive ? "text-foreground" : "text-foreground/85"
            }`}
          >
            {capitalizeFirst(section.name)}
          </span>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <span
            className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
              isActive
                ? "bg-primary/20 text-primary"
                : "bg-muted text-muted-foreground"
            }`}
          >
            {count}
          </span>
        </div>
      </div>
    </button>
  );
}

/**
 * Full sections sidebar panel used by both ComparisionTable and GapTable.
 *
 * Props:
 *   sectionsList      – array of { id, name }
 *   resolvedSectionId – currently active section id
 *   sectionSearch     – current search string
 *   onSearchChange    – (value: string) => void
 *   onSearchClear     – () => void
 *   getSectionCount   – (section) => number
 *   onSectionClick    – (sectionId: string) => void
 *   totalCount        – number shown in the header badge
 */
export function SectionsSidebar({
  sectionsList,
  resolvedSectionId,
  sectionSearch,
  onSearchChange,
  onSearchClear,
  getSectionCount,
  onSectionClick,
  totalCount,
}) {
  return (
    <div className="shrink-0 bg-card border border-border rounded flex flex-col overflow-hidden w-full shadow-sm">
      <div className="px-2 pt-3 pb-2.5 flex flex-col items-start gap-2 border-b border-border bg-primary/5">
        <div className="w-full flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-sm font-semibold text-foreground">
            <span className="text-primary flex items-center justify-center">
              <Icon name="folder" size="16px" />
            </span>{" "}
            Sections
          </div>
          <div className="bg-primary text-white text-xs font-bold px-2 py-0.5 rounded">
            {totalCount}
          </div>
        </div>
        <SearchInput
          value={sectionSearch}
          onChange={onSearchChange}
          onClear={onSearchClear}
          placeholder="Search sections..."
          className="w-full bg-card"
        />
      </div>

      <ScrollArea className="flex-1">
        <div className="p-2 space-y-1">
          {sectionsList.length === 0 ? (
            <div className="text-center py-8 text-sm text-muted-foreground">
              No sections found.
            </div>
          ) : (
            sectionsList.map((section, index) => (
              <SectionButton
                key={`${section.id}-${index}`}
                section={section}
                isActive={resolvedSectionId === section.id}
                count={getSectionCount(section)}
                onClick={() => onSectionClick(section.id)}
              />
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
