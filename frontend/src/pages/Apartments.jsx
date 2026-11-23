import { useCallback, useEffect, useState } from "react";
import { api } from "../api.js";
import Modal from "../components/Modal.jsx";

export default function Apartments() {
  const [apartments, setApartments] = useState([]);
  const [error, setError] = useState("");
  const [showModal, setShowModal] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setApartments(await api.getApartments());
      setError("");
    } catch (e) {
      setError(e.message);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const add = async (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    try {
      await api.addApartment(f.get("name"), f.get("address"));
      setShowModal(false);
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  };

  const remove = async (id) => {
    try {
      await api.removeApartment(id);
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <section>
      <div className="page-header">
        <h2>Apartments</h2>
        <button className="btn btn-primary" onClick={() => setShowModal(true)}>
          + Add apartment
        </button>
      </div>
      {error && <p className="error">{error}</p>}
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Name</th>
            <th>Address</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {apartments.length === 0 && (
            <tr>
              <td colSpan="4">No apartments yet.</td>
            </tr>
          )}
          {apartments.map((a) => (
            <tr key={a.id}>
              <td>{a.id}</td>
              <td>{a.name}</td>
              <td>{a.address}</td>
              <td>
                <button onClick={() => remove(a.id)}>Remove</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {showModal && (
        <Modal title="Add apartment" onClose={() => setShowModal(false)}>
          <form onSubmit={add}>
            <label>
              Name
              <input name="name" placeholder="Sunny Studio" required />
            </label>
            <label>
              Address
              <input name="address" placeholder="1 Main St" required />
            </label>
            <div className="modal-actions">
              <button type="button" onClick={() => setShowModal(false)}>
                Cancel
              </button>
              <button type="submit" className="btn btn-primary">
                Add
              </button>
            </div>
          </form>
        </Modal>
      )}
    </section>
  );
}
