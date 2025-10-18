# Text classification (heuristics + ML)
"""
Text Classification Module
Classifies text spans into categories using heuristics and optional ML models.
"""

import re
import numpy as np
from typing import List, Dict, Optional
from collections import defaultdict


class TextClassifier:
    """
    Hybrid classifier using rule-based heuristics and optional transformer models.
    Prioritizes speed while maintaining high accuracy.
    """
    
    def __init__(self, use_ml: bool = False, confidence_threshold: float = 0.6):
        """
        Initialize classifier.
        
        Args:
            use_ml: Whether to use ML model for ambiguous cases
            confidence_threshold: Minimum confidence for classification
        """
        self.use_ml = use_ml
        self.confidence_threshold = confidence_threshold
        self.ml_model = None
        
        if use_ml:
            self._load_ml_model()
    
    def _load_ml_model(self):
        """Load pre-trained transformer model (optional)."""
        try:
            from sentence_transformers import SentenceTransformer
            self.ml_model = SentenceTransformer('all-MiniLM-L6-v2')
            print("✓ ML model loaded successfully")
        except Exception as e:
            print(f"⚠ Could not load ML model: {e}")
            self.use_ml = False
    
    def classify_span(self, span, features: Dict[str, float]) -> tuple:
        """
        Classify a single text span.
        
        Args:
            span: TextSpan object
            features: Pre-computed features
            
        Returns:
            Tuple of (category, confidence)
        """
        text = span.text.strip()
        
        # Priority 1: Heading Detection (highest priority)
        if self._is_heading(text, features):
            if features['font_size_ratio'] >= 1.5:
                return ('heading', 0.95)
            else:
                return ('subheading', 0.90)
        
        # Priority 2: Question Detection
        if self._is_question(text, features):
            return ('question', 0.92)
        
        # Priority 3: Bullet/List Detection
        if self._is_bullet_point(text, features):
            return ('bullet_point', 0.88)
        
        # Priority 4: Code Detection
        if self._is_code(text, features):
            return ('code', 0.85)
        
        # Priority 5: Definition Detection
        if self._is_definition(text, features):
            return ('definition', 0.80)
        
        # Priority 6: Example Detection
        if self._is_example(text, features):
            return ('example', 0.78)
        
        # Priority 7: Important/Emphasis Detection
        if self._is_important(text, features):
            return ('important', 0.75)
        
        # Default: No highlighting
        return ('normal', 0.0)
    
    def _is_heading(self, text: str, features: Dict[str, float]) -> bool:
        """Detect headings using multiple signals."""
        # Strong signals
        if features['font_size_ratio'] >= 1.3:
            return True
        
        # Medium signals (combine multiple)
        heading_score = 0
        
        if features['is_bold']:
            heading_score += 2
        if features['is_alone_on_line']:
            heading_score += 1
        if features['title_case'] > 0.7:
            heading_score += 1
        if not features['ends_with_period']:
            heading_score += 1
        if features['word_count'] <= 8:
            heading_score += 1
        if features['ends_with_colon']:
            heading_score += 2
        
        # Check for heading patterns
        heading_patterns = [
            r'^(chapter|section|part|unit|lesson|module)\s+\d+',
            r'^\d+\.\s+[A-Z]',  # "1. Introduction"
            r'^[A-Z][A-Z\s]{2,}$',  # ALL CAPS (short)
        ]
        
        for pattern in heading_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                heading_score += 3
                break
        
        return heading_score >= 4
    
    def _is_question(self, text: str, features: Dict[str, float]) -> bool:
        """Detect questions."""
        # Explicit question mark
        if features['ends_with_question']:
            return True
        
        # Question words at start + appropriate punctuation
        question_starters = [
            'what', 'when', 'where', 'who', 'whom', 'whose', 'why', 'how', 'which',
            'can', 'could', 'would', 'should', 'will', 'do', 'does', 'did',
            'is', 'are', 'was', 'were', 'has', 'have', 'had'
        ]
        
        first_word = text.split()[0].lower().rstrip(',:;') if text.split() else ''
        if first_word in question_starters:
            # Extra validation
            if len(text.split()) >= 3:  # At least 3 words
                return True
        
        return False
    
    def _is_bullet_point(self, text: str, features: Dict[str, float]) -> bool:
        """Detect bullet points and list items."""
        if features['is_list_item']:
            return True
        
        # Check for common list indentation
        if features['relative_indent'] > 0.5 and not features['is_bold']:
            # Likely indented list item
            return True
        
        return False
    
    def _is_code(self, text: str, features: Dict[str, float]) -> bool:
        """Detect code snippets."""
        # Monospace font is strong signal
        if features['is_monospace']:
            return True
        
        # Code patterns
        code_score = 0
        
        if features['has_code_markers']:
            code_score += 2
        if features['number_density'] > 0.3:
            code_score += 1
        if re.search(r'[_\-][a-z]+[_\-]', text):  # snake_case, kebab-case
            code_score += 2
        if re.search(r'[a-z][A-Z]', text):  # camelCase
            code_score += 1
        
        # Common code keywords
        code_keywords = ['function', 'return', 'import', 'class', 'def', 'var', 'let', 'const']
        if any(keyword in text.lower() for keyword in code_keywords):
            code_score += 2
        
        return code_score >= 4
    
    def _is_definition(self, text: str, features: Dict[str, float]) -> bool:
        """Detect definitions."""
        if features['is_definition']:
            # Additional validation
            if features['word_count'] >= 5:
                return True
        
        # Pattern: "Term: definition" or "Term - definition"
        if re.match(r'^[A-Z][a-z]+\s*[:–-]\s+', text):
            return True
        
        return False
    
    def _is_example(self, text: str, features: Dict[str, float]) -> bool:
        """Detect examples."""
        return features['is_example'] and features['word_count'] >= 4
    
    def _is_important(self, text: str, features: Dict[str, float]) -> bool:
        """Detect emphasized/important text."""
        importance_score = 0
        
        if features['is_bold'] and not features['is_alone_on_line']:
            importance_score += 2
        if features['is_italic']:
            importance_score += 1
        if features['has_quotes']:
            importance_score += 1
        if features['all_caps'] and features['word_count'] <= 4:
            importance_score += 2
        
        return importance_score >= 2
    
    def classify_document(self, spans: List, features_list: List[Dict]) -> Dict[int, tuple]:
        """
        Classify all spans in a document.
        
        Args:
            spans: List of TextSpan objects
            features_list: List of feature dictionaries
            
        Returns:
            Dictionary mapping span index to (category, confidence)
        """
        classifications = {}
        
        for idx, (span, features) in enumerate(zip(spans, features_list)):
            category, confidence = self.classify_span(span, features)
            classifications[idx] = (category, confidence)
            
            # Store in span object
            span.category = category
        
        return classifications
    
    def get_statistics(self, classifications: Dict[int, tuple]) -> Dict[str, int]:
        """Get classification statistics."""
        stats = defaultdict(int)
        
        for category, confidence in classifications.values():
            if confidence >= self.confidence_threshold:
                stats[category] += 1
        
        return dict(stats)