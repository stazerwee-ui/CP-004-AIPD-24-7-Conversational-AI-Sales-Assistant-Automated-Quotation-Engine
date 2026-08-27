"""
Automated Verification Suite for Bereavement Document Security & Intake Workflow
"""
import os
import sys
import io
import json
import sqlite3
import secrets
import unittest
from fastapi.testclient import TestClient

# Ensure workspace root is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main
from main import app, DOC_STORAGE_DIR, LEADS_DB

class TestBereavementDocuments(unittest.TestCase):
    def setUp(self):
        self.test_token = "test_admin_token_2026_xyz"
        os.environ["SOLACE_ADMIN_TOKEN"] = self.test_token
        self.client = TestClient(app)
        main.init_db()

    def test_criterion_1_storage_isolation(self):
        """1. A file written to the storage directory is NOT fetchable at http://127.0.0.1:8000/<name> or any path under it."""
        secret_filename = f"test_confidential_cert_{secrets.token_hex(4)}.bin"
        secret_path = os.path.join(DOC_STORAGE_DIR, secret_filename)
        with open(secret_path, "wb") as f:
            f.write(b"SECRET_DEATH_CERTIFICATE_CONTENT")

        # Try to access via static server root
        resp = self.client.get(f"/{secret_filename}")
        self.assertIn(resp.status_code, [404, 405])

        # Try relative paths
        resp_dir = self.client.get(f"/solace_secure_docs/{secret_filename}")
        self.assertIn(resp_dir.status_code, [404, 405])

        if os.path.exists(secret_path):
            os.remove(secret_path)

    def test_criterion_2_raw_endpoint_requires_auth(self):
        """2. GET /api/admin/documents/<id>/raw without a token returns 401."""
        resp = self.client.get("/api/admin/documents/DOC-nonexistent/raw")
        self.assertEqual(resp.status_code, 401)
        self.assertIn("Invalid or missing admin token", resp.text)

    def test_criterion_3_unset_env_returns_503_on_all_admin_endpoints(self):
        """3. With SOLACE_ADMIN_TOKEN unset, all four admin endpoints return 503."""
        os.environ.pop("SOLACE_ADMIN_TOKEN", None)

        endpoints = [
            ("GET", "/api/admin/documents"),
            ("GET", "/api/admin/documents/DOC-123/raw"),
            ("POST", "/api/admin/route-probe", {"message": "hello"}),
            ("GET", "/api/admin/events")
        ]

        for method, path, *data in endpoints:
            headers = {"X-Admin-Token": "some_token"}
            if method == "GET":
                resp = self.client.get(path, headers=headers)
            else:
                resp = self.client.post(path, json=data[0] if data else {}, headers=headers)
            self.assertEqual(resp.status_code, 503, f"Endpoint {path} did not return 503 when SOLACE_ADMIN_TOKEN is unset")
            self.assertIn("Admin API disabled", resp.text)

        # Restore token
        os.environ["SOLACE_ADMIN_TOKEN"] = self.test_token

    def test_criterion_4_magic_bytes_validation(self):
        """4. A .txt renamed to .jpg is rejected by magic-byte check."""
        fake_jpg_content = b"This is plain text pretending to be a JPG."
        files = {"file": ("certificate.jpg", io.BytesIO(fake_jpg_content), "image/jpeg")}
        resp = self.client.post("/api/documents/upload", files=files)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Unsupported document format", resp.text)

        # Valid JPEG magic bytes check
        real_jpg_content = b"\xff\xd8\xff\xe0" + b"\x00" * 200
        files = {"file": ("real_certificate.jpg", io.BytesIO(real_jpg_content), "image/jpeg")}
        resp = self.client.post("/api/documents/upload", files=files)
        self.assertEqual(resp.status_code, 201)
        doc_id = resp.json()["doc_id"]
        self.assertTrue(doc_id.startswith("DOC-"))

    def test_criterion_5_size_cap_enforcement_streaming(self):
        """5. An 11 MB file is rejected without the process holding 11 MB in memory."""
        class ChunkStream(io.RawIOBase):
            def __init__(self, total_bytes):
                self.remaining = total_bytes
                self.first = True
            def readable(self): return True
            def readinto(self, b):
                if self.remaining <= 0:
                    return 0
                to_read = min(len(b), self.remaining)
                self.remaining -= to_read
                if self.first:
                    self.first = False
                    b[:4] = b"\xff\xd8\xff\xe0"
                    b[4:to_read] = b"\x00" * (to_read - 4)
                else:
                    b[:to_read] = b"\x00" * to_read
                return to_read

        stream = ChunkStream(11 * 1024 * 1024)
        files = {"file": ("large_cert.jpg", io.BufferedReader(stream), "image/jpeg")}
        resp = self.client.post("/api/documents/upload", files=files)
        self.assertEqual(resp.status_code, 413)
        self.assertIn("exceeds the 10 MB limit", resp.text)

    def test_criterion_6_path_traversal_safe(self):
        """6. A filename of ../../../etc/passwd cannot escape the storage directory."""
        fake_jpg = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        files = {"file": ("../../../etc/passwd", io.BytesIO(fake_jpg), "image/jpeg")}
        resp = self.client.post("/api/documents/upload", files=files)
        self.assertEqual(resp.status_code, 201)
        doc_id = resp.json()["doc_id"]
        
        # Verify stored file is purely inside DOC_STORAGE_DIR
        stored_name = f"{doc_id}.bin"
        stored_path = os.path.join(DOC_STORAGE_DIR, stored_name)
        self.assertTrue(os.path.exists(stored_path))
        self.assertTrue(os.path.abspath(stored_path).startswith(os.path.abspath(DOC_STORAGE_DIR)))

    def test_criterion_7_intake_without_upload(self):
        """7. Completing intake with NO upload still creates the lead and fires the on-call alert."""
        intake_state = {
            "deceasedName": "Uncle Tan",
            "locationOfDeceased": "National University Hospital",
            "contactNumber": "91234567",
            "documentationStatus": "no"
        }
        lead_record = main.save_lead(intake_state, user_id=None)
        self.assertTrue(lead_record["id"].startswith("SOL-"))
        self.assertEqual(lead_record["details"]["deceasedName"], "Uncle Tan")
        
        # Check notify_oncall runs without error
        main.notify_oncall(lead_record)
        self.assertTrue(os.path.exists(main.ALERTS_FILE))
        with open(main.ALERTS_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("Death cert: not attached", content)

    def test_criterion_8_badge_and_metadata_api(self):
        """8. The badge / metadata appears only for records that have a document."""
        # Query for non-existent request id should return 0 documents
        non_existent_req = f"FR-2026-EMPTY-{secrets.token_hex(4)}"
        resp_empty = self.client.get(f"/api/admin/documents?request_id={non_existent_req}", headers={"X-Admin-Token": self.test_token})
        self.assertEqual(resp_empty.status_code, 200)
        self.assertEqual(len(resp_empty.json()["documents"]), 0)

        # Create valid upload for a distinct request id
        req_id = f"FR-2026-TESTREQ-{secrets.token_hex(4)}"
        real_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
        files = {"file": ("cert.png", io.BytesIO(real_png), "image/png")}
        data = {"request_id": req_id}
        resp = self.client.post("/api/documents/upload", files=files, data=data)
        self.assertEqual(resp.status_code, 201)

        # Query metadata for this specific request
        resp_meta = self.client.get(f"/api/admin/documents?request_id={req_id}", headers={"X-Admin-Token": self.test_token})
        self.assertEqual(resp_meta.status_code, 200)
        docs = resp_meta.json()["documents"]
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]["mime_type"], "image/png")

    def test_criterion_10_pdf_raw_streaming(self):
        """10. A PDF upload is streamed with appropriate headers."""
        real_pdf = b"%PDF-1.4\n" + b"0" * 100
        files = {"file": ("cert.pdf", io.BytesIO(real_pdf), "application/pdf")}
        resp = self.client.post("/api/documents/upload", files=files)
        self.assertEqual(resp.status_code, 201)
        doc_id = resp.json()["doc_id"]

        resp_raw = self.client.get(f"/api/admin/documents/{doc_id}/raw", headers={"X-Admin-Token": self.test_token})
        self.assertEqual(resp_raw.status_code, 200)
        self.assertEqual(resp_raw.headers["content-type"], "application/pdf")
        self.assertIn("no-store", resp_raw.headers["cache-control"])
        self.assertEqual(resp_raw.headers["x-content-type-options"], "nosniff")

if __name__ == "__main__":
    unittest.main()
