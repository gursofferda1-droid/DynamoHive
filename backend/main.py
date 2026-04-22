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

# -------------------------
# LATEST CACHE
# -------------------------
LATEST_DATA = []

# -------------------------
# V2 CORE INIT
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
# BACKGROUND LOOP
# -------------------------
def run_loop():

    global LATEST_DATA

    print("🚀 V2 FORCE START")
    print("🔥 ORCHESTRATOR V2 READY")

    while True:

        try:
            print("🔁 LOOP TICK")

            # V2 CYCLE
            data = orchestrator.run_cycle()

            # cache update (opsiyonel)
            if isinstance(data, list):
                LATEST_DATA = data

        except Exception as e:
            print("❌ LOOP ERROR:", e)

        time.sleep(20)


# -------------------------
# STARTUP
# -------------------------
@app.on_event("startup")
def startup_event():
    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()


# -------------------------
# ROOT
# -------------------------
@app.get("/")
def root():
    return {
        "status": "DynamoHive V2 running",
        "items": len(LATEST_DATA)
    }


# -------------------------
# INTEL FEED
# -------------------------
@app.get("/intel")
def intel():
    return JSONResponse(LATEST_DATA)


# -------------------------
# HEALTH
# -------------------------
@app.get("/health")
def health():
    return {"status": "ok"}
