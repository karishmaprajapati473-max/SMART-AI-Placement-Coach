import re
from typing import Iterable

MIN_ML_CONFIDENCE = 0.55

ALLOWED_CONCEPTS = {
    "Syntax & Indentation",
    "Variables & Naming",
    "Data Types & Input Handling",
    "Arrays & Indexing",
    "Loops & Iteration",
    "Recursion",
    "Function Usage",
    "Algorithm Efficiency",
}

ENVIRONMENT_PATTERN = (
    r"Docker API|Docker Desktop|Docker daemon|"
    r"failed to connect to the docker|dockerDesktopLinuxEngine|"
    r"OCI runtime|containerd|npipe://"
)

RULES = [
    (
        r"NameError|not defined|undeclared|cannot find symbol|UnboundLocalError",
        "Variables & Naming",
        "Revise variable declaration, spelling, initialization and scope."
    ),
    (
        r"SyntaxError|IndentationError|invalid syntax|expected token",
        "Syntax & Indentation",
        "Revise syntax, indentation, brackets and statement structure."
    ),
    (
        r"IndexError|out of bounds|out of range|array subscript",
        "Arrays & Indexing",
        "Revise array traversal and valid index boundaries."
    ),
    (
        r"missing .* positional argument|unexpected keyword argument|"
        r"takes .* arguments|object is not callable",
        "Function Usage",
        "Revise function definitions, arguments and return values."
    ),
    (
        r"TypeError|ValueError|NumberFormatException|cannot convert",
        "Data Types & Input Handling",
        "Revise input parsing and data type conversion."
    ),
    (
        r"RecursionError|StackOverflowError|stack overflow",
        "Recursion",
        "Revise base cases and recursive function calls."
    ),
    (
        r"Timeout|timed out|time limit exceeded",
        "Algorithm Efficiency",
        "Revise loop termination and algorithm efficiency."
    ),
]

RECOMMENDATIONS = {
    "Variables & Naming":
        "Revise variables, declarations and initialization.",
    "Syntax & Indentation":
        "Revise syntax, indentation and brackets.",
    "Arrays & Indexing":
        "Revise array traversal and index boundaries.",
    "Data Types & Input Handling":
        "Revise input parsing and type conversion.",
    "Recursion":
        "Revise recursion and base cases.",
    "Function Usage":
        "Revise function parameters and return values.",
    "Algorithm Efficiency":
        "Revise loops and time complexity.",
    "Loops & Iteration":
        "Revise loop conditions and termination."
}


def diagnose_submission(
    question: dict,
    evaluation: dict,
    diagnostic_messages: Iterable[str] = (),
    language: str = "unknown",
    code_snippet: str = "",
) -> dict:

    passed = int(evaluation.get("passed", 0))
    total = int(evaluation.get("total", 0))

    if total > 0 and passed == total:
        return {
            "status": "success",
            "weak_concept": None,
            "confidence": "Not applicable",
            "evidence": f"All {passed}/{total} tests passed.",
            "recommendation":
                "Great work! Review your solution and complexity.",
            "method": "evaluation_result",
        }

    message = "\n".join(
        str(item) for item in diagnostic_messages if item
    )

    # Infrastructure problems must not be treated as student mistakes.
    if re.search(ENVIRONMENT_PATTERN, message, re.I):
        return {
            "status": "environment_error",
            "weak_concept": None,
            "confidence": "Not applicable",
            "evidence": "Docker execution environment failed.",
            "recommendation": "Start Docker Desktop and retry.",
            "method": "environment_check",
        }

    ml_note = "No compiler/runtime diagnostic was available."

    # Primary diagnosis: trained ML model.
    if message:
        try:
            from ml.predict import predict_weak_concept

            error_lines = re.findall(
                r"(?im)^\s*(?:[A-Za-z_][A-Za-z0-9_.]*"
                r"(?:Error|Exception)):\s*[^\r\n]+",
                message
            )

            diagnostic_for_ml = (
                error_lines[-1].strip()
                if error_lines
                else message[-500:]
            )

            prediction = predict_weak_concept(
                diagnostic_message=diagnostic_for_ml,
                language=language,
                topic=str(question.get("topic", "unknown")),
                code_snippet=code_snippet,
            )

            concept = prediction.get("weak_concept")
            score = float(prediction.get("confidence", 0))

            # Accept ML predictions only above the configured threshold.
            if (
                score >= MIN_ML_CONFIDENCE
                and concept in ALLOWED_CONCEPTS
            ):
                return {
                    "status": "needs_revision",
                    "weak_concept": concept,
                    "confidence": f"{score:.0%}",
                    "confidence_score": score,
                    "confidence_note":
                        "Classifier score; not yet calibrated on real data.",
                    "evidence":
                        "The ML classifier analyzed the compiler/runtime diagnostic.",
                    "recommendation": RECOMMENDATIONS.get(
                        concept,
                        "Review the related concept and retry."
                    ),
                    "method": prediction.get(
                        "method", "tfidf_logistic_regression"
                    ),
                }

            ml_note = (
                f"Prediction was not accepted. "
                f"Classifier score: {score:.0%}; "
                f"minimum required: {MIN_ML_CONFIDENCE:.0%}."
            )

        except Exception as error:
            ml_note = f"ML unavailable: {type(error).__name__}"

    # Transparent rule-based fallback for clearly identifiable errors.
    for pattern, concept, recommendation in RULES:
        if re.search(pattern, message, re.I):
            return {
                "status": "needs_revision",
                "weak_concept": concept,
                "confidence": "Rule-based match",
                "evidence":
                    f"Compiler/runtime diagnostic: {message[:250]}",
                "recommendation": recommendation,
                "method": "rules_baseline",
            }

    # Safe abstention: never invent a weak concept.
    return {
        "status": "needs_more_information",
        "weak_concept": None,
        "confidence": "Low",
        "evidence": (
            f"Passed {passed}/{total} tests. {ml_note}"
        ),
        "recommendation": (
            "Review the complete error message and problem statement. "
            "More diagnostic information is needed before identifying "
            "a weak concept."
        ),
        "method": "ml_abstention",
    }