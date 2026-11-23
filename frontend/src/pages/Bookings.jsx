import { useCallback, useEffect, useState } from "react";
import { api } from "../api.js";

export default function Bookings() {
  const [bookings, setBookings] = useState([]);
  const [apartments, setApartments] = useState([]);
  const [error, setError] = useState("");
  const [filterApartment, setFilterApartment] = useState("");
  const [filterFrom, setFilterFrom] = useState("");
  const [filterTo, setFilterTo] = useState("");

  const refresh = useCallback(async () => {
    try {
      const [bks, apts] = await Promise.all([
        api.getBookings(),
        api.getApartments(),
      ]);
      setBookings(bks);
      setApartments(apts);
      setError("");
    } catch (e) {
      setError(e.message);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const create = async (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    try {
      await api.createBooking(
        f.get("apartment_id"),
        f.get("date_from"),
        f.get("date_to")
      );
      e.target.reset();
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  };

  const cancel = async (id) => {
    try {
      await api.cancelBooking(id);
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  };

  const nameFor = (id) =>
    apartments.find((a) => a.id === id)?.name ?? `#${id}`;

  const filtered = bookings.filter(
    (b) =>
      (!filterApartment || b.apartment_id === Number(filterApartment)) &&
      (!filterFrom || b.date_to > filterFrom) &&
      (!filterTo || b.date_from < filterTo)
  );

  return (
    <section>
      <div className="page-header">
        <h2>Bookings</h2>
      </div>
      {error && <p className="error">{error}</p>}

      <form className="filters" onSubmit={create}>
        <select name="apartment_id" required defaultValue="">
          <option value="" disabled>
            Apartment
          </option>
          {apartments.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name}
            </option>
          ))}
        </select>
        <input name="date_from" type="date" required />
        <input name="date_to" type="date" required />
        <button type="submit" className="btn btn-primary">
          Create booking
        </button>
      </form>

      <div className="filters">
        <span>Filter:</span>
        <select
          value={filterApartment}
          onChange={(e) => setFilterApartment(e.target.value)}
        >
          <option value="">All apartments</option>
          {apartments.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name}
            </option>
          ))}
        </select>
        <input
          type="date"
          value={filterFrom}
          onChange={(e) => setFilterFrom(e.target.value)}
          title="Overlapping from"
        />
        <input
          type="date"
          value={filterTo}
          onChange={(e) => setFilterTo(e.target.value)}
          title="Overlapping to"
        />
        {(filterApartment || filterFrom || filterTo) && (
          <button
            onClick={() => {
              setFilterApartment("");
              setFilterFrom("");
              setFilterTo("");
            }}
          >
            Clear
          </button>
        )}
      </div>

      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Apartment</th>
            <th>From</th>
            <th>To</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {filtered.length === 0 && (
            <tr>
              <td colSpan="5">No bookings.</td>
            </tr>
          )}
          {filtered.map((b) => (
            <tr key={b.id}>
              <td>{b.id}</td>
              <td>{nameFor(b.apartment_id)}</td>
              <td>{b.date_from}</td>
              <td>{b.date_to}</td>
              <td>
                <button onClick={() => cancel(b.id)}>Cancel</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
