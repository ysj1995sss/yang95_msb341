"""
Resume Tailorer package - Claude-powered resume tailoring engine.

Provides the ResumeTailorer class for rewriting resume content to match
job requirements while strictly adhering to the Career Truth Profile,
and the ResumeTailoringOptimizer for iterative improvement.
"""

from .resume_tailorer import ResumeTailorer
from .optimizer import ResumeTailoringOptimizer, OptimizationResult

__all__ = ["ResumeTailorer", "ResumeTailoringOptimizer", "OptimizationResult"]
