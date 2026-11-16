import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import AppShell from "../components/AppShell";
import { getQuestion, recordRevisionEvent } from "../services/api";

const revisionLessons = {
  "Variables & Naming": {
    title: "Variables and Naming",
    intro: "A variable stores a value under a name. Initialize it before using it.",
    points: [
      "Choose meaningful variable names.",
      "Initialize variables before using them.",
      "Check spelling and capitalization.",
      "Understand variable scope."
    ]
  },
  "Syntax & Indentation": {
    title: "Syntax and Indentation",
    intro: "Programming languages follow syntax rules. Missing brackets, semicolons or indentation can cause errors.",
    points: [
      "Check opening and closing brackets.",
      "Use correct indentation in Python.",
      "Add semicolons where required.",
      "Check function and statement syntax."
    ]
  },
  "Data Types & Input Handling": {
    title: "Data Types and Input Handling",
    intro: "Input values must be converted into the correct data type before calculations.",
    points: [
      "Understand integers and strings.",
      "Convert input into the required type.",
      "Check input format.",
      "Avoid mixing incompatible data types."
    ]
  },
  "Arrays & Indexing": {
    title: "Arrays and Indexing",
    intro: "Array elements are accessed using indexes. Always make sure the index is within the valid range.",
    points: [
      "Remember that indexing usually starts at zero.",
      "Check array length before accessing elements.",
      "Use correct loop boundaries.",
      "Avoid accessing an index equal to array length."
    ]
  },
  "Loops & Iteration": {
    title: "Loops and Iteration",
    intro: "Loops repeat instructions. A correct loop needs a valid condition and a clear termination point.",
    points: [
      "Initialize the loop variable.",
      "Write a correct loop condition.",
      "Update the counter appropriately.",
      "Make sure the loop eventually terminates."
    ]
  },
  "Recursion": {
    title: "Recursion and Base Cases",
    intro: "A recursive function calls itself. Every recursive solution needs a base case to stop the calls.",
    points: [
      "Identify the base case.",
      "Make progress towards the base case.",
      "Check recursive arguments.",
      "Prevent infinite recursive calls."
    ]
  },
  "Function Usage": {
    title: "Functions and Parameters",
    intro: "Functions organize reusable logic. The arguments passed during a function call must match its parameters.",
    points: [
      "Define the function correctly.",
      "Pass the required number of arguments.",
      "Use the correct parameter types.",
      "Understand return values."
    ]
  },
  "Algorithm Efficiency": {
    title: "Algorithm Efficiency",
    intro: "Efficient algorithms solve problems using fewer operations and less additional memory.",
    points: [
      "Identify repeated calculations.",
      "Avoid unnecessary nested loops.",
      "Look for more efficient approaches.",
      "Understand time and space complexity."
    ]
  }
};

