import { render, screen, fireEvent, waitFor } from '@testing-library/react';
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
    // QueryInput shows spinner, so text is empty
    expect(screen.getByRole('button', { name: ''})).toBeInTheDocument();


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
    expect(await screen.findByText(`Error: ${errorMessage}`)).toBeInTheDocument();
    expect(await screen.findByText(/"status": 500/i)).toBeInTheDocument(); // Check for details

    // Ensure product and summary areas are cleared or show appropriate messages
    expect(screen.queryByText(/loading results.../i)).not.toBeInTheDocument();
    expect(screen.queryByText(/no products found/i)).toBeInTheDocument(); // Or whatever App.tsx renders on error for products
    expect(screen.queryByText(/no summary available/i)).toBeInTheDocument(); // Or for summary
  });
});
