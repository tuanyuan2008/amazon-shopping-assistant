import { render, screen } from '@testing-library/react';
import ResultsDisplay from './ResultsDisplay'; // Adjust path as necessary

describe('ResultsDisplay Component', () => {
  const mockProducts = [
    { title: 'Product 1', price: '10.99', url: 'http://example.com/product1', ranking_explanation: 'Reason 1', price_per_count: '$1.00/oz' },
    { title: 'Product 2', price: '20.50', url: 'http://example.com/product2' }, // No explanation or unit price
  ];

  test('renders "Loading results..." message when isLoading is true', () => {
    render(<ResultsDisplay products={[]} isLoading={true} />);
    expect(screen.getByText(/loading results.../i)).toBeInTheDocument();
  });

  test('renders "No products found." when products array is empty and not loading', () => {
    render(<ResultsDisplay products={[]} isLoading={false} />);
    expect(screen.getByText(/no products found. try a different search!/i)).toBeInTheDocument();
  });

  test('correctly renders a list of product items when products prop has data', () => {
    render(<ResultsDisplay products={mockProducts} isLoading={false} />);

    // Check for Product 1 details
    expect(screen.getByText('Product 1')).toBeInTheDocument();
    expect(screen.getByText((content, element) => element?.tagName.toLowerCase() === 'span' && content.includes('10.99'))).toBeInTheDocument(); // Price
    expect(screen.getByText('Reason 1')).toBeInTheDocument(); // Explanation
    expect(screen.getByText('$1.00/oz')).toBeInTheDocument(); // Unit price
    expect(screen.getByRole('link', { name: /product 1/i })).toHaveAttribute('href', 'http://example.com/product1');

    // Check for Product 2 details
    expect(screen.getByText('Product 2')).toBeInTheDocument();
    expect(screen.getByText((content, element) => element?.tagName.toLowerCase() === 'span' && content.includes('20.50'))).toBeInTheDocument(); // Price
    expect(screen.getByRole('link', { name: /product 2/i })).toHaveAttribute('href', 'http://example.com/product2');
    
    // Ensure elements not present for Product 2 are not rendered
    // This is implicitly tested by not finding them.
    // The test 'does not render explanation or unit price if not provided' also covers this.
  });

  test('renders product titles as links', () => {
    render(<ResultsDisplay products={mockProducts} isLoading={false} />);
    mockProducts.forEach(product => {
      const linkElement = screen.getByRole('link', { name: product.title });
      expect(linkElement).toBeInTheDocument();
      expect(linkElement).toHaveAttribute('href', product.url);
    });
  });

  test('does not render explanation or unit price if not provided', () => {
    const productWithoutOptionalFields = [{ title: 'Product 3', price: '5.00', url: 'http://example.com/product3' }];
    render(<ResultsDisplay products={productWithoutOptionalFields} isLoading={false} />);
    
    expect(screen.getByText('Product 3')).toBeInTheDocument();
    // Check that elements for ranking_explanation and price_per_count are NOT present for Product 3
    // This is harder to assert directly for absence without specific test-ids or more complex queries.
    // We can check that the overall product item for Product 3 does not contain unexpected text.
    const product3Item = screen.getByText('Product 3').closest('.product-item'); // Assuming .product-item class in component
    if (product3Item) {
        // This is a weak check, depends on component structure
        expect(product3Item.textContent).not.toMatch(/Agent's Note/i); 
        expect(product3Item.textContent).not.toMatch(/Unit Price/i); 
    } else {
        throw new Error("Could not find product item for Product 3 to check for absence of optional fields.");
    }
  });
});
