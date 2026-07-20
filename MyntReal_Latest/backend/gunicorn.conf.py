import os

bind = "0.0.0.0:8000"
workers = 2
worker_class = "uvicorn.workers.UvicornWorker"
preload_app = True
timeout = 120
keepalive = 30
loglevel = "info"
# DC_OOM_GUARD_001 (Apr 2026): Recycle workers after N requests to prevent
# memory bloat from ORM object accumulation across many requests.
# DC_POOL_FORK_001 (May 2026): Raised from 300→500 — reduces recycling frequency
# so fewer in-flight uploads are aborted during worker changeover.
# DC_PROXY_STORAGE_001 (Jul 2026): Raised from 500→2000 — 25 req/s traffic was
# recycling workers every ~20s causing DC-PROXY-STORAGE socket hang-ups. At 2000
# requests the recycle window is ~80s, matching the connection keep-alive window.
max_requests = 2000
max_requests_jitter = 200

def post_fork(server, worker):
    # DC_WS_CAPACITY_001: Tag the first-born worker as the primary so APScheduler
    # only runs there.  worker.age is 1-based and increments monotonically; the
    # first worker forked always gets age == 1.
    os.environ["GUNICORN_CHILD_PROC"] = "0" if getattr(worker, "age", 1) == 1 else "1"

    # DC_POOL_FORK_001 (May 2026): Dispose SQLAlchemy connection pool after fork.
    # preload_app=True creates the SQLAlchemy engine in the master process before
    # workers are forked.  Without dispose(), each worker inherits the master's
    # open TCP sockets.  PostgreSQL connections cannot be shared across OS processes
    # — the sockets get duplicated and both master + worker try to use the same
    # connection, corrupting the protocol silently.
    # dispose() closes inherited sockets immediately; each worker then opens its
    # own fresh connections on the first request.  Officially recommended SQLAlchemy
    # pattern for preload_app gunicorn deployments.
    # On Neon (production): without this, 3×(pool_size+max_overflow) connections
    # can exceed Neon's 25-connection ceiling and cause the Replit pre-deploy diff
    # check to queue and time out waiting for a free slot.
    try:
        from app.core.database import engine
        engine.dispose()
        server.log.info(f"[DC-POOL-FORK] Worker {worker.pid}: engine disposed after fork ✅")
    except Exception as e:
        server.log.warning(f"[DC-POOL-FORK] Worker {worker.pid}: engine dispose failed: {e}")


def worker_exit(server, worker):
    # DC_POOL_EXIT_001 (May 2026): Dispose connection pool when a worker exits.
    # During graceful shutdown (SIGTERM before a new deploy), gunicorn stops
    # accepting new connections and drains in-flight requests, then calls
    # worker_exit for each worker.  Without this, the TCP sockets stay open
    # in TIME_WAIT until the OS clears them (~60s), holding Neon connection
    # slots and making the Replit pre-deploy diff check compete for scarce slots.
    # dispose() releases all pool connections immediately so the diff-check
    # (and the new deployment's workers) can connect without queuing.
    try:
        from app.core.database import engine
        engine.dispose()
        server.log.info(f"[DC-POOL-EXIT] Worker {worker.pid}: engine disposed on exit ✅")
    except Exception as e:
        server.log.warning(f"[DC-POOL-EXIT] Worker {worker.pid}: engine dispose on exit failed: {e}")
