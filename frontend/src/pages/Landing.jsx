import { Link } from "react-router-dom";

export default function Landing() {
  return (
    <div className="landing">
      <nav className="landing-nav">
        <span className="logo">
          <span className="logo-dot" />
          Apartment Booking
        </span>
        <div className="nav-actions">
          <Link to="/login" className="btn">
            Sign in
          </Link>
          <Link to="/dashboard" className="btn btn-primary">
            Dashboard →
          </Link>
        </div>
      </nav>

      <section className="hero">
        <div className="hero-text">
          <span className="eyebrow">Python API · SQLite · React</span>
          <h1>
            Manage apartments and bookings{" "}
            <span className="accent">in one place.</span>
          </h1>
          <p>
            Add apartments, create bookings, and check availability — a small
            booking system with a JSON backend and a React dashboard.
          </p>
          <Link to="/dashboard" className="btn btn-primary btn-lg">
            Open dashboard
          </Link>
        </div>

        <div className="preview-card" aria-hidden="true">
          <div className="preview-title">
            <span />
            <span />
            <span />
          </div>
          <div className="preview-row preview-head">
            <span>Apartment</span>
            <span>From</span>
            <span>To</span>
          </div>
          <div className="preview-row">
            <span>Sunny Studio</span>
            <span>Jun 1</span>
            <span>Jun 5</span>
          </div>
          <div className="preview-row">
            <span>Harbor View</span>
            <span>Jun 12</span>
            <span>Jun 20</span>
          </div>
          <div className="preview-row">
            <span>City Loft</span>
            <span>Jul 3</span>
            <span>Jul 9</span>
          </div>
          <div className="preview-badge">3 bookings</div>
        </div>
      </section>

      <section className="features">
        <div className="feature-card">
          <div className="feature-icon blue">▦</div>
          <h3>Apartments</h3>
          <p>Keep a list of rentable units with names and addresses.</p>
        </div>
        <div className="feature-card">
          <div className="feature-icon green">◷</div>
          <h3>Bookings</h3>
          <p>Create and cancel bookings with automatic overlap checks.</p>
        </div>
        <div className="feature-card">
          <div className="feature-icon violet">⌕</div>
          <h3>Availability</h3>
          <p>Search which apartments are free for any date range.</p>
        </div>
      </section>

      <footer className="landing-footer">
        Built with Python http.server · React · SQLite — zero web frameworks
      </footer>
    </div>
  );
}
