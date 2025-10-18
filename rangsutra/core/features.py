# Feature engineering
"""
Feature Extraction Module
Computes rich features from text spans for classification.
"""

import re
import numpy as np
from typing import List, Dict
from collections import Counter


class FeatureExtractor:
    """
    Extracts linguistic and layout features from text spans.
    """
    
    def __init__(self, spans: List):
        self.spans = spans
        self._compute_document_statistics()
        
    def _compute_document_statistics(self):
        """Pre-compute document-wide statistics for normalization."""
        if not self.spans:
            self.median_size = 12.0
            self.max_size = 12.0
            self.min_indent = 0.0
            self.font_ranks = {}
            return
        
        sizes = [s.size for s in self.spans]
        self.median_size = np.median(sizes)
        self.max_size = max(sizes)
        
        indents = [s.x_indent for s in self.spans]
        self.min_indent = min(indents)
        
        # Rank fonts by frequency (most common = rank 0)
        fonts = [s.font for s in self.spans]
        font_counts = Counter(fonts)
        self.font_ranks = {
            font: rank 
            for rank, (font, _) in enumerate(font_counts.most_common())
        }
    
    def extract_features(self, span, line_spans: List = None) -> Dict[str, float]:
        """
        Extract comprehensive features from a text span.
        
        Args:
            span: TextSpan object
            line_spans: Other spans on the same line (for context)
            
        Returns:
            Dictionary of feature values
        """
        text = span.text
        features = {}
        
        # === Layout Features ===
        features['font_size'] = span.size
        features['font_size_ratio'] = span.size / self.median_size if self.median_size > 0 else 1.0
        features['is_largest_on_page'] = float(span.size >= self.max_size - 0.5)
        
        features['is_bold'] = float(span.is_bold)
        features['is_italic'] = float(span.is_italic)
        features['is_monospace'] = float(span.is_monospace)
        
        features['x_indent'] = span.x_indent - self.min_indent
        features['relative_indent'] = (span.x_indent - self.min_indent) / 100.0  # Normalize
        
        features['font_rank'] = self.font_ranks.get(span.font, 99)
        features['is_common_font'] = float(features['font_rank'] <= 2)
        
        # === Text Length Features ===
        features['text_length'] = len(text)
        features['word_count'] = len(text.split())
        features['char_per_word'] = len(text) / max(1, len(text.split()))
        
        # === Punctuation Features ===
        features['ends_with_question'] = float(text.rstrip().endswith('?'))
        features['ends_with_colon'] = float(text.rstrip().endswith(':'))
        features['ends_with_period'] = float(text.rstrip().endswith('.'))
        features['has_question_words'] = float(bool(re.search(
            r'\b(what|when|where|who|whom|whose|why|how|which|can|could|would|should|is|are|do|does|did)\b',
            text.lower()
        )))
        
        # === Capitalization Features ===
        words = text.split()
        if words:
            features['all_caps'] = float(text.isupper())
            features['title_case'] = float(sum(1 for w in words if w and w[0].isupper()) / len(words))
            features['first_word_caps'] = float(words[0][0].isupper() if words[0] else 0)
        else:
            features['all_caps'] = 0.0
            features['title_case'] = 0.0
            features['first_word_caps'] = 0.0
        
        # === List & Bullet Features ===
        bullet_pattern = r'^[\s]*[•\-\*\+\◦\▪\▫\■\□\◆\◇\→\⇒\➔\➤\►\☞]\s+'
        number_pattern = r'^[\s]*\d+[\.\)]\s+'
        letter_pattern = r'^[\s]*[a-zA-Z][\.\)]\s+'
        
        features['starts_with_bullet'] = float(bool(re.match(bullet_pattern, text)))
        features['starts_with_number'] = float(bool(re.match(number_pattern, text)))
        features['starts_with_letter'] = float(bool(re.match(letter_pattern, text)))
        features['is_list_item'] = float(
            features['starts_with_bullet'] or 
            features['starts_with_number'] or 
            features['starts_with_letter']
        )
        
        # === Special Content Detection ===
        features['has_code_markers'] = float(bool(re.search(r'[{}()\[\];=<>]', text)))
        features['has_numbers'] = float(bool(re.search(r'\d', text)))
        features['number_density'] = sum(1 for c in text if c.isdigit()) / max(1, len(text))
        
        # === Definition Detection ===
        definition_pattern = r'\b(is|are|means|refers to|defined as|definition)\b'
        features['is_definition'] = float(bool(re.search(definition_pattern, text.lower())))
        
        # === Example Detection ===
        example_pattern = r'\b(for example|e\.g\.|such as|for instance|like)\b'
        features['is_example'] = float(bool(re.search(example_pattern, text.lower())))
        
        # === Emphasis Detection ===
        features['has_quotes'] = float('"' in text or "'" in text)
        features['has_parentheses'] = float('(' in text and ')' in text)
        
        # === Position Features ===
        if line_spans:
            features['is_first_on_line'] = float(span == line_spans[0])
            features['is_alone_on_line'] = float(len(line_spans) == 1)
        else:
            features['is_first_on_line'] = 0.0
            features['is_alone_on_line'] = 0.0
        
        return features
    
    def extract_batch_features(self, spans_with_lines: List[tuple]) -> List[Dict[str, float]]:
        """
        Extract features for multiple spans efficiently.
        
        Args:
            spans_with_lines: List of (span, line_spans) tuples
            
        Returns:
            List of feature dictionaries
        """
        return [
            self.extract_features(span, line_spans)
            for span, line_spans in spans_with_lines
        ]
    
    def get_feature_vector(self, features: Dict[str, float]) -> np.ndarray:
        """Convert feature dictionary to numpy array."""
        # Maintain consistent ordering
        feature_names = sorted(features.keys())
        return np.array([features[name] for name in feature_names])
    
    def get_feature_names(self, features: Dict[str, float]) -> List[str]:
        """Get ordered list of feature names."""
        return sorted(features.keys())