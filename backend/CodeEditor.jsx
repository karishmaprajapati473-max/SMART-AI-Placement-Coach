import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import Editor from "@monaco-editor/react";
import AppShell from "../components/AppShell";
import { evaluateCode, getQuestion, runCode } from "../services/api";

const editorLanguages = {
  Python: "python",
  C: "c",
  "C++": "cpp",
  Java: "java",
};

export default function CodeEditor() {
  const location = useLocation();
  const navigate = useNavigate();

  const language = location.state?.language || "Python";
  const topic = location.state?.topic || "Arrays";
  const questionId = location.state?.questionId || "largest_element";

  const [code, setCode] = useState("");
  const [inputData, setInputData] = useState("");
  const [question, setQuestion] = useState(null);
  const [loadingQuestion, setLoadingQuestion] = useState(true);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");
  const [output, setOutput] = useState("");
  const [testResults, setTestResults] = useState([]);
  const [diagnosis, setDiagnosis] = useState(location.state?.diagnosis || null);

  // Load this question's metadata, language-specific starter code and example input.
  useEffect(() => {
    let active = true;

    setLoadingQuestion(true);
    setQuestion(null);
    setCode("");
    setInputData("");
    setStatus("");
    setOutput("");
    setTestResults([]);

    getQuestion(questionId)
      .then((data) => {
        if (!active) return;

        setQuestion(data);
        setCode(data.starter_code?.[language] || "");
        setInputData(data.examples?.[0]?.input || "");

        if (!data.starter_code?.[language]) {
          setStatus(`Starter code is not available for ${language}.`);
        }
      })
      .catch((error) => {
        if (active) {
          setQuestion(null);
          setStatus(error.message || "Unable to load the question. Check that the backend is running.");
        }
      })
      .finally(() => {
        if (active) setLoadingQuestion(false);
      });

    return () => {
      active = false;
    };
  }, [questionId, language]);

  const handleRun = async () => {
    setBusy(true);
    setStatus("Running your code...");
    setOutput("");
    setTestResults([]);

    try {
      const result = await runCode({ language, questionId, code, inputData });

      if (result.status !== "success") {
        setStatus("Execution error");
        setOutput(result.error || result.message || "The program could not be executed.");
      } else {
        setStatus("Run completed");
        setOutput(result.output || "Program completed without printed output.");
      }
    } catch (error) {
      setStatus("Connection error");
      setOutput(error.message || "Could not connect to the backend.");
    } finally {
      setBusy(false);
    }
  };

  const handleSubmit = async () => {
    setBusy(true);
    setStatus("Checking test cases...");
    setOutput("");
    setTestResults([]);
    setDiagnosis(null);

    try {
      const result = await evaluateCode({
        language,
        questionId,
        code,
        revisedConcept: location.state?.diagnosis?.weak_concept || null,
      });

      if (result.status === "error") {
        throw new Error(result.message || "Evaluation failed.");
      }

      setStatus(
        result.status === "success"
          ? "All test cases passed"
          : "Some test cases need attention"
      );
      setOutput(`${result.passed} of ${result.total} test cases passed.`);
      setTestResults(result.results || []);
      setDiagnosis(result.diagnosis || null);
    } catch (error) {
      setStatus("Evaluation error");
      setOutput(error.message || "Could not evaluate the solution.");
    } finally {
      setBusy(false);
    }
  };

  const resetCode = () => {
    setCode(question?.starter_code?.[language] || "");
    setStatus("");
    setOutput("");
    setTestResults([]);
  };

  return (
    <AppShell
      active="/coding"
      eyebrow="CODING WORKSPACE"
      title="Solve & evaluate"
      backTo="/practice"
      backLabel="Practice question"
    >
      <div className="page-heading">
        <div>
          <div className="section-kicker">STEP 04 / 04 · YOUR SOLUTION</div>
          <h1>{question?.title || "Coding workspace"}</h1>
          <p>Write your solution, run it with custom input, then submit it for test-case evaluation.</p>
        </div>
        <span className="tag">{language} · {topic}</span>
      </div>

      {diagnosis && (
        <section
          className="card"
          style={{
            marginBottom: 20,
            padding: 24,
            borderLeft: `4px solid ${
              diagnosis.status === "success" ? "#168c68" : "#386fe8"
            }`,
          }}
        >
          <div className="small-label">PERSONALIZED AI LEARNING INSIGHT</div>

          <h2 style={{ marginTop: 10, fontSize: 21 }}>
            {diagnosis.status === "success"
              ? "Excellent work! All tests passed."
              : "Let's strengthen your understanding."}
          </h2>

          <p style={{ marginTop: 14 }}>
            <strong>Suggested focus:</strong>{" "}
            {diagnosis.weak_concept || "No weak concept identified"}
          </p>
          <p style={{ marginTop: 10 }}>
            <strong>Confidence:</strong> {diagnosis.confidence ?? "Not available"}
          </p>
          <p style={{ marginTop: 10 }}>
            <strong>What we noticed:</strong>{" "}
            {diagnosis.evidence || "Review the test-case feedback above."}
          </p>

          {diagnosis.recommendation && (
            <div className="notice" style={{ marginTop: 16 }}>
              <strong>Recommended revision</strong>
              <p style={{ marginTop: 6 }}>{diagnosis.recommendation}</p>
            </div>
          )}

          {diagnosis.method && (
            <span className="tag" style={{ marginTop: 14, display: "inline-flex" }}>
              Method: {diagnosis.method}
            </span>
          )}

          {diagnosis.weak_concept && (
            <button
              className="btn btn-primary"
              style={{ marginTop: 18 }}
              onClick={() =>
                navigate("/learn", {
                  state: {
                    language,
                    topic,
                    questionId,
                    diagnosis,
                  },
                })
              }
            >
              Revise This Concept →
            </button>
          )}
        </section>
      )}

      <div className="editor-layout">
        <section className="card editor-problem">
          <div className="small-label">PROBLEM BRIEF</div>
          <h2>
            {loadingQuestion
              ? "Loading question..."
              : question?.title || "Question details unavailable"}
          </h2>
          <p>
            {question?.description ||
              "The question details could not be loaded. Check the backend connection and return to the practice page."}
          </p>

          <div
            className="example-grid"
            style={{ gridTemplateColumns: "1fr", marginTop: 18 }}
          >
            <div className="example-box">
              <small>Example input</small>
              <code>{question?.examples?.[0]?.input || "—"}</code>
            </div>
            <div className="example-box">
              <small>Expected output</small>
              <code>{question?.examples?.[0]?.output || "—"}</code>
            </div>
          </div>

          <div className="small-label" style={{ marginTop: 22 }}>INPUT FORMAT</div>
          <p>{question?.input_format || "Use the example input format."}</p>
          <div className="small-label">OUTPUT FORMAT</div>
          <p>{question?.output_format || "Print the required result."}</p>

          <div className="notice" style={{ marginTop: 18 }}>
            Tip: test your code with a normal case and an edge case before submitting.
          </div>
        </section>

        <section className="card editor-workspace">
          <div className="editor-toolbar">
            <div>
              <strong>Solution editor</strong>
              <small>{language} · {questionId}</small>
            </div>
            <div className="editor-actions">
              <button
                className="btn btn-secondary"
                onClick={resetCode}
                disabled={busy || loadingQuestion || !question}
              >
                Reset
              </button>
              <button
                className="btn btn-secondary"
                onClick={handleRun}
                disabled={busy || loadingQuestion || !question || !code.trim()}
              >
                ▶ Run
              </button>
              <button
                className="btn btn-primary"
                onClick={handleSubmit}
                disabled={busy || loadingQuestion || !question || !code.trim()}
              >
                Submit
              </button>
            </div>
          </div>

          <div className="editor-pane">
            <Editor
              height="100%"
              language={editorLanguages[language] || "python"}
              theme="vs"
              value={code}
              onChange={(value) => setCode(value ?? "")}
              options={{
                fontSize: 13,
                minimap: { enabled: false },
                automaticLayout: true,
                scrollBeyondLastLine: false,
                padding: { top: 16 },
                wordWrap: "on",
                fontLigatures: true,
                tabSize: 4,
              }}
            />
          </div>

          <div className="input-area">
            <label htmlFor="custom-input">CUSTOM INPUT</label>
            <textarea
              id="custom-input"
              value={inputData}
              onChange={(event) => setInputData(event.target.value)}
              spellCheck="false"
              placeholder="Enter input for your program"
            />
          </div>

          <div className="output-area">
            <div className="output-header">
              <span>CONSOLE</span>
              <span
                style={{
                  color:
                    status.includes("passed") || status === "Run completed"
                      ? "#188c68"
                      : status.toLowerCase().includes("error")
                        ? "#c45b5b"
                        : "#8491a5",
                }}
              >
                {status || "Ready"}
              </span>
            </div>

            {output && <pre>{output}</pre>}

            {testResults.length > 0 && (
              <div style={{ display: "flex", gap: 7, flexWrap: "wrap", marginTop: 11 }}>
                {testResults.map((item) => (
                  <span
                    key={item.test_case}
                    className="tag"
                    style={{
                      background: item.passed ? "#e9f8f1" : "#fff0ef",
                      color: item.passed ? "#168461" : "#bd5751",
                    }}
                  >
                    Test {item.test_case}: {item.passed ? "Passed" : "Failed"}
                  </span>
                ))}
              </div>
            )}

            {!output && testResults.length === 0 && (
              <p className="empty-note" style={{ margin: "9px 0 0" }}>
                Run or submit your code to see the result here.
              </p>
            )}
          </div>
        </section>
      </div>
    </AppShell>
  );
}
