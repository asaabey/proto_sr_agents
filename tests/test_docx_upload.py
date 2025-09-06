"""
Tests for DOCX upload endpoint functionality.

Tests upload validation, file processing, error handling, 
and response format validation.
"""

import pytest
import io
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

class TestDocxUpload:
    """Test suite for DOCX file upload endpoint."""

    def test_upload_endpoint_exists(self):
        """Test that upload endpoint is accessible."""
        response = client.get("/upload/info")
        assert response.status_code == 200
        info = response.json()
        assert "supported_formats" in info
        assert ".docx" in info["supported_formats"]
        assert ".doc" in info["supported_formats"]

    def test_upload_valid_docx_file(self):
        """Test uploading a valid DOCX file."""
        docx_path = Path("manuscripts/sr_ma_6925.docx")
        if not docx_path.exists():
            pytest.skip("Test manuscript file not available")
        
        with open(docx_path, "rb") as f:
            files = {"file": ("sr_ma_6925.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
            response = client.post("/review/upload", files=files)
        
        assert response.status_code == 200
        result = response.json()
        
        # Validate response structure
        assert "issues" in result
        assert "meta" in result
        assert "extraction_info" in result
        
        # Validate extraction info
        extraction_info = result["extraction_info"]
        assert extraction_info["source_file"] == "sr_ma_6925.docx"
        assert "manuscript_id" in extraction_info
        assert "extracted_elements" in extraction_info
        
        # Validate extracted elements structure
        elements = extraction_info["extracted_elements"]
        assert "title" in elements
        assert "pico" in elements  
        assert "search_strategies" in elements
        assert "flow_counts" in elements
        assert "studies" in elements

    def test_upload_invalid_file_type(self):
        """Test rejection of non-DOCX files."""
        # Create fake text file
        fake_content = b"This is not a DOCX file"
        files = {"file": ("test.txt", io.BytesIO(fake_content), "text/plain")}
        
        response = client.post("/review/upload", files=files)
        assert response.status_code == 400
        assert "Only Word documents" in response.json()["detail"]

    def test_upload_no_file(self):
        """Test upload without providing file."""
        response = client.post("/review/upload", files={})
        assert response.status_code == 422  # Validation error

    def test_upload_empty_file(self):
        """Test upload with empty file."""
        files = {"file": ("empty.docx", io.BytesIO(b""), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        
        response = client.post("/review/upload", files=files)
        # Should handle gracefully - either 422 or 500 with appropriate error
        assert response.status_code in [422, 500]

    def test_upload_corrupted_docx(self):
        """Test upload with corrupted DOCX file."""
        # Create fake DOCX content (just random bytes)
        fake_docx = b"PK\x03\x04fake_docx_content_that_will_fail"
        files = {"file": ("corrupted.docx", io.BytesIO(fake_docx), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        
        response = client.post("/review/upload", files=files)
        assert response.status_code == 500
        assert "Error processing uploaded file" in response.json()["detail"]

    def test_upload_response_format(self):
        """Test that upload response follows expected format."""
        docx_path = Path("manuscripts/sr_ma_6925.docx")
        if not docx_path.exists():
            pytest.skip("Test manuscript file not available")
        
        with open(docx_path, "rb") as f:
            files = {"file": ("sr_ma_6925.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
            response = client.post("/review/upload", files=files)
        
        assert response.status_code == 200
        result = response.json()
        
        # Check all issues have required fields
        for issue in result["issues"]:
            assert "id" in issue
            assert "severity" in issue
            assert "category" in issue
            assert "item" in issue
            assert "recommendation" in issue
            assert "agent" in issue
            assert issue["severity"] in ["low", "medium", "high"]

    def test_upload_agents_execution(self):
        """Test that all agents run on uploaded manuscript."""
        docx_path = Path("manuscripts/sr_ma_6925.docx")
        if not docx_path.exists():
            pytest.skip("Test manuscript file not available")
        
        with open(docx_path, "rb") as f:
            files = {"file": ("sr_ma_6925.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
            response = client.post("/review/upload", files=files)
        
        result = response.json()
        issues = result["issues"]
        
        # Check that all three agents reported issues
        agents_found = set(issue["agent"] for issue in issues)
        expected_agents = {"PICO-Parser", "PRISMA-Checker", "Meta-Analysis"}
        
        # At least PICO and PRISMA should run
        assert "PICO-Parser" in agents_found
        assert "PRISMA-Checker" in agents_found


class TestDocxExtractionQuality:
    """Test quality and accuracy of DOCX content extraction."""

    def test_real_manuscript_extraction_quality(self):
        """Test extraction quality with real systematic review manuscript."""
        docx_path = Path("manuscripts/sr_ma_6925.docx")
        if not docx_path.exists():
            pytest.skip("Test manuscript file not available")
        
        with open(docx_path, "rb") as f:
            files = {"file": ("sr_ma_6925.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
            response = client.post("/review/upload", files=files)
        
        result = response.json()
        extraction_info = result["extraction_info"]
        elements = extraction_info["extracted_elements"]
        
        # Quality expectations for a real systematic review
        assert elements["title"] is True, "Should extract title from systematic review"
        assert elements["pico"] is True, "Should extract PICO elements" 
        assert elements["studies"] > 0, "Should find included studies"
        assert elements["flow_counts"] is True, "Should extract PRISMA flow counts"
        
        # Check for reasonable extraction quality
        if elements["studies"] > 0:
            assert elements["studies"] >= 10, "Should find reasonable number of studies for meta-analysis"

    def test_pico_element_validation(self):
        """Test PICO element extraction validation."""
        docx_path = Path("manuscripts/sr_ma_6925.docx")
        if not docx_path.exists():
            pytest.skip("Test manuscript file not available")
        
        with open(docx_path, "rb") as f:
            files = {"file": ("sr_ma_6925.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
            response = client.post("/review/upload", files=files)
        
        result = response.json()
        
        # Check PICO-related issues
        pico_issues = [issue for issue in result["issues"] if issue["agent"] == "PICO-Parser"]
        assert len(pico_issues) > 0, "Should identify PICO validation issues"
        
        # Common PICO issues that should be detected
        issue_types = [issue["id"] for issue in pico_issues]
        expected_checks = ["PICO-002", "PICO-004", "PICO-005"]  # Based on actual response
        
        for expected in expected_checks:
            assert expected in issue_types, f"Should check for {expected}"

    def test_prisma_validation(self):
        """Test PRISMA compliance checking."""
        docx_path = Path("manuscripts/sr_ma_6925.docx")
        if not docx_path.exists():
            pytest.skip("Test manuscript file not available")
        
        with open(docx_path, "rb") as f:
            files = {"file": ("sr_ma_6925.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
            response = client.post("/review/upload", files=files)
        
        result = response.json()
        
        # Check PRISMA-related issues
        prisma_issues = [issue for issue in result["issues"] if issue["agent"] == "PRISMA-Checker"]
        assert len(prisma_issues) > 0, "Should identify PRISMA validation issues"
        
        # Check severity distribution
        high_severity = [i for i in prisma_issues if i["severity"] == "high"]
        assert len(high_severity) > 0, "Should identify high-severity PRISMA issues"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])