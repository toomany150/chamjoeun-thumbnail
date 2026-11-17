import unittest
from document_parser import (
    parse_building_register_title,
    parse_building_register_exclusive,
    merge_building_registers,
    merge_building_and_land_documents,
    parse_land_use_plan,
    parse_raw_script_document,
    identify_document_type
)

# 정부24 / 세움터 표제부 모의 텍스트
SAMPLE_TITLE_TEXT = """
[총괄표제부] (집합건축물대장)
대지위치: 부산광역시 사상구 덕포동 795
지번: 795
도로명주소: 부산광역시 사상구 사상로 300
건축물명칭: 사상 중흥S-클래스 그랜드센트럴
동명칭: 제105동
주용도: 공동주택
구조: 철근콘크리트구조
층수: 지상 36층 / 지하 3층
세대수: 1,572세대
주차장: 옥내자주식 1,685대 총 1,685대
허가일: 2020-03-10
착공일: 2020-04-15
사용승인일: 2023-07-28
"""

# 정부24 / 세움터 전유부 모의 텍스트
SAMPLE_EXCLUSIVE_TEXT = """
[전유부] (집합건축물대장)
대지위치: 부산광역시 사상구 덕포동 795
건축물명칭: 사상 중흥S-클래스 그랜드센트럴 제105동
호명칭: 제2501호
층별: 제25층
주용도: 아파트 (공동주택)

[전유부분]
층별: 25층 | 구조: 철근콘크리트 | 용도: 아파트 | 면적(㎡): 79.8500

[공용부분]
층별: 지하1층 | 구조: 철근콘크리트 | 용도: 계단실, 복도, 승강기실 | 면적(㎡): 31.5700
층별: 지하2층 | 구조: 철근콘크리트 | 용도: 지하주차장, 전기실 | 면적(㎡): 15.2000
"""

