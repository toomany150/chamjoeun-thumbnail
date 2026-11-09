import unittest
from naver_crawler import (
    extract_article_number, 
    parse_naver_clipboard_text, 
    format_thumb_price,
    format_premium_fee,
    normalize_approval_date,
    extract_maintenance_fee_and_detail
)

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
소재지: 부산광역시 사상구 덕포동 795
"""

# 네이버 상가 매물 복사 모의 텍스트 (줄바꿈 테이블 형태)
SAMPLE_COMMERCIAL_CLIPBOARD_TEXT = """
괘법동 1층 대로변 상가
월세 3,000 / 180만원
상가/점포 계약 125.00㎡ / 전용 82.64㎡ (전용률 66.1%)
해당층/총층
1/5층
방향: 남서향
월관리비
10만원
비목별 부과금액을 확인할 수 없어 미표기
권리금
무권리
현재상태
일반음식점 성업중
추천업종
카페, 디저트, 베이커리
준공년월
2018년 05월 20일
소재지
부산광역시 사상구 괘법동 567-8
주구조: 철근콘크리트구조
용도지역: 일반상업지역
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

    def test_parse_clipboard_residential(self):
        res = parse_naver_clipboard_text(SAMPLE_CLIPBOARD_TEXT)
        self.assertEqual(res.get("trade_type"), "매매")
        self.assertIn("6억 2,000", res.get("price_text", ""))
        self.assertEqual(res.get("area_supply"), "111.42")
        self.assertEqual(res.get("area_exclusive"), "79.85")
        self.assertEqual(res.get("floor_info"), "25 / 36층")
        self.assertEqual(res.get("room_bath"), "방 3 / 욕실 2개")
        self.assertEqual(res.get("direction"), "남동향 (거실 기준)")
        self.assertEqual(res.get("entrance_type"), "계단식")
        self.assertEqual(res.get("approval_date"), "2023년 07월 28일")
        self.assertTrue("부산광역시 사상구 덕포동 795" in res.get("location", ""))

    def test_parse_clipboard_commercial(self):
        res = parse_naver_clipboard_text(SAMPLE_COMMERCIAL_CLIPBOARD_TEXT)
        # 1. 소재지
        self.assertEqual(res.get("location"), "부산광역시 사상구 괘법동 567-8")
        # 2. 관리비 & 세부내역 (72% 아파트 추정치 없이 실제 상가 문구 유지)
        self.assertIn("10만", res.get("maintenance_fee", ""))
        self.assertIn("비목별 부과금액을 확인할 수 없어 미표기", res.get("maintenance_detail", ""))
        self.assertNotIn("약 7만 원", res.get("maintenance_detail", ""))
        # 3. 권리금
        self.assertEqual(res.get("premium_fee"), "무권리 (권리금 없음)")
        # 4. 현재업종 및 추천업종
        self.assertEqual(res.get("current_use"), "일반음식점 성업중")
        self.assertEqual(res.get("recommended_use"), "카페, 디저트, 베이커리")
        # 5. 사용승인일 (준공년월에서 변환)
        self.assertEqual(res.get("approval_date"), "2018년 05월 20일")
        # 부가 상가 항목
        self.assertEqual(res.get("structure"), "철근콘크리트구조")
        self.assertEqual(res.get("zone_region"), "일반상업지역")
        self.assertEqual(res.get("area_exclusive"), "82.64")
        self.assertEqual(res.get("area_supply"), "125.00")

    def test_format_premium_fee(self):
        self.assertEqual(format_premium_fee("무권리"), "무권리 (권리금 없음)")
        self.assertEqual(format_premium_fee("없음"), "무권리 (권리금 없음)")
        self.assertEqual(format_premium_fee("0"), "무권리 (권리금 없음)")
        self.assertEqual(format_premium_fee(0), "무권리 (권리금 없음)")
        self.assertEqual(format_premium_fee("협의"), "협의가능")
        self.assertEqual(format_premium_fee("3000"), "3,000만 원")
        self.assertEqual(format_premium_fee(5000), "5,000만 원")
        self.assertEqual(format_premium_fee("12000"), "1억 2,000만 원")
        self.assertEqual(format_premium_fee("3,000만원"), "3,000만 원")

    def test_normalize_approval_date(self):
        self.assertEqual(normalize_approval_date("2018년 5월 20일"), "2018년 05월 20일")
        self.assertEqual(normalize_approval_date("2018-05-20"), "2018년 05월 20일")
        self.assertEqual(normalize_approval_date("2018.05.20"), "2018년 05월 20일")
        self.assertEqual(normalize_approval_date("20180520"), "2018년 05월 20일")
        self.assertEqual(normalize_approval_date("2018년 5월"), "2018년 05월")
        self.assertEqual(normalize_approval_date("2018.05"), "2018년 05월")
        self.assertEqual(normalize_approval_date("2018"), "2018년")

    def test_commercial_maintenance_detail(self):
        # 상가 관리비 없음
        fee, det = extract_maintenance_fee_and_detail(raw_fee="없음", is_commercial=True)
        self.assertIn("정액관리비 없음", det)

        # 상가 10만원 정액관리비 (비목별 미표기)
        fee2, det2 = extract_maintenance_fee_and_detail(raw_fee="10만원", is_commercial=True)
        self.assertIn("비목별 부과금액 미표기", det2)
        self.assertNotIn("약 7만", det2)

    def test_crawl_article_rejects_bogus_shell(self):
        from naver_crawler import crawl_naver_article
        # 존재하지 않거나 만료된 번호로 크롤링 시 쓰레기 데이터가 아닌 False와 빈 dict 반환 검증
        is_ok, msg, data = crawl_naver_article("9999999999")
        self.assertFalse(is_ok)
        self.assertEqual(data, {})
        self.assertNotIn("Npay", data.get("location", ""))
        self.assertNotIn("확인해보세요", data.get("main_title", ""))

if __name__ == "__main__":
    unittest.main()
