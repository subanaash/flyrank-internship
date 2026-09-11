"use client";

import { useState, useCallback } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  Connection,
  Edge,
  Node,
  Handle,
  Position,
  NodeProps,
} from "reactflow";
import "reactflow/dist/style.css";

function DecisionNode({ id, data }: NodeProps) {
  const [prompt, setPrompt] = useState(data.prompt || "");

  const onChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setPrompt(e.target.value);
    data.onPromptChange?.(id, e.target.value);
  };

  return (
    <div style={{
      background: "#FAFAF9",
      border: "1px solid #1A1A1A",
      borderRadius: 8,
      padding: 12,
      width: 220,
      fontFamily: "sans-serif",
    }}>
      <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 6, color: "#1A1A1A" }}>
        Decision Node
      </div>
      <textarea
        value={prompt}
        onChange={onChange}
        placeholder="Is this a support request?"
        style={{
          width: "100%",
          fontSize: 12,
          padding: 6,
          borderRadius: 4,
          border: "1px solid #ccc",
          resize: "none",
        }}
        rows={3}
      />

      <Handle type="target" position={Position.Top} />

      <Handle
        type="source"
        position={Position.Right}
        id="yes"
        style={{ background: "#22c55e", top: "50%" }}
      />
      <Handle
        type="source"
        position={Position.Left}
        id="no"
        style={{ background: "#ef4444", top: "50%" }}
      />
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, marginTop: 4 }}>
        <span style={{ color: "#ef4444" }}>NO</span>
        <span style={{ color: "#22c55e" }}>YES</span>
      </div>
    </div>
  );
}

const nodeTypes = { decision: DecisionNode };

let nodeIdCounter = 1;

export default function FlowEditor() {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node[]>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge[]>([]);

  const handlePromptChange = useCallback((id: string, prompt: string) => {
    setNodes((nds) =>
      nds.map((n) => (n.id === id ? { ...n, data: { ...n.data, prompt } } : n))
    );
  }, [setNodes]);

  const addNode = () => {
    const id = `node-${nodeIdCounter++}`;
    const newNode: Node = {
      id,
      type: "decision",
      position: { x: 100 + Math.random() * 300, y: 100 + Math.random() * 300 },
      data: { prompt: "", onPromptChange: handlePromptChange },
    };
    setNodes((nds) => [...nds, newNode]);
  };

  const onConnect = useCallback(
    (connection: Connection) => {
      const isYes = connection.sourceHandle === "yes";
      const edge: Edge = {
        ...connection,
        id: `e-${connection.source}-${connection.target}-${connection.sourceHandle}`,
        label: isYes ? "YES" : "NO",
        style: { stroke: isYes ? "#22c55e" : "#ef4444" },
        animated: false,
      } as Edge;
      setEdges((eds) => addEdge(edge, eds));
    },
    [setEdges]
  );

  return (
    <div style={{ width: "100vw", height: "100vh" }}>
      <div style={{ position: "absolute", zIndex: 10, padding: 12 }}>
        <button
          onClick={addNode}
          style={{
            background: "#185FA5",
            color: "white",
            border: "none",
            borderRadius: 6,
            padding: "8px 16px",
            fontSize: 14,
            cursor: "pointer",
          }}
        >
          + Add Decision Node
        </button>
      </div>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        fitView
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  );
}