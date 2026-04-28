import axios from "axios";
import { apiScopes } from "../authConfig";

const api = axios.create({
  baseURL: process.env.REACT_APP_API_BASE_URL || "http://localhost:8000",
});

let _msalInstance = null;
let _account = null;
let _msalReady = null;
let _resolveMsalReady = null;

// Create a promise that resolves when MSAL is initialized
_msalReady = new Promise((resolve) => {
  _resolveMsalReady = resolve;
});

/** Store the MSAL instance so the interceptor can acquire tokens */
export function setMsalInstance(instance, account) {
  _msalInstance = instance;
  _account = account;
  if (_resolveMsalReady) {
    _resolveMsalReady();
    _resolveMsalReady = null;
  }
}

/** Axios interceptor — waits for MSAL, then acquires a fresh access token */
api.interceptors.request.use(async (config) => {
  // Wait for MSAL to be initialized (max 10s)
  await Promise.race([
    _msalReady,
    new Promise((_, reject) =>
      setTimeout(() => reject(new Error("MSAL init timeout")), 10000)
    ),
  ]);

  if (_msalInstance && _account) {
    try {
      const resp = await _msalInstance.acquireTokenSilent({
        ...apiScopes,
        account: _account,
      });
      config.headers.Authorization = `Bearer ${resp.accessToken}`;
    } catch (err) {
      console.warn("Silent token failed, trying popup:", err);
      try {
        const resp = await _msalInstance.acquireTokenPopup(apiScopes);
        config.headers.Authorization = `Bearer ${resp.accessToken}`;
      } catch (popupErr) {
        console.error("Token acquisition failed:", popupErr);
        _msalInstance.loginRedirect(apiScopes);
        throw new axios.Cancel("Redirecting to login");
      }
    }
  }
  return config;
});

// ── Blueprints ──────────────────────────────────────────────────
export const getBlueprints = (status) =>
  api.get("/api/blueprints", { params: { status } }).then((r) => r.data);

export const getTenantBlueprints = () =>
  api.get("/api/blueprints/tenant").then((r) => r.data);

export const getBlueprint = (id) =>
  api.get(`/api/blueprints/${id}`).then((r) => r.data);

export const createBlueprint = (data) =>
  api.post("/api/blueprints", data).then((r) => r.data);

export const deprecateBlueprint = (id) =>
  api.patch(`/api/blueprints/${id}/deprecate`).then((r) => r.data);

// ── Identity Requests ──────────────────────────────────────────
export const getIdentityRequests = (params) =>
  api.get("/api/identity-requests", { params }).then((r) => r.data);

export const getIdentityRequest = (id) =>
  api.get(`/api/identity-requests/${id}`).then((r) => r.data);

export const createIdentityRequest = (data) =>
  api.post("/api/identity-requests", data).then((r) => r.data);

// ── Permission Requests ────────────────────────────────────────
export const getPermissionRequests = (params) =>
  api.get("/api/permission-requests", { params }).then((r) => r.data);

export const createPermissionRequest = (data) =>
  api.post("/api/permission-requests", data).then((r) => r.data);

// ── Approvals ──────────────────────────────────────────────────
export const getPendingApprovals = () =>
  api.get("/api/approvals/pending").then((r) => r.data);

export const decideBlueprintRequest = (id, decision, reason = "") =>
  api.post(`/api/approvals/blueprint/${id}`, { decision, reason }).then((r) => r.data);

export const decideIdentityRequest = (id, decision, reason = "") =>
  api.post(`/api/approvals/identity/${id}`, { decision, reason }).then((r) => r.data);

export const decidePermissionRequest = (id, decision, reason = "") =>
  api.post(`/api/approvals/permission/${id}`, { decision, reason }).then((r) => r.data);

// ── Admin ──────────────────────────────────────────────────────
export const getAuditLog = (limit, entityType) =>
  api.get("/api/admin/audit-log", { params: { limit, entity_type: entityType } }).then((r) => r.data);

export const getDashboardStats = () =>
  api.get("/api/admin/stats").then((r) => r.data);

// ── Health ─────────────────────────────────────────────────────
export const getHealth = () =>
  api.get("/api/health").then((r) => r.data);

export default api;
