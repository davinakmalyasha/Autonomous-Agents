import { useRef, useEffect } from 'react';
import type { MouseEvent, WheelEvent } from 'react';
import type { CanvasNode, CanvasEdge } from '../../types/canvas.types';
import CanvasNodeComponent from './CanvasNode';

interface Props {
  nodes: CanvasNode[];
  edges: CanvasEdge[];
  pan: { x: number; y: number };
  zoom: number;
  selectedId: string | null;
  setPan: (pan: { x: number; y: number } | ((prev: { x: number; y: number }) => { x: number; y: number })) => void;
  setZoom: (zoom: number | ((prev: number) => number)) => void;
  onSelectNode: (id: string) => void;
  steps: any[];
}

export default function CanvasWorkspace({ nodes, edges, pan, zoom, selectedId, setPan, setZoom, onSelectNode, steps }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef({ isDragging: false, startX: 0, startY: 0, panX: 0, panY: 0, hasMoved: false });

  const handleMouseDown = (e: MouseEvent) => {
    const target = e.target as HTMLElement;
    if (target.closest('button, input, textarea, select, a, [data-interactive="true"]')) return;
    dragRef.current = { isDragging: true, startX: e.clientX, startY: e.clientY, panX: pan.x, panY: pan.y, hasMoved: false };
  };

  useEffect(() => {
    const onMouseMove = (e: globalThis.MouseEvent) => {
      if (!dragRef.current.isDragging) return;
      const dx = e.clientX - dragRef.current.startX;
      const dy = e.clientY - dragRef.current.startY;
      if (Math.abs(dx) > 3 || Math.abs(dy) > 3) dragRef.current.hasMoved = true;
      setPan({ x: dragRef.current.panX + dx, y: dragRef.current.panY + dy });
    };
    const onMouseUp = () => { dragRef.current.isDragging = false; };
    const onClickCapture = (e: globalThis.MouseEvent) => {
      if (dragRef.current.hasMoved) {
        e.stopPropagation();
        e.preventDefault();
        dragRef.current.hasMoved = false;
      }
    };
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
    window.addEventListener('click', onClickCapture, true);
    return () => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      window.removeEventListener('click', onClickCapture, true);
    };
  }, [setPan]);

  const handleWheel = (e: WheelEvent) => {
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.05 : 0.95;
    setZoom((z) => Math.max(0.3, Math.min(2.5, z * factor)));
  };

  return (
    <div
      ref={containerRef}
      onMouseDown={handleMouseDown}
      onWheel={handleWheel}
      className="relative flex-1 h-full overflow-hidden bg-[#0a0a0c] cursor-grab active:cursor-grabbing select-none"
      style={{
        backgroundImage: 'radial-gradient(rgba(128,128,128,0.15) 1.2px, transparent 1.2px)',
        backgroundSize: `${24 * zoom}px ${24 * zoom}px`,
        backgroundPosition: `${pan.x}px ${pan.y}px`,
      }}
    >
      <div
        className="absolute origin-top-left"
        style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`, width: '2000px', height: '1600px' }}
      >
        <svg className="absolute inset-0 w-full h-full pointer-events-none overflow-visible">
          <defs>
            <marker id="arrow" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 1 L 10 5 L 0 9 z" className="fill-zinc-700" />
            </marker>
          </defs>
          {edges.map((edge) => {
            const fromNode = nodes.find((n) => n.id === edge.from);
            const toNode = nodes.find((n) => n.id === edge.to);
            if (!fromNode || !toNode) return null;
            return (
              <line
                key={edge.id}
                x1={fromNode.x}
                y1={fromNode.y}
                x2={toNode.x}
                y2={toNode.y}
                className={`stroke-2 transition-all duration-300 ${
                  edge.active ? 'stroke-blue-500/80 [stroke-dasharray:5]' : 'stroke-zinc-800'
                }`}
                style={{
                  strokeDasharray: edge.active ? '5' : undefined,
                  animation: edge.active ? 'dash_pulse_anim 10s linear infinite' : undefined,
                }}
              />
            );
          })}
        </svg>
        {nodes.map((node) => (
          <CanvasNodeComponent
            key={node.id}
            node={node}
            steps={steps}
            isActive={selectedId === node.id}
            onClick={() => onSelectNode(node.id)}
          />
        ))}
      </div>
    </div>
  );
}
