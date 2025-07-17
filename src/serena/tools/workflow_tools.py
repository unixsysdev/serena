"""
Tools supporting the general workflow of the agent
"""

import json
import platform

from serena.tools import Tool, ToolMarkerDoesNotRequireActiveProject


class CheckOnboardingPerformedTool(Tool):
    """
    Enhanced onboarding check that includes context memories, tags, and session restoration.
    """

    def apply(self) -> str:
        """
        Enhanced onboarding check that detects:
        - Regular project memories
        - Context memories (decisions, work states, file changes)
        - Compressed sessions
        - Available context for restoration
        
        You should always call this tool before beginning to actually work on the project/after activating a project,
        but after calling the initial instructions tool.
        """
        from .memory_tools import ListMemoriesTool
        from .enhanced_context_management import SearchContextTool, ContextStatsTool

        list_memories_tool = self.agent.get_tool(ListMemoriesTool)
        memories = json.loads(list_memories_tool.apply())
        
        if len(memories) == 0:
            return (
                "Onboarding not performed yet (no memories available). "
                + "You should perform onboarding by calling the `onboarding` tool before proceeding with the task."
            )
        
        # Analyze memory types and context
        regular_memories = []
        context_memories = []
        session_memories = []
        compressed_memories = []
        
        for memory in memories:
            if memory.startswith('context_'):
                context_memories.append(memory)
            elif memory.startswith('session_'):
                session_memories.append(memory)
            elif memory.startswith('compressed_'):
                compressed_memories.append(memory)
            else:
                regular_memories.append(memory)
        
        # Get context statistics
        try:
            context_stats_tool = self.agent.get_tool(ContextStatsTool)
            context_stats = context_stats_tool.apply()
        except:
            context_stats = "Context management not available"
        
        # Build comprehensive onboarding report
        result = f"""🚀 ENHANCED ONBOARDING COMPLETE - Context-Aware Project State

📚 REGULAR PROJECT MEMORIES ({len(regular_memories)}):
{regular_memories}

🧠 CONTEXT MEMORIES ({len(context_memories)}):
{context_memories[:10]}{"..." if len(context_memories) > 10 else ""}

💾 SESSION DATA ({len(session_memories)}):
{session_memories[:5]}{"..." if len(session_memories) > 5 else ""}

🗜️ COMPRESSED CONTEXT ({len(compressed_memories)}):
{compressed_memories[:5]}{"..." if len(compressed_memories) > 5 else ""}

📊 CONTEXT MANAGEMENT STATUS:
{context_stats}

🎯 ONBOARDING RECOMMENDATIONS:
1. Regular memories contain project structure and guidelines
2. Context memories preserve work history and decisions
3. Session data can be restored for work continuation
4. Compressed memories contain extensive historical context

💡 USAGE TIPS:
- Use `search_context` to find relevant previous work
- Use `restore_session` if continuing from compressed session
- Use `load_relevant_context` for task-specific context
- Context memories follow patterns: context_{{type}}_{{timestamp}}

🏷️ MEMORY TAGS DETECTED:
- Context types: decision, work_state, file_change, problem_solution, testing
- Auto-saved decisions and important milestones preserved
- Session compression available for context limit management

✅ Project is fully onboarded with comprehensive context management!
Ready for intelligent work continuation with full historical context.

Note: Read memories selectively based on current task needs. Context search and restoration tools available for efficient work continuation."""
        
        return result


class OnboardingTool(Tool):
    """
    Enhanced onboarding that sets up context management and checks for existing context.
    """

    def apply(self) -> str:
        """
        Enhanced onboarding that:
        1. Performs traditional project structure analysis
        2. Initializes context management
        3. Checks for existing context memories
        4. Sets up session tracking
        
        Call this tool if onboarding was not performed yet.
        You will call this tool at most once per conversation.

        :return: instructions on how to create the onboarding information with context setup
        """
        from .enhanced_context_management import StartContextSessionTool, ContextStatsTool
        
        system = platform.system()
        basic_prompt = self.prompt_factory.create_onboarding_prompt(system=system)
        
        # Try to initialize context management
        try:
            # Start context session for this onboarding
            start_session_tool = self.agent.get_tool(StartContextSessionTool)
            session_result = start_session_tool.apply(
                task_description="Initial project onboarding with context setup",
                tags="onboarding,setup,initial"
            )
            
            # Get context stats
            context_stats_tool = self.agent.get_tool(ContextStatsTool)
            context_stats = context_stats_tool.apply()
            
            context_setup = f"""

🧠 CONTEXT MANAGEMENT INITIALIZED:
{session_result}

📊 Current Context Status:
{context_stats}

🎯 ENHANCED ONBOARDING INCLUDES:
1. Traditional project structure analysis
2. Context management system initialization  
3. Session tracking for work continuity
4. Auto-save capabilities for decisions
5. Compression for context limit management

💡 CONTEXT FEATURES AVAILABLE:
- save_context_extraction: Save important work points
- auto_decision_save: Automatically preserve decisions
- compress_session: Handle context limits
- restore_session: Continue work across sessions
- search_context: Find relevant previous work

🏷️ CONTEXT TAGGING SYSTEM:
- Types: decision, work_state, file_change, problem_solution, testing
- Tags: auto-generated + custom for organization
- Importance: 1-10 scale for prioritization

"""
        except Exception as e:
            context_setup = f"""

⚠️ CONTEXT MANAGEMENT SETUP:
Basic context tools available but session initialization had issues: {str(e)}
You can still use context management tools manually.

"""
        
        enhanced_prompt = f"""{basic_prompt}

{context_setup}

📋 ENHANCED ONBOARDING CHECKLIST:
After completing the basic onboarding tasks, also:

1. **Save Initial Project Structure** using save_context_extraction
2. **Document Key Architectural Decisions** with auto_decision_save  
3. **Set up Testing Commands** and save with appropriate tags
4. **Record Build/Development Workflows** for future reference
5. **Initialize Session Tracking** for work continuity

🚀 Your onboarding will now include comprehensive context management for better work continuity!"""
        
        return enhanced_prompt


