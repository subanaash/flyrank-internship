import { serve } from "inngest/next";
import { inngest } from "@/lib/inngest";

// Functions will be added here in Phase 3
export const { GET, POST, PUT } = serve({
  client: inngest,
  functions: [],
});