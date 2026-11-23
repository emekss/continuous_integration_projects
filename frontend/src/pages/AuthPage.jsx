import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";

export default function AuthPage({ mode }) {
  const isLogin = mode === "login";
  const { setUser } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    setBusy(true);
    try {
      const action = isLogin ? api.login : api.register;
      setUser(await action(f.get("email"), f.get("password")));
      navigate("/dashboard");
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  return (
    <div className="landing auth-page">
      <nav className="landing-nav">
        <Link to="/" className="logo">
          <span className="logo-dot" />
          Apartment Booking
        </Link>
      </nav>
      <div className="auth-card">
        <h1>{isLogin ? "Welcome back" : "Create your account"}</h1>
        <p className="auth-sub">
          {isLogin
            ? "Sign in to manage apartments and bookings."
            : "Register with your email to get started."}
        </p>
        {error && <p className="error">{error}</p>}
        <form className="auth-form" onSubmit={submit}>
          <label>
            Email
            <input
              name="email"
              type="email"
              placeholder="you@example.com"
              autoComplete="email"
              required
            />
          </label>
          <label>
            Password
            <input
              name="password"
              type="password"
              placeholder={isLogin ? "Your password" : "At least 8 characters"}
              autoComplete={isLogin ? "current-password" : "new-password"}
              minLength={isLogin ? undefined : 8}
              required
            />
          </label>
          <button type="submit" className="btn btn-primary" disabled={busy}>
            {isLogin ? "Sign in" : "Register"}
          </button>
        </form>
        <p className="auth-switch">
          {isLogin ? (
            <>
              No account? <Link to="/register">Register</Link>
            </>
          ) : (
            <>
              Already registered? <Link to="/login">Sign in</Link>
            </>
          )}
        </p>
      </div>
    </div>
  );
}
