import React, { useEffect } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import {
  AuthenticatedTemplate,
  UnauthenticatedTemplate,
  useMsal,
} from "@azure/msal-react";
import { loginRequest, apiScopes } from "./authConfig";
import { setMsalInstance } from "./services/api";
import Layout from "./components/Layout";
import Home from "./pages/Home";
import NewBlueprintRequest from "./pages/NewBlueprintRequest";
import NewIdentityRequest from "./pages/NewIdentityRequest";
import NewPermissionRequest from "./pages/NewPermissionRequest";
import MyRequests from "./pages/MyRequests";
import BlueprintCatalog from "./pages/BlueprintCatalog";
import AdminApprovals from "./pages/AdminApprovals";
import AuditLog from "./pages/AuditLog";
import LoginPage from "./pages/LoginPage";

function AppRoutes() {
  const { instance, accounts } = useMsal();

  useEffect(() => {
    if (accounts.length > 0) {
      setMsalInstance(instance, accounts[0]);
    }
  }, [instance, accounts]);

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/request/blueprint" element={<NewBlueprintRequest />} />
        <Route path="/request/identity" element={<NewIdentityRequest />} />
        <Route path="/request/permissions" element={<NewPermissionRequest />} />
        <Route path="/my-requests" element={<MyRequests />} />
        <Route path="/blueprints" element={<BlueprintCatalog />} />
        <Route path="/admin/approvals" element={<AdminApprovals />} />
        <Route path="/admin/audit-log" element={<AuditLog />} />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </Layout>
  );
}

export default function App() {
  return (
    <>
      <AuthenticatedTemplate>
        <AppRoutes />
      </AuthenticatedTemplate>
      <UnauthenticatedTemplate>
        <LoginPage />
      </UnauthenticatedTemplate>
    </>
  );
}
