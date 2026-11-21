"""Kiểm thử cơ bản. Chạy:  python -m unittest discover -s tests"""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vn_plagiarism import (PlagiarismDetector, containment_ngram, jaccard_ngram, load_corpus_dir,  # noqa: E402
                           normalize, split_sentences, winnowing_similarity)


class TestUtils(unittest.TestCase):
    def test_normalize_unicode(self):
        tohop = "a" + chr(0x0323) + chr(0x0302)   # a + dấu nặng + dấu mũ (dạng tổ hợp)
        dung_san = chr(0x1EAD)                     # ậ dựng sẵn
        self.assertNotEqual(tohop, dung_san)
        self.assertEqual(normalize("c" + tohop), normalize("c" + dung_san))

    def test_normalize_punct(self):
        self.assertEqual(normalize("Xin chào, thế giới! 123"), "xin chào thế giới")

    def test_split_sentences(self):
        self.assertEqual(len(split_sentences("Đây là câu thứ nhất. Đây là câu thứ hai! Ok.")), 2)

    def test_similarity_bounds(self):
        t = "học máy là nhánh của trí tuệ nhân tạo".split()
        self.assertAlmostEqual(jaccard_ngram(t, t), 1.0)
        self.assertAlmostEqual(containment_ngram(t, t), 1.0)
        self.assertAlmostEqual(winnowing_similarity(t, t), 1.0)
        self.assertEqual(containment_ngram(t, ["một", "hai", "ba", "bốn"]), 0.0)


class TestDetector(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = load_corpus_dir(ROOT / "data" / "corpus")
        cls.det = PlagiarismDetector(sentence_threshold=0.5).fit(cls.corpus)

    def test_corpus_loaded(self):
        self.assertGreaterEqual(len(self.corpus), 10)

    def test_verbatim_copy_is_flagged(self):
        text = self.corpus["04_bong_da"]
        rep = self.det.check(text)
        self.assertGreaterEqual(rep.overall_score, 0.7)
        self.assertEqual(rep.per_document[0].source_id, "04_bong_da")

    def test_clean_text_not_flagged(self):
        text = (ROOT / "data" / "independent" / "u05_toan_hoc.txt").read_text(encoding="utf-8")
        self.assertLess(self.det.check(text).overall_score, 0.2)

    def test_sentence_level_finds_source(self):
        src = self.corpus["06_am_thuc_pho"].split(". ")[1] + "."
        rep = self.det.check("Hôm nay trời đẹp và tôi đi dạo. " + src + " Tôi về nhà nghỉ ngơi sớm.")
        self.assertTrue(any(m.source_id == "06_am_thuc_pho" for m in rep.matches))


if __name__ == "__main__":
    unittest.main()
