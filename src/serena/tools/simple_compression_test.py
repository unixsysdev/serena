"""
Simple test tool to verify tool loading works
"""

from serena.tools import Tool, ToolMarkerDoesNotRequireActiveProject, TOOL_DEFAULT_MAX_ANSWER_LENGTH


class TestSimpleCompressionTool(Tool, ToolMarkerDoesNotRequireActiveProject):
    """
    Simple test tool for compression functionality.
    """
    
    def apply(self, text: str, max_answer_chars: int = TOOL_DEFAULT_MAX_ANSWER_LENGTH) -> str:
        """
        Simple text compression test.
        
        :param text: Text to compress
        :param max_answer_chars: Maximum response length
        :return: Compressed text result
        """
        try:
            # Simple compression: just apply basic abbreviations
            compressed = text.replace('apiVersion:', 'v:')
            compressed = compressed.replace('metadata:', 'm:')
            compressed = compressed.replace('namespace:', 'ns:')
            compressed = compressed.replace('spec:', 's:')
            compressed = compressed.replace('containers:', 'c:')
            
            original_size = len(text)
            compressed_size = len(compressed)
            ratio = original_size / compressed_size if compressed_size > 0 else 1.0
            
            result = f"""=== SIMPLE COMPRESSION TEST ===
Original size: {original_size} characters
Compressed size: {compressed_size} characters
Compression ratio: {ratio:.2f}x

=== COMPRESSED TEXT ===
{compressed}
"""
            
            return self._limit_length(result, max_answer_chars)
            
        except Exception as e:
            return f"Error in compression test: {str(e)}"
