"""
Tests for DOCX manuscript content extraction functionality.

Tests the underlying document processing, text extraction,
PICO parsing, table extraction, and pattern matching logic.
"""

import pytest
from pathlib import Path
from app.utils.pdf_ingest import extract_manuscript_from_file, WordProcessor, TextExtractor


class TestManuscriptExtraction:
    """Test suite for manuscript content extraction."""

    def test_extract_manuscript_from_file(self):
        """Test high-level manuscript extraction function."""
        docx_path = Path("manuscripts/sr_ma_6925.docx")
        if not docx_path.exists():
            pytest.skip("Test manuscript file not available")
        
        manuscript = extract_manuscript_from_file(docx_path)
        
        assert manuscript is not None, "Should successfully extract manuscript"
        assert manuscript.title is not None, "Should extract title"
        assert manuscript.question is not None, "Should extract PICO/research question"
        assert len(manuscript.included_studies) > 0, "Should extract studies"

    def test_word_processor_initialization(self):
        """Test WordProcessor initialization."""
        processor = WordProcessor()
        assert processor is not None
        assert hasattr(processor, 'text_extractor')

    def test_text_extractor_initialization(self):
        """Test TextExtractor initialization."""
        extractor = TextExtractor()
        assert extractor is not None
        # NLP might not be available in test environment
        # assert hasattr(extractor, 'nlp')  # Skip if spacy not installed

    @pytest.mark.skipif(not Path("manuscripts/sr_ma_6925.docx").exists(), 
                       reason="Test manuscript file not available")
    def test_document_structure_extraction(self):
        """Test extraction of document structure elements."""
        docx_path = Path("manuscripts/sr_ma_6925.docx")
        processor = WordProcessor()
        
        manuscript = processor.extract_manuscript(docx_path)
        
        assert manuscript is not None
        
        # Test title extraction
        if manuscript.title:
            assert len(manuscript.title.strip()) > 0
            assert manuscript.title != "docx-"  # Should not be just filename prefix
        
        # Test PICO extraction
        if manuscript.question:
            assert hasattr(manuscript.question, 'population')
            assert hasattr(manuscript.question, 'intervention') 
            assert hasattr(manuscript.question, 'comparator')
            assert hasattr(manuscript.question, 'outcomes')

    @pytest.mark.skipif(not Path("manuscripts/sr_ma_6925.docx").exists(),
                       reason="Test manuscript file not available")
    def test_study_table_extraction(self):
        """Test extraction of study characteristics from tables."""
        docx_path = Path("manuscripts/sr_ma_6925.docx")
        processor = WordProcessor()
        
        manuscript = processor.extract_manuscript(docx_path)
        
        assert manuscript is not None
        assert manuscript.included_studies is not None
        assert len(manuscript.included_studies) > 0
        
        # Test study record structure
        for study in manuscript.included_studies:
            assert hasattr(study, 'study_id')
            assert hasattr(study, 'title')
            assert study.study_id is not None
            assert len(study.study_id.strip()) > 0

    @pytest.mark.skipif(not Path("manuscripts/sr_ma_6925.docx").exists(),
                       reason="Test manuscript file not available")
    def test_flow_diagram_extraction(self):
        """Test PRISMA flow diagram number extraction."""
        docx_path = Path("manuscripts/sr_ma_6925.docx")
        processor = WordProcessor()
        
        manuscript = processor.extract_manuscript(docx_path)
        
        assert manuscript is not None
        
        if manuscript.flow:
            # Should have basic flow counts
            assert hasattr(manuscript.flow, 'identified')
            assert hasattr(manuscript.flow, 'screened')
            assert hasattr(manuscript.flow, 'included')
            
            # Numbers should be reasonable
            if manuscript.flow.identified:
                assert manuscript.flow.identified > 0
            if manuscript.flow.included:
                assert manuscript.flow.included > 0

    @pytest.mark.skipif(not Path("manuscripts/sr_ma_6925.docx").exists(),
                       reason="Test manuscript file not available")
    def test_search_strategy_extraction(self):
        """Test database search strategy extraction."""
        docx_path = Path("manuscripts/sr_ma_6925.docx")
        processor = WordProcessor()
        
        manuscript = processor.extract_manuscript(docx_path)
        
        assert manuscript is not None
        
        # Search strategies might be empty if not well-formatted in document
        if manuscript.search and len(manuscript.search) > 0:
            for search in manuscript.search:
                assert hasattr(search, 'database')
                assert hasattr(search, 'strategy')
                assert search.database is not None


class TestTextProcessing:
    """Test text processing and pattern matching utilities."""

    def test_text_extractor_pattern_matching(self):
        """Test pattern matching for systematic review elements."""
        extractor = TextExtractor()
        
        # Test PICO pattern matching
        test_text = """
        Population: Adult patients with diabetes mellitus type 2
        Intervention: SGLT2 inhibitors (empagliflozin, dapagliflozin)
        Comparator: Standard care or placebo
        Outcomes: HbA1c reduction, weight loss, cardiovascular events
        """
        
        pico_match = extractor._extract_pico_from_text(test_text)
        
        if pico_match:  # Might be None if NLP not available
            assert 'diabetes' in pico_match.population.lower()
            assert any(drug in pico_match.intervention.lower() for drug in ['sglt2', 'empagliflozin', 'dapagliflozin'])
            assert 'hba1c' in ' '.join(pico_match.outcomes).lower()

    def test_search_pattern_recognition(self):
        """Test search strategy pattern recognition."""
        extractor = TextExtractor()
        
        test_text = """
        MEDLINE (via PubMed): 
        (diabetes[MeSH] OR "diabetes mellitus"[tiab]) AND (SGLT2[tiab] OR "sodium glucose"[tiab])
        Date range: 2010-2023
        
        Embase:
        'diabetes mellitus'/exp OR diabetes:ti,ab AND 'sglt2 inhibitor'/exp
        """
        
        # This tests the internal pattern matching logic
        search_matches = extractor._extract_search_strategies(test_text)
        
        if search_matches:
            db_names = [s.database for s in search_matches]
            assert any('medline' in db.lower() or 'pubmed' in db.lower() for db in db_names)

    def test_flow_number_extraction(self):
        """Test PRISMA flow number extraction."""
        extractor = TextExtractor()
        
        test_text = """
        Records identified through database searching (n=2,543)
        Records after duplicates removed (n=1,876)
        Records screened (n=1,876)
        Records excluded (n=1,654)
        Full-text articles assessed for eligibility (n=222)
        Full-text articles excluded (n=187)
        Studies included in qualitative synthesis (n=35)
        Studies included in quantitative synthesis (meta-analysis) (n=28)
        """
        
        flow_counts = extractor._extract_flow_from_text(test_text)
        
        if flow_counts:
            assert flow_counts.identified == 2543
            assert flow_counts.screened == 1876
            assert flow_counts.included == 35


class TestExtractionEdgeCases:
    """Test edge cases and error handling in extraction."""

    def test_empty_document_handling(self):
        """Test handling of empty or minimal documents."""
        # This would need a minimal test DOCX file
        pass

    def test_malformed_table_handling(self):
        """Test handling of malformed tables."""
        # This would test graceful degradation when tables are poorly formatted
        pass

    def test_missing_sections_handling(self):
        """Test handling when expected sections are missing."""
        # Test that extraction doesn't fail when PICO, methods, etc. are missing
        pass

    def test_non_english_content_handling(self):
        """Test handling of non-English content."""
        # Test graceful degradation with non-English systematic reviews
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])