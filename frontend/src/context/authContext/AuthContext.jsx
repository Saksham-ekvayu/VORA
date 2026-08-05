/* eslint-disable react/prop-types */

import {
  createContext,
  useState,
  useEffect,
  useRef,
  useMemo,
  useCallback,
} from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { resetUnauthorizedFlag } from "@/services/apiService";
import { logoutApi } from "@/services/authService";

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const navigate = useNavigate();
  const [pendingEmail, setPendingEmail] = useState("");

  // Refs to prevent multiple logout calls and track state
  const isLoggingOut = useRef(false);
  const hasShownSessionExpiredToast = useRef(false);
  const sessionCheckInterval = useRef(null);

  // Initialize state from sessionStorage
  const [isAuthenticated, setIsAuthenticated] = useState(() => {
    return JSON.parse(sessionStorage.getItem("isAuthenticated")) || false;
  });

  const [token, setToken] = useState(
    () => sessionStorage.getItem("token") || null
  );

  const [user, setUser] = useState(() => {
    const storedUser = sessionStorage.getItem("user");
    return storedUser ? JSON.parse(storedUser) : null;
  });

  // Store pending email for OTP verification
  const setEmailForVerification = useCallback((email) => {
    setPendingEmail(email);
    sessionStorage.setItem("pendingEmail", email);
  }, []);

  // Get pending email from session
  const getEmailForVerification = useCallback(() => {
    return pendingEmail || sessionStorage.getItem("pendingEmail") || "";
  }, [pendingEmail]);

  // Clear pending email after verification
  const clearPendingEmail = useCallback(() => {
    setPendingEmail("");
    sessionStorage.removeItem("pendingEmail");
  }, []);

  // Refs to track activity
  const lastActivityTime = useRef(Date.now());
  const sessionStartTime = useRef(
    Number.parseInt(sessionStorage.getItem("sessionStartTime")) || Date.now()
  );

  // -------------------------
  // Update user in state + sessionStorage
  // -------------------------
  const updateUser = useCallback((updatedFields) => {
    setUser((prev) => {
      const updated = { ...prev, ...updatedFields };
      sessionStorage.setItem("user", JSON.stringify(updated));
      return updated;
    });
  }, []);

  // -------------------------
  // Login
  // -------------------------
  const login = useCallback((userData, authToken, tenantId = null) => {
    // Reset logout flags
    isLoggingOut.current = false;
    hasShownSessionExpiredToast.current = false;

    // Reset apiService unauthorized flag
    resetUnauthorizedFlag();

    setIsAuthenticated(true);
    setToken(authToken);
    setUser(userData);

    // Save full info in sessionStorage
    sessionStorage.setItem("isAuthenticated", JSON.stringify(true));
    sessionStorage.setItem("token", authToken);
    sessionStorage.setItem("user", JSON.stringify(userData));
    sessionStorage.setItem("sessionStartTime", Date.now().toString());
    if (tenantId) {
      sessionStorage.setItem("tenantId", tenantId);
    } else {
      sessionStorage.removeItem("tenantId");
    }

    sessionStartTime.current = Date.now();
    lastActivityTime.current = Date.now();
  }, []);

  // -------------------------
  // Logout with duplicate prevention
  // -------------------------
  const logout = useCallback(
    async (message = null, showToast = true, toastOpts = null) => {
      // Prevent multiple simultaneous logout calls
      if (isLoggingOut.current) {
        return;
      }

      isLoggingOut.current = true;

      try {
        // Only call logout API if we have a token
        if (token) {
          await logoutApi();
        }
      } catch {
        // Don't show error for logout API failure, just proceed with local logout
      } finally {
        // Clear session check interval
        if (sessionCheckInterval.current) {
          clearInterval(sessionCheckInterval.current);
          sessionCheckInterval.current = null;
        }

        // Always clear local state regardless of API success/failure
        setIsAuthenticated(false);
        setToken(null);
        setUser(null);
        setPendingEmail("");

        sessionStorage.removeItem("isAuthenticated");
        sessionStorage.removeItem("token");
        sessionStorage.removeItem("user");
        sessionStorage.removeItem("sessionStartTime");
        sessionStorage.removeItem("pendingEmail");
        sessionStorage.removeItem("tenantId");

        // Show toast only if requested and not already shown
        if (message && showToast && !hasShownSessionExpiredToast.current) {
          hasShownSessionExpiredToast.current = true;

          // Dismiss ALL existing toasts first
          toast.dismiss();

          // Small delay to ensure all toasts are dismissed
          setTimeout(() => {
            const finalToastOpts = toastOpts || { type: "error", props: {} };

            const defaultProps = {
              duration: 4000,
              id: "session-expired",
            };

            const mergedProps = { ...defaultProps, ...finalToastOpts.props };

            if (finalToastOpts.type === "success") {
              toast.success(message, mergedProps);
            } else {
              toast.error(message, mergedProps);
            }
          }, 100);

          // Reset flag after 5 seconds
          setTimeout(() => {
            hasShownSessionExpiredToast.current = false;
          }, 5000);
        }

        navigate("/auth/login");

        // Reset logout flag after navigation
        setTimeout(() => {
          isLoggingOut.current = false;
        }, 1000);
      }
    },
    [navigate, token]
  );

  // -------------------------
  // Handle global unauthorized API responses
  // -------------------------
  useEffect(() => {
    const handleUnauthorizedResponse = (event) => {
      if (event.detail?.status === 401 && !isLoggingOut.current) {
        logout(
          event.detail.message ||
            "Your session has expired. Please log in again."
        );
      }
    };

    globalThis.addEventListener(
      "unauthorized-response",
      handleUnauthorizedResponse
    );

    return () => {
      globalThis.removeEventListener(
        "unauthorized-response",
        handleUnauthorizedResponse
      );
    };
  }, [logout]);

  // -------------------------
  // Memoize context value
  // -------------------------
  const contextValue = useMemo(
    () => ({
      isAuthenticated,
      token,
      user,
      login,
      logout,
      updateUser,
      setEmailForVerification,
      getEmailForVerification,
      clearPendingEmail,
    }),
    [
      isAuthenticated,
      token,
      user,
      login,
      logout,
      updateUser,
      setEmailForVerification,
      getEmailForVerification,
      clearPendingEmail,
    ]
  );

  return (
    <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>
  );
};

export { AuthContext };
