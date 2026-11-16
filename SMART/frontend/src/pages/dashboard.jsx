
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import AppShell from "../components/AppShell";
import {
  getMyProgress,
  getMLConsent,
  updateMLConsent,
  getRevisionImprovement
} from "../services/api";

export default function Dashboard() {
  const [user, setUser] = useState(null);
  const [progress, setProgress] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

    const [mlConsent, setMlConsent] = useState(false);
  const [consentLoading, setConsentLoading] = useState(true);
  const [consentSaving, setConsentSaving] = useState(false);
  const [consentError, setConsentError] = useState("");
  const [consentMessage, setConsentMessage] = useState("");
  const [revisionReport, setRevisionReport] = useState(null);
  const [revisionLoading, setRevisionLoading] = useState(true);
  const [revisionError, setRevisionError] = useState("");

  useEffect(() => {
    try {
      setUser(JSON.parse(localStorage.getItem("smartUser") || "null"));
    } catch {
      setUser(null);
    }

    let active = true;

    getMyProgress()
      .then((data) => {
        if (active) setProgress(data);
      })
      .catch((err) => {
        if (active) setError(err.message || "Progress could not be loaded.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;

    getMLConsent()
      .then((data) => {
        if (active) {
          setMlConsent(data.enabled === true);
          setConsentError("");
        }
      })
      .catch((err) => {
        if (active) {
          setConsentError(err.message || "Could not load consent.");
        }
      })
      .finally(() => {
        if (active) setConsentLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;

    getRevisionImprovement()
      .then((data) => {
        if (active) setRevisionReport(data);
      })
      .catch((err) => {
        if (active) {
          setRevisionError(err.message || "Could not load revision report.");
        }
      })
      .finally(() => {
        if (active) setRevisionLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);
  const handleConsentChange = async (enabled) => {
    setConsentSaving(true);
    setConsentError("");
    setConsentMessage("");

    try {
      const data = await updateMLConsent(enabled);
      const actualStatus =
        typeof data.enabled === "boolean" ? data.enabled : enabled;

      setMlConsent(actualStatus);
      setConsentMessage(
        actualStatus
          ? "Your participation has been enabled."
          : "Your participation has been disabled."
      );
    } catch (err) {
      setConsentError(err.message || "Could not update consent.");
    } finally {
      setConsentSaving(false);
    }
  };

  const firstName = user?.name?.trim().split(/\s+/)[0] || "there";
  const summary = progress?.summary || {};

  
const activityRows = progress?.daily_activity || [];

const lastSevenDays = Array.from({ length: 7 }, (_, index) => {
  const date = new Date();
  date.setHours(0, 0, 0, 0);
  date.setDate(date.getDate() - (6 - index));

  const dateKey = [
    date.getFullYear(),
    String(date.getMonth() + 1).padStart(2, "0"),
    String(date.getDate()).padStart(2, "0")
  ].join("-");

  const record = activityRows.find(
    (item) => item.activity_date === dateKey
  );

  return {
    dateKey,
    day: date.toLocaleDateString("en-US", { weekday: "short" }),
    attempts: Number(record?.attempts || 0),
    successful: Number(record?.successful_attempts || 0),
    passRate: Number(record?.avg_test_pass_rate || 0)
  };
});

const maxAttempts = Math.max(
  1,
  ...lastSevenDays.map((day) => day.attempts)
);


  const stats = [
    {
      label: "Coding attempts",
      value: summary.total_attempts ?? 0,
      note: "Total submitted solutions",
      icon: "⌘",
    },
    {
      label: "Successful attempts",
      value: summary.successful_attempts ?? 0,
      note: "Submissions passing all tests",
      icon: "✓",
    },
    {
      label: "Questions solved",
      value: summary.unique_questions_solved ?? 0,
      note: "Unique questions completed",
      icon: "✦",
    },
    {
      label: "Average test pass rate",
      value: `${summary.average_test_pass_rate ?? 0}%`,
      note: "Across your attempts",
      icon: "↗",
    },
  ];

  return (
    <AppShell active="/dashboard" eyebrow="STUDENT WORKSPACE" title="Overview">

      <section className="dashboard-hero">
        <div>
          <div className="hero-kicker">YOUR PLACEMENT JOURNEY</div>
          <h1>Good to see you, {firstName}.</h1>
          <p>
            Track your coding practice, understand your weak concepts
            and keep improving with personalized learning.
          </p>
        </div>
        <Link className="btn hero-action" to="/coding">
          Continue learning <span>→</span>
        </Link>
      </section>

            <section
        className="card"
        style={{ padding: 24, marginTop: 22, marginBottom: 28 }}
      >
        <div className="small-label">
          ML RESEARCH PARTICIPATION & PRIVACY
        </div>

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: 12,
            marginTop: 10
          }}
        >
          <h2>Help improve your AI Coding Coach</h2>

          <span className="tag">
            {consentLoading
              ? "Checking consent..."
              : consentError
                ? "Status unavailable"
                : mlConsent
                  ? "Participation ON"
                  : "Participation OFF"}
          </span>
        </div>

        <p style={{ marginTop: 12, lineHeight: 1.7 }}>
          You can optionally allow eligible failed coding attempts
          to be used for improving the weak-concept detection model.
          Collected examples are kept for human review before being
          considered for model training.
        </p>

        <p style={{ marginTop: 10, fontSize: 12, color: "#64748b" }}>
          Direct identifiers are removed from review samples where
          supported. Internal account linkage is retained to manage
          withdrawal and deletion. Do not include passwords, API keys
          or personal details in submitted code.
        </p>

        {consentError && (
          <div className="alert" style={{ marginTop: 15 }}>
            {consentError}
          </div>
        )}

        {consentMessage && (
          <div className="notice" style={{ marginTop: 15 }}>
            {consentMessage}
          </div>
        )}

        <div
          style={{
            display: "flex",
            gap: 12,
            flexWrap: "wrap",
            marginTop: 20
          }}
        >
          <button
            type="button"
            className="btn btn-primary"
            disabled={
              consentLoading ||
              consentSaving ||
              !!consentError ||
              mlConsent
            }
            onClick={() => handleConsentChange(true)}
          >
            {consentSaving && !mlConsent
              ? "Saving..."
              : "Allow participation"}
          </button>

          <button
            type="button"
            className="btn btn-secondary"
            disabled={
              consentLoading ||
              consentSaving ||
              !!consentError ||
              !mlConsent
            }
            onClick={() => handleConsentChange(false)}
          >
            {consentSaving && mlConsent
              ? "Saving..."
              : "Withdraw consent"}
          </button>
        </div>

        <p style={{ fontSize: 11, color: "#64748b", marginTop: 14 }}>
          Participation is optional. It is OFF by default.
          Withdrawing consent stops future collection and requests
          deletion of samples linked to your account.
        </p>
      </section>

      <div className="dashboard-section-title">
        <h2>Your learning performance</h2>
        <span className="small-label">LIVE DATABASE DATA</span>
      </div>

      {loading && (
        <div className="card" style={{ padding: 24 }}>
          Loading your learning statistics...
        </div>
      )}

      {error && (
        <div className="card" style={{ padding: 20, color: "#b45309" }}>
          {error}
        </div>
      )}

      {!loading && !error && (
        <>
          <section className="stat-grid" aria-label="Student progress">
            {stats.map((item) => (
              <article className="card stat-card" key={item.label}>
                <div className="stat-top">
                  <span>{item.label}</span>
                  <span className="stat-icon">{item.icon}</span>
                </div>
                <div className="stat-value">{item.value}</div>
                <div className="stat-note">{item.note}</div>
              </article>
            ))}
          </section>

          <section className="card" style={{ padding: 22, marginBottom: 24 }}>
            <div style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              flexWrap: "wrap",
              gap: 12,
              marginBottom: 18
            }}>
              <div>
                <div className="small-label">PERSONAL LEARNING OUTCOMES</div>
                <h2 style={{ marginTop: 8 }}>Revision &amp; learning improvement</h2>
              </div>
              <span className="tag">
                {revisionLoading
                  ? "Loading report..."
                  : revisionError
                    ? "Status unavailable"
                    : `${revisionReport?.matched_count ?? 0} matched pair(s)`}
              </span>
            </div>

            {revisionLoading ? (
              <p className="empty-note">Loading your revision results...</p>
            ) : revisionError ? (
              <div className="alert">{revisionError}</div>
            ) : revisionReport?.pairs?.length > 0 ? (
              <>
                <div style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
                  gap: 14
                }}>
                  {revisionReport.pairs.map((item, index) => {
                    const change = Number(item.change_percentage_points || 0);

                    return (
                      <article
                        className="card module-card"
                        key={`${item.question_id}-${item.revision_time}-${index}`}
                      >
                        <span className="tag">{item.weak_concept}</span>
                        <h3 style={{ marginTop: 12 }}>
                          {item.question_id.replaceAll("_", " ")}
                        </h3>

                        <p style={{ marginTop: 12 }}>
                          Before revision: <strong>{item.before_passed}/{item.before_total}</strong>
                          {" "}({item.before_rate}%)
                        </p>
                        <p style={{ marginTop: 7 }}>
                          After revision: <strong>{item.after_passed}/{item.after_total}</strong>
                          {" "}({item.after_rate}%)
                        </p>

                        <p style={{
                          marginTop: 12,
                          fontWeight: 700,
                          color: change > 0 ? "#168454" : change < 0 ? "#a16207" : "#64748b"
                        }}>
                          Observed change: {change > 0 ? "+" : ""}{change.toFixed(1)} percentage points
                        </p>

                        <p style={{ fontSize: 11, color: "#64748b", marginTop: 10 }}>
                          Revision recorded: {item.revision_time}
                        </p>
                      </article>
                    );
                  })}
                </div>

                <p style={{ fontSize: 11, color: "#64748b", marginTop: 16 }}>
                  These are matched before-and-after observations. They do not prove that revision alone caused the change.
                </p>
              </>
            ) : (
              <p style={{ color: "#64748b" }}>
                No matched before-and-after coding attempts yet. Complete a revision lesson and then evaluate a practice attempt to build your report.
              </p>
            )}
          </section>
          <div className="dashboard-section-title">
            <h2>Topic-wise performance</h2>
            <span className="small-label">YOUR ACTIVITY</span>
          </div>

          <section className="module-grid">
            {progress.topics?.length > 0 ? (
              progress.topics.map((item) => {
                const rate = item.attempts
                  ? Math.round(
                      (item.successful_attempts / item.attempts) * 100
                    )
                  : 0;

                return (
                  <article className="card module-card" key={item.topic}>
                    <span className="tag">LEARNING TOPIC</span>
                    <h3>{item.topic || "General"}</h3>
                    <p>
                      {item.attempts} attempts · {item.successful_attempts} successful
                    </p>

                    <div
                      style={{
                        height: 8,
                        background: "#e8edf5",
                        borderRadius: 20,
                        overflow: "hidden",
                        marginTop: 16,
                      }}
                    >
                      <div
                        style={{
                          width: `${rate}%`,
                          height: "100%",
                          background: "#3975dc",
                          borderRadius: 20,
                        }}
                      />
                    </div>

                    <p style={{ marginTop: 10, fontSize: 12 }}>
                      Successful attempt rate: {rate}%
                    </p>
                  </article>
                );
              })
            ) : (
              <article className="card module-card">
                <h3>Your learning journey starts here</h3>
                <p>
                  Solve your first coding question to see topic-wise
                  progress here.
                </p>
                <Link to="/coding" className="btn btn-primary">
                  Start practising →
                </Link>
              </article>
            )}
          </section>

          <div className="dashboard-section-title">
            
<div className="dashboard-section-title">
  <h2>Your weekly learning activity</h2>
  <span className="small-label">LAST 7 DAYS</span>
</div>

<section className="card" style={{ padding: 24 }}>
  <div
    style={{
      display: "flex",
      justifyContent: "space-between",
      flexWrap: "wrap",
      gap: 12,
      marginBottom: 24
    }}
  >
    <div>
      <div className="small-label">CODING ACTIVITY</div>
      <h3 style={{ fontSize: 22, marginTop: 8 }}>
        Your learning consistency
      </h3>
    </div>
    <span className="tag">7-day report</span>
  </div>

  <div
    style={{
      display: "grid",
      gridTemplateColumns: "repeat(7, minmax(0, 1fr))",
      gap: 10,
      alignItems: "end",
      minHeight: 190
    }}
  >
    {lastSevenDays.map((day) => (
      <div
        key={day.dateKey}
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 8,
          minWidth: 0
        }}
      >
        <strong style={{ fontSize: 11 }}>
          {day.attempts}
        </strong>

        <div
          style={{
            width: "100%",
            maxWidth: 34,
            height: 125,
            background: "#edf1f7",
            borderRadius: 8,
            display: "flex",
            alignItems: "flex-end",
            overflow: "hidden"
          }}
        >
          <div
            style={{
              width: "100%",
              height: day.attempts
                ? `${Math.max(8, (day.attempts / maxAttempts) * 100)}%`
                : "0%",
              minHeight: day.attempts ? 8 : 0,
              background: "#3975dc",
              borderRadius: 8
            }}
          />
        </div>

        <span style={{ fontSize: 11, color: "#64748b" }}>
          {day.day}
        </span>

        <span style={{ fontSize: 10, color: "#168454" }}>
          {day.passRate}%
        </span>
      </div>
    ))}
  </div>

  <div
    style={{
      display: "flex",
      justifyContent: "center",
      gap: 20,
      flexWrap: "wrap",
      marginTop: 20,
      fontSize: 11,
      color: "#64748b"
    }}
  >
    <span>■ Coding attempts</span>
    <span>Green percentage = daily pass rate</span>
  </div>
</section>

            <h2>Concepts to improve</h2>
            <span className="small-label">PERSONALIZED INSIGHTS</span>
          </div>

          <section className="card" style={{ padding: 22 }}>
            {progress.weak_concepts?.length > 0 ? (
              progress.weak_concepts.map((item) => (
                <div
                  key={item.weak_concept}
                  style={{
                    padding: "13px 0",
                    borderBottom: "1px solid #edf0f5",
                    display: "flex",
                    justifyContent: "space-between",
                    gap: 12,
                  }}
                >
                  <strong>{item.weak_concept}</strong>
                  <span className="tag">
                    {item.occurrences} occurrence(s)
                  </span>
                </div>
              ))
            ) : (
              <p style={{ color: "#64748b" }}>
                No recurring weak concepts recorded yet. Keep practising!
              </p>
            )}
          </section>

          <div className="dashboard-section-title">
            <h2>Recent coding activity</h2>
            <span className="small-label">LATEST SUBMISSIONS</span>
          </div>

          <section className="card" style={{ padding: 22 }}>
            {progress.recent_attempts?.length > 0 ? (
              progress.recent_attempts.map((item) => (
                <div
                  key={item.question_id + item.created_at}
                  style={{
                    padding: "15px 0",
                    borderBottom: "1px solid #edf0f5",
                    display: "flex",
                    justifyContent: "space-between",
                    flexWrap: "wrap",
                    gap: 12,
                  }}
                >
                  <div>
                    <strong>{item.question_id.replaceAll("_", " ")}</strong>
                    <p style={{ fontSize: 12, color: "#64748b", marginTop: 5 }}>
                      {item.topic} · {item.language} · {item.created_at}
                    </p>
                  </div>
                  <span
                    className="tag"
                    style={{
                      background:
                        item.total > 0 && item.passed === item.total
                          ? "#e8f7ef"
                          : "#fff4e5",
                      color:
                        item.total > 0 && item.passed === item.total
                          ? "#168454"
                          : "#a16207",
                    }}
                  >
                    {item.passed}/{item.total} tests passed
                  </span>
                </div>
              ))
            ) : (
              <p style={{ color: "#64748b" }}>
                No coding activity yet. Your submissions will appear here.
              </p>
            )}
          </section>
        </>
      )}

      <div className="dashboard-section-title">
        <h2>Your preparation modules</h2>
        <span className="small-label">CONTINUE LEARNING</span>
      </div>

      <section className="module-grid">
        <article className="card module-card">
          <div className="module-mark">⌘</div>
          <span className="tag">CORE MODULE</span>
          <h3>Coding Coach</h3>
          <p>
            Learn programming concepts, practise questions and
            receive personalized feedback.
          </p>
          <Link to="/coding" className="btn btn-primary">
            Open coding coach →
          </Link>
        </article>

        <article className="card module-card secondary">
          <div className="module-mark">✧</div>
          <span className="tag">NEXT DEVELOPMENT PHASE</span>
          <h3>Interview Coach</h3>
          <p>
            Resume analysis, mock interviews and communication
            feedback are planned for a later release.
          </p>
          <button className="btn btn-secondary" disabled>
            Coming in a future release
          </button>
        </article>
      </section>

    </AppShell>
  );
}
