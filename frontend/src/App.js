import React from "react";
import "./App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "./components/ui/sonner";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { AppProvider } from "./context/AppContext";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import IntakePage from "./pages/IntakePage";
import AssistantPage from "./pages/AssistantPage";
import RequestsPage from "./pages/RequestsPage";
import RequestDetail from "./pages/RequestDetail";
import ApprovalsPage from "./pages/ApprovalsPage";
import PoliciesPage from "./pages/PoliciesPage";
import GrievancesPage from "./pages/GrievancesPage";
import AuditPage from "./pages/AuditPage";
import JudgeMode from "./pages/JudgeMode";
import CaseReport from "./pages/CaseReport";

function Gate() {
  const { authReady, isAuthed } = useAuth();
  if (!authReady) {
    return <div className="min-h-screen bg-[#F1EDE3] flex items-center justify-center text-[#8a8578]">Loading…</div>;
  }
  if (!isAuthed) return <Login />;
  return (
    <AppProvider>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/intake" element={<IntakePage />} />
            <Route path="/assistant" element={<AssistantPage />} />
            <Route path="/requests" element={<RequestsPage />} />
            <Route path="/requests/:id" element={<RequestDetail />} />
            <Route path="/requests/:id/report" element={<CaseReport />} />
            <Route path="/approvals" element={<ApprovalsPage />} />
            <Route path="/policies" element={<PoliciesPage />} />
            <Route path="/grievances" element={<GrievancesPage />} />
            <Route path="/audit" element={<AuditPage />} />
            <Route path="/judge" element={<JudgeMode />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </AppProvider>
  );
}

function App() {
  return (
    <div className="App">
      <AuthProvider>
        <Gate />
      </AuthProvider>
      <Toaster />
    </div>
  );
}

export default App;