export default function LearnConcept() {
  const attemptedRevisionKeyRef = useRef("");
  const revisionVisitEventKeyRef = useRef(window.crypto?.randomUUID?.() || `revision-${Date.now()}-${Math.random().toString(36).slice(2)}`);
  const location = useLocation();
  const navigate = useNavigate();

  const language = location.state?.language || "Python";
  const topic = location.state?.topic || "Arrays";
  const questionId = location.state?.questionId || "largest_element";
  const diagnosis = location.state?.diagnosis || null;

  const [question, setQuestion] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedOption, setSelectedOption] = useState("");

  useEffect(() => {
    let active = true;

    setLoading(true);
    setError("");
    setQuestion(null);
    setSelectedOption("");

    getQuestion(questionId)
      .then((data) => {
        if (active) {
          setQuestion(data);
        }
      })
      .catch((err) => {
        if (active) {
          setError(err.message || "Unable to load the lesson. Check that the backend is running.");
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [questionId]);

  const lesson = question?.learning_content;

const revision = !diagnosis
  ? null
  : diagnosis.weak_concept
    ? revisionLessons[diagnosis.weak_concept]
    : {
        title: "Problem-Solving & Output Verification",
        intro:
          "Your submission needs further review, but there is not enough evidence to identify one specific weak concept. Use these steps to strengthen your problem-solving approach.",
        points: [
          "Read the problem statement carefully and identify exactly what is required.",
          "Understand the input format, expected output and constraints.",
          "Break the problem into smaller logical steps before writing code.",
          "Dry-run your solution using sample inputs.",
          "Check arithmetic operations, conditions, loops and edge cases.",
          "Compare your program's output with the expected output."
        ]
      };

  useEffect(() => {
    if (!revision || !diagnosis?.weak_concept) return;

    const revisionEventKey = [
      diagnosis.weak_concept,
      questionId,
      topic,
      language,
    ].join("|");

    if (attemptedRevisionKeyRef.current === revisionEventKey) return;
    attemptedRevisionKeyRef.current = revisionEventKey;

    let active = true;

    recordRevisionEvent({
      weakConcept: diagnosis.weak_concept,
      questionId,
      topic,
      language,
      eventKey: revisionVisitEventKeyRef.current,
    }).catch((err) => {
      if (active) {
        console.error("Revision event could not be saved:", err);
      }
    });

    return () => {
      active = false;
    };
  }, [diagnosis?.weak_concept, questionId, topic, language, revision]);

  const quiz = Array.isArray(question?.quiz)
    ? question.quiz[0]
    : null;

  const selectedQuizOption = quiz?.options?.find(
    (option) => option.value === selectedOption
  );

  const next = () => {
    navigate("/practice", {
      state: {
        language,
        topic,
        questionId,
        diagnosis
      }
    });
  };

  return (
    <AppShell
      active="/coding"
      eyebrow="LEARNING EXPERIENCE"
      title="Concept lesson"
      backTo="/coding"
      backLabel="Learning setup"
    >
      <div className="page-heading">
        <div>
          <div className="section-kicker">
            STEP 02 / 04 · CONCEPT FOUNDATION
          </div>
          <h1>{lesson?.title || "Learn the concept"}</h1>
          <p>{lesson?.intro || "Your selected topic lesson will appear here."}</p>
        </div>
        <span className="tag">
          {language} · {topic}
        </span>
      </div>

      <div className="stepper">
        <span className="step-chip">01 · Choose</span>
        <span className="step-chip current">02 · Learn</span>
        <span className="step-chip">03 · Practice</span>
        <span className="step-chip">04 · Code & evaluate</span>
      </div>

      {loading ? (
        <section className="card">
          <p className="empty-note">Loading your lesson...</p>
        </section>
      ) : error ? (
        <section className="card">
          <div className="alert">{error}</div>
        </section>
      ) : !lesson ? (
        <section className="card">
          <div className="alert">
            Learning content is not available for this question.
          </div>
        </section>
      ) : (
        <>
          {revision && (
            <section
              className="card"
              style={{
                marginBottom: 20,
                borderLeft: "4px solid #386fe8",
                padding: 24
              }}
            >
              <div className="small-label">
  {diagnosis?.weak_concept
    ? "PERSONALIZED AI REVISION"
    : "GENERAL REVISION"}
</div>

              <h2 style={{ marginTop: 12 }}>
                Let's strengthen this concept
              </h2>

              <h3 style={{ marginTop: 12 }}>
                {revision.title}
              </h3>

              <p style={{ marginTop: 10 }}>
                {revision.intro}
              </p>

              <div className="lesson-list" style={{ marginTop: 18 }}>
                {revision.points.map((point, index) => (
                  <div className="lesson-point" key={point}>
                    <span>{index + 1}</span>
                    <p>{point}</p>
                  </div>
                ))}
              </div>

              <p style={{ marginTop: 16, fontSize: 12, color: "#627189" }}>
                {diagnosis?.weak_concept
  ? `Identified concept: ${diagnosis.weak_concept}`
  : "A specific weak concept could not be confirmed. This general revision will help you review your problem-solving approach."}
              </p>
            </section>
          )}

          <div className="lesson-grid">
            <section className="card lesson-main">
              <div className="small-label">THE CORE IDEA</div>

              <h2>Understand the approach</h2>
              <p>{lesson.intro}</p>

              <div className="lesson-list">
                {lesson.points?.map((point, index) => (
                  <div className="lesson-point" key={index}>
                    <span>{index + 1}</span>
                    <p>{point}</p>
                  </div>
                ))}
              </div>

              <div style={{ marginTop: 25 }}>
                <div className="small-label">
                  STARTER CODE · {language.toUpperCase()}
                </div>

                <div className="lesson-code">
                  <pre>
                    {question.starter_code?.[language] ||
                      "Starter code is not available for this language."}
                  </pre>
                </div>
              </div>

              {question.examples?.length > 0 && (
                <div style={{ marginTop: 22 }}>
                  <div className="small-label">SAMPLE EXAMPLE</div>

                  {question.examples.slice(0, 2).map((example, index) => (
                    <div className="example-grid" key={index}>
                      <div className="example-box">
                        <small>Input</small>
                        <code>{example.input}</code>
                      </div>

                      <div className="example-box">
                        <small>Expected output</small>
                        <code>{example.output}</code>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <div className="example-box" style={{ marginTop: 20 }}>
                <small>Complexity to remember</small>
                <code>{lesson.complexity || "Not specified"}</code>

                {lesson.note && (
                  <p style={{ fontSize: 10, color: "#6b7890", margin: "8px 0 0" }}>
                    {lesson.note}
                  </p>
                )}
              </div>

              {quiz && (
                <section style={{ marginTop: 28 }}>
                  <div className="small-label">QUICK KNOWLEDGE CHECK</div>
                  <h2>{quiz.question}</h2>

                  <div className="topic-list" style={{ marginTop: 14 }}>
                    {quiz.options?.map((option) => (
                      <button
                        type="button"
                        key={option.value}
                        disabled={!!selectedOption}
                        onClick={() => setSelectedOption(option.value)}
                        className={`topic-option ${
                          selectedOption === option.value ? "selected" : ""
                        }`}
                      >
                        <span>
                          <strong>{option.value}.</strong> {option.label}
                        </span>
                      </button>
                    ))}
                  </div>

                  {selectedQuizOption && (
                    <div className="notice" style={{ marginTop: 14 }}>
                      <strong>
                        {selectedOption === quiz.correct_answer
                          ? "Correct answer!"
                          : "Not quite. Try to remember this concept."}
                      </strong>
                      <p style={{ marginTop: 8 }}>
                        {selectedQuizOption.feedback}
                      </p>
                      <p style={{ marginTop: 8 }}>
                        {quiz.explanation}
                      </p>
                    </div>
                  )}
                </section>
              )}

              <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 22 }}>
                <button className="btn btn-primary" onClick={next}>
                  I understand — continue <span>→</span>
                </button>
              </div>
            </section>

            <aside className="card lesson-aside">
              <h3>Lesson outcomes</h3>

              {[
                "Explain the idea in your own words",
                "Follow the steps in the code example",
                "Recognise the relevant input and output",
                "Apply the logic to a practice problem"
              ].map((item) => (
                <div className="outcome-item" key={item}>
                  <b>✓</b>
                  <span>{item}</span>
                </div>
              ))}

              <div
                style={{
                  background: "#f5f7fc",
                  borderRadius: 10,
                  padding: 13,
                  marginTop: 16
                }}
              >
                <div className="small-label">YOUR SESSION</div>
                <p style={{ fontSize: 11, lineHeight: 1.6, color: "#627189", margin: "7px 0 0" }}>
                  Language: <b>{language}</b>
                  <br />
                  Topic: <b>{topic}</b>
                  <br />
                  Next: <b>Practice question</b>
                </p>
              </div>
            </aside>
          </div>
        </>
      )}
    </AppShell>
  );
}
