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
export const exportUsage = (params) =>
  api.get("/usage/export", { params, responseType: "blob" });

// --- Manual Usage Entries ---
export const createManualEntry = (data) => api.post("/usage/manual", data);
export const updateManualEntry = (id, data) => api.put(`/usage/manual/${id}`, data);
export const deleteManualEntry = (id) => api.delete(`/usage/manual/${id}`);

// --- Alerts ---
export const getAlerts = () => api.get("/alerts");
export const createAlert = (data) => api.post("/alerts", data);
export const updateAlert = (id, data) => api.put(`/alerts/${id}`, data);
export const deleteAlert = (id) => api.delete(`/alerts/${id}`);
export const acknowledgeAlert = (id) => api.post(`/alerts/${id}/acknowledge`);

// --- Notifications ---
export const getNotificationPreferences = (userId) =>
  api.get(`/notifications/preferences/${userId}`);
export const updateNotificationPreferences = (userId, prefs) =>
  api.put(`/notifications/preferences/${userId}`, prefs);
export const getNotificationQueue = (params) =>
  api.get("/notifications/queue", { params });
export const createQueueItem = (data) => api.post("/notifications/queue", data);
export const getNotificationHistory = (params) =>
  api.get("/notifications/history", { params });
export const sendTestNotification = (channel, data) =>
  api.post(`/notifications/test/${channel}`, data || {});
export const getNotificationRateLimits = () =>
  api.get("/notifications/rate-limits");

// --- Analytics ---
export const getAnalyticsTrends = (accountId, params) =>
  api.get(`/analytics/trends/${accountId}`, { params });
export const getAnalyticsForecast = (accountId, params) =>
  api.get(`/analytics/forecast/${accountId}`, { params });
export const getAnalyticsAnomalies = (accountId, params) =>
  api.get(`/analytics/anomalies/${accountId}`, { params });
export const triggerAnomalyDetection = (accountId, data) =>
  api.post(`/analytics/anomalies/${accountId}/detect`, data || {});
export const acknowledgeAnomaly = (anomalyId) =>
  api.post(`/analytics/anomalies/${anomalyId}/acknowledge`);
export const getAnalyticsConfig = (accountId) =>
  api.get(`/analytics/config/${accountId}`);
export const updateAnalyticsConfig = (accountId, data) =>
  api.put(`/analytics/config/${accountId}`, data);

export default api;
