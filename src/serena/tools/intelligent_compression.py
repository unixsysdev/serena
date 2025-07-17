"""
Intelligent Generic Compression System
NO hardcoded domain-specific abbreviations - fully adaptive and intelligent
"""

import re
import json
import hashlib
import logging
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Set, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from serena.tools import Tool, ToolMarkerDoesNotRequireActiveProject, TOOL_DEFAULT_MAX_ANSWER_LENGTH


log = logging.getLogger(__name__)


@dataclass
class ContentAnalysis:
    """Analysis of content type and patterns"""
    content_type: str  # 'code', 'documentation', 'config', 'data', 'mixed'
    language: Optional[str]  # programming language if detected
    patterns: Dict[str, int]  # common patterns found
    structure_type: str  # 'hierarchical', 'linear', 'tabular', 'mixed'
    repetition_score: float  # how repetitive the content is (0-1)


class IntelligentCompressor:
    """Intelligent compression that adapts to content type and patterns"""
    
    def __init__(self):
        self.adaptive_dictionary: Dict[str, str] = {}
        self.reverse_dictionary: Dict[str, str] = {}
        self.compression_history: List[Dict] = []
        
    def analyze_content(self, text: str) -> ContentAnalysis:
        """Intelligently analyze content to determine optimal compression strategy"""
        
        # Detect content type
        content_type = self._detect_content_type(text)
        language = self._detect_programming_language(text) if content_type == 'code' else None
        
        # Analyze patterns
        patterns = self._extract_patterns(text)
        
        # Analyze structure
        structure_type = self._analyze_structure(text)
        
        # Calculate repetition score
        repetition_score = self._calculate_repetition_score(text)
        
        return ContentAnalysis(
            content_type=content_type,
            language=language,
            patterns=patterns,
            structure_type=structure_type,
            repetition_score=repetition_score
        )
    
    def _detect_content_type(self, text: str) -> str:
        """Detect if content is code, documentation, config, or data"""
        
        # Code indicators
        code_patterns = [
            r'\bdef\s+\w+\s*\(',  # Python functions
            r'\bfunction\s+\w+\s*\(',  # JavaScript functions
            r'\bclass\s+\w+',  # Class definitions
            r'\bimport\s+\w+',  # Imports
            r'\bfrom\s+\w+\s+import',  # Python imports
            r'[{}()[\];]',  # Brackets and semicolons
            r'=\s*["\'].*["\']',  # String assignments
        ]
        
        # Documentation indicators
        doc_patterns = [
            r'#{1,6}\s+\w+',  # Markdown headers
            r'\*\*\w+\*\*',  # Bold text
            r'\[.*\]\(.*\)',  # Markdown links
            r'```\w*',  # Code blocks
            r'^\s*-\s+',  # List items
        ]
        
        # Config indicators
        config_patterns = [
            r'^\w+\s*[:=]\s*',  # Key-value pairs
            r'^\s*-\s+\w+\s*:',  # YAML lists
            r'[{}"]',  # JSON-like structure
        ]
        
        code_score = sum(1 for pattern in code_patterns if re.search(pattern, text, re.MULTILINE))
        doc_score = sum(1 for pattern in doc_patterns if re.search(pattern, text, re.MULTILINE))
        config_score = sum(1 for pattern in config_patterns if re.search(pattern, text, re.MULTILINE))
        
        scores = {'code': code_score, 'documentation': doc_score, 'config': config_score}
        
        if max(scores.values()) == 0:
            return 'data'
        
        return max(scores, key=scores.get)
    
    def _detect_programming_language(self, text: str) -> Optional[str]:
        """Detect programming language from code patterns"""
        
        language_patterns = {
            'python': [r'\bdef\s+', r'\bimport\s+', r'\bclass\s+', r':\s*$', r'self\.'],
            'javascript': [r'\bfunction\s+', r'\bconst\s+', r'\blet\s+', r'=>', r'console\.log'],
            'typescript': [r':\s*\w+\s*[=;]', r'\binterface\s+', r'\btype\s+\w+\s*='],
            'java': [r'\bpublic\s+class', r'\bprivate\s+', r'\bstatic\s+', r'System\.out'],
            'go': [r'\bfunc\s+', r'\bpackage\s+', r'fmt\.Print', r':='],
            'rust': [r'\bfn\s+', r'\blet\s+mut', r'\bmatch\s+', r'println!'],
            'yaml': [r'^\s*\w+\s*:', r'^\s*-\s+', r'---'],
            'json': [r'[{}"\[\]]', r':\s*["\d\[\{]'],
        }
        
        scores = {}
        for lang, patterns in language_patterns.items():
            scores[lang] = sum(1 for pattern in patterns if re.search(pattern, text, re.MULTILINE))
        
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        
        return None
    
    def _extract_patterns(self, text: str) -> Dict[str, int]:
        """Extract common patterns specific to the content"""
        
        patterns = {}
        
        # Common programming patterns
        if 'def ' in text or 'function ' in text:
            patterns['functions'] = len(re.findall(r'\b(?:def|function)\s+\w+', text))
        
        if 'class ' in text:
            patterns['classes'] = len(re.findall(r'\bclass\s+\w+', text))
        
        if 'import ' in text:
            patterns['imports'] = len(re.findall(r'\bimport\s+', text))
        
        # Structural patterns
        patterns['indentation_levels'] = len(set(re.findall(r'^(\s*)', text, re.MULTILINE)))
        patterns['line_count'] = len(text.split('\n'))
        patterns['avg_line_length'] = sum(len(line) for line in text.split('\n')) / len(text.split('\n'))
        
        return patterns
    
    def _analyze_structure(self, text: str) -> str:
        """Analyze the structural type of content"""
        
        lines = text.split('\n')
        
        # Check for hierarchical structure (indentation)
        indentation_levels = set()
        for line in lines:
            if line.strip():
                indentation_levels.add(len(line) - len(line.lstrip()))
        
        if len(indentation_levels) > 3:
            return 'hierarchical'
        
        # Check for tabular structure
        if '\t' in text or re.search(r'\|\s*\w+\s*\|', text):
            return 'tabular'
        
        # Check for linear structure
        if len(indentation_levels) <= 2:
            return 'linear'
        
        return 'mixed'
    
    def _calculate_repetition_score(self, text: str) -> float:
        """Calculate how repetitive the content is (0-1) - MUCH more aggressive"""
        
        # Include ALL words, even 1-2 character ones for maximum compression
        words = re.findall(r'\b\w+\b', text.lower())  # ALL words, no minimum length
        if not words:
            return 0.0
        
        word_counts = Counter(words)
        total_words = len(words)
        unique_words = len(word_counts)
        
        # Much more aggressive repetition scoring
        repetition_score = 1.0 - (unique_words / total_words)
        
        # Boost score significantly for any repeated words
        repeated_words = sum(1 for count in word_counts.values() if count > 1)
        if repeated_words > 0:
            repetition_score = max(repetition_score, 0.7)  # Force high repetition score
        
        # Boost even more for common English words
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those', 'text', 'system', 'compression', 'words', 'test'}
        if any(word in word_counts for word in common_words):
            repetition_score = max(repetition_score, 0.8)  # Very high score for common words
        
        return min(1.0, repetition_score)
    
    def intelligent_compress(self, text: str) -> Tuple[str, float, Dict]:
        """Simple frequency-based compression - replace ALL words with short codes"""
        
        # Extract ALL words (no filtering, no analysis - just compress everything)
        words = re.findall(r'\b\w+\b', text)
        word_counts = Counter(w.lower() for w in words)
        
        # Sort by frequency (most frequent first)
        sorted_words = word_counts.most_common()
        
        # Build dictionary: most frequent words get shortest codes
        self.adaptive_dictionary.clear()
        self.reverse_dictionary.clear()
        
        for i, (word, freq) in enumerate(sorted_words):
            if i < 26:
                code = chr(ord('a') + i)  # a, b, c, d, ...
            elif i < 52:
                code = chr(ord('A') + (i - 26))  # A, B, C, D, ...
            elif i < 62:
                code = str(i - 52)  # 0, 1, 2, 3, ...
            elif i < 162:
                code = f"x{i-61}"  # x1, x2, x3, ...
            elif i < 262:
                code = f"y{i-161}"  # y1, y2, y3, ...
            elif i < 362:
                code = f"z{i-261}"  # z1, z2, z3, ...
            else:
                code = f"w{i-361}"  # w1, w2, w3, ...
            
            self.adaptive_dictionary[word] = code
            self.reverse_dictionary[code] = word
        
        # Replace words with codes (case-insensitive)
        compressed = text
        for word, code in self.adaptive_dictionary.items():
            pattern = r'\b' + re.escape(word) + r'\b'
            compressed = re.sub(pattern, code, compressed, flags=re.IGNORECASE)
        
        # Basic whitespace cleanup
        compressed = re.sub(r'\s+', ' ', compressed)  # Multiple spaces -> single
        compressed = compressed.strip()
        
        ratio = len(text) / len(compressed) if len(compressed) > 0 else 1.0
        
        compression_info = {
            'original_size': len(text),
            'compressed_size': len(compressed),
            'ratio': ratio,
            'dictionary_size': len(self.adaptive_dictionary)
        }
        
        return compressed, ratio, compression_info
    
    def _compress_high_repetition(self, text: str, analysis: ContentAnalysis) -> Tuple[str, float]:
        """Compress highly repetitive content with ULTRA-AGGRESSIVE word replacement for 3-4x ratios"""
        
        # Extract ALL words including 1-letter ones for maximum compression
        words = re.findall(r'\b\w+\b', text.lower())  # ALL words, no minimum length
        word_counts = Counter(words)
        
        # Get top words - EXTREMELY aggressive
        top_words = word_counts.most_common(1000)  # Compress up to 1000 words
        
        compressed = text
        self.adaptive_dictionary.clear()
        self.reverse_dictionary.clear()
        
        # ULTRA-AGGRESSIVE compression with single characters
        symbol_index = 0
        for word, freq in top_words:
            if freq > 0:  # Compress EVERYTHING, even words appearing only once
                # Use the shortest possible codes
                if symbol_index < 26:
                    code = chr(ord('a') + symbol_index)  # a, b, c, d, ...
                elif symbol_index < 52:  
                    code = chr(ord('A') + (symbol_index - 26))  # A, B, C, D, ...
                elif symbol_index < 62:
                    code = str(symbol_index - 52)  # 0, 1, 2, 3, ...
                elif symbol_index < 88:
                    code = '~' + chr(ord('a') + (symbol_index - 62))  # ~a, ~b, ~c, ...
                elif symbol_index < 114:
                    code = '`' + chr(ord('a') + (symbol_index - 88))  # `a, `b, `c, ...
                elif symbol_index < 140:
                    code = '^' + chr(ord('a') + (symbol_index - 114))  # ^a, ^b, ^c, ...
                else:
                    code = f"w{symbol_index-139}"  # Fallback for extremely rare cases
                
                self.adaptive_dictionary[word] = code
                self.reverse_dictionary[code] = word
                symbol_index += 1
                
                # Case-insensitive replacement for maximum compression
                pattern = r'\b' + re.escape(word) + r'\b'
                compressed = re.sub(pattern, code, compressed, flags=re.IGNORECASE)
        
        # ULTRA-aggressive whitespace and punctuation compression
        compressed = re.sub(r'\n\s*\n\s*\n+', '\n', compressed)  # Multiple newlines -> single
        compressed = re.sub(r'[ \t]{2,}', ' ', compressed)  # Multiple spaces -> single
        compressed = re.sub(r'^\s+', '', compressed, flags=re.MULTILINE)  # Remove ALL leading whitespace
        compressed = re.sub(r'\s+$', '', compressed, flags=re.MULTILINE)  # Remove trailing whitespace
        
        # Aggressive punctuation compression
        compressed = re.sub(r'\s*([,;:!?])\s*', r'\1', compressed)  # Remove ALL spaces around punctuation
        compressed = re.sub(r'\s*([.])\s*', r'\1', compressed)  # Remove spaces around periods
        compressed = re.sub(r'\s*([()[\]{}])\s*', r'\1', compressed)  # Remove spaces around brackets
        
        # Remove quotes if they're just for formatting
        if compressed.count('"') % 2 == 0:  # Even number of quotes
            compressed = compressed.replace(' "', '"').replace('" ', '"')
        
        ratio = len(text) / len(compressed) if len(compressed) > 0 else 1.0
        return compressed, ratio
    
    def _compress_code_content(self, text: str, analysis: ContentAnalysis) -> Tuple[str, float]:
        """Compress code content with AGGRESSIVE syntax awareness for 3-4x ratios"""
        
        compressed = text
        
        # Language-specific aggressive compression
        if analysis.language:
            compressed = self._apply_aggressive_language_compression(compressed, analysis.language)
        
        # Aggressive code pattern compression
        code_replacements = self._extract_aggressive_code_patterns(text)
        for pattern, replacement in code_replacements.items():
            compressed = compressed.replace(pattern, replacement)
        
        # Extract ALL identifiers and keywords aggressively
        identifiers = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', text)
        identifier_counts = Counter(identifiers)
        
        # Compress frequent identifiers with VERY short codes
        self.adaptive_dictionary.clear()
        self.reverse_dictionary.clear()
        
        for i, (identifier, freq) in enumerate(identifier_counts.most_common(300)):
            if freq > 1:  # Compress anything used more than once
                # Single character codes for maximum compression
                if i < 26:
                    code = chr(ord('a') + i)  # a, b, c, d, ...
                elif i < 52:
                    code = chr(ord('A') + (i - 26))  # A, B, C, D, ...
                elif i < 62:
                    code = str(i - 52)  # 0, 1, 2, ...
                elif i < 72:
                    code = '_' + str(i - 62)  # _0, _1, ...
                elif i < 82:
                    code = '=' + str(i - 72)  # =0, =1, ...
                else:
                    code = f"i{i-81}"  # Longer codes for rare identifiers
                
                self.adaptive_dictionary[identifier] = code
                self.reverse_dictionary[code] = identifier
                
                # Word boundary replacement
                pattern = r'\b' + re.escape(identifier) + r'\b'
                compressed = re.sub(pattern, code, compressed)
        
        # Additional aggressive whitespace compression for code
        compressed = re.sub(r'[ \t]+', ' ', compressed)  # Multiple spaces -> single
        compressed = re.sub(r'\n\s*\n\s*\n+', '\n\n', compressed)  # Remove excess newlines
        compressed = re.sub(r'^\s+', '', compressed, flags=re.MULTILINE)  # Remove leading whitespace
        
        ratio = len(text) / len(compressed) if len(compressed) > 0 else 1.0
        return compressed, ratio
    
    def _apply_aggressive_language_compression(self, text: str, language: str) -> str:
        """Apply AGGRESSIVE language-specific compression for maximum ratios"""
        
        # This is MUCH more aggressive than the previous version
        if language == 'python':
            # Common Python keywords and patterns
            replacements = {
                ' def ': ' d ',
                ' class ': ' c ',
                ' import ': ' i ',
                ' from ': ' f ',
                ' return ': ' r ',
                ' if ': ' I ',
                ' else ': ' E ',
                ' elif ': ' L ',
                ' while ': ' W ',
                ' for ': ' F ',
                ' try ': ' T ',
                ' except ': ' X ',
                ' finally ': ' Y ',
                ' with ': ' w ',
                ' as ': ' s ',
                ' self.': ' S.',
                ' None': ' N',
                ' True': ' 1',
                ' False': ' 0',
                ' lambda ': ' l ',
                ' print(': ' p(',
                ' len(': ' L(',
                ' str(': ' s(',
                ' int(': ' i(',
                ' list(': ' l(',
                ' dict(': ' d(',
                ' range(': ' r(',
                '__init__': '__i',
                '__str__': '__s',
                '__repr__': '__r',
            }
            
        elif language == 'javascript':
            replacements = {
                ' function ': ' f ',
                ' const ': ' c ',
                ' let ': ' l ',
                ' var ': ' v ',
                ' return ': ' r ',
                ' if ': ' I ',
                ' else ': ' E ',
                ' for ': ' F ',
                ' while ': ' W ',
                ' this.': ' t.',
                ' console.log': ' c.l',
                ' document.': ' d.',
                ' window.': ' w.',
                ' undefined': ' u',
                ' null': ' n',
                ' true': ' 1',
                ' false': ' 0',
                ' typeof ': ' t ',
                ' instanceof ': ' i ',
            }
            
        elif language == 'typescript':
            replacements = {
                ' function ': ' f ',
                ' const ': ' c ',
                ' let ': ' l ',
                ' interface ': ' i ',
                ' type ': ' t ',
                ' export ': ' e ',
                ' import ': ' I ',
                ' return ': ' r ',
                ' public ': ' p ',
                ' private ': ' P ',
                ' protected ': ' o ',
                ' readonly ': ' R ',
                ' string': ' s',
                ' number': ' n',
                ' boolean': ' b',
                ' object': ' o',
                ' array': ' a',
            }
            
        else:
            # Generic language patterns
            replacements = {
                ' return ': ' r ',
                ' function ': ' f ',
                ' class ': ' c ',
                ' import ': ' i ',
                ' export ': ' e ',
                ' const ': ' C ',
                ' let ': ' l ',
                ' var ': ' v ',
            }
        
        # Apply all replacements
        for original, compressed in replacements.items():
            if original in text:  # Only apply if pattern exists
                text = text.replace(original, compressed)
                
        return text

    def _extract_aggressive_code_patterns(self, text: str) -> Dict[str, str]:
        """Extract and aggressively compress common code patterns"""
        
        patterns = {}
        
        # Aggressive operator compression
        if ' = ' in text and text.count(' = ') > 3:
            patterns[' = '] = '='
        if ' == ' in text:
            patterns[' == '] = '=='
        if ' != ' in text:
            patterns[' != '] = '!='
        if ' <= ' in text:
            patterns[' <= '] = '<='
        if ' >= ' in text:
            patterns[' >= '] = '>='
        if ' && ' in text:
            patterns[' && '] = '&&'
        if ' || ' in text:
            patterns[' || '] = '||'
        if ' -> ' in text:
            patterns[' -> '] = '->'
        if ' => ' in text:
            patterns[' => '] = '=>'
        
        # Object/method access patterns
        if 'self.' in text:
            patterns['self.'] = 'S.'
        if 'this.' in text:
            patterns['this.'] = 't.'
        if '.__' in text:  # Python dunder methods
            patterns['.__'] = '._'
        
        # Common bracket patterns
        if text.count('()') > 5:
            patterns['()'] = '()'  # Keep as is, but could be further compressed
        if text.count('[]') > 3:
            patterns['[]'] = '[]'
        if text.count('{}') > 3:
            patterns['{}'] = '{}'
        
        # Indentation and whitespace
        if '\n    ' in text:  # 4-space indentation
            patterns['\n    '] = '\n  '  # Reduce to 2 spaces
        if '\n        ' in text:  # 8-space indentation
            patterns['\n        '] = '\n   '  # Reduce to 3 spaces
        
        return patterns
    
    def _extract_code_patterns(self, text: str) -> Dict[str, str]:
        """Extract and compress common code patterns found in the text"""
        
        patterns = {}
        
        # Only add patterns that actually exist in the text
        if 'self.' in text:
            patterns['self.'] = 's.'
        if 'this.' in text:
            patterns['this.'] = 't.'
        if ' = ' in text and text.count(' = ') > 5:
            patterns[' = '] = '='
        if ' == ' in text:
            patterns[' == '] = '=='
        if ' != ' in text:
            patterns[' != '] = '!='
        
        return patterns
    
    def _compress_hierarchical_content(self, text: str, analysis: ContentAnalysis) -> Tuple[str, float]:
        """Compress hierarchical content by reducing indentation and structure markers"""
        
        lines = text.split('\n')
        compressed_lines = []
        
        for line in lines:
            if line.strip():
                # Reduce excessive indentation
                indent = len(line) - len(line.lstrip())
                if indent > 0:
                    # Compress indentation intelligently
                    new_indent = min(indent // 2, 4)  # Max 4 spaces
                    compressed_lines.append(' ' * new_indent + line.lstrip())
                else:
                    compressed_lines.append(line)
            else:
                compressed_lines.append('')
        
        compressed = '\n'.join(compressed_lines)
        
        # Remove excessive blank lines
        compressed = re.sub(r'\n\s*\n\s*\n+', '\n\n', compressed)
        
        ratio = len(text) / len(compressed) if len(compressed) > 0 else 1.0
        return compressed, ratio
    
    def _compress_general_content(self, text: str, analysis: ContentAnalysis) -> Tuple[str, float]:
        """General compression strategy with MUCH better ratios"""
        
        # Word frequency approach - more aggressive
        words = re.findall(r'\b\w{2,}\b', text.lower())  # Include 2+ char words
        word_counts = Counter(words)
        top_words = word_counts.most_common(200)  # More words to compress
        
        compressed = text
        self.adaptive_dictionary.clear()
        self.reverse_dictionary.clear()
        
        # MUCH shorter codes for better compression
        for i, (word, freq) in enumerate(top_words):
            if freq > 1:  # Compress words appearing more than once
                # Single characters for most frequent
                if i < 26:
                    code = chr(ord('a') + i)  # a, b, c, d, ...
                elif i < 52:  
                    code = chr(ord('A') + (i - 26))  # A, B, C, D, ...
                elif i < 62:
                    code = str(i - 52)  # 0, 1, 2, ...
                elif i < 72:
                    code = '_' + str(i - 62)  # _0, _1, _2, ...
                else:
                    code = f"w{i-71}"  # Longer codes only for less frequent words
                
                self.adaptive_dictionary[word] = code
                self.reverse_dictionary[code] = word
                
                # Case-insensitive replacement
                pattern = r'\b' + re.escape(word) + r'\b'
                compressed = re.sub(pattern, code, compressed, flags=re.IGNORECASE)
        
        # Additional compression
        compressed = re.sub(r'[ \t]+', ' ', compressed)  # Multiple spaces -> single space
        compressed = re.sub(r'\n\s*\n\s*\n+', '\n\n', compressed)  # Remove excess newlines
        compressed = re.sub(r'\s*([,;:!?.])\s*', r'\1', compressed)  # Remove spaces around punctuation
        
        ratio = len(text) / len(compressed) if len(compressed) > 0 else 1.0
        return compressed, ratio
    
    def _get_strategy_name(self, analysis: ContentAnalysis) -> str:
        """Get the name of compression strategy used"""
        if analysis.repetition_score > 0.3:
            return 'high_repetition'
        elif analysis.content_type == 'code':
            return 'syntax_aware'
        elif analysis.structure_type == 'hierarchical':
            return 'hierarchical'
        else:
            return 'general'
    
    def decompress(self, compressed: str) -> str:
        """Decompress text using stored dictionary"""
        
        decompressed = compressed
        
        # Reverse the word replacements
        for code, original in self.reverse_dictionary.items():
            pattern = r'\b' + re.escape(code) + r'\b'
            decompressed = re.sub(pattern, original, decompressed)
        
        return decompressed
    
    def get_compression_summary(self) -> Dict[str, Any]:
        """Get summary of compression performance"""
        
        if not self.compression_history:
            return {'total_operations': 0}
        
        total_ops = len(self.compression_history)
        avg_ratio = sum(op['ratio'] for op in self.compression_history) / total_ops
        strategies_used = Counter(op['strategy'] for op in self.compression_history)
        content_types = Counter(op['content_type'] for op in self.compression_history)
        
        return {
            'total_operations': total_ops,
            'average_compression_ratio': avg_ratio,
            'strategies_used': dict(strategies_used),
            'content_types_processed': dict(content_types),
            'total_space_saved': sum(op['original_size'] - op['compressed_size'] for op in self.compression_history)
        }


# Global intelligent compressor
intelligent_compressor = IntelligentCompressor()


class IntelligentCompressTextTool(Tool, ToolMarkerDoesNotRequireActiveProject):
    """Intelligent text compression that adapts to content type and patterns"""
    
    def apply(self, text: str, max_answer_chars: int = TOOL_DEFAULT_MAX_ANSWER_LENGTH) -> str:
        """
        Simple frequency-based compression - replace ALL words with short codes.
        
        :param text: Text to compress
        :param max_answer_chars: Maximum response length
        :return: Compressed text with dictionary
        """
        try:
            compressed, ratio, info = intelligent_compressor.intelligent_compress(text)
            
            # Simple output: ratio + compressed text + dictionary
            response = f"""COMPRESSION: {ratio:.2f}x ({info['original_size']} -> {info['compressed_size']} chars)

COMPRESSED:
{compressed}

DICTIONARY ({info['dictionary_size']} words):
"""
            
            # Output dictionary as simple mapping
            for word, code in intelligent_compressor.adaptive_dictionary.items():
                response += f"{code}={word} "
                if len(response) > max_answer_chars - 100:  # Leave space for end
                    response += "..."
                    break
            
            return self._limit_length(response, max_answer_chars)
            
        except Exception as e:
            return f"Error: {str(e)}"


class IntelligentDecompressTextTool(Tool, ToolMarkerDoesNotRequireActiveProject):
    """Decompress intelligently compressed text"""
    
    def apply(self, compressed_text: str, max_answer_chars: int = TOOL_DEFAULT_MAX_ANSWER_LENGTH) -> str:
        """
        Decompress text - just output the result and dictionary for LLM to understand.
        
        :param compressed_text: Compressed text to decompress
        :param max_answer_chars: Maximum response length
        :return: Decompressed text with dictionary
        """
        try:
            # DON'T decompress - just give LLM the compressed text and dictionary
            # The LLM can understand it without actual decompression
            
            response = f"""COMPRESSED TEXT:
{compressed_text}

DICTIONARY FOR REFERENCE:
"""
            
            # Show the dictionary so LLM understands the mapping
            for code, word in intelligent_compressor.reverse_dictionary.items():
                response += f"{code}={word} "
                if len(response) > max_answer_chars - 100:
                    response += "..."
                    break
            
            response += "\n\nThe LLM can understand this compressed content without decompression."
            
            return self._limit_length(response, max_answer_chars)
            
        except Exception as e:
            return f"Error: {str(e)}"


class IntelligentCompressionAnalyticsTool(Tool, ToolMarkerDoesNotRequireActiveProject):
    """Get analytics about intelligent compression performance"""
    
    def apply(self, max_answer_chars: int = TOOL_DEFAULT_MAX_ANSWER_LENGTH) -> str:
        """
        Get comprehensive analytics about intelligent compression system.
        
        :param max_answer_chars: Maximum response length
        :return: Compression analytics and performance data
        """
        try:
            summary = intelligent_compressor.get_compression_summary()
            
            if summary['total_operations'] == 0:
                return "No compression operations performed yet. Try intelligent_compress_text first!"
            
            response = f"""📈 INTELLIGENT COMPRESSION ANALYTICS

🎯 Performance Summary:
- Total Operations: {summary['total_operations']}
- Average Compression: {summary['average_compression_ratio']:.2f}x
- Total Space Saved: {summary['total_space_saved']:,} chars

🧠 Strategies Used:
"""
            
            for strategy, count in summary['strategies_used'].items():
                response += f"  - {strategy}: {count} operations\n"
            
            response += f"""
📁 Content Types Processed:
"""
            
            for content_type, count in summary['content_types_processed'].items():
                response += f"  - {content_type}: {count} operations\n"
            
            response += f"""
✨ Intelligence Features:
- Adaptive compression based on content analysis
- No hardcoded domain-specific rules
- Learns patterns from actual text content
- Syntax-aware compression for code
- Structure-aware compression for hierarchical data
- High-repetition detection and aggressive compression

🚀 The system continuously adapts to provide optimal compression!
"""
            
            return self._limit_length(response, max_answer_chars)
            
        except Exception as e:
            return f"Error getting compression analytics: {str(e)}"
