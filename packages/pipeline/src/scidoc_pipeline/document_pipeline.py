from __future__ import annotations

import subprocess
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pymupdf as fitz
from scidoc_core.config import Settings
from scidoc_core.document import sanitize_filename, sha256_file, validate_pdf
from scidoc_database.models import Document, Element, Job, Page, ProcessingRun
from scidoc_database.repositories import DocumentRepository, JobRepository
from scidoc_engines.registry import EngineRegistry, default_registry
from scidoc_exporters.html import export_html
from scidoc_exporters.searchable_pdf import export_searchable_pdf
from scidoc_observability.logging import get_logger
from scidoc_routing.policy import RoutingPolicy
from scidoc_schema.models import DocumentInfo, ProcessingStats, SdrDocument, SdrPage
from scidoc_storage.local import LocalStorage
from scidoc_storage.paths import DocumentPaths
from sqlalchemy import delete
from sqlalchemy.orm import Session

from scidoc_pipeline.context import PipelineContext
from scidoc_pipeline.page_pipeline import PagePipeline

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class IngestResult:
    document_id: str
    job_id: str
    duplicate: bool


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def _git_commit() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True, timeout=2
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


class DocumentPipeline:
    def __init__(
        self,
        session: Session,
        settings: Settings,
        *,
        storage: LocalStorage | None = None,
        registry: EngineRegistry | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.storage = storage or LocalStorage(settings.storage_root)
        self.registry = registry or default_registry()

    def ingest(self, source: str | Path, *, original_filename: str | None = None) -> IngestResult:
        source_path = Path(source)
        page_count = validate_pdf(source_path)
        digest = sha256_file(source_path)
        documents = DocumentRepository(self.session)
        jobs = JobRepository(self.session)
        duplicate = documents.by_hash(digest)
        if duplicate:
            existing_job = jobs.latest_for_document(duplicate.id)
            configuration_changed = existing_job is None or existing_job.status not in {
                "queued",
                "running",
            }
            if configuration_changed and duplicate.sdr_path and Path(duplicate.sdr_path).exists():
                try:
                    stored_sdr = SdrDocument.model_validate_json(
                        Path(duplicate.sdr_path).read_bytes()
                    )
                    configuration_changed = stored_sdr.config_hash != self.settings.config_hash()
                except (OSError, ValueError):
                    configuration_changed = True
            if existing_job is None or configuration_changed:
                existing_job = Job(
                    id=_id("job"),
                    document_id=duplicate.id,
                    job_type="document_process",
                    pages_total=duplicate.page_count,
                )
                jobs.add(existing_job)
                self.session.commit()
            return IngestResult(duplicate.id, existing_job.id, True)

        document_id = _id("doc")
        paths = DocumentPaths(document_id)
        stored = self.storage.put(paths.original, source_path)
        document = Document(
            id=document_id,
            filename=sanitize_filename(original_filename or source_path.name),
            sha256=digest,
            page_count=page_count,
            status="queued",
            source_path=str(stored),
        )
        job = Job(
            id=_id("job"),
            document_id=document_id,
            job_type="document_process",
            status="queued",
            pages_total=page_count,
            stage="queued",
        )
        documents.add(document)
        jobs.add(job)
        self.session.commit()
        return IngestResult(document_id, job.id, False)

    def _persist_page(
        self, document: Document, sdr_page: SdrPage, result_path: str, rendered_path: str | None
    ) -> None:
        page_id = f"{document.id}-p{sdr_page.number}"
        page_row = self.session.get(Page, page_id)
        if page_row is None:
            page_row = Page(
                id=page_id,
                document_id=document.id,
                page_number=sdr_page.number,
                width=sdr_page.width,
                height=sdr_page.height,
            )
            self.session.add(page_row)
        page_row.width = sdr_page.width
        page_row.height = sdr_page.height
        page_row.classification = sdr_page.classification
        page_row.status = "completed"
        page_row.rendered_path = rendered_path
        page_row.result_path = result_path
        page_row.inspection = {
            **sdr_page.metrics.model_dump(mode="json"),
            "config_hash": self.settings.config_hash(),
        }
        self.session.execute(delete(Element).where(Element.page_id == page_id))
        self.session.flush()
        for item in sdr_page.elements:
            self.session.add(
                Element(
                    id=item.id,
                    page_id=page_id,
                    element_type=item.type.value,
                    bbox=list(item.bbox),
                    reading_order=item.reading_order,
                    content=item.content.model_dump(mode="json"),
                    confidence=item.confidence,
                    confidence_source=item.confidence_source,
                    provenance=item.provenance.model_dump(mode="json"),
                    review_status=item.review_status.value,
                    warnings=item.warnings,
                )
            )

    @staticmethod
    def _stats(pages: list[SdrPage], elapsed: float) -> ProcessingStats:
        elements = [element for page in pages for element in page.elements]
        methods = [element.provenance.method for element in elements]
        return ProcessingStats(
            pages_processed=len(pages),
            regions_processed=len(elements),
            native_elements=sum(method.startswith("native_pdf") for method in methods),
            ocr_elements=methods.count("ocr"),
            formula_elements=sum(
                method in {"formula_recognition", "formula_ocr_fallback"} for method in methods
            ),
            escalations=sum(len(element.content.candidates) > 1 for element in elements),
            high_dpi_retries=sum(len(element.provenance.history) > 0 for element in elements),
            cache_hits=sum(element.provenance.cache_hit for element in elements),
            cache_misses=sum(
                not element.provenance.cache_hit
                and not element.provenance.method.startswith("native_pdf")
                for element in elements
            ),
            failed_regions=sum(
                element.review_status.value == "engine_unavailable" for element in elements
            ),
            human_review_elements=sum(
                element.review_status.value in {"needs_review", "uncertain", "engine_unavailable"}
                for element in elements
            ),
            elapsed_seconds=elapsed,
        )

    def process(
        self, document_id: str, job_id: str, *, force_pages: set[int] | None = None
    ) -> SdrDocument:
        started_clock = time.perf_counter()
        document = self.session.get(Document, document_id)
        job = self.session.get(Job, job_id)
        if document is None or job is None:
            raise ValueError("document or job does not exist")
        if job.error:
            stored_errors = job.details.get("previous_errors", [])
            previous_errors = (
                [str(item) for item in stored_errors] if isinstance(stored_errors, list) else []
            )
            previous_errors.append(job.error)
            job.details = {**job.details, "previous_errors": previous_errors}
        job.error = None
        job.status = "running"
        job.stage = "inspecting document"
        job.started_at = datetime.now(UTC)
        job.attempts += 1
        document.status = "processing"
        run = ProcessingRun(
            id=_id("run"),
            document_id=document_id,
            pipeline_version=self.settings.pipeline_version,
            schema_version=self.settings.sdr_schema_version,
            git_commit=_git_commit(),
            config_hash=self.settings.config_hash(),
            model_versions=self.registry.versions(),
            started_at=datetime.now(UTC),
        )
        self.session.add(run)
        self.session.commit()
        paths = DocumentPaths(document_id)
        source = Path(document.source_path)
        page_results: list[SdrPage] = []
        context = PipelineContext(
            document_id=document_id,
            settings=self.settings,
            registry=self.registry,
            routing_policy=RoutingPolicy.from_settings(self.settings),
        )
        page_pipeline = PagePipeline(context, self.storage.resolve(paths.root))
        try:
            with fitz.open(source) as pdf:
                document.page_count = pdf.page_count
                job.pages_total = pdf.page_count
                for page_index, page in enumerate(pdf):
                    page_number = page_index + 1
                    result_key = paths.page_result(page_number)
                    row = self.session.get(Page, f"{document_id}-p{page_number}")
                    can_resume = (
                        row is not None
                        and row.status == "completed"
                        and row.inspection.get("config_hash") == self.settings.config_hash()
                        and self.storage.exists(result_key)
                        and (not force_pages or page_number not in force_pages)
                    )
                    if can_resume:
                        page_sdr = SdrPage.model_validate_json(self.storage.get(result_key))
                    else:
                        job.stage = f"processing page {page_number}"
                        page_sdr = page_pipeline.process(page)
                        self.storage.put(
                            result_key,
                            page_sdr.model_dump_json(indent=2).encode(),
                        )
                        rendered = next(
                            (
                                str(self.storage.resolve(paths.rendered_page(page_number, dpi)))
                                for dpi in (
                                    self.settings.default_dpi,
                                    self.settings.escalation_dpi,
                                    self.settings.max_dpi,
                                )
                                if self.storage.exists(paths.rendered_page(page_number, dpi))
                            ),
                            None,
                        )
                        self._persist_page(
                            document, page_sdr, str(self.storage.resolve(result_key)), rendered
                        )
                    page_results.append(page_sdr)
                    job.pages_completed = page_number
                    job.progress = page_number / pdf.page_count
                    self.session.commit()
                    logger.info(
                        "page_processed",
                        document_id=document_id,
                        page=page_number,
                        total_pages=pdf.page_count,
                        resumed=can_resume,
                    )

            job.stage = "aggregating SDR"
            stats = self._stats(page_results, time.perf_counter() - started_clock)
            sdr = SdrDocument(
                document=DocumentInfo(
                    id=document.id,
                    filename=document.filename,
                    sha256=document.sha256,
                    page_count=document.page_count,
                ),
                pages=page_results,
                processing=stats,
                pipeline_version=self.settings.pipeline_version,
                config_hash=self.settings.config_hash(),
                model_versions=self.registry.versions(),
            )
            self.storage.put(paths.sdr, sdr.model_dump_json(indent=2).encode())
            document.sdr_path = str(self.storage.resolve(paths.sdr))
            job.stage = "publishing accessible HTML"
            self.session.commit()
            export_html(sdr, self.storage.resolve(paths.export("html")))
            job.stage = "publishing selectable PDF"
            self.session.commit()
            export_searchable_pdf(
                sdr,
                document.source_path,
                self.storage.resolve(paths.export("pdf")),
            )
            document.status = "completed"
            job.status = "completed"
            job.stage = "completed"
            job.progress = 1.0
            job.completed_at = datetime.now(UTC)
            run.statistics = stats.model_dump(mode="json")
            run.completed_at = datetime.now(UTC)
            self.session.commit()
            return sdr
        except Exception as exc:
            document.status = "failed"
            job.status = "failed"
            job.stage = "failed"
            job.error = str(exc)
            job.completed_at = datetime.now(UTC)
            self.session.commit()
            logger.exception("document_processing_failed", document_id=document_id, job_id=job_id)
            raise

    def reprocess_page(self, document_id: str, page_number: int) -> str:
        document = self.session.get(Document, document_id)
        if document is None or page_number < 1 or page_number > document.page_count:
            raise ValueError("page does not exist")
        job = Job(
            id=_id("job"),
            document_id=document_id,
            job_type="page_reprocess",
            pages_total=document.page_count,
            details={"page_number": page_number},
        )
        self.session.add(job)
        self.session.commit()
        self.process(document_id, job.id, force_pages={page_number})
        return job.id
