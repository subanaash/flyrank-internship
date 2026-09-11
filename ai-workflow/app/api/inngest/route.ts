import { NextRequest, NextResponse } from "next/server";
import { inngest } from "../../../lib/inngest";

export async function POST(req: NextRequest) {
  const body = await req.json();
  const { nodes, edges, startNodeId } = body;

  const { ids } = await inngest.send({
    name: "workflow/run",
    data: { nodes, edges, startNodeId },
  });

  const eventId = ids[0];

  // Poll the Inngest dev server's REST API for the run result.
  // Local dev server runs on localhost:8288 by default.
  const inngestDevUrl = process.env.INNGEST_DEV_SERVER_URL || "http://127.0.0.1:8288";

  for (let attempt = 0; attempt < 30; attempt++) {
    await new Promise((r) => setTimeout(r, 1000));

    const runsRes = await fetch(`${inngestDevUrl}/v1/events/${eventId}/runs`, {
      headers: { Accept: "application/json" },
    });

    if (!runsRes.ok) continue;

    const runsData = await runsRes.json();
    const run = runsData?.data?.[0];

    if (run?.status === "Completed") {
      return NextResponse.json(run.output ?? {});
    }
    if (run?.status === "Failed" || run?.status === "Cancelled") {
      return NextResponse.json({ error: `Run ${run.status}` }, { status: 500 });
    }
  }

  return NextResponse.json({ error: "Timed out waiting for workflow result" }, { status: 504 });
}