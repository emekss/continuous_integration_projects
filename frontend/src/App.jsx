import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth.jsx";
import Landing from "./pages/Landing.jsx";
import AuthPage from "./pages/AuthPage.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Apartments from "./pages/Apartments.jsx";
import Bookings from "./pages/Bookings.jsx";
import Availability from "./pages/Availability.jsx";

function Protected({ children }) {
  const { user } = useAuth();
  if (user === undefined) {
    return <p className="loading">Loading…</p>;
  }
  return user ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<AuthPage mode="login" />} />
          <Route path="/register" element={<AuthPage mode="register" />} />
          <Route
            path="/dashboard"
            element={
              <Protected>
                <Dashboard />
              </Protected>
            }
          >
            <Route index element={<Navigate to="apartments" replace />} />
            <Route path="apartments" element={<Apartments />} />
            <Route path="bookings" element={<Bookings />} />
            <Route path="search" element={<Availability />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
