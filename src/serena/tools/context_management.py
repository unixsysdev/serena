"""
Context Management System for Serena with REST API
Handles session tracking, compression, proactive context saving, and Serena integration
"""

import json
import logging
import re
import hashlib
import threading
import uuid
from collections import Counter
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

# Flask import with fallback
try:
    from flask import Flask, request, jsonify
    import socket
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    print("Flask not available - REST API will be disabled")

from serena.tools import Tool, ToolMarkerDoesNotRequireActiveProject, TOOL_DEFAULT_MAX_ANSWER_LENGTH


log = logging.getLogger(__name__)


@dataclass
class SessionContext:
    """Represents a session with its context"""
    session_id: str
    started_at: datetime
    last_activity: datetime
    task_description: str
    files_modified: List[str]
    decisions_made: List[str]
    current_work_state: str
    tags: List[str]
    compressed_context: Optional[str] = None
    compression_ratio: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'session_id': self.session_id,
            'started_at': self.started_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'task_description': self.task_description,
            'files_modified': self.files_modified,
            'decisions_made': self.decisions_made,
            'current_work_state': self.current_work_state,
            'tags': self.tags,
            'compressed_context': self.compressed_context,
            'compression_ratio': self.compression_ratio
        }


@dataclass
class ContextExtraction:
    """Represents extracted context from conversations"""
    content: str
    context_type: str  # 'file_change', 'decision', 'work_state', 'task_info'
    importance: int  # 1-10 scale
    tags: List[str]
    timestamp: datetime
    session_id: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'content': self.content,
            'context_type': self.context_type,
            'importance': self.importance,
            'tags': self.tags,
            'timestamp': self.timestamp.isoformat(),
            'session_id': self.session_id
        }


class ContextCompressor:
    """Handles compression of context using word frequency analysis"""
    
    def __init__(self):
        self.word_to_code: Dict[str, str] = {}
        self.code_to_word: Dict[str, str] = {}
        self.compression_stats: List[Dict] = []
        
    def build_dictionary(self, text: str, max_words: int = 300) -> None:
        """Build compression dictionary from text"""
        words = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_-]{2,}\b', text)
        word_counts = Counter(words)
        top_words = word_counts.most_common(max_words)
        
        self.word_to_code.clear()
        self.code_to_word.clear()
        
        for i, (word, freq) in enumerate(top_words):
            if i < 62:  # Single char codes
                if i < 26:
                    code = chr(ord('a') + i)
                elif i < 52:
                    code = chr(ord('A') + (i - 26))
                else:
                    code = str(i - 52)
            else:  # Multi-char codes
                code = f"x{i-61}"
                
            self.word_to_code[word] = code
            self.code_to_word[code] = word
    
    def compress_text(self, text: str) -> Tuple[str, float]:
        """Compress text using word dictionary"""
        if not self.word_to_code:
            self.build_dictionary(text)
            
        compressed = text
        for word, code in self.word_to_code.items():
            pattern = r'\b' + re.escape(word) + r'\b'
            compressed = re.sub(pattern, code, compressed)
        
        # Basic whitespace compression
        compressed = re.sub(r'\n\s*\n\s*\n', '\n\n', compressed)
        compressed = re.sub(r'[ \t]+', ' ', compressed)
        
        ratio = len(text) / len(compressed) if len(compressed) > 0 else 1.0
        return compressed, ratio
    
    def decompress_text(self, compressed: str) -> str:
        """Decompress text using word dictionary"""
        if not self.code_to_word:
            return compressed
            
        decompressed = compressed
        for code, word in self.code_to_word.items():
            pattern = r'\b' + re.escape(code) + r'\b'
            decompressed = re.sub(pattern, word, decompressed)
            
        return decompressed


