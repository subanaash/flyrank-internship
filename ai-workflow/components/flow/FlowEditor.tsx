"use client";

import { useState, useCallback, useRef } from "react";
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
      background: data.wasVisited ? "#eafff0" : "#FAFAF9",
      border: data.wasVisited ? "2px solid #22c55e" : "1px solid #1A1A1A",
      borderRadius: 8,
      padding: 12,
      width: 220,
      fontFamily: "sans-serif",
    }}>
      <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 6, color: "#1A1A1A" }}>
        Decision Node {data.wasVisited && `(${data.visitedDecision})`}
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
      <Handle type="source" position={Position.Right} id="yes" style={{ background: "#22c55e", top: "50%" }} />
      <Handle type="source" position={Position.Left} id="no" style={{ background: "#ef4444", top: "50%" }} />
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, marginTop: 4 }}>
        <span style={{ color: "#ef4444" }}>NO</span>
        <span style={{ color: "#22c55e" }}>YES</span>
      </div>
    </div>
  );
}

const nodeTypes = { decision: DecisionNode };

let nodeIdCounter = 1;

type LogEntry = { nodeId: string; decision: "YES" | "NO"; timestamp: string };

export default function FlowEditor() {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node[]>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [running, setRunning] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handlePromptChange = useCallback((id: string, prompt: string) => {
    setNodes((nds) => nds.map((n) => (n.id === id ? { ...n, data: { ...n.data, prompt } } : n)));
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

  const onConnect = useCallback((connection: Connection) => {
    const isYes = connection.sourceHandle === "yes";
    const edge: Edge = {
      ...connection,
      id: `e-${connection.source}-${connection.target}-${connection.sourceHandle}`,
      label: isYes ? "YES" : "NO",
      style: { stroke: isYes ? "#22c55e" : "#ef4444" },
      animated: false,
    } as Edge;
    setEdges((eds) => addEdge(edge, eds));
  }, [setEdges]);

  const runWorkflow = async () => {
    const startNode = nodes[0];
    if (!startNode) {
      alert("Add at least one node first");
      return;
    }
    setRunning(true);
    setLogs([]);

    try {
      const response = await fetch("/api/run-workflow", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nodes: nodes.map((n) => ({ id: n.id, data: { prompt: n.data.prompt } })),
          edges: edges.map((e) => ({ source: e.source, target: e.target, sourceHandle: e.sourceHandle })),
          startNodeId: startNode.id,
        }),
      });

      if (!response.ok) {
        throw new Error(`Server responded with ${response.status}`);
      }

      const result = await response.json();
      const executionOrder = result.executionOrder as { nodeId: string; decision: "YES" | "NO" }[] | undefined;

      if (executionOrder) {
        const newLogs = executionOrder.map((e) => ({
          ...e,
          timestamp: new Date().toLocaleTimeString(),
        }));
        setLogs(newLogs);

        const visitedMap = new Map(executionOrder.map((e) => [e.nodeId, e.decision]));
        setNodes((nds) =>
          nds.map((n) => ({
            ...n,
            data: {
              ...n.data,
              wasVisited: visitedMap.has(n.id),
              visitedDecision: visitedMap.get(n.id),
            },
          }))
        );

        setEdges((eds) =>
          eds.map((e) => {
            const wasTaken = executionOrder.some(
              (log, i) =>
                log.nodeId === e.source &&
                e.sourceHandle === log.decision.toLowerCase() &&
                executionOrder[i + 1]?.nodeId === e.target
            );
            return { ...e, animated: wasTaken };
          })
        );
      } else {
        alert("Workflow triggered, but no direct result was returned (check Inngest dashboard).");
      }
    } catch (err) {
      alert(`Workflow run failed: ${err}`);
    } finally {
      setRunning(false);
    }
  };

  const exportJson = () => {
    const data = {
      nodes: nodes.map((n) => ({ id: n.id, position: n.position, data: { prompt: n.data.prompt } })),
      edges: edges.map((e) => ({ source: e.source, target: e.target, sourceHandle: e.sourceHandle })),
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "workflow.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  const importJson = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const data = JSON.parse(event.target?.result as string);
        const loadedNodes: Node[] = data.nodes.map((n: any) => ({
          id: n.id,
          type: "decision",
          position: n.position,
          data: { prompt: n.data.prompt, onPromptChange: handlePromptChange },
        }));
        const loadedEdges: Edge[] = data.edges.map((e: any) => ({
          id: `e-${e.source}-${e.target}-${e.sourceHandle}`,
          source: e.source,
          target: e.target,
          sourceHandle: e.sourceHandle,
          label: e.sourceHandle === "yes" ? "YES" : "NO",
          style: { stroke: e.sourceHandle === "yes" ? "#22c55e" : "#ef4444" },
        }));
        setNodes(loadedNodes);
        setEdges(loadedEdges);
        setLogs([]);
      } catch {
        alert("Invalid workflow JSON file");
      }
    };
    reader.readAsText(file);
  };

  return (
    <div style={{ width: "100vw", height: "100vh", display: "flex" }}>
      <div style={{ flex: 1, position: "relative" }}>
        <div style={{ position: "absolute", zIndex: 10, padding: 12, display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button onClick={addNode} style={btnStyle("#185FA5")}>+ Add Decision Node</button>
          <button onClick={runWorkflow} disabled={running} style={btnStyle(running ? "#9ca3af" : "#22c55e")}>
            {running ? "Running..." : "▶ Run Workflow"}
          </button>
          <button onClick={exportJson} style={btnStyle("#BA7517")}>⬇ Export JSON</button>
          <button onClick={() => fileInputRef.current?.click()} style={btnStyle("#5F5E5A")}>⬆ Import JSON</button>
          <input ref={fileInputRef} type="file" accept=".json" onChange={importJson} style={{ display: "none" }} />
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

      <div style={{ width: 300, borderLeft: "1px solid #ddd", padding: 12, overflowY: "auto", fontFamily: "sans-serif" }}>
        <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 8 }}>Execution Log</h3>
        {logs.length === 0 && <p style={{ fontSize: 12, color: "#888" }}>No run yet. Click "Run Workflow".</p>}
        {logs.map((log, i) => (
          <div key={i} style={{
            fontSize: 12,
            padding: 8,
            marginBottom: 6,
            borderRadius: 6,
            background: log.decision === "YES" ? "#eafff0" : "#fff0f0",
            border: `1px solid ${log.decision === "YES" ? "#22c55e" : "#ef4444"}`,
          }}>
            <div><strong>Step {i + 1}:</strong> {log.nodeId}</div>
            <div>Decision: <strong style={{ color: log.decision === "YES" ? "#22c55e" : "#ef4444" }}>{log.decision}</strong></div>
            <div style={{ color: "#888" }}>{log.timestamp}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function btnStyle(bg: string): React.CSSProperties {
  return {
    background: bg,
    color: "white",
    border: "none",
    borderRadius: 6,
    padding: "8px 16px",
    fontSize: 13,
    cursor: "pointer",
  };
}