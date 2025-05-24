import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event'; // For more complex user interactions
import App from './App'; // Corrected path: App.tsx is in src/ alongside App.test.tsx
import { vi } from 'vitest'; // Vitest's mocking utility

// Mock the api service
// The path should be relative to this test file, or use an alias if configured
vi.mock('./services/api', () => ({
  fetchQueryResults: vi.fn(),
}));

// Import the mocked function after vi.mock call
import { fetchQueryResults } from './services/api';

// Helper to cast mock
const mockedFetchQueryResults = fetchQueryResults as ReturnType<typeof vi.fn>;

describe('App Component Integration Tests', () => {
  beforeEach(() => {
    // Reset mocks and any other setup before each test
    mockedFetchQueryResults.mockClear();
  });

  test('full user flow: type query, submit, display results and summary', async () => {
    const user = userEvent.setup();
    const mockApiResponse = {
      products: [
        { title: 'Laptop X', price: '999.99', url: 'http://example.com/laptopx', ranking_explanation: 'Great laptop' },
      ],
      summary: 'Found a great laptop for you.',
      new_context: { searchId: '12345' },
    };
    mockedFetchQueryResults.mockResolvedValue(mockApiResponse);

    render(<App />);

    const inputElement = screen.getByPlaceholderText(/e.g., organic coffee beans under \$20/i);
    const submitButton = screen.getByRole('button', { name: /search/i });

    // Simulate typing a query
    await user.type(inputElement, 'best gaming laptop');
    expect(inputElement).toHaveValue('best gaming laptop');

    // Simulate form submission
    await user.click(submitButton);

    // Check for loading states (button text changes, loading messages might appear)
    // The exact check for loading state might depend on how it's implemented.
    // For example, if the button text changes to "Searching..."
    // expect(screen.getByRole('button', { name: /searching.../i })).toBeInTheDocument(); 
    // QueryInput shows spinner. Check if the button is disabled (indicating loading)
    // and then check if the spinner SVG is present.
    // After click, the button's content changes to an SVG.
    // We expect it to be disabled.
    // Find the button (it should be the only one in this part of the form)
    // and assert its state *after* the click action has settled.
    // userEvent.click is async and waits for DOM updates.
    
    // The button should be disabled, and its accessible name might change (or become empty)
    // because the text "Search" is replaced by an SVG.
    // We can find it by its current state (disabled) or by its role if it's unique.
    // Let's assume it's the primary button we're interacting with.
    expect(submitButton).toBeDisabled(); // Check the original reference
    expect(submitButton.querySelector('svg.animate-spin')).toBeInTheDocument();


    // Wait for the API call to resolve and UI to update
    await waitFor(() => {
      expect(mockedFetchQueryResults).toHaveBeenCalledTimes(1);
      expect(mockedFetchQueryResults).toHaveBeenCalledWith('best gaming laptop', {}); // Initial context is empty
    });

    // Wait for results and summary to be displayed
    // Need to use findBy methods for elements that appear asynchronously
    expect(await screen.findByText('Laptop X')).toBeInTheDocument();
    expect(await screen.findByText('Found a great laptop for you.')).toBeInTheDocument();
    expect(await screen.findByText('Great laptop')).toBeInTheDocument(); // Ranking explanation

    // Check if button is enabled again
    expect(screen.getByRole('button', { name: /search/i })).toBeEnabled();


    // --- Test subsequent request with updated context ---
    mockedFetchQueryResults.mockClear(); // Clear previous call info
    const mockApiResponse2 = {
      products: [
        { title: 'Mouse Y', price: '49.99', url: 'http://example.com/mousey', ranking_explanation: 'Great mouse' },
      ],
      summary: 'Found a great mouse too.',
      new_context: { searchId: '67890' },
    };
    mockedFetchQueryResults.mockResolvedValue(mockApiResponse2);

    await user.clear(inputElement);
    await user.type(inputElement, 'gaming mouse');
    await user.click(submitButton);

    await waitFor(() => {
      expect(mockedFetchQueryResults).toHaveBeenCalledTimes(1);
      // IMPORTANT: Check that previousContext (mockApiResponse.new_context) is passed
      expect(mockedFetchQueryResults).toHaveBeenCalledWith('gaming mouse', { searchId: '12345' }); 
    });

    expect(await screen.findByText('Mouse Y')).toBeInTheDocument();
    expect(await screen.findByText('Found a great mouse too.')).toBeInTheDocument();
  });

  test('error handling: display error message when API call fails', async () => {
    const user = userEvent.setup();
    const errorMessage = 'Network Error: Failed to fetch';
    mockedFetchQueryResults.mockRejectedValue({ message: errorMessage, details: { status: 500 } });

    render(<App />);

    const inputElement = screen.getByPlaceholderText(/e.g., organic coffee beans under \$20/i);
    const submitButton = screen.getByRole('button', { name: /search/i });

    await user.type(inputElement, 'failing query');
    await user.click(submitButton);

    // Wait for error message to be displayed
    // Check for the "Error" heading and the message paragraph separately
    expect(await screen.findByRole('heading', { name: /error/i, level: 2 })).toBeInTheDocument();
    expect(await screen.findByText(errorMessage)).toBeInTheDocument();
    expect(await screen.findByText(/"status": 500/i)).toBeInTheDocument(); // Check for details

    // Ensure product and summary areas are cleared or show appropriate messages
    // In case of an API error, these sections should not display their usual "empty" messages,
    // as the error section takes precedence.
    expect(screen.queryByText(/loading results.../i)).not.toBeInTheDocument();
    expect(screen.queryByText(/no products found. try a different search!/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/no summary available for the current results./i)).not.toBeInTheDocument();
  });
});
