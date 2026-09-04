import { BrowserRouter as Router } from "react-router-dom";
import { HelmetProvider } from "react-helmet-async";
import AppRoutes from "./routes/routes";
import { AuthProvider } from "./context/authContext/AuthContext";
import { ThemeProvider } from "./context/ThemeContext";
import { ProfileProvider } from "./context/profileContext/ProfileContext";
import AppToaster from "./components/custom/AppToaster";

function AppContent() {
  return (
    <>
      <AppRoutes />
      <AppToaster />
    </>
  );
}

function App() {
  return (
    <HelmetProvider>
      <Router>
        <AuthProvider>
          <ThemeProvider>
            <ProfileProvider>
              <AppContent />
            </ProfileProvider>
          </ThemeProvider>
        </AuthProvider>
      </Router>
    </HelmetProvider>
  );
}

export default App;
