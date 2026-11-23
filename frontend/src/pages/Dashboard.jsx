import { Link, NavLink, Outlet } from "react-router-dom";

export default function Dashboard() {
  return (
    <div className="dashboard">
      <aside className="sidebar">
        <Link to="/" className="logo">
          Apartment Booking
        </Link>
        <nav>
          <NavLink to="apartments">Apartments</NavLink>
          <NavLink to="bookings">Bookings</NavLink>
          <NavLink to="search">Availability</NavLink>
        </nav>
      </aside>
      <main className="dashboard-main">
        <Outlet />
      </main>
    </div>
  );
}
