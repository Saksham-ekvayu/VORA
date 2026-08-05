import { BrowserRouter as Router } from "react-router-dom";
import { useEffect } from "react";
import AppRoutes from "./routes/routes";
import { AuthProvider } from "./context/authContext/AuthContext";
import { ThemeProvider } from "./context/ThemeContext";
import { ProfileProvider } from "./context/profileContext/ProfileContext";
import { useAuth } from "./context/authContext/useAuth";
import AppToaster from "./components/custom/AppToaster";
import { getRoleLabel } from "./utils/commonUtils";

function AppContent() {
  const { user } = useAuth();

  useEffect(() => {
    if (user?.role) {
      const roleLabel = getRoleLabel(user.role);
      document.title = `VORA - ${roleLabel}`;
    } else {
      document.title = "VORA - Authentication";
    }
  }, [user]);

  return (
    <>
      <AppRoutes />
      <AppToaster />
    </>
  );
}

function App() {
  return (
    <Router>
      <AuthProvider>
        <ThemeProvider>
          <ProfileProvider>
            <AppContent />
          </ProfileProvider>
        </ThemeProvider>
      </AuthProvider>
    </Router>
  );
}

export default App;
