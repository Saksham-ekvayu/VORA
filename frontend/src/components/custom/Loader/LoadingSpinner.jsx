/* eslint-disable react/prop-types */

import "./loading.css";

export default function LoadingSpinner({ className }) {
  return (
    <div
      className={`flex flex-col gap-2 items-center justify-center ${className}`}
    >
      <span className="loader"></span>
      <p>Loading...</p>
    </div>
  );
}
