from concurrent.futures import Future, ThreadPoolExecutor, wait, FIRST_COMPLETED
from dataclasses import dataclass, field
import random
from queue import Queue
from threading import Lock, Thread
import time
from uuid import uuid4


@dataclass(frozen=True)
class WorkerConfig:
    max_concurrency: int = 1
    min_delay_seconds: float = 0.0
    max_delay_seconds: float = 0.0


class ProviderWorker:
    def __init__(self, name, config):
        self.name = name
        self.config = config
        self.queue = Queue()
        self.inflight = {}
        self.inflight_lock = Lock()
        self.threads = [
            Thread(target=self._run, name="%s-seat-worker-%s" % (name, index), daemon=True)
            for index in range(config.max_concurrency)
        ]
        for thread in self.threads:
            thread.start()

    def submit(self, key, task):
        with self.inflight_lock:
            if key in self.inflight:
                return self.inflight[key]
            future = Future()
            self.inflight[key] = future
            self.queue.put((key, future, task))
            return future

    def _run(self):
        while True:
            key, future, task = self.queue.get()
            try:
                if not future.set_running_or_notify_cancel():
                    continue
                future.set_result(task())
            except Exception as exc:
                future.set_exception(exc)
            finally:
                with self.inflight_lock:
                    self.inflight.pop(key, None)
                if self.config.max_delay_seconds:
                    time.sleep(random.uniform(self.config.min_delay_seconds, self.config.max_delay_seconds))
                self.queue.task_done()


@dataclass
class SearchJob:
    job_id: str
    status: str = "QUEUED"
    phase: str = "QUEUED"
    screenings: list = field(default_factory=list)
    completed: int = 0
    total: int = 0
    error: str = None
    catalogs: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.monotonic)


class SearchJobManager:
    JOB_TTL_SECONDS = 30 * 60
    MAX_JOBS = 50

    def __init__(self, search_service, worker_configs):
        self.search_service = search_service
        self.jobs = {}
        self.lock = Lock()
        self.provider_executor = ThreadPoolExecutor(max_workers=len(search_service.providers))
        self.job_executor = ThreadPoolExecutor(max_workers=4)
        self.workers = {
            name: ProviderWorker(name, worker_configs.get(name, WorkerConfig()))
            for name in search_service.providers
        }

    def submit(self, request):
        job = SearchJob(str(uuid4()))
        with self.lock:
            self._cleanup_locked()
            self.jobs[job.job_id] = job
        self.job_executor.submit(self._run, job, request)
        return job.job_id

    def get(self, job_id):
        with self.lock:
            self._cleanup_locked()
            job = self.jobs.get(job_id)
            if not job:
                return None
            return {
                "jobId": job.job_id,
                "status": job.status,
                "phase": job.phase,
                "completed": job.completed,
                "total": job.total,
                "screenings": list(job.screenings),
                "error": job.error,
                "catalogs": dict(job.catalogs),
            }

    def _cleanup_locked(self):
        now = time.monotonic()
        terminal = {"COMPLETED", "PARTIAL", "FAILED"}
        expired = [
            job_id for job_id, job in self.jobs.items()
            if job.status in terminal and now - job.created_at > self.JOB_TTL_SECONDS
        ]
        for job_id in expired:
            self.jobs.pop(job_id, None)

        if len(self.jobs) <= self.MAX_JOBS:
            return
        removable = sorted(
            (job for job in self.jobs.values() if job.status in terminal),
            key=lambda job: job.created_at,
        )
        for job in removable[:max(0, len(self.jobs) - self.MAX_JOBS)]:
            self.jobs.pop(job.job_id, None)

    def _run(self, job, request):
        try:
            self._update(job, status="PROCESSING", phase="FETCHING_SHOWTIMES")
            futures = {
                    self.provider_executor.submit(self.search_service._search_provider_details, provider, request): provider.name
                for provider in self.search_service.providers.values()
            }
            screenings = []
            for future in futures:
                try:
                    provider_screenings, catalog_titles = future.result()
                    screenings.extend(provider_screenings)
                    self._update(job, catalogs={**job.catalogs, futures[future].upper(): catalog_titles})
                except Exception:
                    continue

            candidates = self.search_service._select_candidates(screenings, request)
            for screening in candidates:
                screening.seat_status = "LOADING"
            self._update(job, phase="FETCHING_SEATS", screenings=candidates, total=len(candidates))

            tasks = {}
            for screening in candidates:
                worker = self.workers.get(screening.provider)
                if worker:
                    provider = self.search_service.providers[screening.provider]
                    if self.search_service.cached_layout(provider, screening.performance_id) is not None:
                        self._enrich(screening, request)
                        screening.seat_status = "READY" if screening.recommended_seats else "FAILED"
                        job.completed += 1
                        continue
                    key = (screening.provider, screening.performance_id)
                    future = worker.submit(key, lambda item=screening: self._enrich(item, request))
                    tasks.setdefault(future, []).append(screening)

            pending = set(tasks)
            while pending:
                done, pending = wait(pending, return_when=FIRST_COMPLETED)
                for future in done:
                    screenings_for_task = tasks[future]
                    try:
                        future.result()
                        source = screenings_for_task[0]
                        for screening in screenings_for_task:
                            if screening is not source:
                                screening.baseline_price = source.baseline_price
                                screening.seat_quality = source.seat_quality
                                screening.recommended_seats = list(source.recommended_seats)
                                screening.seat_layout = source.seat_layout
                            screening.seat_status = "READY" if screening.recommended_seats else "FAILED"
                    except Exception:
                        for screening in screenings_for_task:
                            screening.seat_status = "FAILED"
                    self._update(job, screenings=candidates, completed=job.completed + len(screenings_for_task))

            successful = [item for item in candidates if item.recommended_seats]
            final_status = "PARTIAL" if len(successful) < len(candidates) else "COMPLETED"
            self._update(job, status=final_status, phase="COMPLETED", screenings=successful)
        except Exception as exc:
            self._update(job, status="FAILED", phase="FAILED", error=str(exc))

    def _enrich(self, screening, request):
        self.search_service._enrich_screening(screening, request)

    def _update(self, job, **values):
        with self.lock:
            for key, value in values.items():
                setattr(job, key, value)