class TestDocumentParser(unittest.TestCase):
    def test_title_parser(self):
        res = parse_building_register_title(SAMPLE_TITLE_TEXT)
        self.assertEqual(res.get("building_name"), "사상 중흥S-클래스 그랜드센트럴")
        self.assertEqual(res.get("max_floor"), "36층")
        self.assertIn("1,685대", res.get("parking", ""))
        self.assertEqual(res.get("households"), "총 1,572세대")
        self.assertEqual(res.get("approval_date"), "2023년 07월 28일")
        self.assertEqual(res.get("structure"), "철근콘크리트구조")

    def test_exclusive_parser(self):
        res = parse_building_register_exclusive(SAMPLE_EXCLUSIVE_TEXT)
        self.assertEqual(res.get("area_exclusive"), "79.85")
        # 79.85 + 31.57 = 111.42
        self.assertEqual(res.get("area_supply"), "111.42")
        self.assertEqual(res.get("current_floor"), "25층")
        self.assertEqual(res.get("room_bath"), "방 3 / 욕실 1개")

    def test_merge_building_registers(self):
        t_res = parse_building_register_title(SAMPLE_TITLE_TEXT)
        e_res = parse_building_register_exclusive(SAMPLE_EXCLUSIVE_TEXT)
        merged = merge_building_registers(t_res, e_res)
        
        print("\n=== MERGED RESULT ===")
        for k, v in merged.items():
            print(f"{k}: {v}")
            
        self.assertEqual(merged.get("area_exclusive"), "79.85")
        self.assertEqual(merged.get("area_supply"), "111.42")
        self.assertEqual(merged.get("floor_info"), "25층 / 36층")
        self.assertEqual(merged.get("approval_date"), "2023년 07월 28일")
        self.assertEqual(merged.get("households"), "총 1,572세대")
        self.assertIn("1,685대", merged.get("parking", ""))
        self.assertIn("덕포동 795", merged.get("location", ""))
        self.assertIn("2501호", merged.get("location", ""))

    def test_land_use_plan_region_and_district_separation(self):
        sample_land_plan = """
        [토지이용계획확인서]
        신청지: 부산광역시 사상구 괘법동 560-1
        지목: 대 | 면적: 452.3㎡
        [지역·지구 등 지정여부]
        1. 「국토의 계획 및 이용에 관한 법률」에 따른 지역·지구 등 :
        일반상업지역, 방화지구, 시가지경관지구(중심), 지구단위계획구역, 가로구역별 최고높이 제한지역(2018-05-02)
        2. 다른 법령 등에 따른 지역·지구 등 :
        상대보호구역(교육환경 보호에 관한 법률), 역사문화환경보존지역, 과밀억제권역(수도권정비계획법)
        """
        res = parse_land_use_plan(sample_land_plan)

        # 14번 용도지역: 순수하게 용도지역만 추출되어야 함 (방화지구 등 지구 침범 금지)
        self.assertEqual(res.get("zone_region"), "일반상업지역")
        self.assertNotIn("방화지구", res.get("zone_region", ""))
        self.assertNotIn("지구단위계획구역", res.get("zone_region", ""))

        # 14번 용도지구: 지구/구역/제한지역 목록 정확 추출
        dist = res.get("zone_district", "")
        self.assertIn("방화지구", dist)
        self.assertIn("지구단위계획구역", dist)
        self.assertIn("가로구역별 최고높이 제한지역", dist)
        self.assertIn("상대보호구역", dist)

        # 16번 사용승인일: 토지이용계획에는 존재하지 않으므로 설정되지 않아야 함
        self.assertIsNone(res.get("approval_date"))

    def test_building_register_approval_dates(self):
        t1 = "사용승인일자: 2018. 06. 15."
        t2 = "준공일자 20190520"
        t3 = "(2021-03-05) 준공인가"

        res1 = parse_building_register_title(t1)
        res2 = parse_building_register_title(t2)
        res3 = parse_building_register_exclusive(t3)

        self.assertEqual(res1.get("approval_date"), "2018년 06월 15일")
        self.assertEqual(res2.get("approval_date"), "2019년 05월 20일")
        self.assertEqual(res3.get("approval_date"), "2021년 03월 05일")

    def test_merge_building_and_land_documents(self):
        sample_building = """
        [일반건축물대장]
        대지위치: 부산광역시 사상구 괘법동 560-1
        주구조: 철근콘크리트구조
        주용도: 제1종근린생활시설
        사용승인일: 2018-06-15
        지역: 일반상업지역
        """
        sample_land_plan = """
        [토지이용계획확인서]
        신청지: 부산광역시 사상구 괘법동 560-1
        국토의 계획 및 이용에 관한 법률:
        일반상업지역, 방화지구, 지구단위계획구역, 가로구역별 최고높이 제한지역
        다른 법령 등에 따른 지역:
        상대보호구역
        """
        b_data = parse_building_register_title(sample_building)
        l_data = parse_land_use_plan(sample_land_plan)

        merged = merge_building_and_land_documents(b_data, land_use_data=l_data)

        # 16번 사용승인일: 건축물대장의 2018년 06월 15일이 100% 보존되어야 함
        self.assertEqual(merged.get("approval_date"), "2018년 06월 15일")

        # 14번 용도지역: 토지이용계획상의 용도지역
        self.assertEqual(merged.get("zone_region"), "일반상업지역")

        # 14번 용도지구: 토지이용계획상의 정밀 지구/구역 목록
        dist = merged.get("zone_district", "")
        self.assertIn("방화지구", dist)
        self.assertIn("지구단위계획구역", dist)
        self.assertIn("가로구역별 최고높이 제한지역", dist)
        self.assertIn("상대보호구역", dist)

    def test_script_document_fusion(self):
        combined_script = """
        [일반건축물대장]
        대지위치: 부산광역시 사상구 괘법동 560-1
        주구조: 철근콘크리트구조
        주용도: 제2종근린생활시설
        사용승인일: 2017-11-20

        [토지이용계획]
        신청지: 부산광역시 사상구 괘법동 560-1
        국토의 계획 및 이용에 관한 법률:
        준주거지역, 방화지구, 지구단위계획구역
        다른 법령 등에 따른 지역:
        상대보호구역
        """
        doc_type, parsed = parse_raw_script_document(combined_script)
        self.assertIn("융합 분석", doc_type)
        self.assertEqual(parsed.get("approval_date"), "2017년 11월 20일")
        self.assertEqual(parsed.get("zone_region"), "준주거지역")
        self.assertIn("방화지구", parsed.get("zone_district", ""))
        self.assertIn("상대보호구역", parsed.get("zone_district", ""))

    def test_commercial_window_poster_custom_cards(self):
        from thumbnail_generator import render_a4_window_poster

        custom_cards = [
            ("해당층 / 총층", "2층 / 총 5층"),
            ("공급 및 전용면적", "전용 57평(188.4㎡) / 계약 66평"),
            ("추천업종", "대형카페 · 음식점 · 베이커리"),
            ("방향 (출입구 기준)", "남향 (주된 출입구 기준)")
        ]

        img = render_a4_window_poster(
            is_commercial=True,
            main_title="괘법동 메인상권 최고의 자리!",
            price_text="임대 1억/990만",
            custom_cards=custom_cards
        )
        self.assertEqual(img.size, (1240, 1754))

if __name__ == "__main__":
    unittest.main()
