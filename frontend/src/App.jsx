import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import Landing from "./pages/Landing.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Apartments from "./pages/Apartments.jsx";
import Bookings from "./pages/Bookings.jsx";
import Availability from "./pages/Availability.jsx";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/dashboard" element={<Dashboard />}>
          <Route index element={<Navigate to="apartments" replace />} />
          <Route path="apartments" element={<Apartments />} />
          <Route path="bookings" element={<Bookings />} />
          <Route path="search" element={<Availability />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
