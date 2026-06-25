"""Provenance Guard — Flask backend.

Milestone 3: POST /submit (signal 1 only), structured audit log, GET /log.
Confidence scoring (M4), the second signal (M4), transparency labels, appeals,
and rate limiting (M5) are layered on in later milestones.
"""

import uuid

from dotenv import load_dotenv
from flask import Flask, jsonify, request

import audit
import scoring
from signals import llm_signal, stylometry_signal

load_dotenv()  # load GROQ_API_KEY from .env

app = Flask(__name__)
audit.init_db()


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/submit", methods=["POST"])
def submit():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    creator_id = (data.get("creator_id") or "").strip()

    if not text:
        return jsonify({"error": "Field 'text' is required and must be non-empty."}), 400
    if not creator_id:
        return jsonify({"error": "Field 'creator_id' is required."}), 400

    content_id = str(uuid.uuid4())

    # --- Detection pipeline: two independent signals ---
    sig1 = llm_signal(text)               # Signal 1: semantic (Groq)
    sig2 = stylometry_signal(text)        # Signal 2: structural (pure Python)
    llm_score = sig1["ai_score"]
    stylo_score = sig2["ai_score"]

    # --- Confidence scoring: combine both signals (planning.md §3) ---
    result = scoring.score(llm_score, stylo_score, stylo_reliable=sig2["reliable"])
    attribution = result["attribution"]
    confidence = result["confidence"]
    ai_probability = result["ai_probability"]

    # --- Placeholder until Milestone 5 wires in the transparency label ---
    label = {
        "headline": "Analysis complete",
        "body": "Transparency label is added in Milestone 5.",
    }

    signals = {"llm_score": llm_score, "stylo_score": stylo_score}

    audit.log_classification(
        content_id=content_id,
        creator_id=creator_id,
        attribution=attribution,
        confidence=confidence,
        ai_probability=ai_probability,
        signals=signals,
        status="classified",
    )

    return jsonify({
        "content_id": content_id,
        "attribution": attribution,
        "confidence": confidence,
        "ai_probability": ai_probability,
        "signals": {
            "llm_score": llm_score,
            "llm_rationale": sig1["rationale"],
            "stylo_score": stylo_score,
            "stylo_metrics": sig2["metrics"],
        },
        "label": label,
    })


@app.route("/log", methods=["GET"])
def log():
    limit = request.args.get("limit", default=50, type=int)
    return jsonify({"entries": audit.get_log(limit=limit)})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
