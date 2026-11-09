import unittest
from unittest.mock import patch, MagicMock
from naver_crawler import crawl_naver_article

MOCK_NAVER_COMMERCIAL_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Npay 부동산 : 괘법동 상가 1층</title>
<meta property="og:title" content="상가 월세 3,000/180">
<meta property="og:description" content="부산시 사상구 괘법동 상가 임대">
</head>
<body>
<div class="article_detail">
    <div class="table_row">
        <div class="item_term __term">소재지</div>
        <div class="item_definition __definition">부산광역시 사상구 괘법동 123-45</div>
    </div>
    <div class="table_row">
        <div class="item_term __term">보증금/월세</div>
        <div class="item_definition __definition">3,000/180만원</div>
    </div>
    <div class="table_row">
        <div class="item_term __term">계약/전용면적</div>
        <div class="item_definition __definition">125.00㎡ / 82.64㎡</div>
    </div>
    <div class="table_row">
        <div class="item_term __term">해당층/총층</div>
        <div class="item_definition __definition">1층 / 5층</div>
    </div>
    <div class="table_row">
        <div class="item_term __term">월관리비</div>
        <div class="item_definition __definition">10만원</div>
    </div>
    <div class="table_row">
        <div class="item_term __term">비목별 부과금액</div>
        <div class="item_definition __definition">비목별 부과금액을 확인할 수 없어 미표기</div>
    </div>
    <div class="table_row">
        <div class="item_term __term">권리금</div>
        <div class="item_definition __definition">3,000만원</div>
    </div>
    <div class="table_row">
        <div class="item_term __term">현재업종</div>
        <div class="item_definition __definition">공실 (즉시입주 가능)</div>
    </div>
    <div class="table_row">
        <div class="item_term __term">추천업종</div>
        <div class="item_definition __definition">카페, 디저트, 베이커리</div>
    </div>
    <div class="table_row">
        <div class="item_term __term">준공년월</div>
        <div class="item_definition __definition">2018년 05월 20일</div>
    </div>
    <div class="table_row">
        <div class="item_term __term">건축물용도</div>
        <div class="item_definition __definition">제1종 근린생활시설</div>
    </div>
    <div class="table_row">
        <div class="item_term __term">주구조</div>
        <div class="item_definition __definition">철근콘크리트구조</div>
    </div>
    <div class="table_row">
        <div class="item_term __term">용도지역</div>
        <div class="item_definition __definition">일반상업지역</div>
    </div>
</div>
</body>
</html>
"""

class TestCommercialCrawler(unittest.TestCase):
    @patch("naver_crawler.requests.get")
    def test_crawl_commercial_article(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = MOCK_NAVER_COMMERCIAL_HTML
        mock_get.return_value = mock_resp

        success, msg, data = crawl_naver_article("2499999999")
        self.assertTrue(success)

        # 1. 소재지
        self.assertEqual(data.get("location"), "부산광역시 사상구 괘법동 123-45")

        # 2. 관리비 및 세부내역
        self.assertIn("10만", data.get("maintenance_fee", ""))
        self.assertEqual(data.get("maintenance_detail"), "비목별 부과금액을 확인할 수 없어 미표기")

        # 3. 권리금
        self.assertEqual(data.get("premium_fee"), "3,000만 원")

        # 4. 현재상태 / 추천업종
        self.assertEqual(data.get("current_use"), "공실 (즉시입주 가능)")
        self.assertEqual(data.get("recommended_use"), "카페, 디저트, 베이커리")

        # 5. 사용승인일 (준공년월에서 추출 및 정규화)
        self.assertEqual(data.get("approval_date"), "2018년 05월 20일")

        # 상가 필수 스펙 검증
        self.assertEqual(data.get("area_supply"), "125.00")
        self.assertEqual(data.get("area_exclusive"), "82.64")
        self.assertEqual(data.get("building_use"), "제1종 근린생활시설")
        self.assertEqual(data.get("structure"), "철근콘크리트구조")
        self.assertEqual(data.get("zone_region"), "일반상업지역")

if __name__ == "__main__":
    unittest.main()

