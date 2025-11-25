"""
Stub reporter module for generating human-readable stub reports.
Provides information about pending stubs and manual completion instructions.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

# Import required modules
from src.models import StubEntry
from src.stub.registry import StubRegistry


class StubReporter:
    """
    Generates reports about stub emails for user review.
    
    Responsibilities:
    - Generate complete stub status report
    - List pending stubs (in /stubs/ folder)
    - List recently completed stubs (moved to /processed/)
    - Provide statistics (total, pending, completed)
    - Provide manual completion instructions (Bloomberg Terminal)
    - Format output for console or file
    """
    
    def __init__(self):
        """Initialize stub reporter."""
        self.logger = logging.getLogger(__name__)
    
    def generate_report(self, registry: StubRegistry, 
                       session_stats: Optional[Dict[str, int]] = None) -> str:
        """
        Generate complete stub report.
        
        Args:
            registry: StubRegistry with current stub data
            session_stats: Optional dict with session statistics
            
        Returns:
            Formatted report string
        """
        report_lines = []
        
        # Header
        report_lines.extend(self._format_header())
        
        # Session statistics (if provided)
        if session_stats:
            report_lines.extend(self._format_session_stats(session_stats))
        
        # Overall statistics
        stats = registry.get_statistics()
        report_lines.extend(self.format_statistics(stats))
        
        # Pending stubs
        pending = registry.get_all_pending()
        report_lines.extend(self.format_pending_stubs(pending))
        
        # Recently completed stubs (if any in session)
        if session_stats and session_stats.get('stubs_completed', 0) > 0:
            completed = registry.get_all_completed()
            # Get only recently completed (last 10)
            recent_completed = completed[-10:] if len(completed) > 10 else completed
            report_lines.extend(self.format_completed_stubs(recent_completed))
        
        # Manual completion instructions
        if pending:
            report_lines.extend(self.format_terminal_instructions())
        
        # Footer
        report_lines.extend(self._format_footer(pending))
        
        return "\n".join(report_lines)
    
    def _format_header(self) -> List[str]:
        """Format report header."""
        return [
            "",
            "="*60,
            "STUB REPORT",
            "="*60,
            ""
        ]
    
    def _format_session_stats(self, session_stats: Dict[str, int]) -> List[str]:
        """Format session statistics."""
        lines = [
            "Session Summary:",
            f"  New stubs created: {session_stats.get('stubs_created', 0)}",
            f"  Stubs completed: {session_stats.get('stubs_completed', 0)}",
            ""
        ]
        return lines
    
    def format_statistics(self, stats: Dict[str, Any]) -> List[str]:
        """Format overall statistics."""
        lines = [
            f"Total stubs pending: {stats['pending']}",
            f"Total stubs completed: {stats['completed']}",
            f"Pending with Story ID: {stats['pending_with_story_id']}",
            f"Pending without Story ID: {stats['pending_without_story_id']}",
            ""
        ]
        return lines
    
    def format_pending_stubs(self, pending: List[StubEntry]) -> List[str]:
        """Format list of pending stubs."""
        if not pending:
            return ["No stubs pending. All emails have been fully indexed.", ""]
        
        lines = [
            "Stubs awaiting manual completion:",
            ""
        ]
        
        for i, stub in enumerate(pending, 1):
            story_id = f"Story ID: {stub.story_id}" if stub.story_id else "No Story ID"
            lines.append(f"{i}. {stub.subject[:60]}...")
            lines.append(f"   {story_id}")
            lines.append(f"   Fingerprint: {stub.fingerprint}")
            lines.append("")
        
        return lines
    
    def format_completed_stubs(self, completed: List[StubEntry]) -> List[str]:
        """Format list of recently completed stubs."""
        if not completed:
            return []
        
        lines = [
            "Recently completed stubs:",
            ""
        ]
        
        for stub in completed:
            lines.append(f"- {stub.subject[:60]}...")
            if stub.completed_at:
                lines.append(f"  Completed at: {stub.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append("")
        
        return lines
    
    def format_terminal_instructions(self) -> List[str]:
        """Format manual completion instructions."""
        lines = [
            "="*60,
            "HOW TO COMPLETE STUBS MANUALLY",
            "="*60,
            "",
            "Stubs are incomplete email notifications from Bloomberg.",
            "To get the full article content:",
            "",
            "1. Open Bloomberg Terminal (requires subscription)",
            "2. Press <GO> and search for the Story ID (e.g., L123ABC456)",
            "3. The full article will appear in the Terminal",
            "4. Bloomberg will send the complete email to your inbox",
            "5. Re-run sync_emails.py to index the complete article",
            "",
            "The stub in /stubs/ will automatically move to /processed/",
            "when the complete version is detected and indexed.",
            ""
        ]
        return lines
    
    def _format_footer(self, pending: List[StubEntry]) -> List[str]:
        """Format report footer."""
        if pending:
            return [
                "="*60,
                f"Total pending stubs: {len(pending)}",
                "="*60,
                ""
            ]
        else:
            return [
                "="*60,
                "All emails fully indexed!",
                "="*60,
                ""
            ]