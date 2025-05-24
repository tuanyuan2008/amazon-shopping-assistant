import React, { useMemo, useEffect, useCallback } from 'react';
import ReactFlow, {
  ReactFlowProvider,
  useNodesState,
  useEdgesState,
  MarkerType,
  // Controls, // Uncomment to add controls
  // MiniMap,  // Uncomment to add minimap
  // Background // Uncomment to add background
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import type { Product } from '../services/api';
import type { Node, Edge, OnNodesChange, OnEdgesChange, OnNodeClick } from '@xyflow/react';

interface ProductGraphDisplayProps {
  products: Product[];
}

const ProductGraphDisplay: React.FC<ProductGraphDisplayProps> = ({ products }) => {
  const initialNodesData = useMemo(() => {
    return products.slice(0, 10).map((product, index) => ({
      id: product.url || `product-${index}-${product.title}`,
      type: 'default',
      data: {
        label: `${product.title} (Price: ${typeof product.price === 'number' ? `$${product.price.toFixed(2)}` : product.price})`,
        rawProduct: product, // Store the full product object
      },
      position: { x: (index % 3) * 300, y: Math.floor(index / 3) * 150 },
    }));
  }, [products]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodesData);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  useEffect(() => {
    setNodes(initialNodesData);
    setEdges([]); // Clear edges when products change
  }, [initialNodesData, setNodes, setEdges]);

  const onNodeClick: OnNodeClick = useCallback((event, clickedNode) => {
    const clickedProductData = clickedNode.data.rawProduct as Product;
    
    // Ensure price is a number. It should be due to App.tsx parsing, but good to double check.
    const numericClickedPrice = typeof clickedProductData.price === 'number' 
      ? clickedProductData.price 
      : parseFloat(String(clickedProductData.price).replace(/[^\d.-]/g, ''));

    if (isNaN(numericClickedPrice)) {
      console.warn("Clicked product has no valid numerical price:", clickedProductData.title, clickedProductData.price);
      setEdges([]); // Clear existing edges
      return;
    }

    const otherNodes = nodes.filter(n => n.id !== clickedNode.id && n.data.rawProduct);

    const pricedNeighbors = otherNodes.map(n => {
      const neighborProduct = n.data.rawProduct as Product;
      const neighborPrice = typeof neighborProduct.price === 'number' 
        ? neighborProduct.price 
        : parseFloat(String(neighborProduct.price).replace(/[^\d.-]/g, ''));
      
      if (isNaN(neighborPrice)) return null;
      
      return { 
        ...n, 
        priceDiff: neighborPrice - numericClickedPrice, // Positive if more expensive, negative if cheaper
        actualPrice: neighborPrice 
      };
    }).filter(n => n !== null) as (Node & { priceDiff: number; actualPrice: number })[]; // Type assertion

    // Separate cheaper and more expensive products
    const cheaperNeighbors = pricedNeighbors
      .filter(n => n.priceDiff < 0)
      .sort((a, b) => b.priceDiff - a.priceDiff); // Sort by most expensive of the cheaper ones (closest to clicked price)
    
    const expensiveNeighbors = pricedNeighbors
      .filter(n => n.priceDiff > 0)
      .sort((a, b) => a.priceDiff - b.priceDiff); // Sort by cheapest of the more expensive ones (closest to clicked price)

    // Select up to 2 from each category
    const selectedNeighbors = [
      ...cheaperNeighbors.slice(0, 2),
      ...expensiveNeighbors.slice(0, 2)
    ];

    const newEdges = selectedNeighbors.map(neighbor => ({
      id: `edge-${clickedNode.id}-${neighbor.id}`,
      source: clickedNode.id,
      target: neighbor.id,
      label: `Diff: $${neighbor.priceDiff.toFixed(2)}`,
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
    }));

    setEdges(newEdges);
  }, [nodes, setEdges]); // Include 'nodes' and 'setEdges' in dependencies

  return (
    <div style={{ width: '100%', height: '600px' }} data-testid="product-graph-display">
      <ReactFlowProvider>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange as OnNodesChange}
          onEdgesChange={onEdgesChange as OnEdgesChange}
          onNodeClick={onNodeClick} // Add the click handler
          fitView
          // proOptions={{ hideAttribution: true }} 
        >
          {/* 
          <Controls />
          <MiniMap />
          <Background variant="dots" gap={12} size={1} /> 
          */}
        </ReactFlow>
      </ReactFlowProvider>
    </div>
  );
};

export default ProductGraphDisplay;
