/* eslint-disable react/prop-types */

function InfoItem({ icon, label, value }) {
  return (
    <div className="flex items-start gap-3 p-3 rounded bg-muted">
      <div className="mt-0.5 text-primary">{icon}</div>
      <div>
        <p className="text-[11px] font-medium uppercase tracking-wider mb-1 text-muted-foreground">
          {label}
        </p>
        {value}
      </div>
    </div>
  );
}

export default InfoItem;
