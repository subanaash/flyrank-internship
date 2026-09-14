from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import timedelta
import uuid
import inngest
import inngest.fast_api

app = FastAPI()

inngest_client = inngest.Inngest(app_id="report-api", is_production=False)

# In-memory store — resets on restart, same lesson as your CRUD API
reports: dict[str, dict] = {}


class ReportRequest(BaseModel):
    topic: str


@inngest_client.create_function(
    fn_id="say-hello",
    trigger=inngest.TriggerEvent(event="test/hello"),
)
async def say_hello(ctx: inngest.Context, step: inngest.Step) -> str:
    await step.sleep("wait-5-seconds", timedelta(seconds=5))
    return "Hello from the background!"


@inngest_client.create_function(
    fn_id="make-report",
    trigger=inngest.TriggerEvent(event="report/requested"),
)
async def make_report(ctx: inngest.Context, step: inngest.Step) -> dict:
    report_id = ctx.event.data["id"]
    topic = ctx.event.data["topic"]

    await step.sleep("do-the-slow-work", timedelta(seconds=8))

    async def build():
        result = f"Report on '{topic}': this is a placeholder result after 8 seconds of work."
        reports[report_id]["status"] = "done"
        reports[report_id]["result"] = result
        return result

    return await step.run("build-report", build)


inngest.fast_api.serve(app, inngest_client, [say_hello, make_report])


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/reports", status_code=202)
async def create_report(payload: ReportRequest):
    report_id = str(uuid.uuid4())
    reports[report_id] = {"id": report_id, "topic": payload.topic, "status": "pending"}

    await inngest_client.send(
        inngest.Event(
            name="report/requested",
            data={"id": report_id, "topic": payload.topic},
        )
    )

    return {"id": report_id, "status": "pending"}


@app.get("/reports/{report_id}")
def get_report(report_id: str):
    report = reports.get(report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
    return report