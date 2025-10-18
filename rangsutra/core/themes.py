# Theme management
"""
Theme Management Module
Handles loading, saving, and validation of color themes.
"""

import json
import os
from typing import Dict, List
from pathlib import Path


class ThemeManager:
    """
    Manages color themes for PDF highlighting.
    """
    
    def __init__(self, theme_dir: str = "config"):
        """
        Initialize theme manager.
        
        Args:
            theme_dir: Directory containing theme JSON files
        """
        self.theme_dir = theme_dir
        self.current_theme = None
        self.available_themes = []
        self._scan_themes()
    
    def _scan_themes(self):
        """Scan theme directory for available themes."""
        if not os.path.exists(self.theme_dir):
            os.makedirs(self.theme_dir, exist_ok=True)
            return
        
        self.available_themes = []
        for file in os.listdir(self.theme_dir):
            if file.endswith('.json'):
                theme_path = os.path.join(self.theme_dir, file)
                try:
                    with open(theme_path, 'r') as f:
                        theme = json.load(f)
                        if self._validate_theme(theme):
                            self.available_themes.append(file)
                except Exception as e:
                    print(f"⚠ Could not load theme {file}: {e}")
    
    def _validate_theme(self, theme: Dict) -> bool:
        """
        Validate theme structure.
        
        Args:
            theme: Theme dictionary
            
        Returns:
            True if valid, False otherwise
        """
        required_keys = ['theme_name', 'categories']
        if not all(key in theme for key in required_keys):
            return False
        
        # Validate categories
        categories = theme.get('categories', {})
        for category, config in categories.items():
            if 'color' not in config:
                return False
            
            color = config['color']
            if not isinstance(color, list) or len(color) != 3:
                return False
            
            # Validate RGB values
            if not all(0 <= c <= 1 for c in color):
                return False
        
        return True
    
    def load_theme(self, theme_name: str) -> Dict:
        """
        Load a theme by name.
        
        Args:
            theme_name: Name of theme file (with or without .json)
            
        Returns:
            Theme dictionary
        """
        if not theme_name.endswith('.json'):
            theme_name += '.json'
        
        theme_path = os.path.join(self.theme_dir, theme_name)
        
        if not os.path.exists(theme_path):
            raise FileNotFoundError(f"Theme not found: {theme_name}")
        
        with open(theme_path, 'r') as f:
            theme = json.load(f)
        
        if not self._validate_theme(theme):
            raise ValueError(f"Invalid theme format: {theme_name}")
        
        self.current_theme = theme
        return theme
    
    def save_theme(self, theme: Dict, filename: str):
        """
        Save a theme to disk.
        
        Args:
            theme: Theme dictionary
            filename: Output filename
        """
        if not self._validate_theme(theme):
            raise ValueError("Invalid theme format")
        
        if not filename.endswith('.json'):
            filename += '.json'
        
        theme_path = os.path.join(self.theme_dir, filename)
        
        with open(theme_path, 'w') as f:
            json.dump(theme, f, indent=2)
        
        self._scan_themes()
    
    def get_default_theme(self) -> Dict:
        """Get the default theme."""
        default_path = os.path.join(self.theme_dir, 'default_theme.json')
        
        if os.path.exists(default_path):
            return self.load_theme('default_theme.json')
        
        # Return hardcoded default if file doesn't exist
        return {
            "theme_name": "Educational Default",
            "version": "1.0",
            "categories": {
                "heading": {
                    "color": [0.0, 0.8, 0.0],
                    "opacity": 0.3,
                    "description": "Main headings and titles"
                },
                "subheading": {
                    "color": [0.0, 0.6, 0.4],
                    "opacity": 0.25,
                    "description": "Subheadings"
                },
                "question": {
                    "color": [1.0, 0.0, 0.0],
                    "opacity": 0.25,
                    "description": "Questions"
                },
                "bullet_point": {
                    "color": [1.0, 1.0, 0.0],
                    "opacity": 0.2,
                    "description": "Bullet points"
                },
                "important": {
                    "color": [1.0, 0.5, 0.0],
                    "opacity": 0.25,
                    "description": "Emphasized text"
                },
                "definition": {
                    "color": [0.6, 0.0, 0.8],
                    "opacity": 0.2,
                    "description": "Definitions"
                },
                "example": {
                    "color": [0.0, 0.5, 1.0],
                    "opacity": 0.2,
                    "description": "Examples"
                },
                "code": {
                    "color": [0.2, 0.2, 0.2],
                    "opacity": 0.1,
                    "description": "Code snippets"
                }
            }
        }
    
    def list_themes(self) -> List[str]:
        """Get list of available themes."""
        return self.available_themes
    
    def create_custom_theme(self, theme_name: str, base_theme: str = None) -> Dict:
        """
        Create a new custom theme.
        
        Args:
            theme_name: Name for the new theme
            base_theme: Optional base theme to copy from
            
        Returns:
            New theme dictionary
        """
        if base_theme:
            theme = self.load_theme(base_theme).copy()
            theme['theme_name'] = theme_name
        else:
            theme = self.get_default_theme().copy()
            theme['theme_name'] = theme_name
        
        return theme
    
    def update_category_color(self, theme: Dict, category: str,
                            color: List[float], opacity: float = None) -> Dict:
        """
        Update color for a category in a theme.
        
        Args:
            theme: Theme dictionary
            category: Category name
            color: RGB color as [r, g, b]
            opacity: Optional opacity value
            
        Returns:
            Updated theme dictionary
        """
        if category not in theme['categories']:
            theme['categories'][category] = {}
        
        theme['categories'][category]['color'] = color
        
        if opacity is not None:
            theme['categories'][category]['opacity'] = opacity
        
        return theme
    
    def export_theme_css(self, theme: Dict) -> str:
        """
        Export theme as CSS variables (useful for web preview).
        
        Args:
            theme: Theme dictionary
            
        Returns:
            CSS string
        """
        css_lines = [":root {"]
        
        for category, config in theme.get('categories', {}).items():
            color = config['color']
            rgb = f"rgb({int(color[0]*255)}, {int(color[1]*255)}, {int(color[2]*255)})"
            css_lines.append(f"  --{category}-color: {rgb};")
            
            if 'opacity' in config:
                css_lines.append(f"  --{category}-opacity: {config['opacity']};")
        
        css_lines.append("}")
        return "\n".join(css_lines)