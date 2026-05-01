import React, { useEffect, useState } from "react";
import {
  Button,
  Spinner,
  Dialog,
  DialogSurface,
  DialogBody,
  DialogTitle,
  DialogContent,
  DialogActions,
} from "@fluentui/react-components";
import {
  getPendingApprovals,
  decideBlueprintRequest,
  decideIdentityRequest,
  decidePermissionRequest,
} from "../services/api";

export default function AdminApprovals() {
  const [data, setData] = useState({
    blueprint_requests: [],
    identity_requests: [],
    permission_requests: [],
  });
  const [loading, setLoading] = useState(true);
  const [rejectReason, setRejectReason] = useState("");
  const [actionTarget, setActionTarget] = useState(null);

  const load = () => {
    setLoading(true);
    getPendingApprovals()
      .then(setData)
      .catch((err) => {
        if (err.response?.status === 403) {
          setData({ _forbidden: true });
        }
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleAction = async (type, id, decision) => {
    if (decision === "reject") {
      setActionTarget({ type, id });
      return;
    }
    try {
      if (type === "blueprint") await decideBlueprintRequest(id, decision);
      else if (type === "identity") await decideIdentityRequest(id, decision);
      else await decidePermissionRequest(id, decision);
      load();
    } catch (err) {
      alert("Action failed: " + (err.response?.data?.detail || err.message));
    }
  };

  const confirmReject = async () => {
    if (!actionTarget) return;
    try {
      if (actionTarget.type === "blueprint") await decideBlueprintRequest(actionTarget.id, "reject", rejectReason);
      else if (actionTarget.type === "identity") await decideIdentityRequest(actionTarget.id, "reject", rejectReason);
      else await decidePermissionRequest(actionTarget.id, "reject", rejectReason);
      setActionTarget(null);
      setRejectReason("");
      load();
    } catch (err) {
      alert("Rejection failed: " + (err.response?.data?.detail || err.message));
    }
  };

  if (loading) return <Spinner label="Loading approvals..." />;

  if (data._forbidden) {
    return (
      <div>
        <div className="page-header"><h1>Approvals</h1></div>
        <div className="empty-state">
          <div className="icon">🔒</div>
          <p>You need <strong>Global Administrator</strong> or <strong>Agent ID Administrator</strong> role to access approvals.</p>
        </div>
      </div>
    );
  }

  const totalPending =
    (data.blueprint_requests?.length || 0) +
    (data.identity_requests?.length || 0) +
    (data.permission_requests?.length || 0);

  const ActionButtons = ({ type, id }) => (
    <div className="approval-actions">
      <Button appearance="primary" size="small" onClick={() => handleAction(type, id, "approve")}>Approve</Button>
      <Button appearance="secondary" size="small" onClick={() => handleAction(type, id, "reject")}>Reject</Button>
    </div>
  );

  return (
    <div>
      <div className="page-header">
        <h1>Pending Approvals</h1>
        <p>{totalPending} request{totalPending !== 1 ? "s" : ""} awaiting review
          <span style={{ fontSize: 12, color: "#888", marginLeft: 8 }}>Requires Global Admin or Agent ID Administrator</span>
        </p>
      </div>

      {data.blueprint_requests?.length > 0 && (
        <>
          <h2 style={{ fontSize: 18, marginBottom: 12 }}>Blueprint Requests ({data.blueprint_requests.length})</h2>
          <table className="data-table" style={{ marginBottom: 32 }}>
            <thead><tr><th>Blueprint</th><th>Type</th><th>Permission Model</th><th>Requester</th><th>Permissions</th><th>Actions</th></tr></thead>
            <tbody>
              {data.blueprint_requests.map((r) => (
                <tr key={r.id}>
                  <td><strong>{r.name}</strong><div style={{ fontSize: 12, color: "#666" }}>{r.description?.slice(0, 80)}</div></td>
                  <td>{r.agent_type}</td>
                  <td><span className={`badge ${r.permission_mode === "inheritable" ? "badge-approved" : "badge-pending"}`}>{r.permission_mode}</span></td>
                  <td>{r.created_by}</td>
                  <td>{r.default_permissions?.length > 0
                    ? r.default_permissions.map((p, i) => <span key={i} className="badge badge-approved" style={{ marginRight: 4, marginBottom: 2 }}>{p.scope}</span>)
                    : <span style={{ color: "#888" }}>Manual</span>}
                  </td>
                  <td><ActionButtons type="blueprint" id={r.id} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      {data.identity_requests?.length > 0 && (
        <>
          <h2 style={{ fontSize: 18, marginBottom: 12 }}>Identity Requests ({data.identity_requests.length})</h2>
          <table className="data-table" style={{ marginBottom: 32 }}>
            <thead><tr><th>Agent Name</th><th>Type</th><th>Environment</th><th>Requester</th><th>Justification</th><th>Actions</th></tr></thead>
            <tbody>
              {data.identity_requests.map((r) => (
                <tr key={r.id}>
                  <td>{r.display_name}</td>
                  <td>{r.agent_type}</td>
                  <td>{r.environment}</td>
                  <td>{r.requested_by}</td>
                  <td style={{ maxWidth: 200, fontSize: 13 }}>{r.justification || "—"}</td>
                  <td><ActionButtons type="identity" id={r.id} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      {data.permission_requests?.length > 0 && (
        <>
          <h2 style={{ fontSize: 18, marginBottom: 12 }}>Permission Requests ({data.permission_requests.length})</h2>
          <table className="data-table">
            <thead><tr><th>Agent</th><th>Permissions</th><th>Requester</th><th>Justification</th><th>Actions</th></tr></thead>
            <tbody>
              {data.permission_requests.map((r) => (
                <tr key={r.id}>
                  <td>{r.identity_display_name}</td>
                  <td>{r.requested_permissions?.map((p, i) => <span key={i} className="badge badge-approved" style={{ marginRight: 4 }}>{p.scope}</span>)}</td>
                  <td>{r.requested_by}</td>
                  <td style={{ maxWidth: 200, fontSize: 13 }}>{r.justification || "—"}</td>
                  <td><ActionButtons type="permission" id={r.id} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      {totalPending === 0 && (
        <div className="empty-state">
          <div className="icon">✅</div>
          <p>All caught up! No pending requests.</p>
        </div>
      )}

      <Dialog open={!!actionTarget} onOpenChange={(_, d) => !d.open && setActionTarget(null)}>
        <DialogSurface>
          <DialogBody>
            <DialogTitle>Reject Request</DialogTitle>
            <DialogContent>
              <div className="form-group" style={{ marginTop: 8 }}>
                <label>Reason for rejection</label>
                <textarea value={rejectReason} onChange={(e) => setRejectReason(e.target.value)}
                  placeholder="Explain why this request is being rejected..." style={{ width: "100%", minHeight: 80 }} />
              </div>
            </DialogContent>
            <DialogActions>
              <Button appearance="secondary" onClick={() => setActionTarget(null)}>Cancel</Button>
              <Button appearance="primary" onClick={confirmReject}>Confirm Rejection</Button>
            </DialogActions>
          </DialogBody>
        </DialogSurface>
      </Dialog>
    </div>
  );
}
