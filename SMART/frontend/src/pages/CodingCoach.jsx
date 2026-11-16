import { useState } from "react";
import { useNavigate } from "react-router-dom";
import AppShell from "../components/AppShell";

const languages = [
  {name:"Python",glyph:"Py",detail:"Readable syntax for problem solving"},
  {name:"C",glyph:"C",detail:"Build strong programming fundamentals"},
  {name:"C++",glyph:"C+",detail:"Practice structured problem solving"},
  {name:"Java",glyph:"J",detail:"Work with object-oriented syntax"},
];

const topics = [
  {
    name: "Variables & Data Types",
    id: "rectangle_area",
    level: "Beginner",
    description: "Understand variables, data types and basic calculations."
  },
  {
    name: "Conditions",
    id: "positive_negative_zero",
    level: "Beginner",
    description: "Make decisions using if, else and conditional statements."
  },
  {
    name: "Loops",
    id: "sum_1_to_n",
    level: "Beginner",
    description: "Repeat instructions using loops."
  },
  {
    name: "Functions",
    id: "gcd_two_numbers",
    level: "Beginner",
    description: "Learn reusable functions and parameters."
  },
  {
    name: "Arrays",
    id: "largest_element",
    level: "Beginner",
    description: "Traverse arrays and compare values."
  },
  {
    name: "Strings",
    id: "count_vowels",
    level: "Beginner",
    description: "Work with strings and characters."
  },
  {
    name: "Searching",
    id: "linear_search",
    level: "Beginner",
    description: "Find elements using searching techniques."
  },
  {
    name: "Sorting",
    id: "sort_numbers",
    level: "Beginner",
    description: "Arrange elements in ascending or descending order."
  },
  {
    name: "Recursion",
    id: "recursive_factorial",
    level: "Beginner",
    description: "Solve problems using recursive functions."
  },
  {
    name: "Basic Data Structures",
    id: "stack_reverse",
    level: "Beginner",
    description: "Understand stacks and basic data structure operations."
  },
  {
    name: "Basic Programming",
    id: "sum_two_numbers",
    level: "Beginner",
    description: "Read input, process values and produce output."
  },
];

export default function CodingCoach() {
  const navigate=useNavigate();
  const [language,setLanguage]=useState("Python");
  const [topic,setTopic]=useState("Arrays");
  const selected=topics.find((item)=>item.name===topic && !item.soon);
  const go=()=>{if(!selected)return;navigate("/learn",{state:{language,topic,questionId:selected.id}});};
  return <AppShell active="/coding" eyebrow="CODING COACH" title="Learning setup" backTo="/dashboard" backLabel="Overview">
    <div className="page-heading"><div><div className="section-kicker">PERSONALISE YOUR SESSION</div><h1>Let’s set up your learning path</h1><p>Choose the language you are most comfortable with, then select a topic to begin. Your selected language will be used in the coding workspace.</p></div><span className="tag">STEP 01 / 04</span></div>
    <div className="stepper"><span className="step-chip current">01 · Choose</span><span className="step-chip">02 · Learn</span><span className="step-chip">03 · Practice</span><span className="step-chip">04 · Code & evaluate</span></div>
    <div className="selection-layout">
      <section className="card selection-panel"><h2>01. Select a programming language</h2><p>All four language modes are available in the editor.</p>
        <div className="language-grid">{languages.map(item=><button type="button" key={item.name} onClick={()=>setLanguage(item.name)} className={`language-option ${language===item.name?"selected":""}`}><span className="language-glyph">{item.glyph}</span><span><strong>{item.name}</strong><small>{item.detail}</small></span>{language===item.name&&<span style={{marginLeft:"auto",color:"#4169e1"}}>✓</span>}</button>)}</div>
      </section>
      <section className="card selection-panel"><h2>02. Choose a learning topic</h2><p>Explore all 11 programming topics and practise in your preferred language.</p>
        <div className="topic-list">{topics.map(item=><button type="button" key={item.name} disabled={!!item.soon} onClick={()=>setTopic(item.name)} className={`topic-option ${topic===item.name?"selected":""}`}><span><strong>{item.name}</strong><small style={{display:"block",marginTop:4}}>{item.description || "Course content is being prepared"}</small></span><span className="topic-status">{item.soon?"Coming soon":topic===item.name?"Selected":"Beginner"}</span></button>)}</div>
        <div className="selection-footer"><span className="empty-note">Selected: <b>{language}</b> · <b>{topic}</b></span><button type="button" className="btn btn-primary" onClick={go} disabled={!selected}>Start learning <span>→</span></button></div>
      </section>
    </div>
    <div className="dashboard-section-title"><h2>Your coaching loop</h2><span className="small-label">LEARN BY DOING</span></div>
    <section className="card flow-strip">{["Learn concept","Solve a question","Write your code","Run test cases","Review feedback","Retry & improve"].map((item,i)=><span key={item} style={{display:"contents"}}><span className="flow-step">{item}</span>{i!==5&&<span className="flow-arrow">→</span>}</span>)}</section>
  </AppShell>;
}
