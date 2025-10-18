"""
PDF Annotation Module
Applies non-destructive highlights to PDFs while preserving layout and fonts.
"""

import fitz  # PyMuPDF
from typing import List, Dict, Tuple
import os


class PDFAnnotator:
    """
    Non-destructive PDF highlighter that preserves exact layout and fonts.
    """
    
    def __init__(self, theme_config: Dict):
        """
        Initialize annotator with color theme.
        
        Args:
            theme_config: Theme configuration with color mappings
        """
        self.theme = theme_config
        self.annotations_applied = 0
    
    def _get_color_for_category(self, category: str) -> Tuple[float, float, float]:
        """
        Get RGB color for a category.
        
        Returns:
            Tuple of (r, g, b) values in range [0, 1]
        """
        if category in self.theme.get('categories', {}):
            return tuple(self.theme['categories'][category]['color'])
        return (0.8, 0.8, 0.8)  # Default gray
    
    def _get_opacity_for_category(self, category: str) -> float:
        """Get opacity value for a category."""
        if category in self.theme.get('categories', {}):
            return self.theme['categories'][category].get('opacity', 0.3)
        return 0.3  # Default opacity
    
    def annotate_pdf(self, input_path: str, output_path: str, 
                     classified_spans: List, classifications: Dict[int, tuple],
                     confidence_threshold: float = 0.6) -> str:
        """
        Apply highlights to PDF based on classifications.
        
        Args:
            input_path: Path to input PDF
            output_path: Path to save annotated PDF
            classified_spans: List of TextSpan objects with categories
            classifications: Dictionary of classifications
            confidence_threshold: Minimum confidence to apply highlight
            
        Returns:
            Path to annotated PDF
        """
        # Open the PDF
        doc = fitz.open(input_path)
        self.annotations_applied = 0
        
        # Group spans by page for efficient processing
        page_spans = {}
        for idx, span in enumerate(classified_spans):
            if span.page_num not in page_spans:
                page_spans[span.page_num] = []
            page_spans[span.page_num].append((idx, span))
        
        # Process each page
        for page_num in range(len(doc)):
            if page_num not in page_spans:
                continue
            
            page = doc[page_num]
            spans_on_page = page_spans[page_num]
            
            for idx, span in spans_on_page:
                category, confidence = classifications.get(idx, ('normal', 0.0))
                
                # Skip if confidence too low or category is 'normal'
                if confidence < confidence_threshold or category == 'normal':
                    continue
                
                # Apply highlight
                self._highlight_span(page, span, category)
                self.annotations_applied += 1
        
        # Save the annotated PDF
        doc.save(output_path, garbage=4, deflate=True, clean=True)
        doc.close()
        
        return output_path
    
    def _highlight_span(self, page, span, category: str):
        """
        Apply highlight annotation to a text span.
        
        Args:
            page: PyMuPDF page object
            span: TextSpan object
            category: Classification category
        """
        # Get color and opacity from theme
        color = self._get_color_for_category(category)
        opacity = self._get_opacity_for_category(category)
        
        # Create rectangle for highlight
        rect = fitz.Rect(span.bbox)
        
        # Add slight padding for better visual appearance
        padding = 1.0
        rect.x0 -= padding
        rect.y0 -= padding
        rect.x1 += padding
        rect.y1 += padding
        
        # Add highlight annotation
        highlight = page.add_highlight_annot(rect)
        
        # Set color with opacity
        highlight.set_colors(stroke=color)
        highlight.set_opacity(opacity)
        
        # Update appearance
        highlight.update()
    
    def create_preview(self, input_path: str, classified_spans: List,
                      classifications: Dict[int, tuple], page_num: int = 0,
                      confidence_threshold: float = 0.6) -> bytes:
        """
        Create a preview image of a single page with highlights.
        
        Args:
            input_path: Path to input PDF
            classified_spans: List of TextSpan objects
            classifications: Dictionary of classifications
            page_num: Page number to preview
            confidence_threshold: Minimum confidence for highlighting
            
        Returns:
            PNG image bytes
        """
        doc = fitz.open(input_path)
        
        if page_num >= len(doc):
            doc.close()
            return None
        
        page = doc[page_num]
        
        # Apply highlights temporarily
        page_span_indices = [
            idx for idx, span in enumerate(classified_spans)
            if span.page_num == page_num
        ]
        
        for idx in page_span_indices:
            span = classified_spans[idx]
            category, confidence = classifications.get(idx, ('normal', 0.0))
            
            if confidence >= confidence_threshold and category != 'normal':
                self._highlight_span(page, span, category)
        
        # Render page to image
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for quality
        img_bytes = pix.tobytes("png")
        
        doc.close()
        return img_bytes
    
    def get_annotation_stats(self) -> Dict[str, int]:
        """Get statistics about applied annotations."""
        return {
            'total_annotations': self.annotations_applied
        }
    
    def batch_annotate(self, input_path: str, output_dir: str,
                      spans_by_page: Dict[int, List],
                      classifications: Dict[int, tuple]) -> List[str]:
        """
        Annotate multiple pages in parallel-ready format.
        
        Args:
            input_path: Input PDF path
            output_dir: Directory for output files
            spans_by_page: Dictionary mapping page numbers to spans
            classifications: Classification results
            
        Returns:
            List of output file paths
        """
        doc = fitz.open(input_path)
        output_paths = []
        
        for page_num in range(len(doc)):
            if page_num not in spans_by_page:
                continue
            
            # Create single-page document
            single_page_doc = fitz.open()
            single_page_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
            
            page = single_page_doc[0]
            spans = spans_by_page[page_num]
            
            # Apply annotations
            for idx, span in spans:
                category, confidence = classifications.get(idx, ('normal', 0.0))
                if confidence >= 0.6 and category != 'normal':
                    self._highlight_span(page, span, category)
            
            # Save page
            output_path = os.path.join(output_dir, f"page_{page_num}.pdf")
            single_page_doc.save(output_path)
            single_page_doc.close()
            output_paths.append(output_path)
        
        doc.close()
        return output_paths