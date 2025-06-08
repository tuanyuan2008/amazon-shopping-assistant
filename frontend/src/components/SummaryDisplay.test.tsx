import { render, screen } from '@testing-library/react';
import SummaryDisplay from './SummaryDisplay'; // Adjust path as necessary

describe('SummaryDisplay Component', () => {
  test('renders "Loading summary..." message when isLoading is true and no initial summary', () => {
    render(<SummaryDisplay summary={null} isLoading={true} />);
    expect(screen.getByText(/loading summary.../i)).toBeInTheDocument();
  });

  test('renders "No summary available." when summary is null and not loading', () => {
    render(<SummaryDisplay summary={null} isLoading={false} />);
    expect(screen.getByText(/no summary available for the current results./i)).toBeInTheDocument();
  });
  
  test('renders "No summary available." when summary is an empty string and not loading', () => {
    render(<SummaryDisplay summary="" isLoading={false} />);
    expect(screen.getByText(/no summary available for the current results./i)).toBeInTheDocument();
  });

  test('renders the summary text when summary prop has data and not loading', () => {
    const mockSummary = 'This is a test summary of the products found.';
    render(<SummaryDisplay summary={mockSummary} isLoading={false} />);
    expect(screen.getByText(mockSummary)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /ai summary/i })).toBeInTheDocument();
  });

  test('renders the summary text even when isLoading is true (showing stale summary while new one loads)', () => {
    const mockSummary = 'This is a stale summary and a new one is loading.';
    render(<SummaryDisplay summary={mockSummary} isLoading={true} />);
    expect(screen.getByText(mockSummary)).toBeInTheDocument();
    expect(screen.getByText(/updating summary.../i)).toBeInTheDocument(); // Check for updating indicator
  });
  
  test('does not show "No summary available" if isLoading is true, even if summary is null', () => {
    render(<SummaryDisplay summary={null} isLoading={true} />);
    // It should show "Loading summary..." instead
    expect(screen.queryByText(/no summary available for the current results./i)).not.toBeInTheDocument();
    expect(screen.getByText(/loading summary.../i)).toBeInTheDocument();
  });
});
