import sys
import types

import pytest

from resume_tailorer.docx_export.converter import convert_docx_to_pdf, DocxConversionUnavailable


def test_raises_unavailable_when_docx2pdf_not_installed(monkeypatch):
    monkeypatch.setitem(sys.modules, "docx2pdf", None)
    with pytest.raises(DocxConversionUnavailable):
        convert_docx_to_pdf("in.docx", "out.pdf")


def test_raises_unavailable_when_convert_fails(monkeypatch):
    fake_module = types.SimpleNamespace(convert=lambda *a, **k: (_ for _ in ()).throw(RuntimeError("Word not found")))
    monkeypatch.setitem(sys.modules, "docx2pdf", fake_module)
    monkeypatch.setattr("resume_tailorer.docx_export.converter._RETRY_DELAY_SECONDS", 0)
    with pytest.raises(DocxConversionUnavailable):
        convert_docx_to_pdf("in.docx", "out.pdf")


def test_succeeds_when_convert_succeeds(monkeypatch):
    calls = []
    fake_module = types.SimpleNamespace(convert=lambda src, dst: calls.append((src, dst)))
    monkeypatch.setitem(sys.modules, "docx2pdf", fake_module)
    convert_docx_to_pdf("in.docx", "out.pdf")
    assert calls == [("in.docx", "out.pdf")]


def test_retries_once_after_transient_failure(monkeypatch):
    attempts = {"count": 0}

    def flaky_convert(src, dst):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise AttributeError("Open.SaveAs")

    fake_module = types.SimpleNamespace(convert=flaky_convert)
    monkeypatch.setitem(sys.modules, "docx2pdf", fake_module)
    monkeypatch.setattr("resume_tailorer.docx_export.converter._RETRY_DELAY_SECONDS", 0)
    convert_docx_to_pdf("in.docx", "out.pdf")
    assert attempts["count"] == 2
