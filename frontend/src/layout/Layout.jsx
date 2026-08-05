/* eslint-disable react/prop-types */

import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { generateBreadcrumbs, PAGE_TITLES } from "../utils/generateBreadcrumbs";
import Header from "./Header";
import Sidebar from "./Sidebar";
import Footer from "./Footer";

function Layout({ children }) {
  const location = useLocation();
  // Using a local state to force a re-render when global labels change
  const [tick, setTick] = useState(0);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const handleTitleUpdate = () => setTick((t) => t + 1);
    globalThis.addEventListener("vora:title-update", handleTitleUpdate);
    return () =>
      globalThis.removeEventListener("vora:title-update", handleTitleUpdate);
  }, []);

  const breadcrumbs = generateBreadcrumbs(location.pathname);

  // Use custom page title if mapped, else dynamic label, else breadcrumb label
  const lastSegment =
    location.pathname.split("/").findLast(Boolean) || "dashboard";

  const pageTitle =
    PAGE_TITLES[lastSegment] ||
    globalThis.__VORA_BREADCRUMB_LABELS__?.[lastSegment] ||
    breadcrumbs[breadcrumbs.length - 1]?.label ||
    "";

  return (
    <div className="px-3 min-h-screen flex flex-col">
      <Sidebar isOpen={isOpen} setIsOpen={setIsOpen} />
      <main className="w-full flex-1 flex flex-col justify-between">
        <div>
          <Header
            pageTitle={pageTitle}
            breadcrumbs={breadcrumbs}
            setIsOpen={setIsOpen}
            tick={tick}
          />
          <div className="">{children}</div>
        </div>
        <Footer />
      </main>
    </div>
  );
}

export default Layout;
