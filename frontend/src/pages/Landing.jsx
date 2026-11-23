import { Link } from "react-router-dom";

export default function Landing() {
  return (
    <div className="landing">
      <nav className="landing-nav">
        <span className="logo">Apartment Booking</span>
        <Link to="/dashboard" className="btn">
          Dashboard
        </Link>
      </nav>
      <section className="hero">
        <h1>Manage apartments and bookings in one place.</h1>
        <p>
          Add apartments, create bookings, and check availability — backed by a
          Python API and SQLite.
        </p>
        <Link to="/dashboard" className="btn btn-primary">
          Open dashboard
        </Link>
      </section>
      <section className="features">
        <div>
          <h3>Apartments</h3>
          <p>Keep a list of rentable units with names and addresses.</p>
        </div>
        <div>
          <h3>Bookings</h3>
          <p>Create and cancel bookings with automatic overlap checks.</p>
        </div>
        <div>
          <h3>Availability</h3>
          <p>Search which apartments are free for any date range.</p>
        </div>
      </section>
    </div>
  );
}
