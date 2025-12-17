import React from "react";
import { SignupPage } from "./pages/SignupPage";
import { Routes, Route, Navigate } from "react-router-dom";
import { LoginPage } from "./pages/LoginPage";
import { DashboardPage } from "./pages/DashboardPage";
import { HabitsPage } from "./pages/HabitsPage";
import { ConnectionTest } from "./pages/ConnectionTest";
import { NavBar } from "./components/NavBar";
import { AuthGuard } from "./components/AuthGuard";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />

      <Route
        path="/*"
        element={
          <AuthGuard>
            <NavBar />
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/habits" element={<HabitsPage />} />
              <Route path="/connect" element={<ConnectionTest />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </AuthGuard>
        }
      />
    </Routes>
  );
}
