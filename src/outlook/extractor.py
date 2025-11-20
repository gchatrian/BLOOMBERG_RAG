"""
Outlook email extractor with folder management.
Handles connection, navigation, extraction, and moving emails between folders.
"""

import win32com.client
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging


class OutlookExtractor:
    """
    Extracts emails from Outlook and manages folder operations.
    
    Responsibilities:
    - Connect to Outlook via COM
    - Navigate folder structure
    - Extract raw email data
    - Move emails between folders (source → indexed/stubs/processed)
    - Skip already processed emails (in subfolders)
    """
    
    def __init__(self, source_folder: str, indexed_folder: str, 
                 stubs_folder: str, processed_folder: str):
        """
        Initialize Outlook extractor.
        
        Args:
            source_folder: Main source folder path (e.g., "Inbox/Bloomberg subs")
            indexed_folder: Folder for indexed complete emails
            stubs_folder: Folder for stub emails
            processed_folder: Folder for completed stubs (archive)
        """
        self.source_folder_path = source_folder
        self.indexed_folder_path = indexed_folder
        self.stubs_folder_path = stubs_folder
        self.processed_folder_path = processed_folder
        
        self.outlook = None
        self.namespace = None
        self.logger = logging.getLogger(__name__)
    
    def connect(self) -> bool:
        """
        Connect to Outlook application via COM.
        
        Returns:
            True if connection successful, False otherwise
            
        Raises:
            Exception: If Outlook is not installed or accessible
        """
        try:
            self.logger.info("Connecting to Outlook...")
            self.outlook = win32com.client.Dispatch("Outlook.Application")
            self.namespace = self.outlook.GetNamespace("MAPI")
            self.logger.info("✓ Connected to Outlook successfully")
            return True
        except Exception as e:
            self.logger.error(f"✗ Failed to connect to Outlook: {e}")
            raise Exception(f"Cannot connect to Outlook. Is it installed and running? Error: {e}")
    
    def get_folder(self, folder_path: str) -> Any:
        """
        Navigate to a specific Outlook folder by path.
        
        Args:
            folder_path: Folder path (e.g., "Inbox/Bloomberg subs")
            
        Returns:
            Outlook folder object
            
        Raises:
            Exception: If folder not found
        """
        if not self.namespace:
            raise Exception("Not connected to Outlook. Call connect() first.")
        
        try:
            # Start from inbox
            inbox = self.namespace.GetDefaultFolder(6)  # 6 = olFolderInbox
            
            # Navigate to target folder
            current_folder = inbox.Parent  # Get root folder store
            
            for folder_name in folder_path.split("/"):
                current_folder = current_folder.Folders[folder_name]
            
            self.logger.info(f"✓ Found folder: {folder_path} ({current_folder.Items.Count} items)")
            return current_folder
            
        except Exception as e:
            self.logger.error(f"✗ Folder not found: {folder_path}. Error: {e}")
            raise Exception(f"Folder '{folder_path}' not found. Please check the path. Error: {e}")
    
    def extract_emails(self, max_count: Optional[int] = None, 
                      sort_by_date_desc: bool = True) -> List[Dict[str, Any]]:
        """
        Extract raw email data from source folder.
        
        CRITICAL: Only extracts emails from source folder, automatically skips:
        - Emails in indexed/ subfolder (already processed)
        - Emails in stubs/ subfolder (pending stubs)
        - Emails in processed/ subfolder (completed stubs archive)
        
        Args:
            max_count: Maximum number of emails to extract (None = all)
            sort_by_date_desc: Sort by received date (newest first)
            
        Returns:
            List of dicts with email data:
            {
                'subject': str,
                'body': str,
                'html_body': str,
                'sender': str,
                'received_date': datetime,
                'outlook_entry_id': str  # Unique Outlook ID
            }
        """
        if not self.namespace:
            raise Exception("Not connected to Outlook. Call connect() first.")
        
        self.logger.info(f"Extracting emails from: {self.source_folder_path}")
        
        try:
            # Get source folder
            source_folder = self.get_folder(self.source_folder_path)
            
            # Get all emails in source folder
            emails = source_folder.Items
            
            # Sort by received date if requested
            if sort_by_date_desc:
                emails.Sort("[ReceivedTime]", True)  # True = descending
            
            extracted = []
            count = 0
            
            for email in emails:
                # Skip if not a mail item (could be meeting requests, etc.)
                if email.Class != 43:  # 43 = olMail
                    continue
                
                # Extract email data
                email_data = {
                    'subject': email.Subject,
                    'body': email.Body,
                    'html_body': email.HTMLBody,
                    'sender': email.SenderEmailAddress,
                    'received_date': self._convert_outlook_date(email.ReceivedTime),
                    'outlook_entry_id': email.EntryID
                }
                
                extracted.append(email_data)
                count += 1
                
                # Stop if reached max count
                if max_count and count >= max_count:
                    self.logger.info(f"Reached max count limit: {max_count}")
                    break
            
            self.logger.info(f"✓ Extracted {len(extracted)} emails from source folder")
            return extracted
            
        except Exception as e:
            self.logger.error(f"✗ Failed to extract emails: {e}")
            raise
    
    def move_email(self, outlook_entry_id: str, target_folder_path: str) -> bool:
        """
        Move an email to a different folder.
        
        Args:
            outlook_entry_id: Unique Outlook EntryID of the email
            target_folder_path: Destination folder path
            
        Returns:
            True if successful, False otherwise
        """
        if not self.namespace:
            raise Exception("Not connected to Outlook. Call connect() first.")
        
        try:
            # Get the email by EntryID
            email = self.namespace.GetItemFromID(outlook_entry_id)
            
            # Get target folder
            target_folder = self.get_folder(target_folder_path)
            
            # Move email
            email.Move(target_folder)
            
            self.logger.debug(f"✓ Moved email '{email.Subject[:30]}...' to {target_folder_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"✗ Failed to move email {outlook_entry_id}: {e}")
            return False
    
    def move_to_indexed(self, outlook_entry_id: str) -> bool:
        """Move email to indexed folder (complete emails)."""
        return self.move_email(outlook_entry_id, self.indexed_folder_path)
    
    def move_to_stubs(self, outlook_entry_id: str) -> bool:
        """Move email to stubs folder (incomplete emails)."""
        return self.move_email(outlook_entry_id, self.stubs_folder_path)
    
    def move_to_processed(self, outlook_entry_id: str) -> bool:
        """Move email to processed folder (completed stubs archive)."""
        return self.move_email(outlook_entry_id, self.processed_folder_path)
    
    def get_folder_counts(self) -> Dict[str, int]:
        """
        Get email counts for all folders.
        
        Returns:
            Dict with folder names and counts:
            {
                'source': int,
                'indexed': int,
                'stubs': int,
                'processed': int
            }
        """
        counts = {}
        
        try:
            source = self.get_folder(self.source_folder_path)
            counts['source'] = source.Items.Count
        except:
            counts['source'] = 0
        
        try:
            indexed = self.get_folder(self.indexed_folder_path)
            counts['indexed'] = indexed.Items.Count
        except:
            counts['indexed'] = 0
        
        try:
            stubs = self.get_folder(self.stubs_folder_path)
            counts['stubs'] = stubs.Items.Count
        except:
            counts['stubs'] = 0
        
        try:
            processed = self.get_folder(self.processed_folder_path)
            counts['processed'] = processed.Items.Count
        except:
            counts['processed'] = 0
        
        return counts
    
    def _convert_outlook_date(self, outlook_date) -> datetime:
        """
        Convert Outlook date to Python datetime.
        
        Args:
            outlook_date: Outlook date object
            
        Returns:
            Python datetime object
        """
        if outlook_date is None:
            return datetime.now()
        
        # Outlook dates are already datetime objects in Python
        if isinstance(outlook_date, datetime):
            return outlook_date
        
        # Try to convert if it's a different type
        try:
            return datetime(outlook_date.year, outlook_date.month, outlook_date.day,
                          outlook_date.hour, outlook_date.minute, outlook_date.second)
        except:
            return datetime.now()
    
    def close(self):
        """Close Outlook connection and cleanup."""
        self.outlook = None
        self.namespace = None
        self.logger.info("Outlook connection closed")


# Example usage
if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize extractor
    extractor = OutlookExtractor(
        source_folder="Inbox/Bloomberg subs",
        indexed_folder="Inbox/Bloomberg subs/indexed",
        stubs_folder="Inbox/Bloomberg subs/stubs",
        processed_folder="Inbox/Bloomberg subs/processed"
    )
    
    try:
        # Connect to Outlook
        extractor.connect()
        
        # Get folder counts
        counts = extractor.get_folder_counts()
        print("\nFolder Status:")
        print(f"  Source:    {counts['source']} emails")
        print(f"  Indexed:   {counts['indexed']} emails")
        print(f"  Stubs:     {counts['stubs']} emails")
        print(f"  Processed: {counts['processed']} emails")
        
        # Extract first 5 emails for testing
        print(f"\nExtracting first 5 emails from source...")
        emails = extractor.extract_emails(max_count=5)
        
        print(f"\nExtracted {len(emails)} emails:")
        for i, email in enumerate(emails, 1):
            print(f"\n{i}. {email['subject']}")
            print(f"   From: {email['sender']}")
            print(f"   Date: {email['received_date']}")
            print(f"   Body preview: {email['body'][:100]}...")
        
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        extractor.close()