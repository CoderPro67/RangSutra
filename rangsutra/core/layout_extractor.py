# PDF text extraction with positions
"""
Layout Extractor Module
Extracts text spans with precise positioning, font metadata, and styling information.
"""

import fitz  # PyMuPDF
from typing import List, Dict, Tuple
import numpy as np


class TextSpan:
    """Represents a single text span with its metadata."""
    
    def __init__(self, text: str, bbox: Tuple[float, float, float, float],
                 font: str, size: float, flags: int, color: int, page_num: int):
        self.text = text
        self.bbox = bbox  # (x0, y0, x1, y1)
        self.font = font
        self.size = size
        self.flags = flags  # Bit flags for bold, italic, etc.
        self.color = color
        self.page_num = page_num
        self.category = None  # Will be assigned by classifier
        
    @property
    def is_bold(self) -> bool:
        """Check if text is bold (flag bit 4)."""
        return bool(self.flags & 2**4)
    
    @property
    def is_italic(self) -> bool:
        """Check if text is italic (flag bit 1)."""
        return bool(self.flags & 2**1)
    
    @property
    def is_monospace(self) -> bool:
        """Check if text is monospace (flag bit 3)."""
        return bool(self.flags & 2**3)
    
    @property
    def width(self) -> float:
        """Calculate span width."""
        return self.bbox[2] - self.bbox[0]
    
    @property
    def height(self) -> float:
        """Calculate span height."""
        return self.bbox[3] - self.bbox[1]
    
    @property
    def x_indent(self) -> float:
        """Left indentation from page edge."""
        return self.bbox[0]
    
    def __repr__(self):
        return f"TextSpan('{self.text[:30]}...', size={self.size:.1f}, bold={self.is_bold})"


class LayoutExtractor:
    """
    Extracts text layout information from PDFs with high fidelity.
    Preserves exact positioning, fonts, and styling.
    """
    
    def __init__(self):
        self.spans: List[TextSpan] = []
        self.page_dimensions: List[Tuple[float, float]] = []
        
    def extract_from_pdf(self, pdf_path: str) -> List[TextSpan]:
        """
        Extract all text spans from a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of TextSpan objects with metadata
        """
        self.spans = []
        self.page_dimensions = []
        
        doc = fitz.open(pdf_path)
        
        for page_num, page in enumerate(doc):
            # Store page dimensions
            self.page_dimensions.append((page.rect.width, page.rect.height))
            
            # Extract text with detailed formatting
            blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
            
            for block in blocks.get("blocks", []):
                if block.get("type") == 0:  # Text block
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text = span.get("text", "").strip()
                            if not text:
                                continue
                            
                            # Extract all metadata
                            bbox = tuple(span.get("bbox", (0, 0, 0, 0)))
                            font = span.get("font", "unknown")
                            size = span.get("size", 12.0)
                            flags = span.get("flags", 0)
                            color = span.get("color", 0)
                            
                            text_span = TextSpan(
                                text=text,
                                bbox=bbox,
                                font=font,
                                size=size,
                                flags=flags,
                                color=color,
                                page_num=page_num
                            )
                            
                            self.spans.append(text_span)
        
        doc.close()
        return self.spans
    
    def get_page_spans(self, page_num: int) -> List[TextSpan]:
        """Get all spans for a specific page."""
        return [span for span in self.spans if span.page_num == page_num]
    
    def get_font_statistics(self) -> Dict[str, any]:
        """
        Analyze font usage across the document.
        Useful for identifying heading fonts vs body text.
        """
        if not self.spans:
            return {}
        
        sizes = [span.size for span in self.spans]
        fonts = [span.font for span in self.spans]
        
        # Count font occurrences
        from collections import Counter
        font_counts = Counter(fonts)
        size_counts = Counter(sizes)
        
        return {
            'most_common_font': font_counts.most_common(1)[0][0] if font_counts else None,
            'most_common_size': size_counts.most_common(1)[0][0] if size_counts else None,
            'size_range': (min(sizes), max(sizes)),
            'unique_fonts': len(font_counts),
            'font_distribution': dict(font_counts.most_common(10))
        }
    
    def group_spans_into_lines(self, page_num: int, tolerance: float = 2.0) -> List[List[TextSpan]]:
        """
        Group spans into lines based on vertical position.
        
        Args:
            page_num: Page number to process
            tolerance: Vertical tolerance for grouping (points)
            
        Returns:
            List of lines, where each line is a list of TextSpan objects
        """
        page_spans = self.get_page_spans(page_num)
        if not page_spans:
            return []
        
        # Sort by vertical position (y0)
        sorted_spans = sorted(page_spans, key=lambda s: s.bbox[1])
        
        lines = []
        current_line = [sorted_spans[0]]
        current_y = sorted_spans[0].bbox[1]
        
        for span in sorted_spans[1:]:
            if abs(span.bbox[1] - current_y) <= tolerance:
                current_line.append(span)
            else:
                # Sort current line by horizontal position
                current_line.sort(key=lambda s: s.bbox[0])
                lines.append(current_line)
                current_line = [span]
                current_y = span.bbox[1]
        
        # Add last line
        if current_line:
            current_line.sort(key=lambda s: s.bbox[0])
            lines.append(current_line)
        
        return lines
    
    def get_line_text(self, line: List[TextSpan]) -> str:
        """Reconstruct text from a line of spans."""
        return " ".join(span.text for span in line)