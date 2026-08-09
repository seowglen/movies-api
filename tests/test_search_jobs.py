import threading
import time

from engine.search_jobs import ProviderWorker, WorkerConfig


def test_provider_worker_deduplicates_concurrent_performance_requests():
    worker = ProviderWorker("gv-test", WorkerConfig(max_concurrency=1))
    calls = []
    barrier = threading.Barrier(2)

    def task():
        calls.append("called")
        time.sleep(0.05)
        return "layout"

    def submit():
        barrier.wait()
        return worker.submit(("gv", "performance-1"), task)

    results = []
    threads = [threading.Thread(target=lambda: results.append(submit())) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    for future in results:
        assert future.result() == "layout"

    assert len(calls) == 1
