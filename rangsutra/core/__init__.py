"""
RangSutra Core Module
Provides PDF text extraction, classification, and annotation capabilities.
"""

from .layout_extractor import LayoutExtractor
from .features import FeatureExtractor
from .classifier import TextClassifier
from .annotator import PDFAnnotator
from .themes import ThemeManager

__all__ = [
    'LayoutExtractor',
    'FeatureExtractor',
    'TextClassifier',
    'PDFAnnotator',
    'ThemeManager'
]

__version__ = '1.0.0'