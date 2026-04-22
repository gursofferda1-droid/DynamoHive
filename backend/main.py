from fastapi import FastAPI
from fastapi.responses import JSONResponse
import threading
import time

from ai_engine.v2.state_store import StateStore
from ai_engine.v2.event_bus import EventBus
from ai_engine.v2.signal_queue import SignalQueue
from ai_engine.v2.execution_graph import ExecutionGraph
from ai_engine.v2.orchestrator_v2 import OrchestratorV2

from backend.storage import save_post


# -------------------------
# APP
# -------------------------
app = FastAPI()

LATEST_DATA = []


# -------------------------
# V2 CORE
# -------------------------
state = StateStore()
bus = EventBus()
queue = SignalQueue()

graph = ExecutionGraph(
    state=state,
    bus=bus,
    queue=queue,
    worker_pool=None,
    intelligence_engine=None,
    decision_engine=None,
    storage=save_post
)

orchestrator = OrchestratorV2(
    state=state,
    bus=bus,
    queue=queue,
    execution_graph=graph
)


# -------------------------
# LOOP
# -------------------------
def run_loop():

    global LATEST_DATA

    print("🚀 V2 STARTED")

    while True:

        try:
            data = orchestrator.run_cycle()

            if isinstance(data, list):
                LATEST_DATA = data

        except Exception as e:
            print("ERROR:", e)

        time.sleep(20)


# -------------------------
# STARTUP
# -------------------------
@app.on_event("startup")
def startup():
    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()


# -------------------------
# ROUTES
# -------------------------
@app.get("/")
def root():
    return {
        "status": "V2 running",
        "items": len(LATEST_DATA)
    }


@app.get("/intel")
def intel():
    return JSONResponse(LATEST_DATA)


@app.get("/health")
def health():
    return {"status": "ok"}
