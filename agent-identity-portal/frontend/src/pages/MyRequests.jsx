import React, { useEffect, useState } from "react";
import { Spinner, Tab, TabList } from "@fluentui/react-components";
import StatusBadge from "../components/StatusBadge";
import { getIdentityRequests, getPermissionRequests } from "../services/api";

export default function MyRequests() {
  const [tab, setTab] = useState("identity");
  const [identityReqs, setIdentityReqs] = useState([]);
  const [permReqs, setPermReqs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      getIdentityRequests({ mine: true }),
      getPermissionRequests({ mine: true }),
    ])
      .then(([ir, pr]) => {
        setIdentityReqs(ir);
        setPermReqs(pr);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner label="Loading requests..." />;

  return (
    <div>
      <div className="page-header">
        <h1>My Requests</h1>
        <p>Track the status of your submitted requests</p>
      </div>

      <TabList
        selectedValue={tab}
        onTabSelect={(_, d) => setTab(d.value)}
        style={{ marginBottom: 20 }}
      >
        <Tab value="identity">
          Identity Requests ({identityReqs.length})
        </Tab>
        <Tab value="permissions">
          Permission Requests ({permReqs.length})
        </Tab>
      </TabList>

      {tab === "identity" && (
        <>
          {identityReqs.length === 0 ? (
            <div className="empty-state">
              <div className="icon">📭</div>
              <p>No identity requests yet.</p>
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Agent Name</th>
                  <th>Type</th>
                  <th>Environment</th>
                  <th>Status</th>
                  <th>Submitted</th>
                  <th>App ID</th>
                </tr>
              </thead>
              <tbody>
                {identityReqs.map((r) => (
                  <tr key={r.id}>
                    <td>{r.display_name}</td>
                    <td>{r.agent_type}</td>
                    <td>{r.environment}</td>
                    <td>
                      <StatusBadge status={r.status} />
                    </td>
                    <td>{new Date(r.requested_at).toLocaleDateString()}</td>
                    <td>
                      {r.provisioned_app_id ? (
                        <code style={{ fontSize: 12 }}>
                          {r.provisioned_app_id}
                        </code>
                      ) : (
                        "—"
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}

      {tab === "permissions" && (
        <>
          {permReqs.length === 0 ? (
            <div className="empty-state">
              <div className="icon">📭</div>
              <p>No permission requests yet.</p>
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Agent</th>
                  <th>Permissions</th>
                  <th>Status</th>
                  <th>Submitted</th>
                </tr>
              </thead>
              <tbody>
                {permReqs.map((r) => (
                  <tr key={r.id}>
                    <td>{r.identity_display_name}</td>
                    <td>
                      {r.requested_permissions?.map((p, i) => (
                        <span key={i} className="badge badge-approved" style={{ marginRight: 4 }}>
                          {p.scope}
                        </span>
                      ))}
                    </td>
                    <td>
                      <StatusBadge status={r.status} />
                    </td>
                    <td>{new Date(r.requested_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </div>
  );
}
