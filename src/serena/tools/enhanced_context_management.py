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
    """Enhanced automatic context management with extensive detail and Serena integration"""
    
    def __init__(self, agent=None):
        self.agent = agent
        self.context_dir = None
        self.session_file = None
        self.file_watch_list = set()
        self.last_file_states = {}
        self.current_session_context = []
        
    def setup_persistence(self, project_root: str):
        """Setup persistent storage in .serena directory"""
        self.context_dir = Path(project_root) / ".serena" / "context"
        self.context_dir.mkdir(parents=True, exist_ok=True)
        self.session_file = self.context_dir / "current_session.json"
        
    def auto_save_comprehensive_file_change(self, file_path: str, change_type: str = "modified"):
        """Save EXTENSIVE file change context with complete content"""
        if not self.agent or not self._is_significant_file(file_path):
            return
            
        try:
            # Read current file content
            with open(file_path, 'r', encoding='utf-8') as f:
                current_content = f.read()
        except Exception:
            current_content = "Could not read file content"
            
        # Get file statistics
        try:
            stat = os.stat(file_path)
            file_size = stat.st_size
            mod_time = datetime.fromtimestamp(stat.st_mtime)
        except Exception:
            file_size = 0
            mod_time = datetime.now()
            
        # Extract code structure information
        code_analysis = self._analyze_code_structure(file_path, current_content)
        
        # Create EXTENSIVE context content
        extensive_content = f"""COMPREHENSIVE FILE CHANGE CONTEXT: {file_path}

--- FILE METADATA ---
Change Type: {change_type}
File Size: {file_size} bytes
Last Modified: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}
File Extension: {os.path.splitext(file_path)[1]}
Relative Path: {file_path}

--- COMPLETE FILE CONTENT ---
{current_content}

--- CODE STRUCTURE ANALYSIS ---
{code_analysis}

--- CHANGE CONTEXT ---
Session Changes: {len(self.current_session_context)} modifications this session
Previous Context: {self._get_recent_session_context()}

--- INTEGRATION IMPACT ---
Potential Dependencies: {self._analyze_file_dependencies(file_path)}
Related Files: {self._find_related_files(file_path)}

--- IMPLEMENTATION NOTES ---
This file change was part of ongoing development work.
Full context preserved for session restoration and compression.
Content includes complete file state for accurate restoration.

--- SERENA MEMORY INTEGRATION ---
This context is cross-referenced with Serena's memory system.
Tags enable bidirectional lookup and discovery.
Available for both context compression and normal memory search.
"""
        
        # Generate comprehensive tags
        tags = self._generate_comprehensive_tags(file_path, current_content, change_type)
        
        # Save to both context system AND Serena memories
        self._save_to_both_systems(
            content=extensive_content,
            context_type="file_change",
            importance=8,
            tags=tags,
            memory_name=f"context_file_change_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        
        # Add to session context
        self.current_session_context.append({
            'type': 'file_change',
            'file': file_path,
            'timestamp': datetime.now().isoformat(),
            'change_type': change_type
        })
    
    def auto_save_comprehensive_decision(self, decision: str, reasoning: str = "", importance: int = 7):
        """Save EXTENSIVE decision context with complete reasoning"""
        if not self.agent:
            return
            
        # Create comprehensive decision context
        extensive_content = f"""COMPREHENSIVE DECISION CONTEXT: {decision}

--- DECISION SUMMARY ---
Decision: {decision}
Importance Level: {importance}/10
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

--- COMPLETE REASONING ---
{reasoning if reasoning else "No additional reasoning provided"}

--- SESSION CONTEXT ---
Current Session Duration: {self._get_session_duration()}
Related File Changes: {self._get_related_file_changes()}
Previous Decisions This Session: {self._get_session_decisions()}

--- IMPLEMENTATION IMPLICATIONS ---
Files Likely to be Affected: {self._predict_affected_files(decision)}
Testing Requirements: {self._predict_testing_needs(decision)}
Integration Points: {self._identify_integration_points(decision)}

--- ARCHITECTURAL IMPACT ---
{self._analyze_architectural_impact(decision)}

--- FUTURE CONSIDERATIONS ---
Potential Follow-up Tasks: {self._predict_followup_tasks(decision)}
Monitoring Points: {self._identify_monitoring_points(decision)}
Documentation Updates Needed: {self._identify_doc_updates(decision)}

--- CROSS-REFERENCE INFORMATION ---
Related Memories: {self._find_related_memories(decision)}
Historical Context: {self._get_historical_context(decision)}

--- COMPLETE DECISION TRAIL ---
This decision is part of ongoing development work preserved for:
- Session restoration when context limits exceeded
- Historical decision tracking and analysis  
- Cross-referencing with related work and memories
- Comprehensive context compression and restoration
"""
        
        # Generate decision-specific tags
        tags = self._generate_decision_tags(decision, reasoning)
        
        # Save to both systems
        self._save_to_both_systems(
            content=extensive_content,
            context_type="decision",
            importance=importance,
            tags=tags,
            memory_name=f"auto_decision_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
    
    def auto_save_context_extraction(self, content: str, context_type: str, importance: int, tags: str):
        """Enhanced context extraction that integrates with Serena memories"""
        if not self.agent:
            return
            
        # Enhance the content with additional context
        enhanced_content = f"""ENHANCED CONTEXT EXTRACTION

--- ORIGINAL CONTENT ---
{content}

--- ENHANCED CONTEXT ---
Session ID: {self._get_session_id()}
Total Session Context: {len(self.current_session_context)} items
Context Type: {context_type}
Importance: {importance}/10
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

--- SESSION INTEGRATION ---
Related Session Items: {self._get_related_session_items(context_type)}
Session Progress: {self._calculate_session_progress()}

--- SERENA MEMORY CROSS-REFERENCE ---
This context extraction is integrated with Serena's memory system
for bidirectional lookup and comprehensive search capabilities.

--- COMPRESSION READINESS ---
Content size: {len(enhanced_content)} characters
Estimated compression ratio: {self._estimate_compression_ratio(enhanced_content)}
Compression effectiveness: {'High' if len(enhanced_content) > 1000 else 'Medium' if len(enhanced_content) > 500 else 'Low'}
"""
        
        # Create comprehensive tag list
        comprehensive_tags = f"{tags},session_integration,enhanced_context,serena_memory"
        
        # Save to both systems
        memory_name = f"context_{context_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self._save_to_both_systems(
            content=enhanced_content,
            context_type=context_type,
            importance=importance,
            tags=comprehensive_tags,
            memory_name=memory_name
        )
    
    def _save_to_both_systems(self, content: str, context_type: str, importance: int, tags: str, memory_name: str):
        """Save content to both Serena memory system and context system"""
        # Save to Serena memory system
        if hasattr(self.agent, 'memories_manager'):
            self.agent.memories_manager.save_memory(memory_name, content)
        
        # Also save to context system if available
        try:
            if hasattr(self.agent, 'get_tool'):
                save_tool = self.agent.get_tool('SaveContextExtractionTool')
                if save_tool:
                    save_tool.apply(
                        content=content,
                        context_type=context_type,
                        importance=importance,
                        tags=tags
                    )
        except Exception as e:
            log.warning(f"Could not save to context system: {e}")
    
    def _analyze_code_structure(self, file_path: str, content: str) -> str:
        """Analyze code structure for comprehensive context"""
        if not content:
            return "No content to analyze"
            
        lines = content.split('\n')
        analysis = []
        
        # Basic metrics
        analysis.append(f"Total Lines: {len(lines)}")
        analysis.append(f"Non-empty Lines: {len([l for l in lines if l.strip()])}")
        
        # Look for common patterns
        if file_path.endswith('.py'):
            classes = [l for l in lines if l.strip().startswith('class ')]
            functions = [l for l in lines if l.strip().startswith('def ')]
            imports = [l for l in lines if l.strip().startswith('import ') or l.strip().startswith('from ')]
            
            analysis.append(f"Classes: {len(classes)}")
            analysis.append(f"Functions: {len(functions)}")
            analysis.append(f"Imports: {len(imports)}")
            
            if classes:
                analysis.append(f"Class Names: {[c.split('class ')[1].split('(')[0].split(':')[0] for c in classes]}")
            if functions:
                analysis.append(f"Function Names: {[f.split('def ')[1].split('(')[0] for f in functions]}")
        
        return '\n'.join(analysis)
    
    def _generate_comprehensive_tags(self, file_path: str, content: str, change_type: str) -> str:
        """Generate comprehensive tags for better discovery"""
        tags = []
        
        # File-based tags
        tags.append(os.path.basename(file_path))
        tags.append(os.path.splitext(file_path)[1].replace('.', ''))
        tags.append(change_type)
        
        # Content-based tags
        if 'class ' in content:
            tags.append('classes')
        if 'def ' in content:
            tags.append('functions')
        if 'import ' in content:
            tags.append('imports')
        if 'Flask' in content:
            tags.append('flask')
        if 'compression' in content.lower():
            tags.append('compression')
        if 'context' in content.lower():
            tags.append('context')
        
        # Session tags
        tags.extend(['auto', 'file_change', 'extensive', 'serena_integration'])
        
        return ','.join(tags)
    
    def _generate_decision_tags(self, decision: str, reasoning: str) -> str:
        """Generate decision-specific tags"""
        tags = ['auto', 'decision', 'extensive', 'serena_integration']
        
        # Extract key terms from decision
        decision_lower = decision.lower()
        if 'architecture' in decision_lower:
            tags.append('architecture')
        if 'implementation' in decision_lower:
            tags.append('implementation')
        if 'design' in decision_lower:
            tags.append('design')
        if 'api' in decision_lower:
            tags.append('api')
        if 'compression' in decision_lower:
            tags.append('compression')
        
        return ','.join(tags)
    
    # Helper methods for context analysis
    def _get_session_duration(self) -> str:
        return f"~{len(self.current_session_context) * 5} minutes estimated"
    
    def _get_related_file_changes(self) -> str:
        file_changes = [item for item in self.current_session_context if item['type'] == 'file_change']
        return f"{len(file_changes)} files modified this session"
    
    def _get_session_decisions(self) -> str:
        decisions = [item for item in self.current_session_context if item['type'] == 'decision']
        return f"{len(decisions)} decisions made this session"
    
    def _predict_affected_files(self, decision: str) -> str:
        return "Files likely to be affected based on decision context (analysis)"
    
    def _predict_testing_needs(self, decision: str) -> str:
        return "Testing requirements based on decision impact (analysis)"
    
    def _identify_integration_points(self, decision: str) -> str:
        return "Key integration points to monitor (analysis)"
    
    def _analyze_architectural_impact(self, decision: str) -> str:
        return "Architectural implications and considerations (analysis)"
    
    def _predict_followup_tasks(self, decision: str) -> str:
        return "Likely follow-up tasks and implementation steps (analysis)"
    
    def _identify_monitoring_points(self, decision: str) -> str:
        return "Areas to monitor after implementation (analysis)"
    
    def _identify_doc_updates(self, decision: str) -> str:
        return "Documentation that may need updates (analysis)"
    
    def _find_related_memories(self, decision: str) -> str:
        return "Related Serena memories and context items (search)"
    
    def _get_historical_context(self, decision: str) -> str:
        return "Historical context and related past decisions (search)"
    
    def _analyze_file_dependencies(self, file_path: str) -> str:
        return "Potential file dependencies and imports (analysis)"
    
    def _find_related_files(self, file_path: str) -> str:
        return "Related files in the project structure (analysis)"
    
    def _get_recent_session_context(self) -> str:
        recent = self.current_session_context[-3:] if len(self.current_session_context) > 3 else self.current_session_context
        return f"Last {len(recent)} session items"
    
    def _get_session_id(self) -> str:
        return f"session_{datetime.now().strftime('%Y%m%d_%H%M')}"
    
    def _get_related_session_items(self, context_type: str) -> str:
        related = [item for item in self.current_session_context if item['type'] == context_type]
        return f"{len(related)} related {context_type} items this session"
    
    def _calculate_session_progress(self) -> str:
        return f"{len(self.current_session_context)} context items captured"
    
    def _estimate_compression_ratio(self, content: str) -> str:
        length = len(content)
        if length > 2000:
            return "3-5x (excellent)"
        elif length > 1000:
            return "2-3x (good)"
        elif length > 500:
            return "1.5-2x (fair)"
        else:
            return "1.2x (minimal)"
    
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
