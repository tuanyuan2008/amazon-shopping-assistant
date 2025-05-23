import pytest
from unittest.mock import patch, MagicMock

# Mock initialize_agent from src.agent BEFORE app is imported.
# This is crucial because initialize_agent is called at the global scope in app.py.
# It needs to return a tuple of 4 items, as expected by app.py
mock_nlp_processor = MagicMock()
mock_scraper = MagicMock()
mock_rate_limiter = MagicMock()
mock_graph_app = MagicMock()

# The patch should target 'src.agent.initialize_agent' because that's where
# the actual function resides. When app.py calls 'initialize_agent' (after
# 'from src.agent import initialize_agent'), this patched version will be used.
patcher = patch('src.agent.initialize_agent', return_value=(
    mock_nlp_processor,
    mock_scraper,
    mock_rate_limiter,
    mock_graph_app
))
# Start the patch before importing app.py
# We need to keep this patcher object to stop it later if necessary,
# or use patch.object or patch.dict for finer control if this were in a fixture.
# For a module-level patch like this that needs to be active before an import,
# starting it globally here is one approach.
# Alternatively, structuring app.py to have a create_app() function is cleaner.
patcher.start()


# Now that src.agent.initialize_agent is patched, we can import the Flask app.
# The global variables in app.py (nlp_processor, scraper, etc.) will be assigned
# the MagicMock objects defined above.
from app import app as flask_app

@pytest.fixture
def app_fixture():
    """Create and configure a new app instance for each test."""
    flask_app.config.update({
        "TESTING": True,
        "SECRET_KEY": "test_secret_key_for_pytest" # Set a secret key for session testing
    })
    # Stop the global patcher when tests are done if necessary,
    # though for pytest, it usually handles cleanup.
    # If issues arise, pytest_sessionfinish or a finalizer fixture could stop it.
    yield flask_app
    # patcher.stop() # Uncomment if issues with patch persisting across test files/sessions

@pytest.fixture
def client(app_fixture):
    """A test client for the app."""
    return app_fixture.test_client()

def test_home_get(client):
    """Test GET request to the home page."""
    response = client.get('/')
    assert response.status_code == 200
    response_data = response.data.decode()
    assert "<h1>Amazon Shopping Assistant</h1>" in response_data
    assert '<form action="/" method="post">' in response_data
    assert 'name="query"' in response_data
    assert "Summary of results will appear here..." in response_data

# Patch 'app.process_query' which is 'src.agent.process_query' imported into app.py
# This is because the 'home' function in app.py calls 'process_query' directly.
@patch('app.process_query')
def test_home_post_with_results(mock_process_query_in_app, client):
    """Test POST request to the home page when process_query returns results."""
    mock_ranked_products = [
        {
            'title': 'Test Product 1', 
            'price': '19.99', 
            'price_per_count': '1.99/oz', 
            'url': 'http://example.com/product1', 
            'ranking_explanation': 'It is a test product.'
        }
    ]
    mock_summary_text = "This is a test summary."
    mock_new_context = {"key": "value"}
    
    mock_process_query_in_app.return_value = (mock_ranked_products, mock_summary_text, mock_new_context)

    response = client.post('/', data={'query': 'test query'})
    assert response.status_code == 200
    response_data = response.data.decode()

    assert "<h1>Amazon Shopping Assistant</h1>" in response_data
    assert 'value="test query"' in response_data
    assert "This is a test summary." in response_data # This comes from format_summary(mock_summary_text)
    assert "Test Product 1" in response_data
    assert "$19.99" in response_data
    assert "(Unit Price: 1.99/oz)" in response_data
    assert 'href="http://example.com/product1"' in response_data
    assert "It is a test product." in response_data
    
    # Assert that the globally mocked graph_app (from initialize_agent mock) and others
    # were passed to the (also mocked) process_query.
    mock_process_query_in_app.assert_called_once_with(
        mock_graph_app,          # from the mocked initialize_agent
        mock_nlp_processor,      # from the mocked initialize_agent
        mock_scraper,            # from the mocked initialize_agent
        mock_rate_limiter,       # from the mocked initialize_agent
        'test query',            # user_input
        {}                       # previous_context (empty for first request in session)
    )

