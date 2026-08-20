/* eslint-disable react/prop-types */

function ProgressBar({ value, height = "4", color = "bg-primary" }) {
  const isHex = color.startsWith("#");
  return (
    <div className={`h-${height} w-full overflow-hidden rounded-full bg-muted shadow-inner`}>
      <div
        className={`h-full rounded-full transition-all duration-700 ease-out ${!isHex ? color : ""} shadow-[0_0_8px_rgba(0,0,0,0.15)]`}
        style={{ width: `${value}%`, ...(isHex ? { backgroundColor: color } : {}) }}
      />
    </div>
  );
}

export default ProgressBar;
