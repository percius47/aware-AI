"""
Conversation Service - Handles persistent conversation threads using Supabase.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger("threads")

# Try to import supabase, fall back gracefully if not available
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
    print("[SUPABASE] Import successful - supabase package is available")
except ImportError as e:
    SUPABASE_AVAILABLE = False
    print(f"[SUPABASE] Import FAILED: {e}")


class ConversationService:
    """
    Service for managing conversation threads with Supabase.
    Falls back to in-memory storage if Supabase is not configured.
    """
    
    def __init__(self):
        self.client: Optional[Any] = None
        self._fallback_threads: Dict[str, Dict] = {}
        self._fallback_messages: Dict[str, List[Dict]] = {}
        
        # Debug: Print what we're working with
        print(f"[SUPABASE] SUPABASE_AVAILABLE: {SUPABASE_AVAILABLE}")
        print(f"[SUPABASE] SUPABASE_URL set: {bool(settings.SUPABASE_URL)}")
        print(f"[SUPABASE] SUPABASE_URL value: {settings.SUPABASE_URL[:30] if settings.SUPABASE_URL else 'EMPTY'}...")
        print(f"[SUPABASE] SUPABASE_KEY set: {bool(settings.SUPABASE_KEY)}")
        
        # Initialize Supabase client if credentials are available
        if SUPABASE_AVAILABLE and settings.SUPABASE_URL and settings.SUPABASE_KEY:
            try:
                print("[SUPABASE] Attempting to create Supabase client...")
                self.client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
                print("[SUPABASE] SUCCESS - Supabase client initialized!")
                logger.info("Supabase client initialized successfully")
            except Exception as e:
                print(f"[SUPABASE] FAILED to create client: {type(e).__name__}: {e}")
                logger.warning(f"Failed to initialize Supabase: {e}. Using fallback.")
                self.client = None
        else:
            print("[SUPABASE] Skipping client creation - missing requirements")
            if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
                print(f"[SUPABASE] Missing: URL={not settings.SUPABASE_URL}, KEY={not settings.SUPABASE_KEY}")
                logger.info("Supabase credentials not configured. Using in-memory fallback.")
        
        print(f"[SUPABASE] Final is_persistent: {self.client is not None}")
    
    @property
    def is_persistent(self) -> bool:
        """Check if using persistent storage (Supabase) or fallback."""
        return self.client is not None
    
    async def list_threads(self, user_id: str = "default_user", limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get all conversation threads for a user, ordered by most recent.
        """
        logger.info(f"[THREADS] Listing threads for user: {user_id}")
        
        if self.client:
            try:
                response = self.client.table("conversations") \
                    .select("id, title, created_at, updated_at") \
                    .eq("user_id", user_id) \
                    .order("updated_at", desc=True) \
                    .limit(limit) \
                    .execute()
                
                threads = response.data or []
                logger.info(f"  └─ Found {len(threads)} threads (Supabase)")
                return threads
            except Exception as e:
                logger.error(f"  └─ Error listing threads: {e}")
                return []
        else:
            # Fallback: in-memory storage
            threads = [
                {**t, "id": tid} 
                for tid, t in self._fallback_threads.items() 
                if t.get("user_id") == user_id
            ]
            threads.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
            logger.info(f"  └─ Found {len(threads)} threads (fallback)")
            return threads[:limit]
    
    async def get_thread(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a single thread with all its messages.
        """
        logger.info(f"[THREADS] Getting thread: {conversation_id[:8]}...")
        
        if self.client:
            try:
                # Get conversation
                conv_response = self.client.table("conversations") \
                    .select("*") \
                    .eq("id", conversation_id) \
                    .single() \
                    .execute()
                
                if not conv_response.data:
                    logger.info("  └─ Thread not found")
                    return None
                
                # Get messages
                msg_response = self.client.table("messages") \
                    .select("*") \
                    .eq("conversation_id", conversation_id) \
                    .order("created_at", desc=False) \
                    .execute()
                
                thread = conv_response.data
                thread["messages"] = msg_response.data or []
                logger.info(f"  └─ Found thread with {len(thread['messages'])} messages")
                return thread
            except Exception as e:
                logger.error(f"  └─ Error getting thread: {e}")
                return None
        else:
            # Fallback
            if conversation_id not in self._fallback_threads:
                logger.info("  └─ Thread not found (fallback)")
                return None
            
            thread = {**self._fallback_threads[conversation_id], "id": conversation_id}
            thread["messages"] = self._fallback_messages.get(conversation_id, [])
            logger.info(f"  └─ Found thread with {len(thread['messages'])} messages (fallback)")
            return thread
    
    async def create_thread(self, user_id: str = "default_user", title: str = "New Chat") -> Dict[str, Any]:
        """
        Create a new conversation thread.
        """
        logger.info(f"[THREADS] Creating new thread for user: {user_id}")
        
        if self.client:
            try:
                response = self.client.table("conversations") \
                    .insert({
                        "user_id": user_id,
                        "title": title
                    }) \
                    .execute()
                
                thread = response.data[0] if response.data else None
                if thread:
                    logger.info(f"  └─ Created thread: {thread['id'][:8]}... (Supabase)")
                return thread
            except Exception as e:
                logger.error(f"  └─ Error creating thread: {e}")
                return None
        else:
            # Fallback: generate UUID-like ID
            import uuid
            thread_id = str(uuid.uuid4())
            now = datetime.utcnow().isoformat()
            
            self._fallback_threads[thread_id] = {
                "user_id": user_id,
                "title": title,
                "created_at": now,
                "updated_at": now
            }
            self._fallback_messages[thread_id] = []
            
            logger.info(f"  └─ Created thread: {thread_id[:8]}... (fallback)")
            return {"id": thread_id, **self._fallback_threads[thread_id]}
    
    async def add_message(
        self, 
        conversation_id: str, 
        role: str, 
        content: str
    ) -> Optional[Dict[str, Any]]:
        """
        Add a message to a conversation.
        """
        logger.info(f"[THREADS] Adding {role} message to thread: {conversation_id[:8]}...")
        
        if self.client:
            try:
                # Add message
                msg_response = self.client.table("messages") \
                    .insert({
                        "conversation_id": conversation_id,
                        "role": role,
                        "content": content
                    }) \
                    .execute()
                
                # Update conversation's updated_at
                self.client.table("conversations") \
                    .update({"updated_at": datetime.utcnow().isoformat()}) \
                    .eq("id", conversation_id) \
                    .execute()
                
                message = msg_response.data[0] if msg_response.data else None
                logger.info(f"  └─ Message added (Supabase)")
                return message
            except Exception as e:
                logger.error(f"  └─ Error adding message: {e}")
                return None
        else:
            # Fallback
            if conversation_id not in self._fallback_messages:
                self._fallback_messages[conversation_id] = []
            
            now = datetime.utcnow().isoformat()
            message = {
                "id": str(len(self._fallback_messages[conversation_id])),
                "conversation_id": conversation_id,
                "role": role,
                "content": content,
                "created_at": now
            }
            self._fallback_messages[conversation_id].append(message)
            
            # Update thread's updated_at
            if conversation_id in self._fallback_threads:
                self._fallback_threads[conversation_id]["updated_at"] = now
            
            logger.info(f"  └─ Message added (fallback)")
            return message
    
    async def update_title(self, conversation_id: str, title: str) -> bool:
        """
        Update conversation title.
        """
        logger.info(f"[THREADS] Updating title for thread: {conversation_id[:8]}...")
        
        if self.client:
            try:
                self.client.table("conversations") \
                    .update({"title": title}) \
                    .eq("id", conversation_id) \
                    .execute()
                logger.info(f"  └─ Title updated: \"{title[:30]}...\"")
                return True
            except Exception as e:
                logger.error(f"  └─ Error updating title: {e}")
                return False
        else:
            if conversation_id in self._fallback_threads:
                self._fallback_threads[conversation_id]["title"] = title
                logger.info(f"  └─ Title updated (fallback): \"{title[:30]}...\"")
                return True
            return False
    
    async def delete_thread(self, conversation_id: str) -> bool:
        """
        Delete a conversation and all its messages.
        """
        logger.info(f"[THREADS] Deleting thread: {conversation_id[:8]}...")
        
        if self.client:
            try:
                # Messages are deleted automatically via CASCADE
                self.client.table("conversations") \
                    .delete() \
                    .eq("id", conversation_id) \
                    .execute()
                logger.info(f"  └─ Thread deleted (Supabase)")
                return True
            except Exception as e:
                logger.error(f"  └─ Error deleting thread: {e}")
                return False
        else:
            if conversation_id in self._fallback_threads:
                del self._fallback_threads[conversation_id]
            if conversation_id in self._fallback_messages:
                del self._fallback_messages[conversation_id]
            logger.info(f"  └─ Thread deleted (fallback)")
            return True
    
    async def get_thread_count(self, user_id: str = "default_user") -> int:
        """
        Get total number of threads for a user.
        """
        if self.client:
            try:
                response = self.client.table("conversations") \
                    .select("id", count="exact") \
                    .eq("user_id", user_id) \
                    .execute()
                return response.count or 0
            except Exception as e:
                logger.error(f"Error getting thread count: {e}")
                return 0
        else:
            return len([t for t in self._fallback_threads.values() if t.get("user_id") == user_id])
    
    def generate_title_from_message(self, message: str) -> str:
        """
        Generate a short title from the first user message.
        """
        # Take first 50 chars, cut at word boundary
        title = message[:50]
        if len(message) > 50:
            # Try to cut at last space
            last_space = title.rfind(' ')
            if last_space > 20:
                title = title[:last_space]
            title += "..."
        return title
