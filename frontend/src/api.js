async function request(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  getApartments: () => request("/api/apartments"),
  addApartment: (name, address) =>
    request("/api/apartments", {
      method: "POST",
      body: JSON.stringify({ name, address }),
    }),
  removeApartment: (id) =>
    request(`/api/apartments/${id}`, { method: "DELETE" }),
  searchApartments: (dateFrom, dateTo) =>
    request(`/api/search?date_from=${dateFrom}&date_to=${dateTo}`),
  getBookings: () => request("/api/bookings"),
  createBooking: (apartmentId, dateFrom, dateTo) =>
    request("/api/bookings", {
      method: "POST",
      body: JSON.stringify({
        apartment_id: Number(apartmentId),
        date_from: dateFrom,
        date_to: dateTo,
      }),
    }),
  cancelBooking: (id) => request(`/api/bookings/${id}`, { method: "DELETE" }),
};