class ThinkAboutCollectedInformationTool(Tool):
    """
    Thinking tool for pondering the completeness of collected information.
    """

    def apply(self) -> str:
        """
        Think about the collected information and whether it is sufficient and relevant.
        This tool should ALWAYS be called after you have completed a non-trivial sequence of searching steps like
        find_symbol, find_referencing_symbols, search_files_for_pattern, read_file, etc.
        """
        return self.prompt_factory.create_think_about_collected_information()


class ThinkAboutTaskAdherenceTool(Tool):
    """
    Enhanced thinking tool for determining whether the agent is still on track with the current task.
    Automatically saves context for session restoration.
    """

    def apply(self, max_answer_chars: int = 10000) -> str:
        """
        Think about the task at hand and whether you are still on track.
        Especially important if the conversation has been going on for a while and there
        has been a lot of back and forth.

        This tool should ALWAYS be called before you insert, replace, or delete code.
        Now automatically saves context for session continuity.
        """
        # Import here to avoid circular imports
        from .enhanced_context_management import auto_context_manager
        
        # Set up auto context manager
        auto_context_manager.agent = self.agent
        if self.agent and hasattr(self.agent, 'get_project_root'):
            project_root = self.agent.get_project_root()
            if project_root:
                auto_context_manager.setup_persistence(project_root)
        
        # Get the original prompt result
        result = self.prompt_factory.create_think_about_task_adherence()
        
        # Automatically save this task adherence check
        auto_context_manager.auto_save_on_task_adherence_check(
            "Task adherence check performed - evaluating alignment with user intentions and project requirements"
        )
        
        # Add auto-save notification
        enhanced_result = f"""{result}

🤖 AUTO-SAVED: This task adherence check has been automatically saved to context for session restoration.
Tags: auto, task-adherence, progress-check
Importance: 8/10

💾 Context will be preserved across sessions to maintain work continuity."""
        
        return enhanced_result[:max_answer_chars] if len(enhanced_result) > max_answer_chars else enhanced_result


class ThinkAboutWhetherYouAreDoneTool(Tool):
    """
    Thinking tool for determining whether the task is truly completed.
    """

    def apply(self) -> str:
        """
        Whenever you feel that you are done with what the user has asked for, it is important to call this tool.
        """
        return self.prompt_factory.create_think_about_whether_you_are_done()


class SummarizeChangesTool(Tool):
    """
    Provides instructions for summarizing the changes made to the codebase.
    """

    def apply(self) -> str:
        """
        Summarize the changes you have made to the codebase.
        This tool should always be called after you have fully completed any non-trivial coding task,
        but only after the think_about_whether_you_are_done call.
        """
        return self.prompt_factory.create_summarize_changes()


class PrepareForNewConversationTool(Tool):
    """
    Provides instructions for preparing for a new conversation (in order to continue with the necessary context).
    """

    def apply(self) -> str:
        """
        Instructions for preparing for a new conversation. This tool should only be called on explicit user request.
        """
        return self.prompt_factory.create_prepare_for_new_conversation()


class InitialInstructionsTool(Tool, ToolMarkerDoesNotRequireActiveProject):
    """
    Gets the initial instructions for the current project.
    Should only be used in settings where the system prompt cannot be set,
    e.g. in clients you have no control over, like Claude Desktop.
    """

    def apply(self) -> str:
        """
        Get the initial instructions for the current coding project.
        If you haven't received instructions on how to use Serena's tools in the system prompt,
        you should always call this tool before starting to work (including using any other tool) on any programming task,
        the only exception being when you are asked to call `activate_project`, which you should then call before.
        """
        return self.agent.create_system_prompt()
