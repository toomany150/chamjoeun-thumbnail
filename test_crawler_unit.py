import unittest
from naver_crawler import extract_article_number, parse_naver_clipboard_text, format_thumb_price

SAMPLE_CLIPBOARD_TEXT = """
사상 중흥S-클래스 그랜드센트럴 105동
매매 6억 2,000만원
아파트 공급 111.42㎡ / 전용 79.85㎡ (전용률 72%)
해당층/총층: 25/36층
방수/욕실수: 3/2개
방향: 남동향 (거실 기준)
현관구조: 계단식
난방(방식/연료): 개별난방 / 도시가스
입주가능일: 즉시입주 협의가능
월관리비: 18만원
총주차대수: 1,685대 (세대당 1.07대)
해당면적 세대수: 331세대 (총 1,572세대)
건축물 용도: 공동주택 (아파트)
사용승인일: 2023.07.28
소재지: 부산광역시 사상구 덕포동 220
"""

class TestNaverCrawler(unittest.TestCase):
    def test_extract_article_number(self):
        self.assertEqual(extract_article_number("2452358814"), "2452358814")
        self.assertEqual(extract_article_number("https://fin.land.naver.com/articles/2452358814"), "2452358814")
        self.assertEqual(extract_article_number("https://m.land.naver.com/article/info/2452358814?type=apt"), "2452358814")
        self.assertEqual(extract_article_number("https://land.naver.com/article/articleDetailInfo.nhn?atclNo=2452358814"), "2452358814")

    def test_format_thumb_price(self):
        self.assertEqual(format_thumb_price("6억 2,000만 원"), "6억2천")
        self.assertEqual(format_thumb_price("2억 4,000만 원"), "2억4천")

    def test_parse_clipboard(self):
        res = parse_naver_clipboard_text(SAMPLE_CLIPBOARD_TEXT)
        self.assertEqual(res.get("trade_type"), "매매")
        self.assertIn("6억 2,000", res.get("price_text", ""))
        self.assertEqual(res.get("area_supply"), "111.42")
        self.assertEqual(res.get("area_exclusive"), "79.85")
        self.assertEqual(res.get("floor_info"), "25 / 36층")
        self.assertEqual(res.get("room_bath"), "방 3 / 욕실 2개")
        self.assertEqual(res.get("direction"), "남동향 (거실 기준)")
        self.assertEqual(res.get("entrance_type"), "계단식")
        self.assertEqual(res.get("approval_date"), "2023.07.28")
        self.assertEqual(res.get("location"), "부산광역시 사상구 덕포동 220")

if __name__ == "__main__":
    unittest.main()
