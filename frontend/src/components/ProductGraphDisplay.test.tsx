import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import ProductGraphDisplay from './ProductGraphDisplay';
import type { Product } from '../services/api'; // Ensure Product type is available

// Mock products to be used in tests
const mockProducts: Product[] = [
  { title: 'Product A', price: 10.00, url: 'prod-a', ranking_explanation: 'Rank A', store_name: 'Store A', rating: 4.5, reviews_count: 100 },
  { title: 'Product B', price: 5.00, url: 'prod-b', ranking_explanation: 'Rank B', store_name: 'Store B', rating: 4.0, reviews_count: 50 },
  { title: 'Product C', price: 15.00, url: 'prod-c', ranking_explanation: 'Rank C', store_name: 'Store C', rating: 4.8, reviews_count: 200 },
  { title: 'Product D', price: 12.00, url: 'prod-d', ranking_explanation: 'Rank D', store_name: 'Store D', rating: 3.5, reviews_count: 75 },
  { title: 'Product E', price: 8.00, url: 'prod-e', ranking_explanation: 'Rank E', store_name: 'Store E', rating: 4.2, reviews_count: 120 },
  { title: 'Product F', price: 10.50, url: 'prod-f', ranking_explanation: 'Rank F', store_name: 'Store F', rating: 4.6, reviews_count: 150 },
];

// Helper to format price for checking labels
const formatPrice = (price: number | string) => {
  if (typeof price === 'number') {
    return `$${price.toFixed(2)}`;
  }
  return price; // Should ideally not happen with parsed prices
};

describe('ProductGraphDisplay', () => {
  test('renders the graph display container', () => {
    render(<ProductGraphDisplay products={mockProducts} />);
    expect(screen.getByTestId('product-graph-display')).toBeInTheDocument();
  });

  test('renders product nodes correctly from props', () => {
    const testProducts = mockProducts.slice(0, 3);
    render(<ProductGraphDisplay products={testProducts} />);

    testProducts.forEach(product => {
      expect(screen.getByText(`${product.title} (Price: ${formatPrice(product.price as number)})`)).toBeInTheDocument();
    });
    
    // Check number of nodes by looking for elements that React Flow renders for nodes
    // Nodes usually have a role like 'button' or a specific class, or data-id
    // This is a bit dependent on React Flow's internal structure but generally stable for default nodes.
    // We expect nodes to be rendered for the products.
    // Let's assume each node label we checked above is within a distinct node element.
    const nodeElements = screen.getAllByText(/\(Price: .*\)/i);
    expect(nodeElements.length).toBe(testProducts.length);
  });

  test('renders no product nodes when products array is empty', () => {
    render(<ProductGraphDisplay products={[]} />);
    // Check that no node labels are present
    expect(screen.queryByText(/\(Price: .*\)/i)).not.toBeInTheDocument();
  });

  test('click interaction creates edges for price neighbors', async () => {
    // Product A: $10.00
    // Product B: $5.00 (Cheaper by 5.00)
    // Product E: $8.00 (Cheaper by 2.00)
    // Product F: $10.50 (More expensive by 0.50)
    // Product D: $12.00 (More expensive by 2.00)
    // Product C: $15.00 (More expensive by 5.00)

    // Clicking Product A ($10.00)
    // Expected cheaper neighbors: Product E ($8.00, diff -2.00), Product B ($5.00, diff -5.00)
    // Expected expensive neighbors: Product F ($10.50, diff +0.50), Product D ($12.00, diff +2.00)
    render(<ProductGraphDisplay products={mockProducts} />);

    const productANodeLabel = `${mockProducts[0].title} (Price: ${formatPrice(mockProducts[0].price as number)})`;
    
    // Find the node. Nodes in React Flow are complex. We click the label which is part of the node.
    const nodeToClick = screen.getByText(productANodeLabel);
    fireEvent.click(nodeToClick);

    // Wait for edges to be rendered (labels on edges show price differences)
    // The component updates edges asynchronously via setEdges
    await waitFor(() => {
      // Edges for Product E (cheaper) and Product B (cheaper)
      expect(screen.getByText('Diff: $-2.00')).toBeInTheDocument(); // A to E
      expect(screen.getByText('Diff: $-5.00')).toBeInTheDocument(); // A to B
      
      // Edges for Product F (more expensive) and Product D (more expensive)
      expect(screen.getByText('Diff: $0.50')).toBeInTheDocument();  // A to F
      expect(screen.getByText('Diff: $2.00')).toBeInTheDocument();  // A to D
    });

    // Verify the number of edges. React Flow renders edges as SVG paths.
    // A common way to find edges is by their role or class.
    // Or, more simply here, by the number of labels we expect.
    const edgeLabels = screen.getAllByText(/Diff: \$/i);
    expect(edgeLabels.length).toBe(4); // 2 cheaper + 2 more expensive
  });

  test('clicking a node with no numeric price does not create edges and clears existing ones', async () => {
    const productsWithInvalidPrice = [
      { ...mockProducts[0], price: 10.00, url: 'valid-price-prod' }, // Product A
      { title: 'Invalid Price Prod', price: 'Not a number', url: 'invalid-price-prod', ranking_explanation: 'Test', store_name: 'Test Store', rating: 0, reviews_count: 0 },
      { ...mockProducts[1], price: 5.00, url: 'another-valid-prod' }, // Product B
    ];
    render(<ProductGraphDisplay products={productsWithInvalidPrice} />);

    // First, click a valid node to establish some edges
    const validNodeLabel = `${productsWithInvalidPrice[0].title} (Price: ${formatPrice(productsWithInvalidPrice[0].price as number)})`;
    fireEvent.click(screen.getByText(validNodeLabel));
    
    await waitFor(() => {
      expect(screen.getByText('Diff: $-5.00')).toBeInTheDocument(); // Edge from Product A to Product B
    });
    expect(screen.getAllByText(/Diff: \$/i).length).toBe(1);


    // Now, click the node with the invalid price
    const invalidNodeLabel = `Invalid Price Prod (Price: Not a number)`;
    fireEvent.click(screen.getByText(invalidNodeLabel));

    await waitFor(() => {
      // Check that previously existing edges are cleared
      expect(screen.queryByText(/Diff: \$/i)).not.toBeInTheDocument();
    });
  });
  
  test('updates nodes when products prop changes', () => {
    const initialProds = [mockProducts[0]];
    const { rerender } = render(<ProductGraphDisplay products={initialProds} />);
    expect(screen.getByText(`${mockProducts[0].title} (Price: ${formatPrice(mockProducts[0].price as number)})`)).toBeInTheDocument();
    expect(screen.queryByText(`${mockProducts[1].title} (Price: ${formatPrice(mockProducts[1].price as number)})`)).not.toBeInTheDocument();

    const updatedProds = [mockProducts[0], mockProducts[1]];
    rerender(<ProductGraphDisplay products={updatedProds} />);
    
    expect(screen.getByText(`${mockProducts[0].title} (Price: ${formatPrice(mockProducts[0].price as number)})`)).toBeInTheDocument();
    expect(screen.getByText(`${mockProducts[1].title} (Price: ${formatPrice(mockProducts[1].price as number)})`)).toBeInTheDocument();
    
    const nodeElements = screen.getAllByText(/\(Price: .*\)/i);
    expect(nodeElements.length).toBe(updatedProds.length);
  });

});
