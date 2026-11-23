import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";

export default function Dashboard() {
  const { user, setUser } = useAuth();
  const navigate = useNavigate();

  const logout = async () => {
    await api.logout();
    setUser(null);
    navigate("/");
  };

  return (
    <div className="dashboard">
      <aside className="sidebar">
        <Link to="/" className="logo">
          <span className="logo-dot" />
          Apartment Booking
        </Link>
        <nav>
          <NavLink to="apartments">Apartments</NavLink>
          <NavLink to="bookings">Bookings</NavLink>
          <NavLink to="search">Availability</NavLink>
        </nav>
        <div className="sidebar-footer">
          <span className="user-email">{user?.email}</span>
          <button onClick={logout}>Log out</button>
        </div>
      </aside>
      <main className="dashboard-main">
        <Outlet />
      </main>
    </div>
  );
}
