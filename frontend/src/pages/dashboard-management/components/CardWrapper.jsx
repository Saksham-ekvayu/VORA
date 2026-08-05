/* eslint-disable react/prop-types */

function CardWrapper({ title, right, children, className = "" }) {
  const isFlexContainer = className.includes("flex flex-col");

  return (
    <div
      className={`rounded border border-border bg-linear-to-br from-background to-card shadow-sm ${className}`}
    >
      <div className="flex items-center justify-between border-b border-border px-2 py-1">
        <h3 className="text-lg font-semibold text-foreground">{title}</h3>
        {right}
      </div>
      <div className={`p-2 ${isFlexContainer ? "flex-1 flex flex-col" : ""}`}>
        {children}
      </div>
    </div>
  );
}

export default CardWrapper;
