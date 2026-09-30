import sys
import threading
import types

from resume_tailorer.docx_export import converter


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
