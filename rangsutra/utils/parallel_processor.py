# Multi-page processing
"""
Parallel Processing Module
Provides multiprocessing utilities for PDF page processing.
"""

from multiprocessing import Pool, cpu_count
from typing import List, Callable, Any
import os


class ParallelProcessor:
    """
    Handles parallel processing of PDF pages for performance optimization.
    """
    
    def __init__(self, num_workers: int = None):
        """
        Initialize parallel processor.
        
        Args:
            num_workers: Number of worker processes (default: CPU count - 1)
        """
        if num_workers is None:
            num_workers = max(1, cpu_count() - 1)
        self.num_workers = min(num_workers, cpu_count())
    
    def process_pages(self, page_data: List[Any], 
                     process_func: Callable, 
                     use_parallel: bool = True) -> List[Any]:
        """
        Process multiple pages in parallel.
        
        Args:
            page_data: List of page data to process
            process_func: Function to apply to each page
            use_parallel: Whether to use parallel processing
            
        Returns:
            List of processed results
        """
        if not use_parallel or len(page_data) < 3:
            # Sequential processing for small documents
            return [process_func(data) for data in page_data]
        
        # Parallel processing
        try:
            with Pool(processes=self.num_workers) as pool:
                results = pool.map(process_func, page_data)
            return results
        except Exception as e:
            print(f"⚠ Parallel processing failed: {e}")
            print("  Falling back to sequential processing...")
            return [process_func(data) for data in page_data]
    
    def process_pages_chunked(self, page_data: List[Any],
                              process_func: Callable,
                              chunk_size: int = 10) -> List[Any]:
        """
        Process pages in chunks for memory efficiency.
        
        Args:
            page_data: List of page data
            process_func: Processing function
            chunk_size: Number of pages per chunk
            
        Returns:
            List of processed results
        """
        results = []
        
        for i in range(0, len(page_data), chunk_size):
            chunk = page_data[i:i + chunk_size]
            chunk_results = self.process_pages(chunk, process_func)
            results.extend(chunk_results)
        
        return results
    
    def get_optimal_chunk_size(self, total_pages: int) -> int:
        """
        Calculate optimal chunk size based on document size.
        
        Args:
            total_pages: Total number of pages
            
        Returns:
            Optimal chunk size
        """
        if total_pages <= 10:
            return total_pages
        elif total_pages <= 50:
            return 10
        elif total_pages <= 200:
            return 20
        else:
            return 50
    
    @staticmethod
    def process_page_wrapper(args):
        """
        Wrapper function for processing a single page with multiple arguments.
        
        Args:
            args: Tuple of (page_num, pdf_path, other_args...)
            
        Returns:
            Processing result
        """
        # This is a helper for more complex parallel operations
        # Can be customized based on specific needs
        pass