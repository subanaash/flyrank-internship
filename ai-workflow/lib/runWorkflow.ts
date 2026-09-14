import { inngest } from "./inngest";
import OpenAI from "openai";

const client = new OpenAI({
  baseURL: process.env.LLM_BASE_URL || "http://localhost:11434/v1/",
  apiKey: process.env.LLM_API_KEY || "ollama",
});

type FlowNode = {
  id: string;
  data: { prompt: string };
};

type FlowEdge = {
  source: string;
  target: string;
  sourceHandle: "yes" | "no";
};

type WorkflowInput = {
  nodes: FlowNode[];
  edges: FlowEdge[];
  startNodeId: string;
};

export const runWorkflow = inngest.createFunction(
  { id: "run-workflow", triggers: { event: "workflow/run" } },
  async ({ event, step }) => {
    const { nodes, edges, startNodeId } = event.data as WorkflowInput;

    const executionOrder: { nodeId: string; decision: "YES" | "NO" }[] = [];
    let currentNodeId: string | undefined = startNodeId;
    let safetyCounter = 0;

    while (currentNodeId && safetyCounter < 50) {
      safetyCounter++;
      const node = nodes.find((n) => n.id === currentNodeId);
      if (!node) break;

      const decision = await step.run(`decide-${node.id}`, async () => {
        const response = await client.chat.completions.create({
          model: process.env.LLM_MODEL || "gemma3:1b",
          temperature: 0,
          messages: [
            {
              role: "system",
              content:
                "You must answer with exactly one word: YES or NO. No explanation, no punctuation, nothing else.",
            },
            { role: "user", content: node.data.prompt },
          ],
        });

        const raw = response.choices[0].message.content?.trim().toUpperCase() || "";
        return raw.includes("YES") ? "YES" : "NO";
      });

      executionOrder.push({ nodeId: currentNodeId, decision });

      const nextEdge = edges.find(
        (e) => e.source === currentNodeId && e.sourceHandle === decision.toLowerCase()
      );
      currentNodeId = nextEdge?.target;
    }

    return { executionOrder };
  }
);