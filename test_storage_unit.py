import unittest
import os
import json
import storage_manager as sm

class TestStorageManager(unittest.TestCase):
    def setUp(self):
        sm.ensure_storage_dir()
        self.test_files = []

    def tearDown(self):
        for fn in self.test_files:
            fp = os.path.join(sm.STORAGE_DIR, fn)
            if os.path.exists(fp):
                try:
                    os.remove(fp)
                except Exception:
                    pass

    def test_save_and_load_record(self):
        item_no = "2664012103"
        prop_type = "apt"
        date_str = "20261126"
        thumb_data = {"main_title": "사상 중흥S-클래스 106동", "thumb_price_text": "6억 7천"}
        poster_data = {"poster_apt_title": "창문포스터 사상중흥", "poster_apt_price": "6억 7,000만 원"}
        ad_data = {"ad_location": "부산시 사상구 괘법동", "ad_area_exclusive": "84.96"}

        ok, msg, filename = sm.save_listing_record(
            item_no=item_no,
            prop_type=prop_type,
            thumbnail_data=thumb_data,
            poster_data=poster_data,
            ad_spec_data=ad_data,
            status="진행중",
            memo="테스트 매물 메모",
            custom_date_str=date_str
        )
        self.assertTrue(ok)
        self.assertEqual(filename, "아파트_2664012103_20261126.json")
        self.test_files.append(filename)

        # Check loaded
        rec = sm.load_listing_record(filename)
        self.assertIsNotNone(rec)
        self.assertEqual(rec["filename"], filename)
        self.assertEqual(rec["item_no"], item_no)
        self.assertEqual(rec["prop_type"], "apt")
        self.assertEqual(rec["prop_type_label"], "아파트")
        self.assertEqual(rec["status"], "진행중")
        self.assertEqual(rec["memo"], "테스트 매물 메모")
        self.assertEqual(rec["thumbnail_data"]["main_title"], "사상 중흥S-클래스 106동")
        self.assertEqual(rec["poster_data"]["poster_apt_price"], "6억 7,000만 원")
        self.assertEqual(rec["ad_spec_data"]["ad_location"], "부산시 사상구 괘법동")

    def test_update_status_and_delete(self):
        ok, msg, fn = sm.save_listing_record(
            item_no="HD76",
            prop_type="comm",
            thumbnail_data={"comm_lease_main_title": "사상로 상가 임차"},
            poster_data={"poster_comm_l_price": "보증금 1억 / 월 550만"},
            ad_spec_data={"comm_ad_location": "부산시 사상구 괘법동 대로변"},
            custom_date_str="20261126"
        )
        self.assertTrue(ok)
        self.assertEqual(fn, "상가_HD76_20261126.json")
        self.test_files.append(fn)

        # Update status
        self.assertTrue(sm.update_listing_status(fn, "거래완료"))
        loaded = sm.load_listing_record(fn)
        self.assertEqual(loaded["status"], "거래완료")

        # Delete
        d_ok, d_msg = sm.delete_listing_record(fn)
        self.assertTrue(d_ok)
        self.assertIsNone(sm.load_listing_record(fn))

    def test_zip_backup_and_restore(self):
        ok, msg, fn = sm.save_listing_record(
            item_no="ZIP01",
            prop_type="house",
            thumbnail_data={"house_main_title": "단독주택 매매"},
            poster_data={"poster_house_price": "3억 8천"},
            ad_spec_data={"house_ad_location": "부산시 사상구 덕포동"},
            custom_date_str="20261126"
        )
        self.test_files.append(fn)

        zip_bytes = sm.create_backup_zip_bytes()
        self.assertGreater(len(zip_bytes), 0)

        # Delete and restore
        sm.delete_listing_record(fn)
        self.assertIsNone(sm.load_listing_record(fn))

        cnt, r_msg = sm.restore_from_zip_or_json(zip_bytes, "backup.zip")
        self.assertGreaterEqual(cnt, 1)
        self.assertIsNotNone(sm.load_listing_record(fn))

if __name__ == "__main__":
    unittest.main()
