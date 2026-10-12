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
    # The docx2pdf path is what these older tests describe; spec 020's private Word is tested below.
    monkeypatch.setattr(converter, "_private_word_available", lambda: False)


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


# --- Spec 020: a conversion owns its own Word instance (Windows) ------------------------------

class _FakeDoc:
    def __init__(self, log, export_error=None, close_error=None):
        self.log, self.export_error, self.close_error = log, export_error, close_error

    def ExportAsFixedFormat(self, path, fmt):
        self.log.append(("export", path, fmt))
        if self.export_error:
            raise self.export_error

    def Close(self, SaveChanges=None):
        self.log.append(("close", SaveChanges))
        if self.close_error:
            raise self.close_error


class _FakeWord:
    def __init__(self, log, doc):
        self.log, self.doc = log, doc
        self.Visible = True
        self.DisplayAlerts = 1
        self.Documents = self

    def Open(self, path, ReadOnly=None, AddToRecentFiles=None, ConfirmConversions=None):
        self.log.append(("open", ReadOnly, AddToRecentFiles, ConfirmConversions))
        return self.doc

    def Quit(self, SaveChanges=None):
        self.log.append(("quit", SaveChanges))


def _private_word(monkeypatch, doc_factory):
    """Only DispatchEx exists on the fake: attaching to a running Word would be an AttributeError."""
    log = []
    created = []

    def dispatch_ex(name):
        assert name == "Word.Application"
        word = _FakeWord(log, doc_factory(log))
        created.append(word)
        return word

    monkeypatch.setattr(converter, "_private_word_available", lambda: True)
    monkeypatch.setattr(converter, "_RETRY_DELAY_SECONDS", 0)
    monkeypatch.setitem(sys.modules, "pythoncom", types.SimpleNamespace(
        CoInitialize=lambda: log.append("init"), CoUninitialize=lambda: log.append("uninit")))
    monkeypatch.setitem(sys.modules, "win32com", types.SimpleNamespace(client=types.SimpleNamespace(DispatchEx=dispatch_ex)))
    monkeypatch.setitem(sys.modules, "win32com.client", sys.modules["win32com"].client)
    return log, created


def test_private_word_opens_read_only_hidden_exports_and_closes_only_its_own(monkeypatch):
    log, created = _private_word(monkeypatch, lambda log: _FakeDoc(log))
    converter.convert_docx_to_pdf("a.docx", "a.pdf")
    assert len(created) == 1 and created[0].Visible is False and created[0].DisplayAlerts == 0
    kinds = [e if isinstance(e, str) else e[0] for e in log]
    assert kinds == ["init", "open", "export", "close", "quit", "uninit"]
    assert ("open", True, False, False) in log and ("close", 0) in log and ("quit", 0) in log
    assert any(e[0] == "export" and e[2] == 17 for e in log if not isinstance(e, str))


def test_private_word_closes_and_quits_even_when_export_fails(monkeypatch):
    log, created = _private_word(monkeypatch, lambda log: _FakeDoc(log, export_error=RuntimeError("export broke")))
    with pytest.raises(converter.DocxConversionUnavailable, match="export broke"):
        converter.convert_docx_to_pdf("a.docx", "a.pdf")
    assert len(created) == 2  # one retry, each with a fresh private instance
    kinds = [e if isinstance(e, str) else e[0] for e in log]
    assert kinds.count("close") == 2 and kinds.count("quit") == 2 and kinds[-1] == "uninit"


def test_a_close_failure_is_reported_not_swallowed(monkeypatch):
    log, _ = _private_word(monkeypatch, lambda log: _FakeDoc(log, close_error=RuntimeError("document still locked")))
    with pytest.raises(converter.DocxConversionUnavailable, match="document still locked"):
        converter.convert_docx_to_pdf("a.docx", "a.pdf")
    assert ("quit", 0) in log  # Word still shut down after the failed close


def test_private_word_never_attaches_to_a_running_word(monkeypatch):
    _private_word(monkeypatch, lambda log: _FakeDoc(log))
    client = sys.modules["win32com.client"]
    assert not hasattr(client, "Dispatch") and not hasattr(client, "GetActiveObject")
    converter.convert_docx_to_pdf("a.docx", "a.pdf")
