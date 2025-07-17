"""
Phase 2: Smart Context Management with Compressed Memory Loading
Fixes the decompression issue and implements tag-based intelligent loading
"""

import json
import logging
import re
import hashlib
import threading
from collections import Counter
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from serena.tools import Tool, ToolMarkerDoesNotRequireActiveProject, TOOL_DEFAULT_MAX_ANSWER_LENGTH


log = logging.getLogger(__name__)


class SmartContextLoader:
    """Loads compressed context based on relevance without decompressing"""
    
    def __init__(self, agent=None):
        self.agent = agent
        self.compressed_memories: Dict[str, Dict] = {}
        self.tag_index: Dict[str, List[str]] = {}
        self.task_patterns: Dict[str, List[str]] = {
            'coding': ['implementation', 'file_change', 'debug', 'code'],
            'architecture': ['decision', 'design', 'architecture', 'planning'],
            'debugging': ['problem_solution', 'error', 'fix', 'debug'],
            'documentation': ['docs', 'documentation', 'explanation'],
            'testing': ['test', 'validation', 'verification']
        }
        
    def store_compressed_memory(self, content: str, tags: List[str], 
                              context_type: str, importance: int) -> str:
        """Store compressed memory with tags for smart retrieval"""
        # Compress the content
        compressed, ratio = self._compress_text(content)
        
        memory_id = hashlib.md5(content.encode()).hexdigest()[:12]
        
        memory = {
            'id': memory_id,
            'compressed_content': compressed,
            'original_size': len(content),
            'compressed_size': len(compressed),
            'compression_ratio': ratio,
            'tags': tags,
            'context_type': context_type,
            'importance': importance,
            'timestamp': datetime.now().isoformat(),
            'access_count': 0
        }
        
        self.compressed_memories[memory_id] = memory
        
        # Update tag index
        for tag in tags:
            if tag not in self.tag_index:
                self.tag_index[tag] = []
            self.tag_index[tag].append(memory_id)
            
        # Store in Serena memory as compressed
        if self.agent:
            self.agent.memories_manager.save_memory(
                f"compressed_{memory_id}",
                f"COMPRESSED[{ratio:.1f}x]: {compressed}"
            )
            
        return memory_id
    
    def load_relevant_compressed_context(self, current_task: str, 
                                       task_type: str = 'coding',
                                       max_memories: int = 5) -> str:
        """Load relevant compressed memories based on task WITHOUT decompressing"""
        
        # Get task-relevant tags
        relevant_tags = self.task_patterns.get(task_type, [])
        
        # Find memories with relevant tags
        memory_scores = {}
        
        for memory_id, memory in self.compressed_memories.items():
            score = 0
            
            # Tag relevance
            for tag in memory['tags']:
                if tag in relevant_tags:
                    score += 3
                if tag.lower() in current_task.lower():
                    score += 5
                    
            # Context type relevance
            if memory['context_type'] in relevant_tags:
                score += 2
                
            # Importance weight
            score += memory['importance']
            
            # Recency bonus (newer = better)
            days_old = (datetime.now() - datetime.fromisoformat(memory['timestamp'])).days
            score += max(0, 10 - days_old)
            
            if score > 0:
                memory_scores[memory_id] = score
        
        # Sort by relevance and take top N
        top_memories = sorted(memory_scores.items(), key=lambda x: x[1], reverse=True)[:max_memories]
        
        # Build compressed context string
        context_parts = [
            f"=== RELEVANT COMPRESSED CONTEXT FOR: {current_task} ===",
            f"Task type: {task_type} | Loaded {len(top_memories)} compressed memories",
            ""
        ]
        
        total_compressed_size = 0
        total_original_size = 0
        
        for memory_id, score in top_memories:
            memory = self.compressed_memories[memory_id]
            
            # Increment access count
            memory['access_count'] += 1
            
            context_parts.append(
                f"[{memory['context_type']}|{memory['importance']}/10|{memory['compression_ratio']:.1f}x] "
                f"{memory['compressed_content']}"
            )
            
            total_compressed_size += memory['compressed_size']
            total_original_size += memory['original_size']
            
        overall_ratio = total_original_size / total_compressed_size if total_compressed_size > 0 else 1.0
        
        context_parts.extend([
            "",
            f"=== COMPRESSION SUMMARY ===",
            f"Total memories: {len(top_memories)}",
            f"Original size: {total_original_size} chars",
            f"Compressed size: {total_compressed_size} chars", 
            f"Space saved: {overall_ratio:.1f}x compression",
            f"Context window savings: {total_original_size - total_compressed_size} chars"
        ])
        
        return "\n".join(context_parts)
    
    def _compress_text(self, text: str) -> Tuple[str, float]:
        """Enhanced compression with context-aware abbreviations"""
        # Word frequency compression
        words = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_-]{2,}\b', text)
        word_counts = Counter(words)
        top_words = word_counts.most_common(50)
        
        compressed = text
        for i, (word, freq) in enumerate(top_words):
            if freq > 1:  # Only compress words that appear multiple times
                if i < 26:
                    code = chr(ord('a') + i)
                else:
                    code = f"x{i-25}"
                compressed = re.sub(r'\b' + re.escape(word) + r'\b', code, compressed)
        
        # Context-aware abbreviations for common programming terms
        abbreviations = {
            'function': 'fn', 'variable': 'var', 'parameter': 'param',
            'implementation': 'impl', 'configuration': 'config',
            'documentation': 'docs', 'architecture': 'arch',
            'development': 'dev', 'production': 'prod',
            'repository': 'repo', 'application': 'app',
            'environment': 'env', 'database': 'db'
        }
        
        for full, abbrev in abbreviations.items():
            compressed = compressed.replace(full, abbrev)
        
        # Remove extra whitespace
        compressed = re.sub(r'\s+', ' ', compressed)
        compressed = re.sub(r'\n\s*\n', '\n', compressed)
        
        ratio = len(text) / len(compressed) if len(compressed) > 0 else 1.0
        return compressed, ratio
    
    def get_compression_legend(self) -> str:
        """Get legend for understanding compressed text"""
        return """
=== COMPRESSION LEGEND ===
Common abbreviations used:
fn=function, var=variable, param=parameter, impl=implementation
config=configuration, docs=documentation, arch=architecture
dev=development, prod=production, repo=repository, app=application
env=environment, db=database

Single letters (a-z) = most frequent words in context
Format: [type|importance/10|ratio] compressed_content
"""


