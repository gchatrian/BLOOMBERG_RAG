"""
Stub matcher module for matching complete emails with pending stubs.
Handles stub completion and cleanup via Story ID or fingerprint matching.
"""

from typing import Optional, Tuple
from datetime import datetime
import logging

# Import required modules
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from models import EmailDocument, StubEntry
from stub.registry import StubRegistry


class StubMatcher:
    """
    Matches complete emails with pending stubs and manages cleanup.
    
    Responsibilities:
    - Find matching stubs for complete emails
    - Match by Story ID (primary method)
    - Match by fingerprint (fallback method)
    - Move matched stub from /stubs/ to /processed/
    - Update registry status to "completed"
    
    Matching priority:
    1. Story ID match (if both stub and complete have Story ID)
    2. Fingerprint match (subject + date, fallback if no Story ID)
    """
    
    def __init__(self, registry: StubRegistry):
        """
        Initialize stub matcher.
        
        Args:
            registry: StubRegistry instance for stub tracking
        """
        self.registry = registry
        self.logger = logging.getLogger(__name__)
    
    def find_matching_stub(self, email_document: EmailDocument) -> Optional[StubEntry]:
        """
        Find matching stub for a complete email.
        
        Tries matching in priority order:
        1. Story ID match (primary)
        2. Fingerprint match (fallback)
        
        Args:
            email_document: Complete EmailDocument to match
            
        Returns:
            Matching StubEntry or None if no match found
        """
        # Try Story ID match first (primary method)
        story_id = email_document.bloomberg_metadata.story_id
        
        if story_id:
            stub = self.match_by_story_id(story_id)
            if stub:
                self.logger.info(f"✓ Found stub match by Story ID: {story_id}")
                return stub
        
        # Fallback to fingerprint match
        fingerprint = email_document.get_fingerprint()
        stub = self.match_by_fingerprint(fingerprint)
        
        if stub:
            self.logger.info(f"✓ Found stub match by fingerprint: {fingerprint}")
            return stub
        
        # No match found
        self.logger.debug(f"No stub match found for: {email_document.subject[:50]}...")
        return None
    
    def match_by_story_id(self, story_id: str) -> Optional[StubEntry]:
        """
        Match by Bloomberg Story ID (primary matching method).
        
        Args:
            story_id: Bloomberg Story ID from complete email
            
        Returns:
            Matching pending StubEntry or None
        """
        if not story_id:
            return None
        
        return self.registry.find_by_story_id(story_id)
    
    def match_by_fingerprint(self, fingerprint: str) -> Optional[StubEntry]:
        """
        Match by fingerprint: subject + date (fallback matching method).
        
        Args:
            fingerprint: Fingerprint from complete email
            
        Returns:
            Matching pending StubEntry or None
        """
        if not fingerprint:
            return None
        
        return self.registry.find_by_fingerprint(fingerprint)
    
    def complete_stub(self, stub_entry: StubEntry, outlook_extractor) -> bool:
        """
        Complete a stub: move to /processed/ and update registry.
        
        Complete workflow:
        1. Move stub email from /stubs/ to /processed/ in Outlook
        2. Update registry status from "pending" to "completed"
        3. Record completion timestamp
        
        Args:
            stub_entry: StubEntry to complete
            outlook_extractor: OutlookExtractor instance for moving emails
            
        Returns:
            True if completed successfully, False otherwise
        """
        try:
            # Step 1: Move stub to /processed/ folder
            success = self.move_stub_to_processed(stub_entry.outlook_entry_id, outlook_extractor)
            
            if not success:
                self.logger.error(f"Failed to move stub to /processed/: {stub_entry.subject[:50]}...")
                return False
            
            # Step 2: Update registry status
            success = self.update_registry(stub_entry)
            
            if not success:
                self.logger.error(f"Failed to update registry: {stub_entry.subject[:50]}...")
                return False
            
            self.logger.info(f"✓ Completed stub: {stub_entry.subject[:50]}...")
            return True
            
        except Exception as e:
            self.logger.error(f"Error completing stub: {e}")
            return False
    
    def move_stub_to_processed(self, outlook_entry_id: str, outlook_extractor) -> bool:
        """
        Move stub email from /stubs/ to /processed/ folder.
        
        Args:
            outlook_entry_id: Unique Outlook identifier
            outlook_extractor: OutlookExtractor instance
            
        Returns:
            True if moved successfully, False otherwise
        """
        try:
            success = outlook_extractor.move_to_processed(outlook_entry_id)
            
            if success:
                self.logger.debug(f"Moved stub to /processed/ folder: {outlook_entry_id}")
            else:
                self.logger.error(f"Failed to move stub: {outlook_entry_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error moving stub to /processed/: {e}")
            return False
    
    def update_registry(self, stub_entry: StubEntry) -> bool:
        """
        Update registry status to "completed".
        
        Args:
            stub_entry: StubEntry to update
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            success = self.registry.update_status(
                outlook_entry_id=stub_entry.outlook_entry_id,
                new_status="completed",
                completed_at=datetime.now()
            )
            
            if success:
                self.logger.debug(f"Updated registry status to 'completed': {stub_entry.outlook_entry_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error updating registry: {e}")
            return False
    
    def process_complete_email(self, email_document: EmailDocument, 
                               outlook_extractor) -> Tuple[bool, Optional[StubEntry]]:
        """
        Process complete email: check for matching stub and complete it if found.
        
        Complete workflow for processing incoming complete email:
        1. Find matching stub (by Story ID or fingerprint)
        2. If match found: complete the stub (move + update registry)
        3. Return whether match was found and the stub entry
        
        Args:
            email_document: Complete EmailDocument
            outlook_extractor: OutlookExtractor instance
            
        Returns:
            Tuple of (match_found: bool, stub_entry: Optional[StubEntry])
        """
        # Find matching stub
        stub_entry = self.find_matching_stub(email_document)
        
        if not stub_entry:
            # No matching stub found, nothing to do
            return False, None
        
        # Complete the stub
        success = self.complete_stub(stub_entry, outlook_extractor)
        
        if success:
            self.logger.info(f"✓ Successfully completed stub for: {email_document.subject[:50]}...")
            return True, stub_entry
        else:
            self.logger.error(f"✗ Failed to complete stub for: {email_document.subject[:50]}...")
            return False, stub_entry


# Example usage
if __name__ == "__main__":
    from datetime import datetime
    from models import BloombergMetadata
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("="*60)
    print("STUB MATCHER TEST")
    print("="*60)
    
    # Create test registry
    test_registry_path = Path("test_stub_registry.json")
    registry = StubRegistry(test_registry_path)
    
    # Create matcher with registry
    matcher = StubMatcher(registry)
    
    # Create test stub entry and add to registry
    stub_entry = StubEntry(
        outlook_entry_id="STUB_ABC123",
        story_id="L123ABC456",
        fingerprint="swiss watch exports fell again in october_20241120",
        subject="Swiss Watch Exports Fell Again in October",
        received_time=datetime(2024, 11, 20, 10, 30),
        status="pending"
    )
    
    registry.add_stub(stub_entry)
    print("\n1. Added test stub to registry:")
    print(f"   Subject: {stub_entry.subject}")
    print(f"   Story ID: {stub_entry.story_id}")
    print(f"   Status: {stub_entry.status}")
    
    # Create complete email with matching Story ID
    metadata = BloombergMetadata(
        story_id="L123ABC456",
        category="BFW",
        author="John Doe"
    )
    
    complete_doc = EmailDocument(
        outlook_entry_id="COMPLETE_XYZ789",
        subject="Swiss Watch Exports Fell Again in October on US Tariff Hit",
        body="Full article content here...",
        raw_body="Raw body...",
        sender="bloomberg@bloomberg.net",
        received_date=datetime(2024, 11, 20, 12, 0),
        bloomberg_metadata=metadata,
        status="complete",
        is_stub=False
    )
    
    print("\n2. Created complete email document:")
    print(f"   Subject: {complete_doc.subject}")
    print(f"   Story ID: {complete_doc.bloomberg_metadata.story_id}")
    
    # Test Story ID matching
    print("\n3. Testing Story ID matching...")
    found_stub = matcher.match_by_story_id("L123ABC456")
    
    if found_stub:
        print(f"   ✓ Found matching stub: {found_stub.subject[:50]}...")
    else:
        print(f"   ✗ No matching stub found")
    
    # Test fingerprint matching
    print("\n4. Testing fingerprint matching...")
    fingerprint = complete_doc.get_fingerprint()
    print(f"   Complete email fingerprint: {fingerprint}")
    
    # Test find_matching_stub (will use Story ID)
    print("\n5. Testing find_matching_stub...")
    found = matcher.find_matching_stub(complete_doc)
    
    if found:
        print(f"   ✓ Found match: {found.subject[:50]}...")
        print(f"   Match method: Story ID")
    
    # Test update registry (without moving - no Outlook connection)
    print("\n6. Testing registry update...")
    success = matcher.update_registry(found)
    
    if success:
        print(f"   ✓ Updated registry status to 'completed'")
        
        # Verify update
        updated_stub = registry.get_stub_by_id(stub_entry.outlook_entry_id)
        print(f"   Status: {updated_stub.status}")
        print(f"   Completed at: {updated_stub.completed_at}")
    
    # Check statistics
    print("\n7. Registry statistics:")
    stats = registry.get_statistics()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # Cleanup test file
    if test_registry_path.exists():
        test_registry_path.unlink()
        print("\n✓ Cleaned up test registry file")