import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import AppShell from "../components/AppShell";
import { getQuestion } from "../services/api";

export default function PracticeQuestion(){
  const location=useLocation(); const navigate=useNavigate();
  const language=location.state?.language||"Python"; const topic=location.state?.topic||"Arrays"; const questionId=location.state?.questionId||"largest_element";
  const diagnosis = location.state?.diagnosis || null;
  const [question,setQuestion]=useState(null); const [error,setError]=useState(""); const [loading,setLoading]=useState(true);
  useEffect(()=>{let active=true;setLoading(true);getQuestion(questionId).then((data)=>{if(active){setQuestion(data);setError("");}}).catch((err)=>{if(active)setError(err.message||"Unable to load the question. Check that the backend is running.");}).finally(()=>{if(active)setLoading(false);});return()=>{active=false;};},[questionId]);
  const go=()=>navigate("/code-editor",{state:{language,topic,questionId,diagnosis}});
  return <AppShell active="/coding" eyebrow="PRACTICE LIBRARY" title="Practice question" backTo="/learn" backLabel="Concept lesson">
    <div className="page-heading"><div><div className="section-kicker">STEP 03 / 04 · APPLY WHAT YOU LEARNED</div><h1>Turn understanding into practice</h1><p>Read the problem and examples, then move into the editor when you are ready to solve it.</p></div><span className="tag">{language} · {topic}</span></div>
    <div className="stepper"><span className="step-chip">01 · Choose</span><span className="step-chip">02 · Learn</span><span className="step-chip current">03 · Practice</span><span className="step-chip">04 · Code & evaluate</span></div>
    <section className="card practice-card">
      {loading?<p className="empty-note">Loading practice question…</p>:error?<div className="alert">{error}</div>:<>
        <div className="small-label">{question?.topic||topic} · QUESTION</div>
        <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",gap:16,flexWrap:"wrap"}}><h2 className="question-title">{question.title}</h2><span className="tag">{question.difficulty||"Beginner"}</span></div>
        <p className="question-description">{question.description}</p>
        <div style={{marginTop:22}}><div className="small-label">INPUT & OUTPUT FORMAT</div><p className="question-description"><b>Input:</b> {question.input_format||"As described in the example."}<br/><b>Output:</b> {question.output_format||"Print the expected result."}</p></div>
        <div className="example-grid"><div className="example-box"><small>Example input</small><code>{question.examples?.[0]?.input||"—"}</code></div><div className="example-box"><small>Expected output</small><code>{question.examples?.[0]?.output||"—"}</code></div></div>
        {question.examples?.[1]&&<div className="example-grid"><div className="example-box"><small>Another input</small><code>{question.examples[1].input}</code></div><div className="example-box"><small>Expected output</small><code>{question.examples[1].output}</code></div></div>}
        <div className="notice">Think through the edge cases too. The evaluator checks multiple test cases, not just the example shown above.</div>
      </>}
      <div className="practice-actions"><span className="empty-note">Selected language: <b>{language}</b></span><button className="btn btn-primary" onClick={go} disabled={!question||loading}>Open coding workspace <span>→</span></button></div>
    </section>
  </AppShell>;
}