class ContextManager:
    """Main context management system"""
    
    def __init__(self, agent=None):
        self.agent = agent
        self.compressor = ContextCompressor()
        self.sessions: Dict[str, SessionContext] = {}
        self.extractions: List[ContextExtraction] = []
        self.current_session_id: Optional[str] = None
        self.lock = threading.Lock()
        
    def start_session(self, task_description: str, tags: List[str] = None) -> str:
        """Start a new session"""
        session_id = str(uuid.uuid4())[:8]
        tags = tags or []
        
        session = SessionContext(
            session_id=session_id,
            started_at=datetime.now(),
            last_activity=datetime.now(),
            task_description=task_description,
            files_modified=[],
            decisions_made=[],
            current_work_state="",
            tags=tags + ["session", "active"]
        )
        
        with self.lock:
            self.sessions[session_id] = session
            self.current_session_id = session_id
            
        # Store in Serena memory if agent available
        if self.agent:
            self.agent.memories_manager.save_memory(
                f"session_{session_id}_start",
                f"Started session: {task_description}\nTags: {', '.join(tags)}"
            )
        
        return session_id
    
    def update_session_activity(self, session_id: str, activity: str) -> None:
        """Update session with new activity"""
        with self.lock:
            if session_id in self.sessions:
                self.sessions[session_id].last_activity = datetime.now()
                self.sessions[session_id].current_work_state = activity
    
    def add_file_modification(self, session_id: str, file_path: str) -> None:
        """Track file modification in session"""
        with self.lock:
            if session_id in self.sessions:
                if file_path not in self.sessions[session_id].files_modified:
                    self.sessions[session_id].files_modified.append(file_path)
                    
        # Store in Serena memory
        if self.agent:
            self.agent.memories_manager.save_memory(
                f"session_{session_id}_file_mod",
                f"Modified file: {file_path}"
            )
    
    def add_decision(self, session_id: str, decision: str) -> None:
        """Track decision made in session"""
        with self.lock:
            if session_id in self.sessions:
                self.sessions[session_id].decisions_made.append(decision)
                
        # Store in Serena memory
        if self.agent:
            self.agent.memories_manager.save_memory(
                f"session_{session_id}_decision",
                f"Decision: {decision}"
            )
    
    def extract_context(self, content: str, context_type: str, importance: int = 5, 
                       tags: List[str] = None) -> str:
        """Extract and store context from conversation"""
        if not self.current_session_id:
            self.start_session("Automatic session", ["auto"])
            
        tags = tags or []
        extraction = ContextExtraction(
            content=content,
            context_type=context_type,
            importance=importance,
            tags=tags + [context_type],
            timestamp=datetime.now(),
            session_id=self.current_session_id
        )
        
        with self.lock:
            self.extractions.append(extraction)
            
        # Store in Serena memory with tags
        if self.agent:
            memory_name = f"context_{context_type}_{extraction.timestamp.strftime('%Y%m%d_%H%M%S')}"
            self.agent.memories_manager.save_memory(memory_name, content)
            
        return extraction.session_id
    
    def compress_session(self, session_id: str) -> bool:
        """Compress session context"""
        with self.lock:
            if session_id not in self.sessions:
                return False
                
            session = self.sessions[session_id]
            
            # Build context text
            context_parts = [
                f"Task: {session.task_description}",
                f"Files modified: {', '.join(session.files_modified)}",
                f"Decisions: {'; '.join(session.decisions_made)}",
                f"Current state: {session.current_work_state}"
            ]
            
            # Add extractions for this session
            session_extractions = [e for e in self.extractions if e.session_id == session_id]
            for extraction in session_extractions:
                context_parts.append(f"{extraction.context_type}: {extraction.content}")
            
            full_context = "\n".join(context_parts)
            
            # Compress
            compressed, ratio = self.compressor.compress_text(full_context)
            
            session.compressed_context = compressed
            session.compression_ratio = ratio
            
            # Store compressed session in Serena memory
            if self.agent:
                self.agent.memories_manager.save_memory(
                    f"session_{session_id}_compressed",
                    f"Compressed session context (ratio: {ratio:.2f}x)\n{compressed}"
                )
            
            return True
    
    def restore_session(self, session_id: str) -> Optional[str]:
        """Restore session from compressed context"""
        with self.lock:
            if session_id not in self.sessions:
                return None
                
            session = self.sessions[session_id]
            if not session.compressed_context:
                return None
                
            # Decompress
            restored = self.compressor.decompress_text(session.compressed_context)
            return restored
    
    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session summary"""
        with self.lock:
            if session_id not in self.sessions:
                return None
            return self.sessions[session_id].to_dict()
    
    def get_relevant_context(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Get relevant context based on query"""
        # Simple keyword matching for now
        query_words = set(query.lower().split())
        
        results = []
        for extraction in self.extractions:
            content_words = set(extraction.content.lower().split())
            relevance = len(query_words.intersection(content_words))
            
            if relevance > 0:
                result = extraction.to_dict()
                result['relevance'] = relevance
                results.append(result)
        
        # Sort by relevance and importance
        results.sort(key=lambda x: (x['relevance'], x['importance']), reverse=True)
        return results[:max_results]
    
    def cleanup_old_sessions(self, max_age_days: int = 30) -> int:
        """Clean up old sessions"""
        cutoff = datetime.now().timestamp() - (max_age_days * 24 * 60 * 60)
        cleaned = 0
        
        with self.lock:
            to_remove = []
            for session_id, session in self.sessions.items():
                if session.last_activity.timestamp() < cutoff:
                    to_remove.append(session_id)
            
            for session_id in to_remove:
                del self.sessions[session_id]
                cleaned += 1
                
        return cleaned
    
    def get_stats(self) -> Dict[str, Any]:
        """Get context manager statistics"""
        with self.lock:
            active_sessions = len([s for s in self.sessions.values() if "active" in s.tags])
            total_extractions = len(self.extractions)
            
            return {
                'total_sessions': len(self.sessions),
                'active_sessions': active_sessions,
                'total_extractions': total_extractions,
                'current_session': self.current_session_id,
                'compression_stats': self.compressor.compression_stats
            }


