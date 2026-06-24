"""Provenance Guard — Flask backend.

Milestone 3: POST /submit (signal 1 only), structured audit log, GET /log.
Confidence scoring (M4), the second signal (M4), transparency labels, appeals,
and rate limiting (M5) are layered on in later milestones.
"""

import uuid

from dotenv import load_dotenv
from flask import Flask, jsonify, request

import audit
from signals import llm_signal

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

    # --- Signal 1: LLM classifier ---
    sig1 = llm_signal(text)
    llm_score = sig1["ai_score"]

    # --- Placeholders until Milestone 4 wires in the second signal + real scoring ---
    confidence = round(abs(llm_score - 0.5) * 2, 3)  # placeholder: certainty from one signal
    attribution = "pending"
    label = {
        "headline": "Analysis in progress",
        "body": "Confidence scoring and transparency label are added in Milestone 4–5.",
    }

    signals = {"llm_score": llm_score}

    audit.log_classification(
        content_id=content_id,
        creator_id=creator_id,
        attribution=attribution,
        confidence=confidence,
        ai_probability=llm_score,  # placeholder: single-signal estimate
        signals=signals,
        status="classified",
    )

    return jsonify({
        "content_id": content_id,
        "attribution": attribution,
        "confidence": confidence,
        "ai_probability": llm_score,
        "signals": {**signals, "llm_rationale": sig1["rationale"]},
        "label": label,
    })


@app.route("/log", methods=["GET"])
def log():
    limit = request.args.get("limit", default=50, type=int)
    return jsonify({"entries": audit.get_log(limit=limit)})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
