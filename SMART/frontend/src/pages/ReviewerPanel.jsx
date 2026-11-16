import { useEffect, useState } from "react";
import AppShell from "../components/AppShell";
import {
  getPendingMLSamples,
  reviewMLSample,
  exportMLSamples
} from "../services/api";

const WEAK_CONCEPTS = [
  "Syntax & Indentation",
  "Variables & Naming",
  "Data Types & Input Handling",
  "Arrays & Indexing",
  "Loops & Iteration",
  "Recursion",
  "Function Usage",
  "Algorithm Efficiency"
];

export default function ReviewerPanel() {
  const [samples, setSamples] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busyId, setBusyId] = useState(null);
  const [exportBusy, setExportBusy] = useState(false);
  const [decisions, setDecisions] = useState({});

  async function loadSamples() {
    setLoading(true);
    setError("");

    try {
      const data = await getPendingMLSamples();
      setSamples(data.samples || []);
    } catch (err) {
      setError(err.message || "Could not load pending samples.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadSamples();
  }, []);

  function updateDecision(sampleId, field, value) {
    setDecisions((previous) => ({
      ...previous,
      [sampleId]: {
        label: previous[sampleId]?.label || "",
        note: previous[sampleId]?.note || "",
        [field]: value
      }
    }));
  }

  async function handleReview(sample, action) {
    const decision = decisions[sample.id] || {
      label: "",
      note: ""
    };

    if (action === "approve" && !decision.label) {
      setError("Select a weak-concept label before approving.");
      return;
    }

    setBusyId(sample.id);
    setError("");
    setNotice("");

    try {
      await reviewMLSample(sample.id, {
        action,
        label: action === "approve" ? decision.label : null,
        reviewerNote: decision.note
      });

      setSamples((previous) =>
        previous.filter((item) => item.id !== sample.id)
      );

      setNotice(
        action === "approve"
          ? `Sample ${sample.id} approved with label: ${decision.label}`
          : `Sample ${sample.id} rejected successfully.`
      );
    } catch (err) {
      setError(err.message || "Review action failed.");
    } finally {
      setBusyId(null);
    }
  }

  async function handleExport() {
    setExportBusy(true);
    setError("");
    setNotice("");

    try {
      const data = await exportMLSamples();

      if (!data.samples || data.samples.length === 0) {
        setNotice("No approved samples available for export yet.");
        return;
      }

      const blob = new Blob(
        [JSON.stringify(data.samples, null, 2)],
        { type: "application/json" }
      );

      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");

      link.href = url;
      link.download = "approved_ml_training_samples.json";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      setNotice(`${data.count} approved samples exported successfully.`);
    } catch (err) {
      setError(err.message || "Export failed.");
    } finally {
      setExportBusy(false);
    }
  }

  return (
    <AppShell
      active="/dashboard"
      eyebrow="ML REVIEW WORKSPACE"
      title="Human Reviewer Panel"
      backTo="/dashboard"
      backLabel="Dashboard"
    >
      <div className="page-heading">
        <div>
          <div className="section-kicker">
            HUMAN-VERIFIED TRAINING DATA
          </div>
          <h1>Review coding-error samples</h1>
          <p>
            Inspect anonymized coding submissions and assign the
            correct weak-concept category before model training.
          </p>
        </div>

        <span className="tag">REVIEWER ACCESS</span>
      </div>

      <section className="card" style={{ padding: 22, marginBottom: 22 }}>
        <div className="small-label">REVIEW GUIDELINES</div>
        <p style={{ marginTop: 10, lineHeight: 1.7 }}>
          Only genuine student coding errors should be approved.
          Reject Docker failures, infrastructure errors, test
          submissions and unrelated samples. Never treat the
          model's predicted category as a verified label.
        </p>

        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginTop: 18 }}>
          <button
            className="btn btn-secondary"
            onClick={loadSamples}
            disabled={loading || busyId !== null}
          >
            Refresh samples
          </button>

          <button
            className="btn btn-primary"
            onClick={handleExport}
            disabled={exportBusy}
          >
            {exportBusy ? "Exporting..." : "Export approved data"}
          </button>
        </div>
      </section>

      <div className="dashboard-section-title">
        <h2>Pending samples</h2>
        <span className="small-label">
          {samples.length} AWAITING REVIEW
        </span>
      </div>

      {error && (
        <div className="alert" style={{ marginBottom: 16 }}>
          {error}
        </div>
      )}

      {notice && (
        <div className="notice" style={{ marginBottom: 16 }}>
          {notice}
        </div>
      )}

      {loading ? (
        <section className="card" style={{ padding: 24 }}>
          Loading pending samples...
        </section>
      ) : samples.length === 0 ? (
        <section className="card" style={{ padding: 28 }}>
          <h3>No pending samples</h3>
          <p style={{ marginTop: 10, color: "#64748b" }}>
            New eligible samples from students who have opted in
            will appear here for human review.
          </p>
        </section>
      ) : (
        <div style={{ display: "grid", gap: 18 }}>
          {samples.map((sample) => {
            const decision = decisions[sample.id] || {
              label: "",
              note: ""
            };

            return (
              <section
                className="card"
                key={sample.id}
                style={{ padding: 24 }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    flexWrap: "wrap",
                    gap: 12
                  }}
                >
                  <div>
                    <span className="tag">
                      SAMPLE #{sample.id}
                    </span>

                    <h3 style={{ marginTop: 12 }}>
                      {sample.question_id.replaceAll("_", " ")}
                    </h3>

                    <p style={{ marginTop: 7, color: "#64748b" }}>
                      {sample.topic} · {sample.language}
                    </p>
                  </div>

                  <span className="tag">
                    {sample.passed}/{sample.total} tests passed
                  </span>
                </div>

                <div style={{ marginTop: 20 }}>
                  <div className="small-label">
                    COMPILER / RUNTIME DIAGNOSTIC
                  </div>

                  <pre
                    style={{
                      whiteSpace: "pre-wrap",
                      overflowWrap: "anywhere",
                      background: "#f5f7fc",
                      padding: 14,
                      borderRadius: 9,
                      marginTop: 9,
                      maxHeight: 180,
                      overflowY: "auto",
                      fontSize: 12
                    }}
                  >
                    {sample.diagnostic_message}
                  </pre>
                </div>

                <div style={{ marginTop: 18 }}>
                  <div className="small-label">
                    SUBMITTED CODE
                  </div>

                  <pre
                    style={{
                      whiteSpace: "pre-wrap",
                      overflowWrap: "anywhere",
                      background: "#f5f7fc",
                      padding: 14,
                      borderRadius: 9,
                      marginTop: 9,
                      maxHeight: 220,
                      overflowY: "auto",
                      fontSize: 12
                    }}
                  >
                    {sample.code_snippet}
                  </pre>
                </div>

                <div style={{ marginTop: 20 }}>
                  <label
                    className="small-label"
                    htmlFor={`label-${sample.id}`}
                  >
                    HUMAN-VERIFIED WEAK CONCEPT
                  </label>

                  <select
                    id={`label-${sample.id}`}
                    value={decision.label}
                    onChange={(event) =>
                      updateDecision(
                        sample.id,
                        "label",
                        event.target.value
                      )
                    }
                    style={{
                      display: "block",
                      width: "100%",
                      padding: 12,
                      borderRadius: 8,
                      border: "1px solid #dbe2ed",
                      marginTop: 9,
                      background: "white"
                    }}
                  >
                    <option value="">Select verified category</option>
                    {WEAK_CONCEPTS.map((concept) => (
                      <option key={concept} value={concept}>
                        {concept}
                      </option>
                    ))}
                  </select>
                </div>

                <div style={{ marginTop: 16 }}>
                  <label
                    className="small-label"
                    htmlFor={`note-${sample.id}`}
                  >
                    REVIEWER NOTE
                  </label>

                  <textarea
                    id={`note-${sample.id}`}
                    value={decision.note}
                    maxLength={1000}
                    onChange={(event) =>
                      updateDecision(
                        sample.id,
                        "note",
                        event.target.value
                      )
                    }
                    placeholder="Explain why this label is appropriate..."
                    rows={3}
                    style={{
                      display: "block",
                      width: "100%",
                      padding: 12,
                      borderRadius: 8,
                      border: "1px solid #dbe2ed",
                      marginTop: 9,
                      resize: "vertical"
                    }}
                  />
                </div>

                <div
                  style={{
                    display: "flex",
                    gap: 10,
                    flexWrap: "wrap",
                    marginTop: 18
                  }}
                >
                  <button
                    className="btn btn-primary"
                    disabled={busyId !== null}
                    onClick={() => handleReview(sample, "approve")}
                  >
                    {busyId === sample.id ? "Saving..." : "Approve sample"}
                  </button>

                  <button
                    className="btn btn-secondary"
                    disabled={busyId !== null}
                    onClick={() => handleReview(sample, "reject")}
                  >
                    Reject sample
                  </button>
                </div>
              </section>
            );
          })}
        </div>
      )}
    </AppShell>
  );
}