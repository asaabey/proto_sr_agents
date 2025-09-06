"""
End-to-end integration tests for the complete systematic review analysis pipeline.

Tests the full workflow from document upload through all agent analyses,
validating that the entire system works together coherently.
"""

import pytest
import json
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestEndToEndWorkflow:
    """Test complete end-to-end workflows."""

    @pytest.mark.integration
    def test_complete_docx_analysis_workflow(self):
        """Test complete workflow: upload → extract → analyze → validate response."""
        docx_path = Path("manuscripts/sr_ma_6925.docx")
        if not docx_path.exists():
            pytest.skip("Test manuscript file not available")
        
        # Step 1: Upload and process document
        with open(docx_path, "rb") as f:
            files = {"file": ("sr_ma_6925.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
            response = client.post("/review/upload", files=files)
        
        assert response.status_code == 200, f"Upload failed: {response.text}"
        
        result = response.json()
        
        # Step 2: Validate extraction occurred
        extraction_info = result["extraction_info"]
        assert extraction_info["source_file"] == "sr_ma_6925.docx"
        
        elements = extraction_info["extracted_elements"]
        assert elements["title"] is True
        assert elements["pico"] is True
        assert elements["studies"] > 0
        
        # Step 3: Validate all agents ran
        issues = result["issues"]
        agents = set(issue["agent"] for issue in issues)
        
        # Core agents should all provide feedback
        expected_agents = {"PICO-Parser", "PRISMA-Checker"}
        for agent in expected_agents:
            assert agent in agents, f"Agent {agent} should have run"
        
        # Step 4: Validate issue categorization and severity
        severity_counts = {}
        category_counts = {}
        
        for issue in issues:
            severity = issue["severity"]
            category = issue["category"]
            
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Should have mix of severities
        assert "high" in severity_counts or "medium" in severity_counts
        
        # Should cover multiple categories
        assert len(category_counts) >= 2
        assert "PICO" in category_counts
        assert "PRISMA" in category_counts
        
        # Step 5: Validate recommendations are actionable
        for issue in issues:
            assert len(issue["recommendation"]) > 20, "Recommendations should be detailed"
            assert "." in issue["recommendation"], "Recommendations should be complete sentences"

    @pytest.mark.integration
    def test_json_vs_upload_consistency(self):
        """Test that JSON API and upload API produce consistent results."""
        docx_path = Path("manuscripts/sr_ma_6925.docx")
        if not docx_path.exists():
            pytest.skip("Test manuscript file not available")
        
        # Get upload result
        with open(docx_path, "rb") as f:
            files = {"file": ("sr_ma_6925.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
            upload_response = client.post("/review/upload", files=files)
        
        assert upload_response.status_code == 200
        upload_result = upload_response.json()
        
        # Extract manuscript data for JSON API
        extraction_info = upload_result["extraction_info"]
        extracted_elements = extraction_info["extracted_elements"]
        
        # Create equivalent manuscript JSON (simplified for comparison)
        manuscript_json = {
            "manuscript_id": "test-comparison",
            "title": "Test Systematic Review" if extracted_elements["title"] else None,
            "question": {
                "population": "Test population",
                "intervention": "Test intervention", 
                "comparator": "Control",
                "outcomes": ["Test outcome"]
            } if extracted_elements["pico"] else None,
            "search": [],
            "flow": {
                "identified": 100,
                "screened": 80,
                "included": 10,
                "exclusion_reasons": []
            } if extracted_elements["flow_counts"] else None,
            "included_studies": [
                {
                    "study_id": f"study_{i}",
                    "title": f"Study {i}",
                    "design": "RCT",
                    "n": 100,
                    "outcomes": []
                } for i in range(min(extracted_elements["studies"], 5))
            ]
        }
        
        # Test JSON API
        json_response = client.post("/review/start", json=manuscript_json)
        assert json_response.status_code == 200
        json_result = json_response.json()
        
        # Compare agent execution
        upload_agents = set(issue["agent"] for issue in upload_result["issues"])
        json_agents = set(issue["agent"] for issue in json_result["issues"])
        
        # Same agents should run (though may find different issues)
        core_agents = {"PICO-Parser", "PRISMA-Checker"}
        assert core_agents.issubset(upload_agents)
        assert core_agents.issubset(json_agents)

    @pytest.mark.integration  
    def test_concurrent_upload_processing(self):
        """Test system handles concurrent uploads gracefully."""
        docx_path = Path("manuscripts/sr_ma_6925.docx")
        if not docx_path.exists():
            pytest.skip("Test manuscript file not available")
        
        import asyncio
        import httpx
        
        async def upload_manuscript(session, filename_suffix=""):
            with open(docx_path, "rb") as f:
                files = {"file": (f"sr_ma_6925_{filename_suffix}.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
                response = await session.post("http://127.0.0.1:8000/review/upload", files=files)
                return response
        
        async def test_concurrent():
            async with httpx.AsyncClient() as session:
                # Submit 3 concurrent uploads
                tasks = [
                    upload_manuscript(session, "1"),
                    upload_manuscript(session, "2"), 
                    upload_manuscript(session, "3")
                ]
                
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                
                # All should succeed
                for i, response in enumerate(responses):
                    assert not isinstance(response, Exception), f"Upload {i} failed with exception"
                    assert response.status_code == 200, f"Upload {i} failed with status {response.status_code}"
        
        # Run the async test
        asyncio.run(test_concurrent())

    @pytest.mark.integration
    def test_error_recovery_workflow(self):
        """Test system recovers gracefully from various error conditions."""
        
        # Test 1: Invalid file type
        fake_content = b"This is not a DOCX file"
        files = {"file": ("test.txt", fake_content, "text/plain")}
        
        response = client.post("/review/upload", files=files)
        assert response.status_code == 400
        assert "Only Word documents" in response.json()["detail"]
        
        # Test 2: Corrupted DOCX
        fake_docx = b"PK\x03\x04fake_docx_content"
        files = {"file": ("corrupted.docx", fake_docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        
        response = client.post("/review/upload", files=files)
        assert response.status_code == 500
        assert "Error processing uploaded file" in response.json()["detail"]
        
        # Test 3: Server should still be responsive after errors
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    @pytest.mark.integration
    def test_performance_benchmarks(self):
        """Test performance benchmarks for document processing."""
        docx_path = Path("manuscripts/sr_ma_6925.docx")
        if not docx_path.exists():
            pytest.skip("Test manuscript file not available")
        
        import time
        
        start_time = time.time()
        
        with open(docx_path, "rb") as f:
            files = {"file": ("sr_ma_6925.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
            response = client.post("/review/upload", files=files)
        
        processing_time = time.time() - start_time
        
        assert response.status_code == 200
        
        # Performance expectations (adjust based on system capabilities)
        assert processing_time < 30.0, f"Processing took too long: {processing_time:.2f}s"
        
        result = response.json()
        
        # Quality vs speed trade-off validation
        assert len(result["issues"]) > 0, "Should identify some issues"
        assert result["extraction_info"]["extracted_elements"]["studies"] > 0, "Should extract studies"


class TestSystemIntegration:
    """Test integration between different system components."""

    def test_health_check(self):
        """Test system health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_upload_info_endpoint(self):
        """Test upload information endpoint."""
        response = client.get("/upload/info")
        assert response.status_code == 200
        
        info = response.json()
        assert "supported_formats" in info
        assert "requirements" in info
        assert "extraction_capabilities" in info
        
        # Validate content structure
        assert ".docx" in info["supported_formats"]
        assert "pico_extraction" in info["extraction_capabilities"]

    def test_api_endpoints_exist(self):
        """Test that all expected API endpoints exist."""
        # Test JSON manuscript endpoint
        test_manuscript = {
            "manuscript_id": "test",
            "title": "Test",
            "question": None,
            "search": [],
            "flow": None,
            "included_studies": []
        }
        
        response = client.post("/review/start", json=test_manuscript)
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])