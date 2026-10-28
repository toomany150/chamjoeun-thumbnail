import unittest
from document_parser import (
    parse_building_register_title,
    parse_building_register_exclusive,
    merge_building_registers,
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

if __name__ == "__main__":
    unittest.main()