# Global context manager instance
context_manager = ContextManager()


class ContextAPI:
    """REST API for context management"""
    
    def __init__(self, manager: ContextManager):
        self.manager = manager
        if FLASK_AVAILABLE:
            self.app = Flask(__name__)
            self.app.config['JSON_SORT_KEYS'] = False
            self._setup_routes()
        else:
            self.app = None
            
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/health', methods=['GET'])
        def health():
            return jsonify({
                'status': 'healthy',
                'service': 'context-management-api',
                'flask_available': FLASK_AVAILABLE,
                'timestamp': datetime.now().isoformat()
            })
        
        @self.app.route('/sessions', methods=['POST'])
        def start_session():
            try:
                data = request.get_json()
                task_description = data.get('task_description', 'New task')
                tags = data.get('tags', [])
                
                session_id = self.manager.start_session(task_description, tags)
                return jsonify({'session_id': session_id, 'message': 'Session started'})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/sessions/<session_id>', methods=['GET'])
        def get_session(session_id):
            try:
                summary = self.manager.get_session_summary(session_id)
                if not summary:
                    return jsonify({'error': 'Session not found'}), 404
                return jsonify({'session': summary})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/sessions/<session_id>/compress', methods=['POST'])
        def compress_session(session_id):
            try:
                if self.manager.compress_session(session_id):
                    return jsonify({'message': 'Session compressed successfully'})
                return jsonify({'error': 'Session not found'}), 404
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/sessions/<session_id>/restore', methods=['GET'])
        def restore_session(session_id):
            try:
                restored = self.manager.restore_session(session_id)
                if restored is None:
                    return jsonify({'error': 'Session not found or not compressed'}), 404
                return jsonify({'restored_context': restored})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/context', methods=['POST'])
        def extract_context():
            try:
                data = request.get_json()
                if not data or 'content' not in data:
                    return jsonify({'error': 'Missing content parameter'}), 400
                
                content = data['content']
                context_type = data.get('context_type', 'general')
                importance = data.get('importance', 5)
                tags = data.get('tags', [])
                
                session_id = self.manager.extract_context(content, context_type, importance, tags)
                return jsonify({'session_id': session_id, 'message': 'Context extracted'})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/context/search', methods=['POST'])
        def search_context():
            try:
                data = request.get_json()
                if not data or 'query' not in data:
                    return jsonify({'error': 'Missing query parameter'}), 400
                
                query = data['query']
                max_results = data.get('max_results', 10)
                
                results = self.manager.get_relevant_context(query, max_results)
                return jsonify({'results': results, 'count': len(results)})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/stats', methods=['GET'])
        def get_stats():
            try:
                stats = self.manager.get_stats()
                return jsonify({'stats': stats})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/cleanup', methods=['POST'])
        def cleanup():
            try:
                data = request.get_json() or {}
                max_age_days = data.get('max_age_days', 30)
                
                cleaned = self.manager.cleanup_old_sessions(max_age_days)
                return jsonify({'cleaned_sessions': cleaned})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
    
    def run(self, host: str = "localhost", port: int = 5002, debug: bool = False):
        """Run the context API"""
        if not self.app:
            print("Flask not available - cannot start REST API")
            return
        
        print(f"🚀 Starting Context Management API on http://{host}:{port}")
        print(f"📋 Health check: http://{host}:{port}/health")
        print(f"🎯 Start session: POST http://{host}:{port}/sessions")
        print(f"🧠 Extract context: POST http://{host}:{port}/context")
        print(f"🔍 Search context: POST http://{host}:{port}/context/search")
        
        self.app.run(host=host, port=port, debug=debug, use_reloader=False, threaded=True)


