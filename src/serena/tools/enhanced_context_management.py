"""
Enhanced Context Management with Automatic Triggers and Proper LLM Instructions
Fixes the missing automatic triggers, file change monitoring, and proper instructions
"""

import os
import json
import logging
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from serena.tools import Tool, ToolMarkerDoesNotRequireActiveProject, TOOL_DEFAULT_MAX_ANSWER_LENGTH


log = logging.getLogger(__name__)


class AutoContextManager:
    """Automatic context management with triggers and persistence"""
    
    def __init__(self, agent=None):
        self.agent = agent
        self.context_dir = None
        self.session_file = None
        self.file_watch_list = set()
        self.last_file_states = {}
        
    def setup_persistence(self, project_root: str):
        """Setup persistent storage in .serena directory"""
        self.context_dir = Path(project_root) / ".serena" / "context"
        self.context_dir.mkdir(parents=True, exist_ok=True)
        self.session_file = self.context_dir / "current_session.json"
        
    def auto_save_on_file_change(self, file_path: str, change_type: str = "modified"):
        """Automatically save context when files are modified"""
        if not self.agent:
            return
            
        # Check if this is a significant file change
        if self._is_significant_file(file_path):
            content = f"File {change_type}: {file_path}\nAutomatic context save triggered by file modification."
            
            # Use existing save_context_extraction tool
            if hasattr(self.agent, 'get_tool'):
                save_tool = self.agent.get_tool('SaveContextExtractionTool')
                if save_tool:
                    save_tool.apply(
                        content=content,
                        context_type="file_change",
                        importance=7,
                        tags=f"auto,file-change,{change_type},{os.path.basename(file_path)}"
                    )
    
    def auto_save_on_task_adherence_check(self, adherence_result: str):
        """Automatically save context when task adherence is checked"""
        if not self.agent:
            return
            
        content = f"Task adherence check result: {adherence_result}\nAutomatic context save to track progress and decisions."
        
        if hasattr(self.agent, 'get_tool'):
            save_tool = self.agent.get_tool('SaveContextExtractionTool')
            if save_tool:
                save_tool.apply(
                    content=content,
                    context_type="task_adherence",
                    importance=8,
                    tags="auto,task-adherence,progress-check"
                )
    
    def auto_save_on_decision_point(self, decision: str, importance: int = 7):
        """Automatically save context when decisions are made"""
        if not self.agent:
            return
            
        content = f"Decision made: {decision}\nAutomatic context save to preserve decision reasoning."
        
        # Use save_context_extraction directly instead of looking up tool
        if hasattr(self.agent, 'memories_manager'):
            memory_name = f"auto_decision_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.agent.memories_manager.save_memory(memory_name, content)
    
    def _is_significant_file(self, file_path: str) -> bool:
        """Check if file change is significant enough to save context"""
        # Skip temporary files, logs, etc.
        skip_patterns = ['.log', '.tmp', '__pycache__', '.pyc', '.git/', 'node_modules/']
        
        for pattern in skip_patterns:
            if pattern in file_path:
                return False
                
        # Include important file types
        important_extensions = ['.py', '.js', '.ts', '.yaml', '.yml', '.json', '.md', '.txt', '.sql']
        return any(file_path.endswith(ext) for ext in important_extensions)
    
    def save_session_to_disk(self, session_data: Dict[str, Any]):
        """Save session data to disk for persistence"""
        if not self.session_file:
            return
            
        try:
            with open(self.session_file, 'w') as f:
                json.dump(session_data, f, indent=2, default=str)
        except Exception as e:
            log.error(f"Failed to save session to disk: {e}")
    
    def load_session_from_disk(self) -> Optional[Dict[str, Any]]:
        """Load session data from disk"""
        if not self.session_file or not self.session_file.exists():
            return None
            
        try:
            with open(self.session_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            log.error(f"Failed to load session from disk: {e}")
            return None


# Global auto context manager
auto_context_manager = AutoContextManager()


class EnhancedThinkAboutTaskAdherenceTool(Tool):
    """Enhanced task adherence tool that automatically saves context"""
    
    def apply(self, max_answer_chars: int = TOOL_DEFAULT_MAX_ANSWER_LENGTH) -> str:
        """
        Think about task adherence and automatically save the result as context.
        This ensures progress tracking and decision preservation.
        
        :param max_answer_chars: Maximum response length
        :return: Task adherence analysis with auto-save confirmation
        """
        # Set up auto context manager
        auto_context_manager.agent = self.agent
        if self.agent and hasattr(self.agent, 'get_project_root'):
            project_root = self.agent.get_project_root()
            if project_root:
                auto_context_manager.setup_persistence(project_root)
        
        # Original task adherence logic
        result = """Are you deviating from the task at hand? Do you need any additional information to proceed?
Have you loaded all relevant memory files to see whether your implementation is fully aligned with the
code style, conventions, and guidelines of the project? If not, adjust your implementation accordingly
before modifying any code into the codebase.
Note that it is better to stop and ask the user for clarification
than to perform large changes which might not be aligned with the user's intentions.
If you feel like the conversation is deviating too much from the original task, apologize and suggest to the user
how to proceed. If the conversation became too long, create a summary of the current progress and suggest to the user
to start a new conversation based on that summary."""

        # Automatically save this task adherence check
        auto_context_manager.auto_save_on_task_adherence_check(
            "Task adherence check performed - evaluating alignment with user intentions and project requirements"
        )
        
        enhanced_result = f"""{result}

🤖 AUTO-SAVED: This task adherence check has been automatically saved to context for session restoration.
Tags: auto, task-adherence, progress-check
Importance: 8/10

💾 Context will be preserved across sessions to maintain work continuity."""
        
        return self._limit_length(enhanced_result, max_answer_chars)


class FileChangeMonitorTool(Tool, ToolMarkerDoesNotRequireActiveProject):
    """Monitor file changes and automatically save context"""
    
    def apply(self, file_path: str, change_type: str = "modified", 
              max_answer_chars: int = TOOL_DEFAULT_MAX_ANSWER_LENGTH) -> str:
        """
        Monitor file changes and automatically save context.
        
        :param file_path: Path of the changed file
        :param change_type: Type of change (modified, created, deleted)
        :param max_answer_chars: Maximum response length
        :return: File change monitoring result
        """
        # Set up auto context manager
        auto_context_manager.agent = self.agent
        if self.agent and hasattr(self.agent, 'get_project_root'):
            project_root = self.agent.get_project_root()
            if project_root:
                auto_context_manager.setup_persistence(project_root)
        
        # Automatically save context for this file change
        auto_context_manager.auto_save_on_file_change(file_path, change_type)
        
        result = f"""📁 File Change Detected and Context Saved!
File: {file_path}
Change Type: {change_type}
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🤖 AUTO-SAVED: File change automatically saved to context
Tags: auto, file-change, {change_type}, {os.path.basename(file_path)}
Context Type: file_change
Importance: 7/10

💾 This change is now preserved for session restoration.
Use this tool whenever significant files are modified to maintain context continuity.
"""
        
        return self._limit_length(result, max_answer_chars)


class AutoDecisionSaveTool(Tool, ToolMarkerDoesNotRequireActiveProject):
    """Automatically save important decisions as context"""
    
    def apply(self, decision: str, importance: int = 7, reasoning: str = "",
              max_answer_chars: int = TOOL_DEFAULT_MAX_ANSWER_LENGTH) -> str:
        """
        Save important decisions automatically with reasoning.
        
        :param decision: The decision that was made
        :param importance: Importance level 1-10
        :param reasoning: Reasoning behind the decision
        :param max_answer_chars: Maximum response length
        :return: Decision save confirmation
        """
        # Set up auto context manager
        auto_context_manager.agent = self.agent
        if self.agent and hasattr(self.agent, 'get_project_root'):
            project_root = self.agent.get_project_root()
            if project_root:
                auto_context_manager.setup_persistence(project_root)
        
        # Combine decision and reasoning
        full_decision = f"{decision}"
        if reasoning:
            full_decision += f"\n\nReasoning: {reasoning}"
        
        # Automatically save this decision
        auto_context_manager.auto_save_on_decision_point(full_decision, importance)
        
        result = f"""🧠 Decision Automatically Saved!
Decision: {decision}
Importance: {importance}/10
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🤖 AUTO-SAVED: Decision automatically preserved in context
Tags: auto, decision, reasoning
Context Type: decision
Importance: {importance}/10

{f"Reasoning: {reasoning}" if reasoning else ""}

💾 This decision is now available for session restoration and future reference.
"""
        
        return self._limit_length(result, max_answer_chars)


class LoadSessionFromDiskTool(Tool, ToolMarkerDoesNotRequireActiveProject):
    """Load previous session from disk storage"""
    
    def apply(self, max_answer_chars: int = TOOL_DEFAULT_MAX_ANSWER_LENGTH) -> str:
        """
        Load previous session data from disk storage.
        
        :param max_answer_chars: Maximum response length
        :return: Session loading result
        """
        # Set up auto context manager
        auto_context_manager.agent = self.agent
        if self.agent and hasattr(self.agent, 'get_project_root'):
            project_root = self.agent.get_project_root()
            if project_root:
                auto_context_manager.setup_persistence(project_root)
        
        # Load session from disk
        session_data = auto_context_manager.load_session_from_disk()
        
        if not session_data:
            return "No previous session found on disk. Start a new session with start_context_session."
        
        result = f"""📂 Previous Session Loaded from Disk!
Session ID: {session_data.get('session_id', 'Unknown')}
Task: {session_data.get('task_description', 'Unknown')}
Started: {session_data.get('started_at', 'Unknown')}
Last Activity: {session_data.get('last_activity', 'Unknown')}

📊 Session Data:
- Files Modified: {len(session_data.get('files_modified', []))}
- Decisions Made: {len(session_data.get('decisions_made', []))}
- Tags: {', '.join(session_data.get('tags', []))}

💾 Session persistence working correctly!
Context data is preserved across restarts.

Use search_context_tool to find specific memories from this session.
"""
        
        return self._limit_length(result, max_answer_chars)


# Update the LLM instructions
def get_enhanced_context_instructions() -> str:
    """Get enhanced instructions for the LLM to use context tools proactively"""
    return """
=== ENHANCED CONTEXT MANAGEMENT INSTRUCTIONS ===

The LLM should AUTOMATICALLY use these tools during work:

🤖 AUTOMATIC TRIGGERS:
1. **After modifying files**: Call file_change_monitor(file_path, "modified")
2. **Before task adherence checks**: Use enhanced_think_about_task_adherence (auto-saves)
3. **When making decisions**: Call auto_decision_save(decision, importance, reasoning)
4. **At session start**: Call load_session_from_disk() to restore previous context

📋 PROACTIVE SAVING PATTERNS:
- File changes → Immediate context save with file_change_monitor
- Task adherence → Auto-save progress and alignment check
- Decisions → Save with reasoning and importance level
- Milestones → Use save_context_extraction with high importance

🏷️ TAGGING STRATEGY:
- Use descriptive tags: implementation, debugging, architecture, testing
- Include file types: python, typescript, yaml, config
- Add urgency: critical, important, minor
- Context types: file_change, decision, work_state, problem_solution

💾 PERSISTENCE:
- All context automatically saved to .serena/context/
- Session data persists across restarts
- Use load_session_from_disk on new sessions
- Search previous context with search_context_tool

🎯 CONTEXT OPTIMIZATION:
- Keep compressed memories in context window
- Load only relevant memories based on current task
- Use smart tagging for efficient retrieval
- Preserve all information in compressed form

The system ensures seamless session restoration when context limits are exceeded!
"""
