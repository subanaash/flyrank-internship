# Visual AI Workflow System

A visual workflow builder where each node is an AI decision step that returns YES or NO. Built with React Flow for the visual editor and Inngest for reliable, observable execution, with each node running as its own retryable Inngest step.

## What this does

Design a decision tree visually: add nodes, write a yes/no question as each node's prompt, and connect nodes with YES or NO edges. Click "Run Workflow" and each node's prompt is sent to a local LLM (via Ollama), which must answer exactly YES or NO. The workflow follows the corresponding edge to the next node, continuing until it reaches a node with no further connection on that path.

## How to run it

1. Clone the repo and enter the folder:
   ```
   git clone https://github.com/subanaash/flyrank-internship.git
   cd flyrank-internship/ai-workflow
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Install [Ollama](https://ollama.com/download) and pull a model:
   ```
   ollama run gemma3:1b
   ```

4. Create `.env.local`:
   ```
   LLM_BASE_URL=http://localhost:11434/v1/
   LLM_API_KEY=ollama
   LLM_MODEL=gemma3:1b
   INNGEST_DEV=1
   ```

5. Start the Next.js dev server:
   ```
   npm run dev
   ```

6. In a separate terminal, start the Inngest dev server:
   ```
   npx inngest-cli@latest dev
   ```

7. Open `http://localhost:3000` — the flow editor loads. Inngest's own dashboard (run history, traces) is at `http://localhost:8288`.

## How to use it

1. Click **"+ Add Decision Node"** to add a node. Type a yes/no question into its prompt box.
2. Drag from a node's **green handle (YES)** or **red handle (NO)** to another node to connect them.
3. Click **"▶ Run Workflow"**. Execution starts from the first node created and follows the AI's YES/NO answer at each step.
4. Watch the **Execution Log** panel on the right for a step-by-step record of each decision, and watch visited nodes turn green with their decision shown in the title.
5. Use **"⬇ Export JSON"** to save the current workflow to a file, and **"⬆ Import JSON"** to load one back in.

## Architecture

- **Frontend (React Flow):** renders the graph, handles node creation, editing, and connections entirely in local React state.
- **Execution (Inngest):** each node's AI call is wrapped in `step.run(...)`, so it's independently retryable and observable in the Inngest dashboard, not just a single opaque function call.
- **The API route** (`/api/run-workflow`) sends the graph to Inngest as an event, then polls the local Inngest dev server's REST API until the run completes, returning the full execution order back to the frontend.
- **The model call** uses the standard `openai` npm package pointed at Ollama's OpenAI-compatible local endpoint — no cloud API key needed, no cost per call.