# Serena Tools Integration
class StartContextSessionTool(Tool, ToolMarkerDoesNotRequireActiveProject):
    """Start a new context tracking session"""
    
    def apply(self, task_description: str, tags: str = "", max_answer_chars: int = TOOL_DEFAULT_MAX_ANSWER_LENGTH) -> str:
        """
        Start a new context tracking session for better session management.
        
        :param task_description: Description of the task/work being done
        :param tags: Comma-separated tags for the session
        :param max_answer_chars: Maximum response length
        :return: Session ID and status
        """
        try:
            # Set agent reference for Serena integration
            context_manager.agent = self.agent
            
            tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
            session_id = context_manager.start_session(task_description, tag_list)
            
            response = f"""✅ Context session started!
Session ID: {session_id}
Task: {task_description}
Tags: {', '.join(tag_list) if tag_list else 'None'}
Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🎯 This session will now track:
- File modifications
- Decisions made
- Work progress
- Context for future restoration

Use save_context_extraction to manually save important context points.
"""
            
            return self._limit_length(response, max_answer_chars)
            
        except Exception as e:
            return f"Error starting context session: {str(e)}"


class SaveContextExtractionTool(Tool, ToolMarkerDoesNotRequireActiveProject):
    """Save important context for session restoration"""
    
    def apply(self, content: str, context_type: str = "general", importance: int = 5, 
              tags: str = "", max_answer_chars: int = TOOL_DEFAULT_MAX_ANSWER_LENGTH) -> str:
        """
        Save important context that should be preserved for session restoration.
        
        :param content: The context content to save
        :param context_type: Type of context (file_change, decision, work_state, task_info)
        :param importance: Importance level 1-10
        :param tags: Comma-separated tags
        :param max_answer_chars: Maximum response length
        :return: Status message
        """
        try:
            # Set agent reference for Serena integration
            context_manager.agent = self.agent
            
            tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
            session_id = context_manager.extract_context(content, context_type, importance, tag_list)
            
            response = f"""💾 Context saved successfully!
Session ID: {session_id}
Type: {context_type}
Importance: {importance}/10
Tags: {', '.join(tag_list) if tag_list else 'None'}

Content preview: {content[:200]}{'...' if len(content) > 200 else ''}

This context will be compressed and available for session restoration.
"""
            
            return self._limit_length(response, max_answer_chars)
            
        except Exception as e:
            return f"Error saving context: {str(e)}"


class CompressSessionTool(Tool, ToolMarkerDoesNotRequireActiveProject):
    """Compress current session for efficient storage"""
    
    def apply(self, session_id: str = "", max_answer_chars: int = TOOL_DEFAULT_MAX_ANSWER_LENGTH) -> str:
        """
        Compress session context for efficient storage and later restoration.
        
        :param session_id: Session ID to compress (empty for current session)
        :param max_answer_chars: Maximum response length
        :return: Compression status and statistics
        """
        try:
            # Set agent reference for Serena integration
            context_manager.agent = self.agent
            
            target_session = session_id or context_manager.current_session_id
            if not target_session:
                return "No active session to compress. Start a session first."
            
            if context_manager.compress_session(target_session):
                session = context_manager.sessions[target_session]
                
                response = f"""🗜️ Session compressed successfully!
Session ID: {target_session}
Compression ratio: {session.compression_ratio:.2f}x
Original context size: {len(session.current_work_state + ' '.join(session.decisions_made))} chars
Compressed size: {len(session.compressed_context)} chars

✅ Session context is now stored in compressed form and saved to Serena memories.
This will allow for efficient session restoration when context limit is exceeded.
"""
                
                return self._limit_length(response, max_answer_chars)
            else:
                return f"Session {target_session} not found or already compressed."
                
        except Exception as e:
            return f"Error compressing session: {str(e)}"


class RestoreSessionTool(Tool, ToolMarkerDoesNotRequireActiveProject):
    """Restore session context from compressed storage"""
    
    def apply(self, session_id: str, max_answer_chars: int = TOOL_DEFAULT_MAX_ANSWER_LENGTH) -> str:
        """
        Restore session context from compressed storage.
        
        :param session_id: Session ID to restore
        :param max_answer_chars: Maximum response length
        :return: Restored context
        """
        try:
            # Set agent reference for Serena integration
            context_manager.agent = self.agent
            
            restored = context_manager.restore_session(session_id)
            if restored is None:
                return f"Session {session_id} not found or not compressed."
            
            response = f"""🔄 Session restored successfully!
Session ID: {session_id}

=== RESTORED CONTEXT ===
{restored}

✅ You can now continue from where you left off.
"""
            
            return self._limit_length(response, max_answer_chars)
            
        except Exception as e:
            return f"Error restoring session: {str(e)}"


