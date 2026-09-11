import { NextRequest, NextResponse } from "next/server";
import { inngest } from "../../../lib/inngest";

export async function POST(req: NextRequest) {
  const body = await req.json();
  const { nodes, edges, startNodeId } = body;

  await inngest.send({
    name: "workflow/run",
    data: { nodes, edges, startNodeId },
  });

  return NextResponse.json({ status: "triggered" });
}