import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Spinner } from "@fluentui/react-components";
import { createIdentityRequest, getBlueprints, getTenantBlueprints } from "../services/api";

export default function NewIdentityRequest() {
  const navigate = useNavigate();
  const [allBlueprints, setAllBlueprints] = useState([]);
  const [selectedBp, setSelectedBp] = useState(null);
  const [loading, setLoading] = useState(false);
  const [bpLoading, setBpLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [permFilter, setPermFilter] = useState("all");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [form, setForm] = useState({
    blueprint_id: "",
    display_name: "",
    description: "",
    agent_type: "copilot_studio",
    environment: "dev",
    justification: "",
  });

  useEffect(() => {
    setBpLoading(true);
    // Fetch both local DB blueprints and tenant-wide blueprints from Graph
    Promise.all([
      getBlueprints("active").catch(() => []),
      getTenantBlueprints().catch(() => ({ tenant_blueprints: [] })),
    ]).then(([localBps, tenantData]) => {
      const localIds = new Set(localBps.map((b) => b.id));
      // Mark local blueprints
      const local = localBps.map((b) => ({ ...b, source: "portal" }));
      // Add tenant blueprints that aren't already in local DB
      const tenant = (tenantData.tenant_blueprints || [])
        .filter((b) => !localIds.has(b.id))
        .map((b) => ({ ...b, source: b.source || "entra" }));
      setAllBlueprints([...local, ...tenant]);
      setBpLoading(false);
    });
  }, []);

  const filtered = allBlueprints.filter((bp) => {
    if (typeFilter !== "all" && bp.agent_type !== typeFilter) return false;
    if (permFilter !== "all" && bp.permission_mode !== permFilter) return false;
    if (sourceFilter !== "all" && bp.source !== sourceFilter) return false;
    if (search) {
      const q = search.toLowerCase();
      return (
        (bp.name || "").toLowerCase().includes(q) ||
        (bp.description || "").toLowerCase().includes(q) ||
        (bp.agent_type || "").toLowerCase().includes(q) ||
        (bp.created_by || "").toLowerCase().includes(q) ||
        (bp.app_id || "").toLowerCase().includes(q)
      );
    }
    return true;
  });

  const agentTypes = [...new Set(allBlueprints.map((b) => b.agent_type))];

  const selectBlueprint = (bp) => {
    setSelectedBp(bp);
    setForm((f) => ({
      ...f,
      blueprint_id: bp.id,
      agent_type: bp.agent_type,
      description: bp.description,
    }));
  };

  const clearSelection = () => {
    setSelectedBp(null);
    setForm((f) => ({ ...f, blueprint_id: "", agent_type: "copilot_studio", description: "" }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.blueprint_id) return;
    setLoading(true);
    try {
      await createIdentityRequest(form);
      navigate("/my-requests");
    } catch (err) {
      const detail = err.response?.data?.detail || err.response?.statusText || err.message || "";
      alert("Failed to submit request. " + detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <h1>Request Agent Identity</h1>
        <p>
          Select an approved blueprint, then fill in the identity details.
          The identity will inherit the blueprint's configuration.
        </p>
      </div>

      {/* ── Step 1: Select Blueprint ──────────────────────────── */}
      {!selectedBp && (
        <div style={{ marginBottom: 24 }}>
          <div style={{ display: "flex", gap: 12, marginBottom: 16, flexWrap: "wrap", alignItems: "center" }}>
            <input
              placeholder="Search blueprints by name, description, type, or creator..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{
                flex: 1,
                minWidth: 280,
                padding: "10px 14px",
                border: "1px solid #c8c8c8",
                borderRadius: 4,
                fontSize: 14,
              }}
            />
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              style={{ padding: "10px 12px", border: "1px solid #c8c8c8", borderRadius: 4, fontSize: 13 }}
            >
              <option value="all">All Types</option>
              {agentTypes.map((t) => (
                <option key={t} value={t}>{t === "copilot_studio" ? "Copilot Studio" : t === "foundry" ? "Foundry" : "Custom"}</option>
              ))}
            </select>
            <select
              value={permFilter}
              onChange={(e) => setPermFilter(e.target.value)}
              style={{ padding: "10px 12px", border: "1px solid #c8c8c8", borderRadius: 4, fontSize: 13 }}
            >
              <option value="all">All Permission Models</option>
              <option value="inheritable">Inheritable</option>
              <option value="manual">Manual</option>
            </select>
            <select
              value={sourceFilter}
              onChange={(e) => setSourceFilter(e.target.value)}
              style={{ padding: "10px 12px", border: "1px solid #c8c8c8", borderRadius: 4, fontSize: 13 }}
            >
              <option value="all">All Sources</option>
              <option value="portal">Portal</option>
              <option value="entra">Entra ID</option>
            </select>
            <span style={{ fontSize: 13, color: "#888" }}>
              {filtered.length} of {allBlueprints.length} blueprints
            </span>
          </div>

          {bpLoading ? (
            <Spinner label="Loading blueprints..." />
          ) : allBlueprints.length === 0 ? (
            <div style={{ background: "#fff3cd", border: "1px solid #ffc107", borderRadius: 8, padding: 20, fontSize: 13, color: "#856404" }}>
              <strong>No blueprints available yet.</strong>
              <div style={{ marginTop: 8 }}>
                <a href="/request/blueprint" style={{ color: "#0078d4", fontWeight: 600 }}>Request a new blueprint</a> to get started.
              </div>
              <div style={{ marginTop: 6 }}>
                If you already have a Copilot Studio or Foundry agent and need to add permissions, go to{" "}
                <a href="/request/permissions" style={{ color: "#0078d4", fontWeight: 600 }}>Request Permissions</a> instead.
              </div>
            </div>
          ) : filtered.length === 0 ? (
            <div className="empty-state">
              <p>No blueprints match your filters. Try broadening your search.</p>
            </div>
          ) : (
            <div className="card-grid">
              {filtered.map((bp) => (
                <div
                  key={bp.id}
                  className="card"
                  onClick={() => selectBlueprint(bp)}
                  style={{ cursor: "pointer" }}
                >
                  <div className="card-title">{bp.name}</div>
                  {bp.app_id && <div style={{ fontSize: 11, color: "#999", fontFamily: "monospace" }}>{bp.app_id}</div>}
                  <div className="card-desc">{bp.description || "No description"}</div>
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 8 }}>
                    <span className="badge badge-provisioned">
                      {bp.agent_type === "copilot_studio" ? "Copilot Studio" : bp.agent_type === "foundry" ? "Foundry" : "Custom"}
                    </span>
                    <span className={`badge ${bp.permission_mode === "inheritable" ? "badge-approved" : "badge-pending"}`}>
                      {bp.permission_mode === "inheritable" ? "Inheritable" : "Manual"}
                    </span>
                    <span className="badge" style={{
                      background: bp.source === "portal" ? "#e8f4fd" : "#f3e8fd",
                      color: bp.source === "portal" ? "#004085" : "#5b2d8e",
                    }}>
                      {bp.source === "portal" ? "Portal" : "Entra ID"}
                    </span>
                  </div>
                  {bp.permission_mode === "inheritable" && bp.default_permissions?.length > 0 && (
                    <div style={{ marginTop: 8 }}>
                      <div style={{ fontSize: 11, color: "#888", marginBottom: 2 }}>Inherits:</div>
                      <div style={{ display: "flex", gap: 3, flexWrap: "wrap" }}>
                        {bp.default_permissions.slice(0, 4).map((p, i) => (
                          <span key={i} className="badge badge-approved" style={{ fontSize: 11 }}>{p.scope}</span>
                        ))}
                        {bp.default_permissions.length > 4 && (
                          <span style={{ fontSize: 11, color: "#888" }}>+{bp.default_permissions.length - 4} more</span>
                        )}
                      </div>
                    </div>
                  )}
                  <div style={{ fontSize: 11, color: "#999", marginTop: 8 }}>
                    Created by {bp.created_by} · {new Date(bp.created_at).toLocaleDateString()}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Step 2: Selected blueprint + identity form ────────── */}
      {selectedBp && (
        <form className="form-container" onSubmit={handleSubmit}>
          <div style={{
            background: "#f0f6ff", border: "1px solid #b3d4fc", borderRadius: 8,
            padding: 20, marginBottom: 24, position: "relative",
          }}>
            <button
              type="button"
              onClick={clearSelection}
              style={{
                position: "absolute", top: 12, right: 12,
                background: "none", border: "1px solid #b3d4fc", borderRadius: 4,
                padding: "4px 10px", cursor: "pointer", fontSize: 12, color: "#0078d4",
              }}
            >
              Change Blueprint
            </button>
            <div style={{ fontWeight: 700, fontSize: 16, marginBottom: 4 }}>{selectedBp.name}</div>
            <div style={{ fontSize: 13, color: "#555" }}>{selectedBp.description}</div>
            <div style={{ marginTop: 8, display: "flex", gap: 6, flexWrap: "wrap" }}>
              <span className="badge badge-provisioned">
                {selectedBp.agent_type === "copilot_studio" ? "Copilot Studio" : selectedBp.agent_type === "foundry" ? "Foundry" : "Custom"}
              </span>
              <span className={`badge ${selectedBp.permission_mode === "inheritable" ? "badge-approved" : "badge-pending"}`}>
                {selectedBp.permission_mode === "inheritable" ? "Inheritable Permissions" : "Manual Permissions"}
              </span>
            </div>
            {selectedBp.permission_mode === "inheritable" && selectedBp.default_permissions?.length > 0 && (
              <div style={{ marginTop: 12 }}>
                <strong style={{ fontSize: 13 }}>Permissions that will be inherited:</strong>
                <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginTop: 4 }}>
                  {selectedBp.default_permissions.map((p, i) => (
                    <span key={i} className="badge badge-approved">{p.scope}</span>
                  ))}
                </div>
              </div>
            )}
            {selectedBp.permission_mode === "manual" && (
              <div style={{ marginTop: 12, padding: 10, background: "#fff3cd", border: "1px solid #ffc107", borderRadius: 4, color: "#856404", fontSize: 13 }}>
                <strong>Manual Permissions:</strong> After provisioning, submit a separate{" "}
                <a href="/request/permissions" style={{ color: "#0078d4", fontWeight: 600 }}>Permission Request</a> with the provisioned App ID.
              </div>
            )}
          </div>

          <div className="form-group">
            <label>Agent Display Name *</label>
            <input
              required
              placeholder="e.g., Contoso Support Agent"
              value={form.display_name}
              onChange={(e) => setForm({ ...form, display_name: e.target.value })}
            />
          </div>

          <div className="form-group">
            <label>Agent Type</label>
            <select value={form.agent_type} disabled>
              <option value="copilot_studio">Copilot Studio</option>
              <option value="foundry">Azure AI Foundry</option>
              <option value="custom">Custom / 3rd-Party Agent</option>
            </select>
            <div style={{ fontSize: 12, color: "#888", marginTop: 2 }}>Locked to blueprint's agent type</div>
          </div>

          <div className="form-group">
            <label>Environment</label>
            <select
              value={form.environment}
              onChange={(e) => setForm({ ...form, environment: e.target.value })}
            >
              <option value="dev">Development</option>
              <option value="staging">Staging</option>
              <option value="production">Production</option>
            </select>
          </div>

          {selectedBp?.permission_mode === "manual" && (
            <div style={{ background: "#f8f9fa", border: "1px solid #dee2e6", borderRadius: 6, padding: 20, marginBottom: 16 }}>
              <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>Existing Agent Identity (if applicable)</div>
              <div style={{ fontSize: 13, color: "#666", marginBottom: 12 }}>
                If this agent already has an identity in Copilot Studio or Foundry, enter its App ID to link them.
              </div>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label>Existing Agent App ID (Client ID)</label>
                <input
                  placeholder="e.g., 00000000-0000-0000-0000-000000000000 (leave blank if new)"
                  value={form.existing_app_id || ""}
                  onChange={(e) => setForm({ ...form, existing_app_id: e.target.value })}
                />
              </div>
            </div>
          )}

          <div className="form-group">
            <label>Description</label>
            <textarea
              placeholder="Describe what the agent does and why it needs an identity..."
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </div>

          <div className="form-group">
            <label>Business Justification *</label>
            <textarea
              required
              placeholder="Why is this agent identity needed? Who will manage it?"
              value={form.justification}
              onChange={(e) => setForm({ ...form, justification: e.target.value })}
            />
          </div>

          <Button appearance="primary" type="submit" disabled={loading} style={{ minWidth: 160 }}>
            {loading ? <Spinner size="tiny" /> : "Submit Request"}
          </Button>
        </form>
      )}
    </div>
  );
}
