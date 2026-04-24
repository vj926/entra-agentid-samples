import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Spinner } from "@fluentui/react-components";
import { createBlueprint } from "../services/api";

const COMMON_PERMISSIONS = [
  { resource: "Microsoft Graph", scope: "User.Read.All", type: "Application" },
  { resource: "Microsoft Graph", scope: "Mail.Send", type: "Application" },
  { resource: "Microsoft Graph", scope: "Calendars.Read", type: "Application" },
  { resource: "Microsoft Graph", scope: "Files.Read.All", type: "Application" },
  { resource: "Microsoft Graph", scope: "Directory.Read.All", type: "Application" },
  { resource: "Microsoft Graph", scope: "Application.Read.All", type: "Application" },
  { resource: "Microsoft Graph", scope: "Sites.Read.All", type: "Application" },
  { resource: "Microsoft Graph", scope: "Chat.Read", type: "Delegated" },
  { resource: "Microsoft Graph", scope: "Mail.Read", type: "Application" },
  { resource: "Microsoft Graph", scope: "Group.Read.All", type: "Application" },
];

export default function NewBlueprintRequest() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    name: "",
    description: "",
    agent_type: "copilot_studio",
    permission_mode: "manual",
    default_permissions: [],
    required_apis: [],
  });
  const [customPerm, setCustomPerm] = useState({
    resource: "Microsoft Graph",
    scope: "",
    type: "Application",
  });

  const togglePerm = (perm) => {
    setForm((prev) => {
      const key = `${perm.resource}:${perm.scope}`;
      const exists = prev.default_permissions.some(
        (p) => `${p.resource}:${p.scope}` === key
      );
      return {
        ...prev,
        default_permissions: exists
          ? prev.default_permissions.filter(
              (p) => `${p.resource}:${p.scope}` !== key
            )
          : [...prev.default_permissions, perm],
      };
    });
  };

  const addCustom = () => {
    if (customPerm.scope) {
      setForm((prev) => ({
        ...prev,
        default_permissions: [...prev.default_permissions, { ...customPerm }],
      }));
      setCustomPerm({ resource: "Microsoft Graph", scope: "", type: "Application" });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (
      form.permission_mode === "inheritable" &&
      form.default_permissions.length === 0
    ) {
      alert(
        "Inheritable mode requires at least one permission. Add permissions or switch to Manual mode."
      );
      return;
    }
    if (form.agent_type === "custom" && !form.identity_display_name) {
      alert("Custom agents require an Agent Display Name for the linked identity.");
      return;
    }
    setLoading(true);
    try {
      const payload = { ...form };
      if (form.agent_type === "custom") {
        payload.identity_justification = form.justification;
      }
      await createBlueprint(payload);
      navigate("/blueprints");
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
        <h1>Request Agent Blueprint</h1>
        <p>
          Define a new blueprint template for agents. Once approved, teams can
          request agent identities based on this blueprint.
        </p>
      </div>

      <form className="form-container" onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Blueprint Name *</label>
          <input
            required
            placeholder="e.g., Customer Service Agent, HR Copilot"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
        </div>

        <div className="form-group">
          <label>Description *</label>
          <textarea
            required
            placeholder="Describe the purpose of this blueprint — what kind of agents will use it and what they need access to..."
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
          />
        </div>

        <div className="form-group">
          <label>Agent Type</label>
          <select
            value={form.agent_type}
            onChange={(e) => {
              const type = e.target.value;
              const mustBeManual = type === "copilot_studio" || type === "foundry";
              setForm({
                ...form,
                agent_type: type,
                permission_mode: mustBeManual ? "manual" : form.permission_mode,
                default_permissions: mustBeManual ? [] : form.default_permissions,
              });
            }}
          >
            <option value="copilot_studio">Copilot Studio</option>
            <option value="foundry">Azure AI Foundry</option>
            <option value="custom">Custom / 3rd-Party Agent</option>
          </select>
        </div>

        {/* ── Permission Mode toggle ────────────────────────── */}
        <div className="form-group">
          <label>Permission Model</label>
          {(form.agent_type === "copilot_studio" || form.agent_type === "foundry") && (
            <div style={{ background: "#e8f4fd", border: "1px solid #b3d4fc", borderRadius: 6, padding: 12, fontSize: 13, color: "#004085", marginBottom: 10 }}>
              Copilot Studio and Foundry agents manage their own identity lifecycle — inheritable permissions are not available. Permissions must be requested separately after the agent identity is created.
            </div>
          )}
          <div
            style={{
              display: "flex",
              gap: 12,
              marginTop: 4,
            }}
          >
            <label
              className={`card ${
                form.permission_mode === "inheritable" ? "card-selected" : ""
              }`}
              style={{
                flex: 1,
                cursor: form.agent_type === "custom" ? "pointer" : "not-allowed",
                border:
                  form.permission_mode === "inheritable"
                    ? "2px solid #0078d4"
                    : undefined,
                padding: 16,
                opacity: form.agent_type === "custom" ? 1 : 0.4,
              }}
            >
              <input
                type="radio"
                name="permission_mode"
                value="inheritable"
                checked={form.permission_mode === "inheritable"}
                disabled={form.agent_type !== "custom"}
                onChange={() =>
                  setForm({ ...form, permission_mode: "inheritable" })
                }
                style={{ marginRight: 8 }}
              />
              <strong>Inheritable Permissions</strong>
              <div style={{ fontSize: 13, color: "#666", marginTop: 4 }}>
                Permissions are pre-defined on the blueprint. When an agent
                identity is created from this blueprint, it automatically
                inherits these permissions — no separate approval needed.
                {form.agent_type !== "custom" && (
                  <div style={{ color: "#856404", marginTop: 4, fontStyle: "italic" }}>
                    Only available for Custom / 3rd-party agents.
                  </div>
                )}
              </div>
            </label>
            <label
              className={`card ${
                form.permission_mode === "manual" ? "card-selected" : ""
              }`}
              style={{
                flex: 1,
                cursor: "pointer",
                border:
                  form.permission_mode === "manual"
                    ? "2px solid #0078d4"
                    : undefined,
                padding: 16,
              }}
            >
              <input
                type="radio"
                name="permission_mode"
                value="manual"
                checked={form.permission_mode === "manual"}
                onChange={() =>
                  setForm({
                    ...form,
                    permission_mode: "manual",
                    default_permissions: [],
                  })
                }
                style={{ marginRight: 8 }}
              />
              <strong>Manual Request &amp; Approval</strong>
              <div style={{ fontSize: 13, color: "#666", marginTop: 4 }}>
                No permissions are pre-assigned. After the agent identity is
                created, the owner must submit a separate permission request
                that goes through the approval workflow.
              </div>
            </label>
          </div>
        </div>

        {/* ── Permission picker (only for inheritable) ──────── */}
        {form.permission_mode === "inheritable" && (
          <>
            <div className="form-group">
              <label>
                Blueprint Permissions{" "}
                <span style={{ fontWeight: 400, color: "#888" }}>
                  (inherited by all identities created from this blueprint)
                </span>
              </label>
              <div
                style={{
                  border: "1px solid #c8c8c8",
                  borderRadius: 4,
                  padding: 8 ,
                  maxHeight: 320,
                  overflow: "auto",
                }}
              >
                {COMMON_PERMISSIONS.map((perm) => {
                  const key = `${perm.resource}:${perm.scope}`;
                  const checked = form.default_permissions.some(
                    (p) => `${p.resource}:${p.scope}` === key
                  );
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

            {form.default_permissions.length > 0 && (
              <div className="form-group">
                <label>
                  Selected Permissions ({form.default_permissions.length})
                </label>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {form.default_permissions.map((p, i) => (
                    <span
                      key={i}
                      className="badge badge-approved"
                      style={{ cursor: "pointer" }}
                      onClick={() => togglePerm(p)}
                      title="Click to remove"
                    >
                      {p.scope} ✕
                    </span>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {form.permission_mode === "manual" && (
          <div
            style={{
              background: "#fff3cd",
              border: "1px solid #ffc107",
              borderRadius: 6,
              padding: 16,
              fontSize: 13,
              color: "#856404",
            }}
          >
            <strong>Manual Permission Mode:</strong> Identities created from
            this blueprint will start with no permissions. Owners will need to
            submit a separate "Permission Request" after the identity is
            provisioned. Each permission request goes through admin approval.
          </div>
        )}

        {/* ── Linked Agent Identity (custom/3P only) ─────────── */}
        {form.agent_type === "custom" && (
          <div style={{
            background: "#f0f6ff",
            border: "1px solid #b3d4fc",
            borderRadius: 8,
            padding: 24,
            marginBottom: 20,
          }}>
            <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 4 }}>
              Agent Identity
            </div>
            <div style={{ fontSize: 13, color: "#555", marginBottom: 16 }}>
              For custom / 3rd-party agents, an agent identity is created alongside the blueprint.
              The identity will be linked to this blueprint and provisioned together upon approval.
            </div>

            <div className="form-group">
              <label>Agent Display Name *</label>
              <input
                required
                placeholder="e.g., Contoso Support Agent"
                value={form.identity_display_name || ""}
                onChange={(e) =>
                  setForm({ ...form, identity_display_name: e.target.value })
                }
              />
            </div>

            <div className="form-group">
              <label>Environment</label>
              <select
                value={form.identity_environment || "dev"}
                onChange={(e) =>
                  setForm({ ...form, identity_environment: e.target.value })
                }
              >
                <option value="dev">Development</option>
                <option value="staging">Staging</option>
                <option value="production">Production</option>
              </select>
            </div>
          </div>
        )}

        <div className="form-group">
          <label>Business Justification *</label>
          <textarea
            required
            placeholder="Why is this blueprint needed? What teams or scenarios will use it?"
            value={form.justification || ""}
            onChange={(e) => setForm({ ...form, justification: e.target.value })}
          />
        </div>

        <Button
          appearance="primary"
          type="submit"
          disabled={loading}
          style={{ minWidth: 180 }}
        >
          {loading ? <Spinner size="tiny" /> : "Submit Blueprint Request"}
        </Button>
      </form>
    </div>
  );
}
