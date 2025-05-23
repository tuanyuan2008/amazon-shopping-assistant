from flask import Flask, render_template, request, session
from src.agent import (
    initialize_agent,
    process_query,
    format_display_results,
    format_summary
)
import os

app = Flask(__name__)
app.secret_key = os.urandom(24) # Needed for session management

# Initialize agent components once when the app starts
nlp_processor, scraper, rate_limiter, graph_app = initialize_agent()

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        user_query = request.form.get('query')
        previous_context = session.get('previous_context', {})

        ranked_products, summary_text, new_context = process_query(
            graph_app, nlp_processor, scraper, rate_limiter, user_query, previous_context
        )

        session['previous_context'] = new_context

        # The format_display_results and format_summary from src.agent return strings,
        # which might not be ideal for direct HTML rendering if they contain HTML.
        # For now, we'll pass the raw data and let Jinja handle the structure.
        # If these functions were designed to output safe HTML, we could use them directly.
        
        # We will adapt the display logic in the template.
        # For now, let's pass the raw ranked_products and summary_text.
        # The format_summary is simple enough to be used.
        
        formatted_summary = format_summary(summary_text) if summary_text else "No summary available."
        
        # We'll pass ranked_products directly and let the template handle formatting.
        # The format_display_results function creates a single string, 
        # which is less flexible for templating than having the list of products.

        return render_template('index.html', 
                               query=user_query, 
                               summary=formatted_summary, 
                               products=ranked_products)
    
    # GET request
    session.pop('previous_context', None) # Reset context on new GET
    return render_template('index.html', summary="Summary of results will appear here...", products=[])

if __name__ == "__main__":
    app.run(debug=True)
