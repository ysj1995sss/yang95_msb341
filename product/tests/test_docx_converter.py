import os
import sys
import threading
import types

import pytest

from resume_tailorer.docx_export import converter


@pytest.fixture(autouse=True)
def _word_machine(monkeypatch):
    """These tests describe a Windows/macOS machine with Word and no LibreOffice."""
    monkeypatch.setattr(converter, "_word_platform", lambda: True)
    monkeypatch.setattr(converter, "_soffice", lambda: None)


def _fake_modules(monkeypatch, convert):
    events = []
    pythoncom = types.SimpleNamespace(
        CoInitialize=lambda: events.append("init"), CoUninitialize=lambda: events.append("uninit")
    )
    docx2pdf = types.SimpleNamespace(convert=lambda src, dst: (events.append("convert"), convert(src, dst)))
    monkeypatch.setitem(sys.modules, "pythoncom", pythoncom)
    monkeypatch.setitem(sys.modules, "docx2pdf", docx2pdf)
    return events


def test_com_is_initialized_around_each_conversion_and_released(monkeypatch):
    events = _fake_modules(monkeypatch, lambda src, dst: None)
    converter.convert_docx_to_pdf("a.docx", "a.pdf")
    assert events == ["init", "convert", "uninit"]


def test_com_is_released_even_when_word_fails(monkeypatch):
    monkeypatch.setattr(converter, "_RETRY_DELAY_SECONDS", 0)

    def boom(src, dst):
        raise RuntimeError("Word crashed")

    events = _fake_modules(monkeypatch, boom)
    try:
        converter.convert_docx_to_pdf("a.docx", "a.pdf")
        raised = False
    except converter.DocxConversionUnavailable:
        raised = True
    assert raised and events[0] == "init" and events[-1] == "uninit"


def test_conversion_from_a_worker_thread_initializes_that_thread(monkeypatch):
    events = _fake_modules(monkeypatch, lambda src, dst: None)
    worker = threading.Thread(target=converter.convert_docx_to_pdf, args=("a.docx", "a.pdf"))
    worker.start()
    worker.join()
    assert events == ["init", "convert", "uninit"]


def test_machines_without_pywin32_still_convert(monkeypatch):
    events = []
    monkeypatch.setitem(sys.modules, "pythoncom", None)  # import raises ImportError
    monkeypatch.setitem(sys.modules, "docx2pdf", types.SimpleNamespace(convert=lambda s, d: events.append("convert")))
    converter.convert_docx_to_pdf("a.docx", "a.pdf")
    assert events == ["convert"]


def _fake_soffice(monkeypatch, calls, produce=True):
    def run(command, **kwargs):
        calls.append(command)
        if produce:
            out_dir = command[command.index("--outdir") + 1]
            os.makedirs(out_dir, exist_ok=True)
            with open(os.path.join(out_dir, "resume.pdf"), "wb") as f:
                f.write(b"%PDF-1.4 from libreoffice")
        return types.SimpleNamespace(returncode=0 if produce else 1, stdout="", stderr="" if produce else "boom")

    monkeypatch.setattr(converter.subprocess, "run", run)
    monkeypatch.setattr(converter, "_soffice", lambda: "/usr/bin/soffice")


def test_linux_converts_with_libreoffice(monkeypatch, tmp_path):
    monkeypatch.setattr(converter, "_word_platform", lambda: False)
    calls = []
    _fake_soffice(monkeypatch, calls)
    converter.convert_docx_to_pdf(str(tmp_path / "resume.docx"), str(tmp_path / "resume.pdf"))
    assert (tmp_path / "resume.pdf").read_bytes() == b"%PDF-1.4 from libreoffice"
    command = calls[0]
    assert command[:2] == ["/usr/bin/soffice", "--headless"] and "--convert-to" in command
    assert any(arg.startswith("-env:UserInstallation=file:") for arg in command)  # private profile


def test_word_failure_falls_back_to_libreoffice(monkeypatch, tmp_path):
    monkeypatch.setattr(converter, "_RETRY_DELAY_SECONDS", 0)
    _fake_modules(monkeypatch, lambda src, dst: (_ for _ in ()).throw(RuntimeError("Word crashed")))
    calls = []
    _fake_soffice(monkeypatch, calls)
    converter.convert_docx_to_pdf(str(tmp_path / "resume.docx"), str(tmp_path / "resume.pdf"))
    assert calls and (tmp_path / "resume.pdf").exists()


def test_libreoffice_failure_is_reported_not_crashed(monkeypatch, tmp_path):
    monkeypatch.setattr(converter, "_word_platform", lambda: False)
    _fake_soffice(monkeypatch, [], produce=False)
    with pytest.raises(converter.DocxConversionUnavailable, match="boom"):
        converter.convert_docx_to_pdf(str(tmp_path / "resume.docx"), str(tmp_path / "resume.pdf"))


def test_no_converter_at_all_says_what_to_install(monkeypatch):
    monkeypatch.setattr(converter, "_word_platform", lambda: False)
    with pytest.raises(converter.DocxConversionUnavailable, match="LibreOffice"):
        converter.convert_docx_to_pdf("a.docx", "a.pdf")
