/* eslint-disable react/prop-types */

function ProgressBar({ value, color = "bg-primary" }) {
  return (
    <div className="h-4 w-full overflow-hidden rounded-full bg-muted">
      <div
        className={`h-full rounded-full ${color}`}
        style={{ width: `${value}%` }}
      />
    </div>
  );
}

export default ProgressBar;
