"""tools/datasheet.py without the network: picking the part, the PDF links, and page numbers."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import datasheet as D  # noqa: E402

TEXT = """cover
=====PAGE 1=====
TMC2209 DATASHEET
=====PAGE 2=====
MSCNT counts the microsteps
nothing here
=====PAGE 3=====
ENN high: outputs off
MSCNT again""".splitlines()


def test_grep_gives_the_pdf_page_of_each_hit():
    assert D.grep(TEXT, "mscnt") == ["p2   : MSCNT counts the microsteps", "p3   : MSCNT again"]
    assert D.grep(TEXT, "cover") == ["p0   : cover"]           # before any page marker
    assert D.grep(TEXT, "absent") == []


def test_grep_context_marks_hits_and_merges_overlaps():
    out = D.grep(TEXT, "ENN", context=1)
    assert out == ["p2   - nothing here", "p3   : ENN high: outputs off", "p3   - MSCNT again"]


def test_page_text():
    assert D.page_text(TEXT, 2) == "MSCNT counts the microsteps\nnothing here"


def test_pick_prefers_the_exact_code_then_the_exact_part_then_stock():
    rows = [dict(componentCode="C1", componentModelEn="TMC2209-BOB", stockCount=0),
            dict(componentCode="C2150710", componentModelEn="TMC2209-LA-T", stockCount=25000),
            dict(componentCode="C3", componentModelEn="TMC2209", stockCount=5)]
    assert D.pick("c2150710", rows)["componentCode"] == "C2150710"
    assert D.pick("TMC2209", rows)["componentCode"] == "C3"
    assert D.pick("tmc22", rows)["componentCode"] == "C2150710"


def test_pdf_links_try_the_signed_one_then_lcscs_pdf_host():
    rec = dict(componentCode="C2150710", componentModelEn="TMC2209-LA-T",
               dataManualFileAccessIdUrl="https://jlc-prod-smt.example/x.pdf?sig=1",
               dataManualUrl="https://www.lcsc.com/datasheet/lcsc_datasheet_2202031830_TMC2209-LA-T_C2150710.pdf")
    u = D.pdf_urls(rec)
    assert u[0].startswith("https://jlc-prod-smt.example/")
    assert u[1] == "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2202031830_TMC2209-LA-T_C2150710.pdf"
    assert D.safe_name(rec) == "C2150710-TMC2209-LA-T"
