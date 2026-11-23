import { useState } from "react";
import { api } from "../api.js";

export default function Availability() {
  const [results, setResults] = useState(null);
  const [range, setRange] = useState({ from: "", to: "" });
  const [error, setError] = useState("");

  const search = async (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    const from = f.get("date_from");
    const to = f.get("date_to");
    try {
      setResults(await api.searchApartments(from, to));
      setRange({ from, to });
      setError("");
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <section>
      <div className="page-header">
        <h2>Search availability</h2>
      </div>
      {error && <p className="error">{error}</p>}
      <form className="filters" onSubmit={search}>
        <input name="date_from" type="date" required />
        <input name="date_to" type="date" required />
        <button type="submit" className="btn btn-primary">
          Search
        </button>
      </form>

      {results && (
        <>
          <p>
            {results.length} apartment{results.length !== 1 && "s"} available{" "}
            {range.from}–{range.to}
          </p>
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Address</th>
              </tr>
            </thead>
            <tbody>
              {results.map((a) => (
                <tr key={a.id}>
                  <td>{a.id}</td>
                  <td>{a.name}</td>
                  <td>{a.address}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </section>
  );
}
