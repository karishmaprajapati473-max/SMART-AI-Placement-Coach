
import { useEffect, useState } from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate
} from "react-router-dom";

import Signup from "./pages/signup";
import Login from "./pages/login";
import Dashboard from "./pages/dashboard";
import CodingCoach from "./pages/CodingCoach";
import LearnConcept from "./pages/LearnConcept";
import PracticeQuestion from "./pages/PracticeQuestion";
import CodeEditor from "./pages/CodeEditor";
import ReviewerPanel from "./pages/ReviewerPanel";
import { getCurrentUser } from "./services/api";


function ProtectedRoute({ children }) {
  const [status, setStatus] = useState("checking");

  useEffect(() => {
    let active = true;

    getCurrentUser()
      .then((data) => {
        if (!active) return;

        localStorage.setItem(
          "smartUser",
          JSON.stringify(data.user)
        );

        setStatus("authenticated");
      })
      .catch(() => {
        if (!active) return;

        localStorage.removeItem("smartUser");
        setStatus("unauthenticated");
      });

    return () => {
      active = false;
    };
  }, []);

  if (status === "checking") {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "grid",
          placeItems: "center",
          color: "#334155"
        }}
      >
        Checking your session...
      </div>
    );
  }

  if (status === "unauthenticated") {
    return (
      <Navigate
        to="/"
        replace
        state={{
          notice: "Please sign in to access your learning workspace."
        }}
      />
    );
  }

  return children;
}

function ReviewerRoute({ children }) {
  const [status, setStatus] = useState("checking");

  useEffect(() => {
    let active = true;

    getCurrentUser()
      .then((data) => {
        if (!active) return;

        setStatus(
          data.user?.role === "reviewer"
            ? "authorized"
            : "forbidden"
        );
      })
      .catch(() => {
        if (active) setStatus("unauthenticated");
      });

    return () => {
      active = false;
    };
  }, []);

  if (status === "checking") {
    return <div style={{ padding: 30 }}>Checking reviewer access...</div>;
  }

  if (status === "unauthenticated") {
    return <Navigate to="/" replace />;
  }

  if (status === "forbidden") {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public pages */}
        <Route path="/" element={<Login />} />
        <Route path="/signup" element={<Signup />} />

        {/* Protected student pages */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />

        <Route
          path="/coding"
          element={
            <ProtectedRoute>
              <CodingCoach />
            </ProtectedRoute>
          }
        />

        <Route
          path="/learn"
          element={
            <ProtectedRoute>
              <LearnConcept />
            </ProtectedRoute>
          }
        />

        <Route
          path="/practice"
          element={
            <ProtectedRoute>
              <PracticeQuestion />
            </ProtectedRoute>
          }
        />

        <Route
          path="/code-editor"
          element={
            <ProtectedRoute>
              <CodeEditor />
            </ProtectedRoute>
          }
        />
          <Route
  path="/reviewer"
  element={
    <ReviewerRoute>
      <ReviewerPanel />
    </ReviewerRoute>
  }
/>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
