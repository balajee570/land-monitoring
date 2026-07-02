"""Parser tests built from the actual decoded text of a real Bihar Bhumi LPC.

The fixture below is the (jumbled, multi-column) text our stdlib extractor
recovers from the sample document, so these tests exercise the parser against
realistic — not idealised — input.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jamabandi.parser import (  # noqa: E402
    normalize, parse_jamabandi, _rakba_to_hectare, JamabandiRecord,
)

SAMPLE = (
    "Ownership Document Samastipur Rosera Rosera मो० मो 69 बिहार राजस "
    "Acknowledgement Receipt भूमि 18-Jun-2026 . Your Application has been "
    "Submitted Successfully.Your Application Number is 106/2026 - 2027 "
    "Applicant Details: Applicant Balajee Venkatesh Father Sri Ranjan Kumar "
    "Thakur Relation : Father Case : 106/2026 - 2027 "
    "District : Bihar District : Samastpur State : Bihar PI 848210 "
    "Email Id : balajee.venkatesh9570@gmail.com Mobile 9503020511 "
    "Aadhar XXXX-XXXX-7814 Purpose of LPC: जमाबंदी भाग 151 पृष 1 जिला अनुमंडल "
    "अचंल हलका मौजा थाना जमाबंदी बालाजी ठाकुर जाति भूमि खाता पोट रकबा चौहदी "
    "389 2049 1 ए 53.42 डि 0 हे कमरकांत रंजन खुशी विसमर "
    "2116 0 ए 12 डि 0 हे शशिकांत रंजन रामदेव "
    "980 0 ए 13.42 डि 0 हे सडक नीज रंजन मनोज "
    "2023- 2024 2025- 2026 680 340 170 अंचलाधिकारी मे नही किया"
)


class TestNormalize(unittest.TestCase):
    def test_devanagari_digits(self):
        self.assertEqual(normalize("खाता १२३"), "खाता 123")

    def test_whitespace_collapse(self):
        self.assertEqual(normalize("a    b\tc"), "a b c")


class TestAreaConversion(unittest.TestCase):
    def test_decimal_to_hectare(self):
        # 53.42 decimal ~= 0.2162 ha (1 decimal = 0.00404686 ha)
        ha = _rakba_to_hectare(1.0, 53.42, 0.0)
        self.assertAlmostEqual(ha, 0.62087, places=4)

    def test_zero(self):
        self.assertIsNone(_rakba_to_hectare(0, 0, 0))


class TestParseSample(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rec = parse_jamabandi(SAMPLE)

    def test_returns_record(self):
        self.assertIsInstance(self.rec, JamabandiRecord)

    def test_jamabandi_number(self):
        self.assertEqual(self.rec.jamabandi_no, "106/2026 - 2027")

    def test_part_number(self):
        self.assertEqual(self.rec.part_no, "151")

    def test_state(self):
        self.assertEqual(self.rec.state, "Bihar")

    def test_district_is_not_state(self):
        # Must skip "District : Bihar" and pick the real district
        self.assertEqual(self.rec.district, "Samastpur")

    def test_plots_extracted(self):
        self.assertGreaterEqual(len(self.rec.plots), 3)
        khesras = {p.khesra_no for p in self.rec.plots}
        self.assertIn("2049", khesras)
        self.assertIn("2116", khesras)

    def test_plot_area_computed(self):
        p = next(p for p in self.rec.plots if p.khesra_no == "2049")
        self.assertAlmostEqual(p.rakba_hectare, 0.62087, places=4)

    def test_total_hectare(self):
        self.assertGreater(self.rec.total_hectare(), 0)

    def test_applicant(self):
        a = self.rec.applicant
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "Balajee Venkatesh")
        self.assertEqual(a.mobile, "9503020511")
        self.assertEqual(a.email, "balajee.venkatesh9570@gmail.com")
        self.assertEqual(a.aadhaar, "XXXX-XXXX-7814")

    def test_location_query_no_labels(self):
        q = self.rec.location_query()
        self.assertIn("Samastpur", q)
        self.assertIn("India", q)
        # must not leak column-header words
        for bad in ("जमाबंदी", "हलका", "थाना", "जाति"):
            self.assertNotIn(bad, q)

    def test_owners_no_stopwords(self):
        for name in self.rec.owners:
            for bad in ("जमाबंदी", "रैयत", "विवरण", "संखा", "नाम"):
                self.assertNotIn(bad, name)

    def test_dues_years(self):
        years = {d.year for d in self.rec.dues}
        self.assertIn("2023-2024", years)


class TestEmptyAndGarbage(unittest.TestCase):
    def test_empty(self):
        rec = parse_jamabandi("")
        self.assertIsInstance(rec, JamabandiRecord)
        self.assertEqual(rec.plots, [])

    def test_non_jamabandi_text(self):
        rec = parse_jamabandi("hello world this is not a land record")
        self.assertIsInstance(rec, JamabandiRecord)
        self.assertEqual(rec.raw_text, "hello world this is not a land record")


if __name__ == "__main__":
    unittest.main(verbosity=2)
