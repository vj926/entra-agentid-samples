import React from "react";
import { NavLink } from "react-router-dom";
import { useMsal } from "@azure/msal-react";
import {
  ShieldCheckmarkRegular,
  HomeRegular,
  AddCircleRegular,
  ListRegular,
  GridRegular,
  CheckmarkCircleRegular,
  DocumentSearchRegular,
  KeyRegular,
  DocumentBulletListRegular,
} from "@fluentui/react-icons";

export default function Layout({ children }) {
  const { accounts } = useMsal();
  const user = accounts[0];

  return (
    <div className="app-layout">
      <nav className="sidebar">
        <div className="sidebar-brand">
          <ShieldCheckmarkRegular className="shield" />
          <span>Agent Identity Portal</span>
        </div>

        <div className="sidebar-section">
          <div className="sidebar-section-title">Navigate</div>
          <NavLink to="/" end>
            <HomeRegular /> Dashboard
          </NavLink>
          <NavLink to="/blueprints">
            <GridRegular /> Blueprint Catalog
          </NavLink>
        </div>

        <div className="sidebar-section">
          <div className="sidebar-section-title">Requests</div>
          <NavLink to="/request/blueprint">
            <DocumentBulletListRegular /> Request Blueprint
          </NavLink>
          <NavLink to="/request/identity">
            <AddCircleRegular /> Request Identity
          </NavLink>
          <NavLink to="/request/permissions">
            <KeyRegular /> Request Permissions
          </NavLink>
          <NavLink to="/my-requests">
            <ListRegular /> My Requests
          </NavLink>
        </div>

        <div className="sidebar-section">
          <div className="sidebar-section-title">Admin</div>
          <NavLink to="/admin/approvals">
            <CheckmarkCircleRegular /> Approvals
          </NavLink>
          <NavLink to="/admin/audit-log">
            <DocumentSearchRegular /> Audit Log
          </NavLink>
        </div>

        {user && (
          <div className="sidebar-user">
            Signed in as
            <br />
            <strong>{user.name || user.username}</strong>
          </div>
        )}
      </nav>

      <main className="main-content">{children}</main>
    </div>
  );
}
