"""
Stub registry module for tracking incomplete Bloomberg emails.
Manages stub_registry.json for matching stubs with complete emails.
"""

import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

# Import models
from src.models import EmailDocument, StubEntry, BloombergMetadata


class StubRegistry:
    """
    Registry for tracking stub emails.
    
    Responsibilities:
    - Register new stub emails with "pending" status
    - Find stubs by Story ID (primary matching method)
    - Find stubs by fingerprint (fallback matching method)
    - Update stub status to "completed" when match found
    - Persist registry to disk (JSON)
    - Load registry from disk
    
    Registry schema:
    [
        {
            "outlook_entry_id": "ABC123",
            "story_id": "L123ABC456" or null,
            "fingerprint": "subject_20240115",
            "subject": "Swiss Watch Exports...",
            "received_time": "2024-01-15T10:30:00",
            "status": "pending" or "completed",
            "completed_at": "2024-01-15T12:00:00" or null
        },
        ...
    ]
    """
    
    def __init__(self, registry_path: Path):
        """
        Initialize stub registry.
        
        Args:
            registry_path: Path to stub_registry.json file
        """
        self.registry_path = registry_path
        self.stubs: List[StubEntry] = []
        self.logger = logging.getLogger(__name__)
        
        # Load existing registry if available
        if self.registry_path.exists():
            self.load()
    
    def add_stub(self, stub_entry: StubEntry) -> bool:
        """
        Add new stub to registry with "pending" status.
        
        Args:
            stub_entry: StubEntry object to add
            
        Returns:
            True if added successfully, False if already exists
        """
        # Check if stub already exists (by outlook_entry_id)
        existing = self.get_stub_by_id(stub_entry.outlook_entry_id)
        
        if existing:
            self.logger.warning(f"Stub already exists: {stub_entry.outlook_entry_id}")
            return False
        
        # Set status to pending
        stub_entry.status = "pending"
        stub_entry.completed_at = None
        
        # Add to registry
        self.stubs.append(stub_entry)
        
        self.logger.info(f"Added stub to registry: {stub_entry.subject[:50]}...")
        
        # Save to disk
        self.save()
        
        return True
    
    def get_stub_by_id(self, outlook_entry_id: str) -> Optional[StubEntry]:
        """
        Get stub by Outlook EntryID.
        
        Args:
            outlook_entry_id: Unique Outlook identifier
            
        Returns:
            StubEntry or None if not found
        """
        for stub in self.stubs:
            if stub.outlook_entry_id == outlook_entry_id:
                return stub
        
        return None
    
    def find_by_story_id(self, story_id: str) -> Optional[StubEntry]:
        """
        Find stub by Bloomberg Story ID (primary matching method).
        
        Args:
            story_id: Bloomberg Story ID (e.g., "L123ABC456")
            
        Returns:
            First matching pending stub or None
        """
        if not story_id:
            return None
        
        for stub in self.stubs:
            # Only match pending stubs
            if stub.status == "pending" and stub.story_id == story_id:
                self.logger.debug(f"Found stub match by Story ID: {story_id}")
                return stub
        
        return None
    
    def find_by_fingerprint(self, fingerprint: str) -> Optional[StubEntry]:
        """
        Find stub by fingerprint (fallback matching method).
        
        Used when Story ID is not available for matching.
        
        Args:
            fingerprint: Subject + date fingerprint
            
        Returns:
            First matching pending stub or None
        """
        if not fingerprint:
            return None
        
        for stub in self.stubs:
            # Only match pending stubs
            if stub.status == "pending" and stub.fingerprint == fingerprint:
                self.logger.debug(f"Found stub match by fingerprint: {fingerprint}")
                return stub
        
        return None
    
    def update_status(self, outlook_entry_id: str, new_status: str, 
                     completed_at: Optional[datetime] = None) -> bool:
        """
        Update stub status (pending to completed).
        
        Args:
            outlook_entry_id: Unique Outlook identifier
            new_status: New status ("completed")
            completed_at: Completion timestamp (default: now)
            
        Returns:
            True if updated, False if stub not found
        """
        stub = self.get_stub_by_id(outlook_entry_id)
        
        if not stub:
            self.logger.warning(f"Stub not found for update: {outlook_entry_id}")
            return False
        
        stub.status = new_status
        stub.completed_at = completed_at or datetime.now()
        
        self.logger.info(f"Updated stub status to '{new_status}': {stub.subject[:50]}...")
        
        # Save to disk
        self.save()
        
        return True
    
    def get_all_pending(self) -> List[StubEntry]:
        """
        Get all stubs with "pending" status.
        
        Returns:
            List of pending StubEntry objects
        """
        return [stub for stub in self.stubs if stub.status == "pending"]
    
    def get_all_completed(self) -> List[StubEntry]:
        """
        Get all stubs with "completed" status.
        
        Returns:
            List of completed StubEntry objects
        """
        return [stub for stub in self.stubs if stub.status == "completed"]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get registry statistics.
        
        Returns:
            Dict with counts and info
        """
        pending = self.get_all_pending()
        completed = self.get_all_completed()
        
        return {
            "total": len(self.stubs),
            "pending": len(pending),
            "completed": len(completed),
            "pending_with_story_id": len([s for s in pending if s.story_id]),
            "pending_without_story_id": len([s for s in pending if not s.story_id])
        }
    
    def save(self) -> bool:
        """
        Save registry to disk (JSON).
        
        Returns:
            True if saved successfully
        """
        try:
            # Ensure directory exists
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert to JSON-serializable format
            data = [stub.to_dict() for stub in self.stubs]
            
            # Write to file
            with open(self.registry_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.logger.debug(f"Saved registry: {len(self.stubs)} stubs")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save registry: {e}")
            return False
    
    def load(self) -> bool:
        """
        Load registry from disk (JSON).
        
        Returns:
            True if loaded successfully
        """
        try:
            if not self.registry_path.exists():
                self.logger.info("No existing registry found, starting fresh")
                return False
            
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert from dict to StubEntry objects
            self.stubs = [StubEntry.from_dict(entry) for entry in data]
            
            self.logger.info(f"Loaded registry: {len(self.stubs)} stubs")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load registry: {e}")
            return False
    
    @staticmethod
    def create_fingerprint(subject: str, received_date: datetime) -> str:
        """
        Create fingerprint for stub matching.
        
        Formula: subject.lower().strip() + "_" + date (YYYYMMDD)
        
        Args:
            subject: Email subject
            received_date: Email received date
            
        Returns:
            Fingerprint string
        """
        subject_clean = subject.lower().strip()
        date_str = received_date.strftime("%Y%m%d")
        return f"{subject_clean}_{date_str}"


# Example usage
if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create test registry
    test_registry_path = Path("test_stub_registry.json")
    registry = StubRegistry(test_registry_path)
    
    print("="*60)
    print("STUB REGISTRY TEST")
    print("="*60)
    
    # Create test stub entry
    stub1 = StubEntry(
        outlook_entry_id="ABC123",
        story_id="L123ABC456",
        fingerprint=StubRegistry.create_fingerprint(
            "Swiss Watch Exports Fell",
            datetime.now()
        ),
        subject="Swiss Watch Exports Fell Again in October",
        received_time=datetime.now(),
        status="pending"
    )
    
    # Add stub
    print("\n1. Adding stub to registry...")
    registry.add_stub(stub1)
    print(f"   OK Added: {stub1.subject}")
    
    # Check statistics
    print("\n2. Registry statistics:")
    stats = registry.get_statistics()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # Find by Story ID
    print("\n3. Finding stub by Story ID...")
    found = registry.find_by_story_id("L123ABC456")
    if found:
        print(f"   OK Found: {found.subject}")
    
    # Update status
    print("\n4. Updating stub status to 'completed'...")
    registry.update_status("ABC123", "completed")
    print(f"   OK Updated")
    
    # Check statistics again
    print("\n5. Registry statistics after completion:")
    stats = registry.get_statistics()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # Get pending stubs
    print("\n6. Pending stubs:")
    pending = registry.get_all_pending()
    print(f"   Count: {len(pending)}")
    
    # Cleanup test file
    if test_registry_path.exists():
        test_registry_path.unlink()
        print("\nOK Cleaned up test registry file")