@patch('app.process_query')
def test_home_post_no_results(mock_process_query_in_app, client):
    """Test POST request to the home page when process_query returns no results."""
    mock_process_query_in_app.return_value = ([], None, {})

    response = client.post('/', data={'query': 'empty search'})
    assert response.status_code == 200
    response_data = response.data.decode()

    assert "<h1>Amazon Shopping Assistant</h1>" in response_data
    assert 'value="empty search"' in response_data
    assert "No summary available." in response_data
    assert "No products found for your query." in response_data
    
    mock_process_query_in_app.assert_called_once_with(
        mock_graph_app, mock_nlp_processor, mock_scraper, mock_rate_limiter,
        'empty search', {}
    )

@patch('app.process_query')
def test_home_post_context_management(mock_process_query_in_app, client):
    """Test that context is managed across POST requests via session."""
    mock_new_context_first_call = {"query": "first query", "results_count": 1}
    
    # Configure side_effect for multiple calls if needed, or just reconfigure return_value
    mock_process_query_in_app.return_value = (
        [{'title': 'Product A', 'price': '10', 'url': 'urlA', 'ranking_explanation': 'explA'}],
        "Summary A",
        mock_new_context_first_call
    )

    # First POST
    client.post('/', data={'query': 'first query'})
    
    mock_process_query_in_app.assert_called_with(
        mock_graph_app, mock_nlp_processor, mock_scraper, mock_rate_limiter,
        'first query', {} 
    )

    # Setup mock for second call
    mock_new_context_second_call = {"query": "second query", "results_count": 2}
    mock_process_query_in_app.return_value = ( # Reconfigure for the second call
        [{'title': 'Product B', 'price': '20', 'url': 'urlB', 'ranking_explanation': 'explB'}],
        "Summary B",
        mock_new_context_second_call
    )
    
    # Second POST
    client.post('/', data={'query': 'second query'})
    
    assert mock_process_query_in_app.call_count == 2
    mock_process_query_in_app.assert_called_with(
        mock_graph_app, mock_nlp_processor, mock_scraper, mock_rate_limiter,
        'second query', mock_new_context_first_call # previous_context is from first call's new_context
    )

@patch('app.process_query') # Patch for the initial POST
def test_home_get_clears_context(mock_process_query_post, client):
    """Test that a GET request clears the previous_context from session."""
    # Simulate a POST request first to populate session
    mock_process_query_post.return_value = ([], "Initial Summary", {"some_key": "some_value"})
    client.post('/', data={'query': 'initial query'})
    
    # Now perform a GET request
    response = client.get('/')
    assert response.status_code == 200
    
    # To verify context is cleared, make another POST and check the context passed to process_query
    with patch('app.process_query') as mock_process_query_after_get: # New patch for this specific call
        mock_process_query_after_get.return_value = ([], "Next Summary", {})
        client.post('/', data={'query': 'next query'})
        
        mock_process_query_after_get.assert_called_once_with(
            mock_graph_app, mock_nlp_processor, mock_scraper, mock_rate_limiter,
            'next query', {} # previous_context for 'next query' should be empty
        )

# If you started a global patcher and need to stop it:
# @pytest.fixture(scope="session", autouse=True)
# def stop_global_patch():
#     yield
#     patcher.stop() # This stops the patcher started at the beginning of the file
# This is generally good practice if the patcher isn't managed by pytest's fixture system.
# However, for `patch()` started with `patcher.start()`, it should ideally be stopped.
# A cleaner way for pytest is to use fixtures that manage the patch's lifecycle.
# For now, this explicit start/stop (if needed) will do.
# Given pytest's test isolation, it might not be strictly necessary for this single test file.
# Let's add a session-scoped autouse fixture to stop the patcher after all tests.

@pytest.fixture(scope="session", autouse=True)
def cleanup_global_patch(request):
    """Stop the global patcher after the test session."""
    def fin():
        patcher.stop()
    request.addfinalizer(fin)
