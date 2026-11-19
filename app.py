from flask import Flask, jsonify, request, send_from_directory

import rag

app = Flask(__name__, static_folder="static")
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024


@app.errorhandler(413)
def request_too_large(_error):
    return jsonify(error="La petición es demasiado grande."), 413


@app.get("/")
def home():
    return send_from_directory(app.static_folder, "index.html")


@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Envía una petición JSON válida."), 400
    question = data.get("question")
    history = data.get("history", [])
    if not isinstance(question, str) or not 1 <= len(question.strip()) <= 2000:
        return jsonify(error="La pregunta debe tener entre 1 y 2000 caracteres."), 400
    if (not isinstance(history, list) or len(history) > 6
            or any(not isinstance(turn, dict) or turn.get("role") not in ("user", "assistant")
                   or not isinstance(turn.get("content"), str) or len(turn["content"]) > 3000
                   for turn in history)):
        return jsonify(error="El historial no es válido."), 400
    try:
        return jsonify(rag.answer(question.strip(), history))
    except rag.RagError as exc:
        app.logger.warning("Error del chat: %s", exc)
        return jsonify(error=str(exc)), 503


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
