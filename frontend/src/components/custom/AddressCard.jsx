import Icon from "@/components/custom/Icon";

const renderAddressField = (value) => value || "N/A";

export default function AddressCard({ title, iconName, address }) {
  return (
    <div className="p-4 rounded border border-border bg-card shadow-lg relative overflow-hidden border-l-4 border-l-primary/80">
      <div className="flex items-center gap-2 mb-4 pb-2 border-b border-border/40">
        <div className="p-1 rounded bg-primary/10 text-primary flex items-center justify-center">
          <Icon name={iconName || "map-pin"} size="16px" />
        </div>
        <h3 className="font-bold text-foreground">{title}</h3>
      </div>
      <div className="space-y-2.5 text-sm">
        <div>
          <span className="text-[10px] uppercase font-bold text-muted-foreground tracking-widest block opacity-70">
            Locality
          </span>
          <span className="font-semibold text-foreground wrap-break-words">
            {renderAddressField(address?.locality)}
          </span>
        </div>
        <div className="grid grid-cols-3 gap-2 mt-6">
          <div>
            <span className="text-[10px] uppercase font-bold text-muted-foreground tracking-widest block opacity-70">
              City
            </span>
            <span className="font-semibold text-foreground truncate block">
              {renderAddressField(address?.city)}
            </span>
          </div>
          <div>
            <span className="text-[10px] uppercase font-bold text-muted-foreground tracking-widest block opacity-70">
              State
            </span>
            <span className="font-semibold text-foreground truncate block">
              {renderAddressField(address?.state)}
            </span>
          </div>
          <div>
            <span className="text-[10px] uppercase font-bold text-muted-foreground tracking-widest block opacity-70">
              Country
            </span>
            <span className="font-semibold text-foreground truncate block">
              {renderAddressField(address?.country)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
