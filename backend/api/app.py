"""Flask application factory and REST/SSE routes."""
from datetime import date
import json
import queue
import uuid
from flask import Flask, Response, jsonify, request, send_from_directory
from flask_cors import CORS
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from backend.config import settings
from backend.core.messaging import InMemoryBus
from backend.core.storage import create_storage
from backend.parsing.categoriser import CATEGORIES


class TransactionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount: float
    date: str = Field(default_factory=lambda: date.today().isoformat())
    description: str = ""
    category: str = ""
    payment_mode: str = "UPI"


class GoalInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    target: float
    saved: float = 0
    emoji: str = "◎"


def create_app(database_path: str | None = None):
    """Build the app with injected storage and messaging dependencies."""
    app = Flask(__name__, static_folder="../../frontend", static_url_path="")
    CORS(app, origins=settings.frontend_origin)
    storage = create_storage(database_path or settings.database_path)
    bus = InMemoryBus()
    app.config.update(storage=storage, bus=bus)

    @app.get("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "gmail_watch_expires_at": None, "redis_connected": False, "db_connected": True})

    @app.get("/api/transactions")
    def transactions():
        return jsonify(storage.list_transactions(request.args.get("month"), request.args.get("q", "")))

    @app.post("/api/transactions")
    def add_transaction():
        try:
            payload = TransactionInput.model_validate(request.get_json() or {})
        except ValidationError as error:
            return jsonify({"error": error.errors(), "code": "VALIDATION_ERROR"}), 400
        item = {"id": str(uuid.uuid4()), "amount": payload.amount, "currency": "INR", "merchant": payload.description or "Manual entry", "merchant_raw": payload.description or "Manual entry", "category": payload.category, "classified": bool(payload.category), "payment_mode": payload.payment_mode, "source": "manual", "bank": "", "email_message_id": None, "date": payload.date, "ts": int(__import__('datetime').datetime.now().timestamp() * 1000), "deleted_at": None, "parse_failed": False, "notes": ""}
        saved = storage.save_transaction(item)
        bus.publish("flux:transactions", {"type": "transaction", "data": saved})
        return jsonify(saved), 201

    @app.post("/api/classify")
    def classify():
        body = request.get_json() or {}
        if not body.get("id") or body.get("category") not in CATEGORIES:
            return jsonify({"error": "id and valid category are required", "code": "VALIDATION_ERROR"}), 400
        item = storage.classify(body["id"], body["category"])
        if not item:
            return jsonify({"error": "Transaction not found", "code": "NOT_FOUND"}), 404
        bus.publish("flux:transactions", {"type": "classified", "data": item})
        return jsonify(item)

    @app.delete("/api/transactions/<transaction_id>")
    def delete_transaction(transaction_id):
        storage.delete_transaction(transaction_id)
        return "", 204

    @app.get("/api/summary")
    def summary():
        return jsonify(storage.summary(request.args.get("month", date.today().strftime("%Y-%m"))))

    @app.get("/api/budgets")
    def budgets(): return jsonify(storage.budgets())

    @app.put("/api/budgets/<category>")
    def save_budget(category):
        limit = (request.get_json() or {}).get("monthly_limit")
        if not isinstance(limit, (int, float)) or limit < 0: return jsonify({"error": "monthly_limit must be non-negative", "code": "VALIDATION_ERROR"}), 400
        storage.save_budget(category, limit)
        return jsonify({"category": category, "monthly_limit": limit})

    @app.get("/api/goals")
    def goals(): return jsonify(storage.goals())

    @app.post("/api/goals")
    def create_goal():
        try: payload = GoalInput.model_validate(request.get_json() or {})
        except ValidationError as error: return jsonify({"error": error.errors(), "code": "VALIDATION_ERROR"}), 400
        item = {"id": str(uuid.uuid4()), **payload.model_dump()}
        return jsonify(storage.save_goal(item)), 201

    @app.patch("/api/goals/<goal_id>")
    def update_goal(goal_id):
        goals = storage.goals(); goal = next((item for item in goals if item["id"] == goal_id), None)
        if not goal: return jsonify({"error": "Goal not found", "code": "NOT_FOUND"}), 404
        goal["saved"] = (request.get_json() or {}).get("saved", goal["saved"])
        return jsonify(storage.save_goal(goal))

    @app.delete("/api/goals/<goal_id>")
    def remove_goal(goal_id): storage.delete_goal(goal_id); return "", 204

    @app.get("/api/stream")
    def stream():
        events = bus.subscribe("flux:transactions")
        def generate():
            while True:
                try: event = events.get(timeout=25); yield f"data: {json.dumps(event)}\n\n"
                except queue.Empty: yield "data: {\"type\":\"heartbeat\",\"data\":{}}\n\n"
        return Response(generate(), mimetype="text/event-stream")

    @app.post("/gmail/webhook")
    def gmail_webhook():
        return jsonify({"status": "accepted", "message": "Gmail ingestion is disabled until OAuth is configured"})

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
