import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Spinner } from "@fluentui/react-components";
import { getBlueprints } from "../services/api";
import StatusBadge from "../components/StatusBadge";

export default function BlueprintCatalog() {
  const navigate = useNavigate();
  const [blueprints, setBlueprints] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getBlueprints()
      .then(setBlueprints)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner label="Loading blueprints..." />;

  return (
    <div>
      <div className="page-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "start" }}>
        <div>
          <h1>Agent Blueprints</h1>
          <p>
            Approved blueprint templates — select one when requesting a new
            agent identity
          </p>
        </div>
        <Button appearance="primary" onClick={() => navigate("/request/blueprint")}>
          + Request New Blueprint
        </Button>
      </div>

      {blueprints.length === 0 ? (
        <div className="empty-state">
          <div className="icon">📋</div>
          <p>No blueprints created yet. Create one to get started.</p>
        </div>
      ) : (
        <div className="card-grid">
          {blueprints.map((bp) => (
            <div key={bp.id} className="card">
              <div className="card-title">{bp.name}</div>
              <div className="card-desc">{bp.description}</div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <StatusBadge status={bp.status} />
                <span className="badge badge-provisioned">{bp.agent_type}</span>
                <span className={`badge ${bp.permission_mode === "inheritable" ? "badge-approved" : "badge-pending"}`}>
                  {bp.permission_mode === "inheritable" ? "Inheritable" : "Manual"} Permissions
                </span>
              </div>
              {bp.permission_mode === "inheritable" && bp.default_permissions?.length > 0 && (
                <div style={{ marginTop: 12 }}>
                  <strong style={{ fontSize: 12 }}>Inherited Permissions:</strong>
                  <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginTop: 4 }}>
                    {bp.default_permissions.map((p, i) => (
                      <span key={i} className="badge badge-approved">{p.scope}</span>
                    ))}
                  </div>
                </div>
              )}
              {bp.permission_mode === "manual" && (
                <div style={{ marginTop: 12, fontSize: 12, color: "#856404" }}>
                  Permissions must be requested separately after identity creation
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
