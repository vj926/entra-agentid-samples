import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@fluentui/react-components";
import { getDashboardStats } from "../services/api";

export default function Home() {
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);

  useEffect(() => {
    getDashboardStats().then(setStats).catch(() => {});
  }, []);

  const quickActions = [
    {
      title: "Request Agent Blueprint",
      desc: "Define a new blueprint for agents with inheritable or manually-approved permissions.",
      path: "/request/blueprint",
      icon: "📋",
    },
    {
      title: "Request Agent Identity",
      desc: "Create a new Entra ID identity for your AI agent from an existing approved blueprint.",
      path: "/request/identity",
      icon: "🤖",
    },
    {
      title: "Request Permissions",
      desc: "Add API permissions to an existing agent identity created in Copilot Studio or Foundry.",
      path: "/request/permissions",
      icon: "🔑",
    },
    {
      title: "Browse Blueprints",
      desc: "Explore all approved agent blueprints and their permission configurations.",
      path: "/blueprints",
      icon: "🗒️",
    },
    {
      title: "View My Requests",
      desc: "Track the status of your submitted blueprint, identity, and permission requests.",
      path: "/my-requests",
      icon: "📊",
    },
  ];

  return (
    <div>
      <div className="page-header">
        <h1>Dashboard</h1>
        <p>Manage agent identities and permissions across your organization</p>
      </div>

      {stats && (
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-value">{stats.active_blueprints || 0}</div>
            <div className="stat-label">Active Blueprints</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.provisioned_identities || 0}</div>
            <div className="stat-label">Provisioned Identities</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.granted_permissions || 0}</div>
            <div className="stat-label">Permissions Granted</div>
          </div>
          <div className="stat-card">
            <div className="stat-value" style={{ color: (stats.pending_approvals || 0) > 0 ? "#856404" : undefined }}>
              {stats.pending_approvals || 0}
            </div>
            <div className="stat-label">Pending Approvals</div>
          </div>
          {(stats.identity_requests?.failed || 0) > 0 && (
            <div className="stat-card" style={{ borderColor: "#f5c6cb" }}>
              <div className="stat-value" style={{ color: "#721c24" }}>{stats.identity_requests.failed}</div>
              <div className="stat-label">Failed Provisions</div>
            </div>
          )}
        </div>
      )}

      <div className="card-grid">
        {quickActions.map((action) => (
          <div
            key={action.path}
            className="card"
            onClick={() => navigate(action.path)}
          >
            <div style={{ fontSize: 28, marginBottom: 8 }}>{action.icon}</div>
            <div className="card-title">{action.title}</div>
            <div className="card-desc">{action.desc}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
