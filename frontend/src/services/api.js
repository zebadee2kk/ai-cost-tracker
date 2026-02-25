import axios from "axios";

const BASE_URL = process.env.REACT_APP_API_URL || "/api";

const api = axios.create({ baseURL: BASE_URL });

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Redirect to login on 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem("token");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

// --- Auth ---
export const login = (email, password) =>
  api.post("/auth/login", { email, password });
export const register = (email, password) =>
  api.post("/auth/register", { email, password });
export const getMe = () => api.get("/auth/me");
export const logout = () => api.post("/auth/logout");

// --- Services ---
export const getServices = () => api.get("/services");
export const getService = (id) => api.get(`/services/${id}`);
export const updateServicePricing = (id, pricing_model) =>
  api.put(`/services/${id}/pricing`, { pricing_model });

// --- Accounts ---
export const getAccounts = () => api.get("/accounts");
export const createAccount = (data) => api.post("/accounts", data);
export const getAccount = (id) => api.get(`/accounts/${id}`);
export const updateAccount = (id, data) => api.put(`/accounts/${id}`, data);
export const deleteAccount = (id) => api.delete(`/accounts/${id}`);
export const testAccount = (id) => api.post(`/accounts/${id}/test`);

// --- Usage ---
export const getCurrentUsage = () => api.get("/usage");
export const getUsageHistory = (params) => api.get("/usage/history", { params });
export const getUsageByService = () => api.get("/usage/by-service");
export const getUsageForecast = () => api.get("/usage/forecast");

// --- Alerts ---
export const getAlerts = () => api.get("/alerts");
export const createAlert = (data) => api.post("/alerts", data);
export const updateAlert = (id, data) => api.put(`/alerts/${id}`, data);
export const deleteAlert = (id) => api.delete(`/alerts/${id}`);
export const acknowledgeAlert = (id) => api.post(`/alerts/${id}/acknowledge`);

export default api;
