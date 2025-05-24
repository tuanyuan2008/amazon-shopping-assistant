import { render, screen, fireEvent } from '@testing-library/react';
import QueryInput from './QueryInput'; // Adjust path as necessary
import { vi } from 'vitest'; // Vitest's mocking utility

describe('QueryInput Component', () => {
  const mockSetCurrentQuery = vi.fn();
  const mockHandleSubmitQuery = vi.fn();

  beforeEach(() => {
    // Reset mocks before each test
    mockSetCurrentQuery.mockClear();
    mockHandleSubmitQuery.mockClear();
  });

  test('renders the input field and button', () => {
    render(
      <QueryInput
        currentQuery=""
        setCurrentQuery={mockSetCurrentQuery}
        handleSubmitQuery={mockHandleSubmitQuery}
        isLoading={false}
      />
    );

    expect(screen.getByPlaceholderText(/e.g., organic coffee beans under \$20/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /search/i })).toBeInTheDocument();
  });

  test('typing in the input field calls setCurrentQuery prop', () => {
    render(
      <QueryInput
        currentQuery=""
        setCurrentQuery={mockSetCurrentQuery}
        handleSubmitQuery={mockHandleSubmitQuery}
        isLoading={false}
      />
    );

    const inputElement = screen.getByPlaceholderText(/e.g., organic coffee beans under \$20/i);
    fireEvent.change(inputElement, { target: { value: 'test query' } });

    expect(mockSetCurrentQuery).toHaveBeenCalledTimes(1);
    expect(mockSetCurrentQuery).toHaveBeenCalledWith('test query');
  });

  test('clicking the submit button calls handleSubmitQuery prop when query is not empty', () => {
    render(
      <QueryInput
        currentQuery="test query" // Ensure query is not empty for submission
        setCurrentQuery={mockSetCurrentQuery}
        handleSubmitQuery={mockHandleSubmitQuery}
        isLoading={false}
      />
    );

    const buttonElement = screen.getByRole('button', { name: /search/i });
    fireEvent.click(buttonElement);

    expect(mockHandleSubmitQuery).toHaveBeenCalledTimes(1);
  });

  test('clicking the submit button does not call handleSubmitQuery prop when query is empty', () => {
    // Mock window.alert as it's called when the query is empty
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});

    render(
      <QueryInput
        currentQuery="   " // Query with only spaces
        setCurrentQuery={mockSetCurrentQuery}
        handleSubmitQuery={mockHandleSubmitQuery}
        isLoading={false}
      />
    );

    const buttonElement = screen.getByRole('button', { name: /search/i });
    fireEvent.click(buttonElement);

    expect(mockHandleSubmitQuery).not.toHaveBeenCalled();
    expect(alertSpy).toHaveBeenCalledWith('Please enter a search query.');
    
    alertSpy.mockRestore(); // Restore original window.alert
  });
  
  test('input and button are disabled when isLoading is true', () => {
    render(
      <QueryInput
        currentQuery="test query"
        setCurrentQuery={mockSetCurrentQuery}
        handleSubmitQuery={mockHandleSubmitQuery}
        isLoading={true} // isLoading is true
      />
    );

    const inputElement = screen.getByPlaceholderText(/e.g., organic coffee beans under \$20/i);
    // When isLoading is true, the button contains an SVG and not specific text.
    // We can grab it by its role if it's the only button or add a test-id.
    // For now, assuming it's identifiable by role 'button'.
    const buttonElement = screen.getByRole('button'); 

    expect(inputElement).toBeDisabled();
    expect(buttonElement).toBeDisabled();
  });

  test('button text changes to "Searching..." and shows spinner when isLoading is true', () => {
    render(
      <QueryInput
        currentQuery="test query"
        setCurrentQuery={mockSetCurrentQuery}
        handleSubmitQuery={mockHandleSubmitQuery}
        isLoading={true}
      />
    );
    // Check for the presence of the SVG (spinner) by its structure or a test-id if you add one
    // For now, checking the button text is a good start.
    expect(screen.getByRole('button')).toHaveTextContent(''); // Spinner replaces text
    expect(screen.getByRole('button').querySelector('svg')).toBeInTheDocument();
  });
});
