import React from "react";
import { useMsal } from "@azure/msal-react";
import { Button } from "@fluentui/react-components";
import { loginRequest } from "../authConfig";

export default function LoginPage() {
  const { instance } = useMsal();

  return (
    <div className="login-page">
      <div className="login-card">
        <div style={{ fontSize: 48 }}>🛡️</div>
        <h1>Agent Identity Portal</h1>
        <p>
          Self-service portal for requesting Agent Blueprints, Identities, and
          Permissions with built-in approval workflows.
        </p>
        <Button
          appearance="primary"
          size="large"
          onClick={() => instance.loginRedirect(loginRequest)}
          style={{ minWidth: 200 }}
        >
          Sign in with Microsoft
        </Button>
      </div>
    </div>
  );
}
