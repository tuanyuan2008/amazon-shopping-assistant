import pytest
import json # For working with JSON data
from unittest.mock import patch, MagicMock

# --- Global Mocking for initialize_agent ---
# This needs to be active BEFORE 'app' is imported.
mock_nlp_processor_global = MagicMock()
mock_scraper_global = MagicMock()
mock_rate_limiter_global = MagicMock()
mock_graph_app_global = MagicMock()

patcher_initialize_agent = patch('src.agent.initialize_agent', return_value=(
    mock_nlp_processor_global,
    mock_scraper_global,
    mock_rate_limiter_global,
    mock_graph_app_global
))
patcher_initialize_agent.start()
# --- End Global Mocking ---

# Now import the Flask app. The initialize_agent call in app.py will use the mock.
from app import app as flask_app 

@pytest.fixture
def app_fixture():
    """Create and configure a new app instance for each test."""
    flask_app.config.update({
        "TESTING": True,
        # SECRET_KEY is not strictly needed anymore for /api/query as session isn't used for context,
        # but good to keep if other parts of Flask or extensions might use sessions.
        "SECRET_KEY": "test_secret_key_for_pytest_api" 
    })
    yield flask_app

@pytest.fixture
def client(app_fixture):
    """A test client for the app."""
    return app_fixture.test_client()

def test_home_get_api_running(client):
    """Test GET request to the root path '/'."""
    response = client.get('/')
    assert response.status_code == 200
    assert response.content_type == 'application/json'
    expected_data = {"message": "Backend API is running"}
    assert response.json == expected_data

# Patch 'app.process_query' which is 'src.agent.process_query' imported into app.py's scope.
@patch('app.process_query')
def test_api_query_with_results(mock_process_query_in_app, client):
    """Test POST to /api/query when process_query returns results."""
    mock_ranked_products = [
        {'title': 'API Test Product 1', 'price': '29.99', 'url': 'http://api.example.com/p1'}
    ]
    mock_summary_text = "API test summary for product 1."
    mock_new_context = {"api_context_key": "api_value1"}
    
    mock_process_query_in_app.return_value = (mock_ranked_products, mock_summary_text, mock_new_context)

    payload = {
        "user_input": "api test query",
        "previous_context": {"initial_api_context": "data"}
    }
    response = client.post('/api/query', data=json.dumps(payload), content_type='application/json')
    
    assert response.status_code == 200
    assert response.content_type == 'application/json'
    
    response_data = response.json
    assert response_data["products"] == mock_ranked_products
    assert response_data["summary"] == mock_summary_text
    assert response_data["new_context"] == mock_new_context
    
    mock_process_query_in_app.assert_called_once_with(
        mock_graph_app_global,      # from the globally mocked initialize_agent
        mock_nlp_processor_global,
        mock_scraper_global,
        mock_rate_limiter_global,
        payload["user_input"],
        payload["previous_context"]
    )

@patch('app.process_query')
def test_api_query_no_results(mock_process_query_in_app, client):
    """Test POST to /api/query when process_query returns no results."""
    mock_process_query_in_app.return_value = ([], None, {"empty_results_context": True})

    payload = {"user_input": "query yielding no results", "previous_context": {}}
    response = client.post('/api/query', json=payload) # Using json=payload automatically sets content_type

    assert response.status_code == 200
    assert response.content_type == 'application/json'
    
    response_data = response.json
    assert response_data["products"] == []
    assert response_data["summary"] is None
    assert response_data["new_context"] == {"empty_results_context": True}

    mock_process_query_in_app.assert_called_once_with(
        mock_graph_app_global, mock_nlp_processor_global, mock_scraper_global, mock_rate_limiter_global,
        payload["user_input"], payload["previous_context"]
    )

@patch('app.process_query')
def test_api_query_context_passing(mock_process_query_in_app, client):
    """Test that previous_context is correctly passed to process_query."""
    initial_context = {"session_id": "123", "filter": "electronics"}
    payload = {"user_input": "find a laptop", "previous_context": initial_context}

    # Doesn't matter what process_query returns for this test, only that it's called correctly
    mock_process_query_in_app.return_value = ([], None, {"new_mock_context": "value"}) 

    client.post('/api/query', json=payload)

    mock_process_query_in_app.assert_called_once_with(
        mock_graph_app_global, mock_nlp_processor_global, mock_scraper_global, mock_rate_limiter_global,
        payload["user_input"], 
        initial_context # Crucial check: was the provided context passed?
    )

def test_api_query_missing_user_input(client):
    """Test POST to /api/query with missing user_input."""
    payload = {"previous_context": {}} # Missing user_input
    response = client.post('/api/query', json=payload)

    assert response.status_code == 400
    assert response.content_type == 'application/json'
    assert "error" in response.json
    assert response.json["error"] == "user_input is required"

def test_api_query_invalid_json_payload(client):
    """Test POST to /api/query with an invalid JSON payload."""
    response = client.post('/api/query', data="not a valid json", content_type='application/json')
    
    assert response.status_code == 400
    assert response.content_type == 'application/json'
    assert "error" in response.json 
    # The exact error message for invalid JSON can vary depending on Flask version
    # It might be "Invalid JSON payload" (custom) or Flask's default.
    # For now, checking for "error" key is a good start.
    # Example Flask error: "Failed to decode JSON object: Expecting value: line 1 column 1 (char 0)"

def test_api_query_empty_json_payload(client):
    """Test POST to /api/query with an empty JSON payload {}."""
    response = client.post('/api/query', json={})
    
    assert response.status_code == 400 # Because user_input is required
    assert response.content_type == 'application/json'
    assert "error" in response.json
    assert response.json["error"] == "user_input is required"

def test_api_query_default_previous_context(mock_process_query_in_app, client):
    """Test that previous_context defaults to {} if not provided."""
    payload = {"user_input": "a query without context"}
    # previous_context is omitted from payload

    mock_process_query_in_app.return_value = ([], None, {}) 
    client.post('/api/query', json=payload)

    mock_process_query_in_app.assert_called_once_with(
        mock_graph_app_global, mock_nlp_processor_global, mock_scraper_global, mock_rate_limiter_global,
        payload["user_input"], 
        {} # Crucial check: was previous_context defaulted to {}?
    )


# Fixture to stop the global patcher after the test session.
@pytest.fixture(scope="session", autouse=True)
def cleanup_global_patcher_initialize_agent(request):
    """Stop the global patcher_initialize_agent after the test session."""
    def fin():
        patcher_initialize_agent.stop()
    request.addfinalizer(fin)
