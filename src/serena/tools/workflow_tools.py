"""
Tools supporting the general workflow of the agent
"""

import json
import platform

from serena.tools import Tool, ToolMarkerDoesNotRequireActiveProject


class CheckOnboardingPerformedTool(Tool):
    """
    Checks whether project onboarding was already performed.
    """

    def apply(self) -> str:
        """
        Checks whether project onboarding was already performed.
        You should always call this tool before beginning to actually work on the project/after activating a project,
        but after calling the initial instructions tool.
        """
        from .memory_tools import ListMemoriesTool

        list_memories_tool = self.agent.get_tool(ListMemoriesTool)
        memories = json.loads(list_memories_tool.apply())
        if len(memories) == 0:
            return (
                "Onboarding not performed yet (no memories available). "
                + "You should perform onboarding by calling the `onboarding` tool before proceeding with the task."
            )
        else:
            return f"""The onboarding was already performed, below is the list of available memories.
            Do not read them immediately, just remember that they exist and that you can read them later, if it is necessary
            for the current task.
            Some memories may be based on previous conversations, others may be general for the current project.
            You should be able to tell which one you need based on the name of the memory.
            
            {memories}"""


class OnboardingTool(Tool):
    """
    Performs onboarding (identifying the project structure and essential tasks, e.g. for testing or building).
    """

    def apply(self) -> str:
        """
        Call this tool if onboarding was not performed yet.
        You will call this tool at most once per conversation.

        :return: instructions on how to create the onboarding information
        """
        system = platform.system()
        return self.prompt_factory.create_onboarding_prompt(system=system)


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
