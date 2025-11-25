"""
Stub matcher module for matching complete emails with pending stubs.
Handles stub completion and cleanup via Story ID or fingerprint matching.
"""

from typing import Optional, Tuple
from datetime import datetime
import logging

# Import required modules
from src.models import EmailDocument, StubEntry
from src.stub.registry import StubRegistry


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
                self.logger.info(f"OK Found stub match by Story ID: {story_id}")
                return stub
        
        # Fallback to fingerprint match
        fingerprint = email_document.get_fingerprint()
        stub = self.match_by_fingerprint(fingerprint)
        
        if stub:
            self.logger.info(f"OK Found stub match by fingerprint: {fingerprint}")
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
            # =================================================================
            # FIX: Handle tuple return from move_to_processed()
            # =================================================================
            success, new_entry_id = self.move_stub_to_processed(stub_entry.outlook_entry_id, outlook_extractor)
            
            if not success:
                self.logger.error(f"Failed to move stub to /processed/: {stub_entry.subject[:50]}...")
                return False
            
            # Log the new EntryID if available
            if new_entry_id:
                self.logger.debug(f"Stub moved, new EntryID: {new_entry_id}")
            
            # Update registry status
            success = self.update_registry(stub_entry)
            
            if not success:
                self.logger.error(f"Failed to update registry: {stub_entry.subject[:50]}...")
                return False
            
            self.logger.info(f"OK Completed stub: {stub_entry.subject[:50]}...")
            return True
            
        except Exception as e:
            self.logger.error(f"Error completing stub: {e}", exc_info=True)
            return False
    
    def move_stub_to_processed(self, outlook_entry_id: str, outlook_extractor) -> Tuple[bool, Optional[str]]:
        """
        Move stub email from /stubs/ to /processed/ folder.
        
        Args:
            outlook_entry_id: Unique Outlook identifier
            outlook_extractor: OutlookExtractor instance
            
        Returns:
            Tuple of (success: bool, new_entry_id: Optional[str])
        """
        try:
            # =================================================================
            # FIX: Capture tuple return (success, new_entry_id)
            # =================================================================
            success, new_entry_id = outlook_extractor.move_to_processed(outlook_entry_id)
            
            if success:
                self.logger.debug(f"Moved stub to /processed/ folder: {outlook_entry_id}")
            else:
                self.logger.error(f"Failed to move stub: {outlook_entry_id}")
            
            return success, new_entry_id
            
        except Exception as e:
            self.logger.error(f"Error moving stub to /processed/: {e}")
            return False, None
    
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