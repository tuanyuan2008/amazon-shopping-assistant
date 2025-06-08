from flask import Flask, request, jsonify
from flask_cors import CORS
from src.agent import (
    initialize_agent,
    process_query
)
import os

app = Flask(__name__)
app.secret_key = os.urandom(24) # Kept for now, might be used by extensions

# Initialize CORS, allowing all origins for now.
# For production, specify origins: CORS(app, origins=["http://localhost:3000"])
CORS(app) 

# Initialize agent components once when the app starts
# These are global and will be used by the /api/query endpoint
nlp_processor, scraper, rate_limiter, graph_app = initialize_agent()

@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "Backend API is running"})

@app.route('/api/query', methods=['POST'])
def api_query():
    data = request.json
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    user_input = data.get('user_input')
    previous_context = data.get('previous_context', {})

    if not user_input:
        return jsonify({"error": "user_input is required"}), 400

    ranked_products, summary_text, new_context = process_query(
        graph_app, nlp_processor, scraper, rate_limiter, user_input, previous_context
    )

    return jsonify({
        "products": ranked_products,
        "summary": summary_text,
        "new_context": new_context
    })

if __name__ == "__main__":
    # Note: For development, Flask's built-in server is fine.
    # For production, use a proper WSGI server like Gunicorn or uWSGI.
    app.run(debug=True, host='0.0.0.0', port=5001)
