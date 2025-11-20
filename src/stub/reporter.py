"""
Stub reporter module for generating human-readable stub reports.
Provides information about pending stubs and manual completion instructions.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

# Import required modules
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from models import StubEntry
from stub.registry import StubRegistry


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
            session_stats: Optional dict with session statistics:
                {
                    'stubs_created': int,  # New stubs in this session
                    'stubs_completed': int  # Stubs completed in this session
                }
            
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
        lines = []
        lines.append("=" * 80)
        lines.append("BLOOMBERG RAG - STUB STATUS REPORT")
        lines.append("=" * 80)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        return lines
    
    def _format_session_stats(self, session_stats: Dict[str, int]) -> List[str]:
        """Format session statistics."""
        lines = []
        lines.append("SESSION SUMMARY")
        lines.append("-" * 80)
        lines.append(f"New stubs created:       {session_stats.get('stubs_created', 0)}")
        lines.append(f"Stubs completed:         {session_stats.get('stubs_completed', 0)}")
        lines.append("")
        return lines
    
    def format_statistics(self, stats: Dict[str, Any]) -> List[str]:
        """
        Format overall statistics.
        
        Args:
            stats: Statistics dict from registry.get_statistics()
            
        Returns:
            List of formatted lines
        """
        lines = []
        lines.append("OVERALL STATISTICS")
        lines.append("-" * 80)
        lines.append(f"Total stubs tracked:     {stats.get('total', 0)}")
        lines.append(f"Pending (awaiting):      {stats.get('pending', 0)}")
        lines.append(f"Completed (archived):    {stats.get('completed', 0)}")
        lines.append(f"  - With Story ID:       {stats.get('pending_with_story_id', 0)}")
        lines.append(f"  - Without Story ID:    {stats.get('pending_without_story_id', 0)}")
        lines.append("")
        return lines
    
    def format_pending_stubs(self, stubs: List[StubEntry]) -> List[str]:
        """
        Format list of pending stubs.
        
        Args:
            stubs: List of pending StubEntry objects
            
        Returns:
            List of formatted lines
        """
        lines = []
        lines.append("PENDING STUBS (in /stubs/ folder)")
        lines.append("-" * 80)
        
        if not stubs:
            lines.append("✓ No pending stubs - all clear!")
            lines.append("")
            return lines
        
        lines.append(f"Found {len(stubs)} pending stub(s) awaiting manual completion:")
        lines.append("")
        
        for i, stub in enumerate(stubs, 1):
            lines.append(f"{i}. {stub.subject}")
            lines.append(f"   Story ID:    {stub.story_id or 'N/A'}")
            lines.append(f"   Received:    {stub.received_time.strftime('%Y-%m-%d %H:%M')}")
            lines.append(f"   Entry ID:    {stub.outlook_entry_id[:20]}...")
            
            # Add Bloomberg URL if Story ID available
            if stub.story_id:
                url = f"https://bloomberg.com/news/articles/{stub.story_id}"
                lines.append(f"   URL:         {url}")
            
            lines.append("")
        
        return lines
    
    def format_completed_stubs(self, stubs: List[StubEntry]) -> List[str]:
        """
        Format list of recently completed stubs.
        
        Args:
            stubs: List of completed StubEntry objects
            
        Returns:
            List of formatted lines
        """
        lines = []
        lines.append("RECENTLY COMPLETED STUBS (moved to /processed/)")
        lines.append("-" * 80)
        
        if not stubs:
            lines.append("No stubs completed in this session.")
            lines.append("")
            return lines
        
        lines.append(f"Completed {len(stubs)} stub(s) in this session:")
        lines.append("")
        
        for i, stub in enumerate(stubs, 1):
            lines.append(f"{i}. {stub.subject}")
            lines.append(f"   Story ID:    {stub.story_id or 'N/A'}")
            lines.append(f"   Completed:   {stub.completed_at.strftime('%Y-%m-%d %H:%M') if stub.completed_at else 'N/A'}")
            lines.append("")
        
        return lines
    
    def format_terminal_instructions(self) -> List[str]:
        """
        Format manual completion instructions for Bloomberg Terminal.
        
        Returns:
            List of formatted lines with step-by-step instructions
        """
        lines = []
        lines.append("MANUAL COMPLETION INSTRUCTIONS")
        lines.append("-" * 80)
        lines.append("To complete pending stubs manually via Bloomberg Terminal:")
        lines.append("")
        lines.append("1. Open Bloomberg Terminal")
        lines.append("")
        lines.append("2. For each stub above, open the article URL in Terminal or web browser")
        lines.append("")
        lines.append("3. Read the full article content")
        lines.append("")
        lines.append("4. In Outlook, find the stub email in 'Bloomberg subs/stubs/' folder")
        lines.append("")
        lines.append("5. Forward or send yourself the COMPLETE article as a new email")
        lines.append("   - Make sure the email contains the full article text")
        lines.append("   - The Story ID in the URL must match the stub")
        lines.append("")
        lines.append("6. The system will automatically match and archive the stub on next sync")
        lines.append("")
        lines.append("NOTE: Stubs are moved to 'Bloomberg subs/processed/' when completed.")
        lines.append("")
        return lines
    
    def _format_footer(self, pending_stubs: List[StubEntry]) -> List[str]:
        """Format report footer."""
        lines = []
        lines.append("=" * 80)
        
        if pending_stubs:
            lines.append(f"⚠  ACTION REQUIRED: {len(pending_stubs)} stub(s) need manual completion")
            lines.append("   See instructions above for completing stubs via Bloomberg Terminal")
        else:
            lines.append("✓  All stubs completed - no action required")
        
        lines.append("=" * 80)
        lines.append("")
        return lines
    
    def print_report(self, registry: StubRegistry, 
                    session_stats: Optional[Dict[str, int]] = None):
        """
        Generate and print report to console.
        
        Args:
            registry: StubRegistry instance
            session_stats: Optional session statistics
        """
        report = self.generate_report(registry, session_stats)
        print(report)
    
    def save_report(self, registry: StubRegistry, output_path: Path,
                   session_stats: Optional[Dict[str, int]] = None) -> bool:
        """
        Generate and save report to file.
        
        Args:
            registry: StubRegistry instance
            output_path: Path to save report file
            session_stats: Optional session statistics
            
        Returns:
            True if saved successfully
        """
        try:
            report = self.generate_report(registry, session_stats)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report)
            
            self.logger.info(f"Report saved to: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save report: {e}")
            return False


# Example usage
if __name__ == "__main__":
    from datetime import datetime
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("="*80)
    print("STUB REPORTER TEST")
    print("="*80)
    
    # Create test registry
    test_registry_path = Path("test_stub_registry.json")
    registry = StubRegistry(test_registry_path)
    
    # Add test stubs
    stub1 = StubEntry(
        outlook_entry_id="STUB_ABC123",
        story_id="L123ABC456",
        fingerprint="swiss watch exports fell_20241120",
        subject="Swiss Watch Exports Fell Again in October",
        received_time=datetime(2024, 11, 20, 10, 30),
        status="pending"
    )
    
    stub2 = StubEntry(
        outlook_entry_id="STUB_DEF789",
        story_id=None,  # No Story ID
        fingerprint="ai regulation update_20241120",
        subject="AI Regulation Update from EU Commission",
        received_time=datetime(2024, 11, 20, 11, 45),
        status="pending"
    )
    
    stub3 = StubEntry(
        outlook_entry_id="STUB_GHI012",
        story_id="L789XYZ123",
        fingerprint="tech earnings season_20241119",
        subject="Tech Earnings Season Kicks Off",
        received_time=datetime(2024, 11, 19, 15, 20),
        status="completed",
        completed_at=datetime(2024, 11, 20, 9, 0)
    )
    
    registry.add_stub(stub1)
    registry.add_stub(stub2)
    registry.add_stub(stub3)
    
    # Create reporter
    reporter = StubReporter()
    
    # Session statistics
    session_stats = {
        'stubs_created': 2,
        'stubs_completed': 1
    }
    
    # Generate and print report
    print("\n" + "="*80)
    print("GENERATED REPORT:")
    print("="*80 + "\n")
    
    reporter.print_report(registry, session_stats)
    
    # Cleanup test file
    if test_registry_path.exists():
        test_registry_path.unlink()
        print("\n✓ Cleaned up test registry file")