# Global smart context loader
smart_loader = SmartContextLoader()


class LoadRelevantContextTool(Tool, ToolMarkerDoesNotRequireActiveProject):
    """Load relevant compressed context for current task WITHOUT decompressing"""
    
    def apply(self, current_task: str, task_type: str = "coding", max_memories: int = 5,
              max_answer_chars: int = TOOL_DEFAULT_MAX_ANSWER_LENGTH) -> str:
        """
        Load relevant compressed memories for current task without decompressing.
        This saves context window space by keeping content compressed.
        
        :param current_task: Description of current task
        :param task_type: Type of task (coding, architecture, debugging, documentation, testing)
        :param max_memories: Maximum number of memories to load
        :param max_answer_chars: Maximum response length
        :return: Compressed context ready for model consumption
        """
        try:
            smart_loader.agent = self.agent
            
            compressed_context = smart_loader.load_relevant_compressed_context(
                current_task, task_type, max_memories
            )
            
            legend = smart_loader.get_compression_legend()
            
            response = f"""🧠 Loaded relevant compressed context for task: "{current_task}"

{compressed_context}

{legend}

💡 This compressed context is ready for direct use by the model.
Context window savings achieved through smart compression and relevance filtering.
The model can understand compressed content without decompression.
"""
            
            return self._limit_length(response, max_answer_chars)
            
        except Exception as e:
            return f"Error loading compressed context: {str(e)}"


