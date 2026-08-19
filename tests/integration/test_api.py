from pathlib import Path

import pymupdf as fitz
from fastapi.testclient import TestClient
from scidoc_api.main import create_app
from scidoc_core.config import Settings


def test_upload_read_job_and_sdr(tiny_pdf: Path, tmp_path: Path) -> None:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'api.db'}",
        storage_root=tmp_path / "data",
        queue_mode="synchronous",
        narration_provider="openai",
    )
    with TestClient(create_app(settings)) as client:
        with tiny_pdf.open("rb") as handle:
            response = client.post(
                "/api/documents", files={"file": ("science.pdf", handle, "application/pdf")}
            )
        assert response.status_code == 202, response.text
        payload = response.json()
        document = client.get(f"/api/documents/{payload['document_id']}")
        assert document.status_code == 200
        assert document.json()["status"] == "completed"
        job = client.get(f"/api/jobs/{payload['job_id']}")
        assert job.json()["status"] == "completed"
        sdr = client.get(f"/api/documents/{payload['document_id']}/sdr")
        assert sdr.status_code == 200
        assert sdr.json()["pages"][0]["elements"]
        page = client.get(f"/api/documents/{payload['document_id']}/pages/1")
        assert page.status_code == 200
        accessible_html = client.get(f"/api/documents/{payload['document_id']}/exports/html")
        assert accessible_html.status_code == 200
        assert accessible_html.headers["content-type"].startswith("text/html")
        assert "inline" in accessible_html.headers["content-disposition"]
        assert '<main id="main-content">' in accessible_html.text
        assert "Accessible document export" in accessible_html.text
        selectable_pdf = client.get(f"/api/documents/{payload['document_id']}/exports/pdf")
        assert selectable_pdf.status_code == 200
        assert selectable_pdf.headers["content-type"] == "application/pdf"
        assert "inline" in selectable_pdf.headers["content-disposition"]
        with fitz.open(stream=selectable_pdf.content, filetype="pdf") as exported:
            assert "Scientific document" in exported[0].get_text()
        narration = client.post(
            f"/api/documents/{payload['document_id']}/narration",
            json={"page_number": 1, "voice": "marin"},
        )
        assert narration.status_code == 503
        assert "OpenAI key" in narration.json()["detail"]


def test_rejects_non_pdf(tmp_path: Path) -> None:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'bad.db'}",
        storage_root=tmp_path / "data",
        queue_mode="synchronous",
    )
    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/documents", files={"file": ("bad.pdf", b"not a PDF", "application/pdf")}
        )
        assert response.status_code == 422


def test_reports_truthful_runtime_capabilities(tmp_path: Path) -> None:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'capabilities.db'}",
        storage_root=tmp_path / "data",
        queue_mode="synchronous",
        narration_provider="openai",
    )
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/capabilities")
        assert response.status_code == 200
        payload = response.json()
        assert payload["processing_mode"] == "local-first"
        assert payload["deterministic_core"] is True
        assert payload["llm_in_evidence_path"] is False
        assert payload["feature_flags"]["tables"] is True
        assert any(engine["name"] == "lightweight_ocr" for engine in payload["engines"])
        narration = client.get("/api/narration/capabilities")
        assert narration.status_code == 200
        assert narration.json()["configured"] is False
        assert narration.json()["default_voice"] == "marin"
        assert narration.json()["ai_generated"] is False


def test_generates_and_caches_neural_narration(tiny_pdf: Path, tmp_path: Path, monkeypatch) -> None:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'narration.db'}",
        storage_root=tmp_path / "data",
        queue_mode="synchronous",
        narration_provider="openai",
        narration_api_key="test-api-key",
    )
    calls: list[tuple[str, str]] = []

    async def fake_synthesis(script: str, *, voice: str, settings: Settings) -> bytes:
        calls.append((script, voice))
        from scidoc_api.neural_voice import pcm_to_wav

        return pcm_to_wav(b"\x00\x00" * 240)

    monkeypatch.setattr("scidoc_api.routes.narration.synthesize_narration_wav", fake_synthesis)
    with TestClient(create_app(settings)) as client:
        with tiny_pdf.open("rb") as handle:
            upload = client.post(
                "/api/documents", files={"file": ("science.pdf", handle, "application/pdf")}
            )
        document_id = upload.json()["document_id"]
        for expected_cache in ("miss", "hit"):
            response = client.post(
                f"/api/documents/{document_id}/narration",
                json={"page_number": 1, "voice": "cedar"},
            )
            assert response.status_code == 200, response.text
            assert response.headers["content-type"] == "audio/wav"
            assert response.headers["x-scidoc-ai-generated"] == "true"
            assert response.headers["x-scidoc-narration-cache"] == expected_cache
            assert response.content.startswith(b"RIFF")

    assert len(calls) == 1
    assert "Scientific document intelligence" in calls[0][0]
    assert calls[0][1] == "cedar"
