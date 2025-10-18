"""
RangSutra - Context-Aware PDF Note Highlighting App
Main Streamlit Application
"""

import streamlit as st
import os
import time
import tempfile
from pathlib import Path

# Core imports
from core import (
    LayoutExtractor,
    FeatureExtractor,
    TextClassifier,
    PDFAnnotator,
    ThemeManager
)
from utils import CacheManager, ParallelProcessor

# Page configuration
st.set_page_config(
    page_title="RangSutra - Smart PDF Highlighter",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stat-box {
        background: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .success-box {
        background: #d4edda;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #28a745;
    }
</style>
""", unsafe_allow_html=True)


# Initialize session state
def init_session_state():
    """Initialize session state variables."""
    if 'pdf_uploaded' not in st.session_state:
        st.session_state.pdf_uploaded = False
    if 'processing_complete' not in st.session_state:
        st.session_state.processing_complete = False
    if 'current_theme' not in st.session_state:
        theme_manager = ThemeManager()
        st.session_state.current_theme = theme_manager.get_default_theme()
    if 'classified_spans' not in st.session_state:
        st.session_state.classified_spans = None
    if 'classifications' not in st.session_state:
        st.session_state.classifications = None
    if 'output_path' not in st.session_state:
        st.session_state.output_path = None


def process_pdf(uploaded_file, theme, use_parallel=True, confidence_threshold=0.6):
    """
    Main PDF processing pipeline.
    
    Args:
        uploaded_file: Streamlit UploadedFile object
        theme: Theme configuration dictionary
        use_parallel: Whether to use parallel processing
        confidence_threshold: Minimum confidence for highlighting
        
    Returns:
        Tuple of (output_path, statistics)
    """
    # Create temporary file for uploaded PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_input:
        tmp_input.write(uploaded_file.read())
        input_path = tmp_input.name
    
    # Progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Step 1: Extract layout
        status_text.text("📄 Extracting text layout...")
        progress_bar.progress(10)
        
        extractor = LayoutExtractor()
        spans = extractor.extract_from_pdf(input_path)
        
        if not spans:
            st.error("No text found in PDF!")
            return None, None
        
        progress_bar.progress(25)
        
        # Step 2: Extract features
        status_text.text("🔍 Analyzing text features...")
        
        feature_extractor = FeatureExtractor(spans)
        
        # Group spans into lines for context
        features_list = []
        for page_num in range(len(extractor.page_dimensions)):
            lines = extractor.group_spans_into_lines(page_num)
            for line in lines:
                for span in line:
                    features = feature_extractor.extract_features(span, line)
                    features_list.append(features)
        
        progress_bar.progress(45)
        
        # Step 3: Classify spans
        status_text.text("🎯 Classifying text elements...")
        
        classifier = TextClassifier(use_ml=False, confidence_threshold=confidence_threshold)
        classifications = classifier.classify_document(spans, features_list)
        
        progress_bar.progress(70)
        
        # Step 4: Apply annotations
        status_text.text("🎨 Applying highlights...")
        
        annotator = PDFAnnotator(theme)
        
        # Create output file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_output:
            output_path = tmp_output.name
        
        annotator.annotate_pdf(
            input_path=input_path,
            output_path=output_path,
            classified_spans=spans,
            classifications=classifications,
            confidence_threshold=confidence_threshold
        )
        
        progress_bar.progress(100)
        status_text.text("✅ Processing complete!")
        
        # Gather statistics
        stats = classifier.get_statistics(classifications)
        stats['total_spans'] = len(spans)
        stats['annotations_applied'] = annotator.annotations_applied
        stats['font_stats'] = extractor.get_font_statistics()
        
        # Store in session state
        st.session_state.classified_spans = spans
        st.session_state.classifications = classifications
        st.session_state.output_path = output_path
        
        # Cleanup
        os.unlink(input_path)
        
        return output_path, stats
        
    except Exception as e:
        st.error(f"Error processing PDF: {str(e)}")
        if os.path.exists(input_path):
            os.unlink(input_path)
        return None, None


def main():
    """Main application function."""
    init_session_state()
    
    # Header
    st.markdown('<div class="main-header">📚 RangSutra</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Context-Aware PDF Note Highlighting System</div>',
        unsafe_allow_html=True
    )
    
    # Sidebar - Configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Theme management
        st.subheader("🎨 Color Theme")
        theme_manager = ThemeManager()
        
        available_themes = theme_manager.list_themes()
        if available_themes:
            selected_theme = st.selectbox(
                "Select Theme",
                available_themes,
                index=0 if available_themes else None
            )
            if st.button("Load Theme"):
                st.session_state.current_theme = theme_manager.load_theme(selected_theme)
                st.success(f"Loaded theme: {selected_theme}")
        
        # Theme editor
        with st.expander("🎨 Edit Current Theme"):
            st.write("**Current Theme:** " + st.session_state.current_theme.get('theme_name', 'Unknown'))
            
            for category, config in st.session_state.current_theme.get('categories', {}).items():
                st.write(f"**{category.replace('_', ' ').title()}**")
                
                col1, col2 = st.columns(2)
                with col1:
                    color = config['color']
                    # Convert to hex for color picker
                    hex_color = "#{:02x}{:02x}{:02x}".format(
                        int(color[0]*255), int(color[1]*255), int(color[2]*255)
                    )
                    new_color = st.color_picker(
                        f"{category}_color",
                        hex_color,
                        key=f"color_{category}",
                        label_visibility="collapsed"
                    )
                    # Convert back to RGB
                    rgb = tuple(int(new_color.lstrip('#')[i:i+2], 16)/255 for i in (0, 2, 4))
                    st.session_state.current_theme['categories'][category]['color'] = list(rgb)
                
                with col2:
                    opacity = st.slider(
                        f"{category}_opacity",
                        0.0, 1.0,
                        config.get('opacity', 0.3),
                        0.05,
                        key=f"opacity_{category}",
                        label_visibility="collapsed"
                    )
                    st.session_state.current_theme['categories'][category]['opacity'] = opacity
        
        # Save custom theme
        new_theme_name = st.text_input("Save Theme As:")
        if st.button("💾 Save Theme") and new_theme_name:
            st.session_state.current_theme['theme_name'] = new_theme_name
            theme_manager.save_theme(st.session_state.current_theme, new_theme_name)
            st.success(f"Theme saved: {new_theme_name}.json")
        
        st.divider()
        
        # Processing options
        st.subheader("🔧 Processing Options")
        
        confidence_threshold = st.slider(
            "Confidence Threshold",
            0.0, 1.0, 0.6, 0.05,
            help="Minimum confidence level to apply highlights"
        )
        
        use_parallel = st.checkbox(
            "Enable Parallel Processing",
            value=True,
            help="Use multiprocessing for faster performance"
        )
        
        st.divider()
        
        # Info
        st.subheader("ℹ️ About")
        st.info(
            "**RangSutra** automatically highlights different text elements in PDFs:\n\n"
            "🟢 **Headings** - Section titles\n"
            "🔴 **Questions** - Interrogative text\n"
            "🟡 **Bullets** - List items\n"
            "🟠 **Important** - Bold/emphasized\n"
            "🟣 **Definitions** - Key terms\n"
            "🔵 **Examples** - Illustrations\n"
            "⚫ **Code** - Technical snippets"
        )
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📤 Upload PDF")
        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type=['pdf'],
            help="Upload your PDF document to highlight"
        )
        
        if uploaded_file is not None:
            st.session_state.pdf_uploaded = True
            
            # Display file info
            file_size = uploaded_file.size / (1024 * 1024)  # MB
            st.info(f"📄 **{uploaded_file.name}** ({file_size:.2f} MB)")
            
            # Process button
            if st.button("🚀 Process PDF", type="primary", use_container_width=True):
                with st.spinner("Processing..."):
                    output_path, stats = process_pdf(
                        uploaded_file,
                        st.session_state.current_theme,
                        use_parallel,
                        confidence_threshold
                    )
                    
                    if output_path and stats:
                        st.session_state.processing_complete = True
                        st.session_state.output_path = output_path
                        st.session_state.stats = stats
    
    with col2:
        st.header("📊 Statistics")
        
        if st.session_state.get('processing_complete', False) and st.session_state.get('stats'):
            stats = st.session_state.stats
            
            # Display statistics
            st.markdown('<div class="stat-box">', unsafe_allow_html=True)
            st.metric("Total Text Spans", stats.get('total_spans', 0))
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="stat-box">', unsafe_allow_html=True)
            st.metric("Highlights Applied", stats.get('annotations_applied', 0))
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Category breakdown
            st.subheader("By Category")
            for category in ['heading', 'subheading', 'question', 'bullet_point', 
                           'important', 'definition', 'example', 'code']:
                count = stats.get(category, 0)
                if count > 0:
                    st.write(f"**{category.replace('_', ' ').title()}:** {count}")
        else:
            st.info("Upload and process a PDF to see statistics")
    
    # Download section
    if st.session_state.get('processing_complete', False) and st.session_state.get('output_path'):
        st.divider()
        st.header("⬇️ Download Results")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.markdown(
                '<div class="success-box">✅ Your PDF has been successfully processed!</div>',
                unsafe_allow_html=True
            )
        
        with col2:
            # Preview button
            if st.button("👁️ Preview", use_container_width=True):
                st.info("Preview feature coming soon!")
        
        with col3:
            # Download button
            with open(st.session_state.output_path, 'rb') as f:
                pdf_bytes = f.read()
            
            st.download_button(
                label="📥 Download PDF",
                data=pdf_bytes,
                file_name=f"highlighted_{uploaded_file.name if uploaded_file else 'document.pdf'}",
                mime="application/pdf",
                use_container_width=True
            )
    
    # Footer
    st.divider()
    st.markdown(
        "<p style='text-align: center; color: #666;'>"
        "Made with ❤️ using Streamlit & PyMuPDF | "
        "<a href='https://github.com/yourusername/rangsutra'>GitHub</a>"
        "</p>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()