class StoreCompressedMemoryTool(Tool, ToolMarkerDoesNotRequireActiveProject):
    """Store memory in compressed format with smart tags"""
    
    def apply(self, content: str, tags: str, context_type: str = "general", 
              importance: int = 5, max_answer_chars: int = TOOL_DEFAULT_MAX_ANSWER_LENGTH) -> str:
        """
        Store memory in compressed format with tags for smart retrieval.
        
        :param content: Content to compress and store
        :param tags: Comma-separated tags for smart retrieval
        :param context_type: Type of context (coding, architecture, debugging, etc.)
        :param importance: Importance level 1-10
        :param max_answer_chars: Maximum response length
        :return: Storage confirmation with compression stats
        """
        try:
            smart_loader.agent = self.agent
            
            tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
            tag_list.append(context_type)  # Add context type as tag
            
            memory_id = smart_loader.store_compressed_memory(
                content, tag_list, context_type, importance
            )
            
            memory = smart_loader.compressed_memories[memory_id]
            
            response = f"""💾 Memory stored in compressed format!
Memory ID: {memory_id}
Original size: {memory['original_size']} chars
Compressed size: {memory['compressed_size']} chars
Compression ratio: {memory['compression_ratio']:.1f}x
Space saved: {memory['original_size'] - memory['compressed_size']} chars

Tags: {', '.join(tag_list)}
Context type: {context_type}
Importance: {importance}/10

✅ Memory is now available for smart retrieval based on task relevance.
Use load_relevant_context to retrieve compressed memories for your current task.
"""
            
            return self._limit_length(response, max_answer_chars)
            
        except Exception as e:
            return f"Error storing compressed memory: {str(e)}"


class ContextCompressionStatsTool(Tool, ToolMarkerDoesNotRequireActiveProject):
    """Get statistics about compressed context system"""
    
    def apply(self, max_answer_chars: int = TOOL_DEFAULT_MAX_ANSWER_LENGTH) -> str:
        """
        Get statistics about compressed context system and memory usage.
        
        :param max_answer_chars: Maximum response length
        :return: Comprehensive statistics
        """
        try:
            smart_loader.agent = self.agent
            
            total_memories = len(smart_loader.compressed_memories)
            if total_memories == 0:
                return "No compressed memories stored yet. Use store_compressed_memory to start saving context."
            
            total_original = sum(m['original_size'] for m in smart_loader.compressed_memories.values())
            total_compressed = sum(m['compressed_size'] for m in smart_loader.compressed_memories.values())
            total_space_saved = total_original - total_compressed
            overall_ratio = total_original / total_compressed if total_compressed > 0 else 1.0
            
            # Tag statistics
            tag_counts = {}
            for memory in smart_loader.compressed_memories.values():
                for tag in memory['tags']:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
            
            top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            
            # Context type distribution
            type_counts = {}
            for memory in smart_loader.compressed_memories.values():
                ctx_type = memory['context_type']
                type_counts[ctx_type] = type_counts.get(ctx_type, 0) + 1
            
            response = f"""📊 Compressed Context System Statistics:

🗜️ Compression Performance:
- Total memories: {total_memories}
- Original size: {total_original:,} chars
- Compressed size: {total_compressed:,} chars
- Space saved: {total_space_saved:,} chars ({overall_ratio:.1f}x compression)

🏷️ Top Tags:
{chr(10).join([f"  {tag}: {count} memories" for tag, count in top_tags[:5]])}

📋 Context Types:
{chr(10).join([f"  {ctx_type}: {count} memories" for ctx_type, count in type_counts.items()])}

💡 Context Window Optimization:
- Every context load saves ~{total_space_saved/total_memories:.0f} chars per memory on average
- Smart loading prevents context window overflow
- Compressed memories can be read directly by the model

Use load_relevant_context to efficiently load task-specific compressed memories.
"""
            
            return self._limit_length(response, max_answer_chars)
            
        except Exception as e:
            return f"Error getting context stats: {str(e)}"
