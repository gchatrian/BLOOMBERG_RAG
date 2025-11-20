"""
Stub manager module for organizing and moving stub emails.
Coordinates stub detection, registration, and folder movement.
"""

from typing import List
import logging

# Import required modules
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from models import EmailDocument, StubEntry
from stub.registry import StubRegistry


class StubManager:
    """
    Manages stub email organization and movement.
    
    Responsibilities:
    - Process identified stub emails
    - Create StubEntry objects
    - Register stubs in StubRegistry
    - Move stub emails to /stubs/ folder in Outlook
    - Maintain list of active (pending) stubs
    
    Coordinates:
    - StubDetector (detection)
    - StubRegistry (tracking)
    - OutlookExtractor (folder movement)
    """
    
    def __init__(self, registry: StubRegistry):
        """
        Initialize stub manager.
        
        Args:
            registry: StubRegistry instance for tracking stubs
        """
        self.registry = registry
        self.logger = logging.getLogger(__name__)
    
    def process_stub(self, email_document: EmailDocument, outlook_extractor) -> bool:
        """
        Process a stub email: register and move to /stubs/ folder.
        
        Complete workflow:
        1. Create StubEntry from EmailDocument
        2. Register in StubRegistry with "pending" status
        3. Move email from source to /stubs/ folder in Outlook
        
        Args:
            email_document: EmailDocument classified as stub
            outlook_extractor: OutlookExtractor instance for moving emails
            
        Returns:
            True if processed successfully, False otherwise
        """
        try:
            # Step 1: Register stub in registry
            stub_entry = self.register_stub(email_document)
            
            if not stub_entry:
                self.logger.error(f"Failed to register stub: {email_document.subject[:50]}...")
                return False
            
            # Step 2: Move email to /stubs/ folder
            success = self.move_stub_to_folder(email_document.outlook_entry_id, outlook_extractor)
            
            if not success:
                self.logger.error(f"Failed to move stub to folder: {email_document.subject[:50]}...")
                return False
            
            self.logger.info(f"✓ Processed stub: {email_document.subject[:50]}...")
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing stub: {e}")
            return False
    
    def register_stub(self, email_document: EmailDocument) -> StubEntry:
        """
        Create StubEntry and register in registry.
        
        Args:
            email_document: EmailDocument classified as stub
            
        Returns:
            StubEntry object or None if failed
        """
        try:
            # Create StubEntry
            stub_entry = StubEntry(
                outlook_entry_id=email_document.outlook_entry_id,
                story_id=email_document.bloomberg_metadata.story_id,
                fingerprint=email_document.get_fingerprint(),
                subject=email_document.subject,
                received_time=email_document.received_date,
                status="pending"
            )
            
            # Add to registry
            success = self.registry.add_stub(stub_entry)
            
            if not success:
                self.logger.warning(f"Stub already in registry: {email_document.subject[:50]}...")
                # Return existing stub
                return self.registry.get_stub_by_id(email_document.outlook_entry_id)
            
            self.logger.debug(f"Registered stub: Story ID={stub_entry.story_id}, Fingerprint={stub_entry.fingerprint}")
            
            return stub_entry
            
        except Exception as e:
            self.logger.error(f"Failed to register stub: {e}")
            return None
    
    def move_stub_to_folder(self, outlook_entry_id: str, outlook_extractor) -> bool:
        """
        Move stub email to /stubs/ folder in Outlook.
        
        Args:
            outlook_entry_id: Unique Outlook identifier
            outlook_extractor: OutlookExtractor instance
            
        Returns:
            True if moved successfully, False otherwise
        """
        try:
            success = outlook_extractor.move_to_stubs(outlook_entry_id)
            
            if success:
                self.logger.debug(f"Moved stub to /stubs/ folder: {outlook_entry_id}")
            else:
                self.logger.error(f"Failed to move stub: {outlook_entry_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error moving stub to folder: {e}")
            return False
    
    def get_active_stubs(self) -> List[StubEntry]:
        """
        Get list of all active (pending) stubs.
        
        Returns:
            List of StubEntry objects with status "pending"
        """
        return self.registry.get_all_pending()
    
    def get_stub_count(self) -> dict:
        """
        Get stub statistics.
        
        Returns:
            Dict with stub counts
        """
        return self.registry.get_statistics()


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
    print("STUB MANAGER TEST")
    print("="*60)
    
    # Create test registry
    test_registry_path = Path("test_stub_registry.json")
    registry = StubRegistry(test_registry_path)
    
    # Create manager
    manager = StubManager(registry)
    
    # Create test stub email document
    metadata = BloombergMetadata(
        story_id="L123ABC456",
        category="BFW",
        author=None
    )
    
    stub_doc = EmailDocument(
        outlook_entry_id="TEST_STUB_123",
        subject="Swiss Watch Exports Fell Again in October",
        body="Alert:\nSPOTLIGHT NEWS\nSource: BN (Bloomberg News)\nTickers...",
        raw_body="Raw body...",
        sender="bloomberg@bloomberg.net",
        received_date=datetime.now(),
        bloomberg_metadata=metadata,
        status="stub",
        is_stub=True
    )
    
    print("\n1. Test stub document:")
    print(f"   Subject: {stub_doc.subject}")
    print(f"   Story ID: {stub_doc.bloomberg_metadata.story_id}")
    print(f"   Fingerprint: {stub_doc.get_fingerprint()}")
    
    # Register stub (without moving - no Outlook connection in test)
    print("\n2. Registering stub...")
    stub_entry = manager.register_stub(stub_doc)
    
    if stub_entry:
        print(f"   ✓ Registered: {stub_entry.subject[:50]}...")
        print(f"   Status: {stub_entry.status}")
    
    # Get active stubs
    print("\n3. Active stubs:")
    active = manager.get_active_stubs()
    print(f"   Count: {len(active)}")
    for stub in active:
        print(f"   - {stub.subject[:50]}... (Story ID: {stub.story_id})")
    
    # Get statistics
    print("\n4. Stub statistics:")
    stats = manager.get_stub_count()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # Cleanup test file
    if test_registry_path.exists():
        test_registry_path.unlink()
        print("\n✓ Cleaned up test registry file")