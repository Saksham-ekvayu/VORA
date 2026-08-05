/* eslint-disable react/prop-types */

import { useTheme } from "../context/ThemeContext";
import Icon from "../components/custom/Icon";
import logoImage from "../assets/loggo.png";
import { Button } from "@/components/ui/button";

function AuthLayout({ children }) {
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="relative min-h-screen flex bg-background overflow-hidden">
      {/* Theme Toggle */}
      <Button
        onClick={toggleTheme}
        size="icon"
        variant="outline"
        className="
          fixed top-6 right-6 z-50
          flex h-12 w-12 items-center justify-center
          rounded-full border border-border
          shadow-md transition
          hover:scale-110 hover:rotate-12
        "
        aria-label="Toggle theme"
      >
        <Icon name={theme === "light" ? "moon" : "sun"} size="20px" />
      </Button>

      {/* LEFT : Branding Section */}
      <div
        className="
          relative hidden lg:flex w-1/2
          items-center justify-center
          bg-linear-to-br
          from-primary via-primary/70 to-secondary
          px-16
          overflow-hidden
        "
      >
        {/* Decorative blobs */}
        <div className="absolute -top-24 -right-24 h-96 w-96 rounded-full bg-white/10 blur-3xl" />
        <div className="absolute bottom-20 left-10 h-72 w-72 rounded-full bg-white/10 blur-3xl" />

        <div className="relative z-10 max-w-md text-center text-white animate-in fade-in slide-in-from-left duration-700">
          {/* Logo */}
          <div className="mx-auto mb-10 flex h-28 w-28 items-center justify-center rounded shadow-xl overflow-hidden">
            <img
              src={logoImage}
              alt="VORA Logo"
              className="h-full w-full object-contain rounded mix-blend-screen"
              style={{
                filter: "drop-shadow(0 0 10px rgba(255,255,255,0.3))",
                background: "transparent",
              }}
              loading="lazy"
              decoding="async"
            />
          </div>

          <h1 className="text-4xl font-extrabold tracking-tight mb-3">VORA</h1>

          <p className="text-lg text-white/90 mb-12">
            AI-Powered Compliance Auditing Platform
          </p>

          {/* Features */}
          <div className="space-y-6 text-left">
            {[
              {
                icon: "check-circle",
                title: "Automated Compliance",
                desc: "Streamline your audit processes with AI",
              },
              {
                icon: "shield",
                title: "Multi-Framework Support",
                desc: "ISO 27001, NIST, SOX, GDPR & more",
              },
              {
                icon: "chart",
                title: "Real-Time Insights",
                desc: "Monitor compliance instantly",
              },
            ].map((f, i) => (
              <div
                key={f.title}
                className="
                  flex items-start gap-4 rounded
                  bg-white/10 backdrop-blur
                  border border-white/20 p-4
                  transition hover:translate-x-1
                  animate-in fade-in slide-in-from-bottom
                "
                style={{ animationDelay: `${i * 150}ms` }}
              >
                <div className="flex h-12 w-12 items-center justify-center rounded bg-white/20">
                  <Icon name={f.icon} size="24px" />
                </div>
                <div>
                  <h3 className="font-semibold">{f.title}</h3>
                  <p className="text-sm text-white/80">{f.desc}</p>
                </div>
              </div>
            ))}
          </div>

          <p className="mt-10 text-xs text-white/40 text-center tracking-wide">
            Powered by Ekvayu Tech Pvt. Ltd.
          </p>
        </div>
      </div>

      {/* RIGHT : Form Section */}
      <div className="flex w-full lg:w-1/2 items-center justify-center p-8 bg-background">
        <div
          className="
            w-full max-w-md
            animate-in fade-in slide-in-from-right
            duration-700
          "
        >
          {children}
          <p className="mt-6 text-xs text-muted-foreground/50 text-center">
            © {new Date().getFullYear()} Ekvayu Tech Pvt. Ltd. All rights
            reserved.
          </p>
        </div>
      </div>
    </div>
  );
}

export default AuthLayout;
