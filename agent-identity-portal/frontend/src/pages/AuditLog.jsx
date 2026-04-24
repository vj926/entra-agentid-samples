import React, { useEffect, useState } from "react";
import { Spinner } from "@fluentui/react-components";
import { getAuditLog } from "../services/api";

export default function AuditLog() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getAuditLog(100)
      .then(setLogs)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner label="Loading audit log..." />;

  return (
    <div>
      <div className="page-header">
        <h1>Audit Log</h1>
        <p>Complete record of all actions taken in the portal</p>
      </div>

      {logs.length === 0 ? (
        <div className="empty-state">
          <div className="icon">📝</div>
          <p>No audit entries yet.</p>
        </div>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Entity Type</th>
              <th>Action</th>
              <th>Performed By</th>
              <th>Entity ID</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => (
              <tr key={log.id}>
                <td style={{ whiteSpace: "nowrap", fontSize: 13 }}>
                  {new Date(log.performed_at).toLocaleString()}
                </td>
                <td>{log.entity_type}</td>
                <td>
                  <span
                    className={`badge ${
                      log.action === "approved" || log.action === "granted"
                        ? "badge-approved"
                        : log.action === "rejected" || log.action.includes("failed")
                        ? "badge-rejected"
                        : "badge-pending"
                    }`}
                  >
                    {log.action}
                  </span>
                </td>
                <td>{log.performed_by}</td>
                <td>
                  <code style={{ fontSize: 11 }}>{log.entity_id.slice(0, 8)}...</code>
                </td>
                <td style={{ fontSize: 12, color: "#666" }}>
                  {Object.keys(log.details || {}).length > 0
                    ? JSON.stringify(log.details)
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
