import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Spinner } from "@fluentui/react-components";
import { createPermissionRequest } from "../services/api";

// Permissions allowed for agent identities
const ALLOWED_PERMISSIONS = [
  { resource: "Microsoft Graph", scope: "User.Read.All", type: "Application" },
  { resource: "Microsoft Graph", scope: "Mail.Send", type: "Application" },
  { resource: "Microsoft Graph", scope: "Mail.Read", type: "Application" },
  { resource: "Microsoft Graph", scope: "Directory.Read.All", type: "Application" },
  { resource: "Microsoft Graph", scope: "Application.Read.All", type: "Application" },
  { resource: "Microsoft Graph", scope: "Group.Read.All", type: "Application" },
];

// Commonly requested but blocked for agents — shown as disabled
const BLOCKED_PERMISSIONS = [
  { resource: "Microsoft Graph", scope: "Files.Read.All", type: "Application" },
  { resource: "Microsoft Graph", scope: "Sites.Read.All", type: "Application" },
  { resource: "Microsoft Graph", scope: "Calendars.Read", type: "Application" },
  { resource: "Microsoft Graph", scope: "Chat.Read.All", type: "Application" },
  { resource: "Microsoft Graph", scope: "Application.ReadWrite.All", type: "Application" },
  { resource: "Microsoft Graph", scope: "User.ReadWrite.All", type: "Application" },
  { resource: "Microsoft Graph", scope: "Directory.ReadWrite.All", type: "Application" },
];

export default function NewPermissionRequest() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    identity_app_id: "",
    identity_display_name: "",
    justification: "",
  });
  const [selected, setSelected] = useState([]);
  const [customPerm, setCustomPerm] = useState({ resource: "", scope: "", type: "Application" });

  const togglePerm = (perm) => {
    setSelected((prev) => {
      const key = `${perm.resource}:${perm.scope}`;
      const exists = prev.some((p) => `${p.resource}:${p.scope}` === key);
      return exists ? prev.filter((p) => `${p.resource}:${p.scope}` !== key) : [...prev, perm];
    });
  };

  const addCustom = () => {
    if (customPerm.resource && customPerm.scope) {
      setSelected((prev) => [...prev, { ...customPerm }]);
      setCustomPerm({ resource: "", scope: "", type: "Application" });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (selected.length === 0) {
      alert("Select at least one permission.");
      return;
    }
    setLoading(true);
    try {
      await createPermissionRequest({
        ...form,
        requested_permissions: selected,
      });
      navigate("/my-requests");
    } catch (err) {
      const detail = err.response?.data?.detail || err.response?.statusText || err.message || "";
      alert("Failed to submit. " + detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <h1>Request Permissions</h1>
        <p>
          Add API permissions to an existing agent identity (created via Copilot
          Studio, Foundry, or this portal).
        </p>
      </div>

      <form className="form-container" onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Agent App ID (Client ID) *</label>
          <input
            required
            placeholder="e.g., 00000000-0000-0000-0000-000000000000"
            value={form.identity_app_id}
            onChange={(e) => setForm({ ...form, identity_app_id: e.target.value })}
          />
        </div>

        <div className="form-group">
          <label>Agent Display Name *</label>
          <input
            required
            placeholder="e.g., Contoso Triage Agent"
            value={form.identity_display_name}
            onChange={(e) =>
              setForm({ ...form, identity_display_name: e.target.value })
            }
          />
        </div>

        <div className="form-group">
          <label>Select Permissions</label>
          <div
            style={{
              border: "1px solid #c8c8c8",
              borderRadius: 4,
              padding: 8,
              maxHeight: 360,
              overflow: "auto",
            }}
          >
            <div style={{ fontSize: 12, fontWeight: 600, color: "#155724", marginBottom: 4, padding: "4px 4px" }}>ALLOWED FOR AGENTS</div>
            {ALLOWED_PERMISSIONS.map((perm) => {
              const key = `${perm.resource}:${perm.scope}`;
              const checked = selected.some((p) => `${p.resource}:${p.scope}` === key);
              return (
                <label key={key} className="perm-row">
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => togglePerm(perm)}
                  />
                  <code>{perm.scope}</code>
                  <span className="perm-meta">
                    {perm.type} — {perm.resource}
                  </span>
                </label>
              );
            })}
            <div style={{ fontSize: 12, fontWeight: 600, color: "#721c24", marginTop: 8, marginBottom: 4, borderTop: "1px solid #e0e0e0", padding: "8px 4px 0" }}>BLOCKED FOR AGENT IDENTITIES</div>
            {BLOCKED_PERMISSIONS.map((perm) => (
              <label
                key={`${perm.resource}:${perm.scope}`}
                className="perm-row"
                style={{ opacity: 0.5, cursor: "not-allowed" }}
                title="This permission is blocked for agent identities by Microsoft Entra"
              >
                <input type="checkbox" disabled />
                <code style={{ textDecoration: "line-through" }}>{perm.scope}</code>
                <span className="perm-meta" style={{ color: "#721c24" }}>Blocked</span>
              </label>
            ))}
          </div>
        </div>

        <div className="form-group">
          <label>Add Custom Permission</label>
          <div style={{ display: "flex", gap: 8, alignItems: "end" }}>
            <input
              placeholder="Resource (e.g., Custom API)"
              value={customPerm.resource}
              onChange={(e) =>
                setCustomPerm({ ...customPerm, resource: e.target.value })
              }
              style={{ flex: 1 }}
            />
            <input
              placeholder="Scope (e.g., Tasks.Read)"
              value={customPerm.scope}
              onChange={(e) =>
                setCustomPerm({ ...customPerm, scope: e.target.value })
              }
              style={{ flex: 1 }}
            />
            <select
              value={customPerm.type}
              onChange={(e) =>
                setCustomPerm({ ...customPerm, type: e.target.value })
              }
              style={{ width: 130 }}
            >
              <option value="Application">Application</option>
              <option value="Delegated">Delegated</option>
            </select>
            <Button appearance="secondary" onClick={addCustom} type="button">
              Add
            </Button>
          </div>
        </div>

        {selected.length > 0 && (
          <div className="form-group">
            <label>Selected ({selected.length})</label>
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: 6,
              }}
            >
              {selected.map((p, i) => (
                <span key={i} className="badge badge-approved">
                  {p.scope}
                </span>
              ))}
            </div>
          </div>
        )}

        <div className="form-group">
          <label>Business Justification *</label>
          <textarea
            required
            placeholder="Why does this agent need these permissions?"
            value={form.justification}
            onChange={(e) => setForm({ ...form, justification: e.target.value })}
          />
        </div>

        <Button
          appearance="primary"
          type="submit"
          disabled={loading}
          style={{ minWidth: 160 }}
        >
          {loading ? <Spinner size="tiny" /> : "Submit Request"}
        </Button>
      </form>
    </div>
  );
}