class SearchContextTool(Tool, ToolMarkerDoesNotRequireActiveProject):
    """Search saved context for relevant information"""
    
    def apply(self, query: str, max_results: int = 10, max_answer_chars: int = TOOL_DEFAULT_MAX_ANSWER_LENGTH) -> str:
        """
        Search saved context for relevant information.
        
        :param query: Search query
        :param max_results: Maximum number of results
        :param max_answer_chars: Maximum response length
        :return: Search results
        """
        try:
            # Set agent reference for Serena integration
            context_manager.agent = self.agent
            
            results = context_manager.get_relevant_context(query, max_results)
            
            if not results:
                return f"No relevant context found for query: '{query}'"
            
            response = f"""🔍 Found {len(results)} relevant context items for '{query}':

"""
            
            for i, result in enumerate(results, 1):
                response += f"{i}. [{result['context_type']}] {result['content'][:100]}{'...' if len(result['content']) > 100 else ''}\n"
                response += f"   Tags: {', '.join(result['tags'])} | Importance: {result['importance']}/10\n"
                response += f"   Session: {result['session_id']} | {result['timestamp']}\n\n"
            
            return self._limit_length(response, max_answer_chars)
            
        except Exception as e:
            return f"Error searching context: {str(e)}"


class ContextStatsTool(Tool, ToolMarkerDoesNotRequireActiveProject):
    """Get context management statistics"""
    
    def apply(self, max_answer_chars: int = TOOL_DEFAULT_MAX_ANSWER_LENGTH) -> str:
        """
        Get context management statistics and current status.
        
        :param max_answer_chars: Maximum response length
        :return: Statistics and status
        """
        try:
            # Set agent reference for Serena integration
            context_manager.agent = self.agent
            
            stats = context_manager.get_stats()
            
            response = f"""📊 Context Management Statistics:

🎯 Sessions:
- Total sessions: {stats['total_sessions']}
- Active sessions: {stats['active_sessions']}
- Current session: {stats['current_session'] or 'None'}

🧠 Context Extractions:
- Total extractions: {stats['total_extractions']}

🗜️ Compression:
- Compression stats: {len(stats['compression_stats'])} operations

💡 The system is actively tracking context for better session management
and will help restore work when context limits are exceeded.
"""
            
            return self._limit_length(response, max_answer_chars)
            
        except Exception as e:
            return f"Error getting context stats: {str(e)}"


class StartContextAPITool(Tool, ToolMarkerDoesNotRequireActiveProject):
    """Start the Context Management REST API"""
    
    def apply(self, port: int = 5002, max_answer_chars: int = TOOL_DEFAULT_MAX_ANSWER_LENGTH) -> str:
        """
        Start the Context Management REST API server.
        
        :param port: Port to run the API on
        :param max_answer_chars: Maximum response length
        :return: API status and endpoints
        """
        try:
            if not FLASK_AVAILABLE:
                return "Flask not available - cannot start REST API. Install Flask to use this feature."
            
            # Set agent reference for Serena integration
            context_manager.agent = self.agent
            
            api = ContextAPI(context_manager)
            
            # Start API in thread
            import threading
            thread = threading.Thread(target=lambda: api.run(port=port), daemon=True)
            thread.start()
            
            response = f"""🚀 Context Management API started on port {port}!

📋 Available endpoints:
- GET  /health - Health check
- POST /sessions - Start new session
- GET  /sessions/<id> - Get session info
- POST /sessions/<id>/compress - Compress session
- GET  /sessions/<id>/restore - Restore session
- POST /context - Extract context
- POST /context/search - Search context
- GET  /stats - Get statistics
- POST /cleanup - Cleanup old sessions

🔌 API is now running and ready for external integrations.
You can decouple this later for distributed deployments.

Example usage:
curl -X POST http://localhost:{port}/sessions \\
  -H "Content-Type: application/json" \\
  -d '{{"task_description": "Test task", "tags": ["test"]}}'
"""
            
            return self._limit_length(response, max_answer_chars)
            
        except Exception as e:
            return f"Error starting Context API: {str(e)}"


def main():
    """Standalone execution for testing"""
    if FLASK_AVAILABLE:
        api = ContextAPI(context_manager)
        api.run(port=5002)
    else:
        print("Flask not available - install flask to run the API")


if __name__ == "__main__":
    main()
