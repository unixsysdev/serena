"""
Text compression tools for context management using hash dictionary compression.
"""

import json
import logging
import re
from collections import Counter
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import hashlib
import threading

from serena.tools import Tool, ToolMarkerDoesNotRequireActiveProject, TOOL_DEFAULT_MAX_ANSWER_LENGTH


log = logging.getLogger(__name__)


@dataclass
class CompressionStats:
    """Statistics about compression operations"""
    original_size: int
    compressed_size: int
    ratio: float
    dictionary_size: int
    timestamp: datetime
    operation: str  # 'compress' or 'decompress'


@dataclass
class WordMapping:
    """Mapping between original word and compressed code"""
    original: str
    code: str
    frequency: int


class CompressionDictionary:
    """Manages word frequency analysis and compression mappings"""
    
    def __init__(self):
        self.word_to_code: Dict[str, str] = {}
        self.code_to_word: Dict[str, str] = {}
        self.word_frequencies: Dict[str, int] = {}
        self.dictionary_hash: Optional[str] = None
        
    def build_from_text(self, text: str, max_words: int = 200) -> None:
        """Build dictionary from text using word frequency analysis"""
        # Extract words (alphanumeric with underscores/hyphens, min 3 chars)
        words = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_-]{2,}\b', text)
        
        # Count frequencies
        word_counts = Counter(words)
        
        # Take top N most frequent words
        top_words = word_counts.most_common(max_words)
        
        # Create mappings (most frequent words get shortest codes)
        self.word_to_code = {}
        self.code_to_word = {}
        self.word_frequencies = {}
        
        for i, (word, freq) in enumerate(top_words):
            if i < 50:
                code = f"w{i+1}"
            elif i < 100:
                code = f"x{i-49}"
            elif i < 150:
                code = f"y{i-99}"
            else:
                code = f"z{i-149}"
                
            self.word_to_code[word] = code
            self.code_to_word[code] = word
            self.word_frequencies[word] = freq
        
        # Generate dictionary hash for versioning
        dict_str = json.dumps(self.word_to_code, sort_keys=True)
        self.dictionary_hash = hashlib.md5(dict_str.encode()).hexdigest()[:8]
    
    def compress_text(self, text: str) -> str:
        """Apply compression mappings to text"""
        if not self.word_to_code:
            return text
            
        # Apply word replacements
        compressed = text
        for word, code in self.word_to_code.items():
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(word) + r'\b'
            compressed = re.sub(pattern, code, compressed)
        
        # Apply common abbreviations
        abbreviations = {
            'apiVersion:': 'v:',
            'metadata:': 'm:',
            'namespace:': 'ns:',
            'labels:': 'l:',
            'annotations:': 'a:',
            'spec:': 's:',
            'template:': 't:',
            'containers:': 'c:',
            'image:': 'i:',
            'resources:': 'r:',
            'requests:': 'rq:',
            'limits:': 'lm:',
            'environment:': 'e:',
            'variables:': 'vars:',
            'deployment:': 'dep:',
            'service:': 'svc:',
            'configmap:': 'cm:',
            'secret:': 'sec:',
            'kubernetes': 'k8s',
            'application': 'app',
            'configuration': 'config',
            'environment': 'env',
            'development': 'dev',
            'production': 'prod',
            'staging': 'stage',
            'repository': 'repo',
            'pipeline': 'pipe',
            'container': 'ctr',
            'manifest': 'mf',
            'FILE:': 'F:',
        }
        
        for original, abbrev in abbreviations.items():
            compressed = compressed.replace(original, abbrev)
            
        return compressed
    
    def decompress_text(self, compressed: str) -> str:
        """Decompress text using stored mappings"""
        if not self.code_to_word:
            return compressed
            
        # Reverse word mappings
        decompressed = compressed
        for code, word in self.code_to_word.items():
            pattern = r'\b' + re.escape(code) + r'\b'
            decompressed = re.sub(pattern, word, decompressed)
            
        # Reverse abbreviations
        reverse_abbreviations = {
            'v:': 'apiVersion:',
            'm:': 'metadata:',
            'ns:': 'namespace:',
            'l:': 'labels:',
            'a:': 'annotations:',
            's:': 'spec:',
            't:': 'template:',
            'c:': 'containers:',
            'i:': 'image:',
            'r:': 'resources:',
            'rq:': 'requests:',
            'lm:': 'limits:',
            'e:': 'environment:',
            'vars:': 'variables:',
            'dep:': 'deployment:',
            'svc:': 'service:',
            'cm:': 'configmap:',
            'sec:': 'secret:',
            'k8s': 'kubernetes',
            'app': 'application',
            'config': 'configuration',
            'env': 'environment',
            'dev': 'development',
            'prod': 'production',
            'stage': 'staging',
            'repo': 'repository',
            'pipe': 'pipeline',
            'ctr': 'container',
            'mf': 'manifest',
            'F:': 'FILE:',
        }
        
        for abbrev, original in reverse_abbreviations.items():
            decompressed = decompressed.replace(abbrev, original)
            
        return decompressed
    
    def get_dictionary_info(self) -> Dict[str, Any]:
        """Get dictionary metadata"""
        return {
            'hash': self.dictionary_hash,
            'word_count': len(self.word_to_code),
            'mappings': [
                {'original': word, 'code': code, 'frequency': self.word_frequencies.get(word, 0)}
                for word, code in self.word_to_code.items()
            ]
        }


class CompressionService:
    """Service for managing compression operations and statistics"""
    
    def __init__(self):
        self.dictionaries: Dict[str, CompressionDictionary] = {}
        self.stats: List[CompressionStats] = []
        self.lock = threading.Lock()
        
    def compress_with_dictionary(self, text: str, dictionary_name: str = "default") -> tuple[str, CompressionStats]:
        """Compress text using or creating a named dictionary"""
        with self.lock:
            # Create or get dictionary
            if dictionary_name not in self.dictionaries:
                self.dictionaries[dictionary_name] = CompressionDictionary()
                self.dictionaries[dictionary_name].build_from_text(text)
            
            dictionary = self.dictionaries[dictionary_name]
            
            # Compress
            compressed = dictionary.compress_text(text)
            
            # Create stats
            stats = CompressionStats(
                original_size=len(text),
                compressed_size=len(compressed),
                ratio=len(text) / len(compressed) if len(compressed) > 0 else 1.0,
                dictionary_size=len(dictionary.word_to_code),
                timestamp=datetime.now(),
                operation='compress'
            )
            
            self.stats.append(stats)
            return compressed, stats
    
    def decompress_with_dictionary(self, compressed: str, dictionary_name: str = "default") -> tuple[str, CompressionStats]:
        """Decompress text using named dictionary"""
        with self.lock:
            if dictionary_name not in self.dictionaries:
                raise ValueError(f"Dictionary '{dictionary_name}' not found")
                
            dictionary = self.dictionaries[dictionary_name]
            decompressed = dictionary.decompress_text(compressed)
            
            # Create stats
            stats = CompressionStats(
                original_size=len(compressed),
                compressed_size=len(decompressed),
                ratio=len(decompressed) / len(compressed) if len(compressed) > 0 else 1.0,
                dictionary_size=len(dictionary.word_to_code),
                timestamp=datetime.now(),
                operation='decompress'
            )
            
            self.stats.append(stats)
            return decompressed, stats
    
    def get_dictionary_info(self, dictionary_name: str) -> Dict[str, Any]:
        """Get information about a specific dictionary"""
        with self.lock:
            if dictionary_name not in self.dictionaries:
                raise ValueError(f"Dictionary '{dictionary_name}' not found")
            return self.dictionaries[dictionary_name].get_dictionary_info()
    
    def get_stats(self) -> List[Dict[str, Any]]:
        """Get compression statistics"""
        with self.lock:
            return [
                {
                    'original_size': stat.original_size,
                    'compressed_size': stat.compressed_size,
                    'ratio': stat.ratio,
                    'dictionary_size': stat.dictionary_size,
                    'timestamp': stat.timestamp.isoformat(),
                    'operation': stat.operation
                }
                for stat in self.stats
            ]
    
    def clear_stats(self) -> None:
        """Clear compression statistics"""
        with self.lock:
            self.stats.clear()
            
    def list_dictionaries(self) -> List[str]:
        """List available dictionaries"""
        with self.lock:
            return list(self.dictionaries.keys())


# Global compression service instance
_compression_service = CompressionService()


class CompressTextTool(Tool, ToolMarkerDoesNotRequireActiveProject):
    """
    Compresses text using hash dictionary compression for context management.
    """
    
    def apply(self, text: str, dictionary_name: str = "default", max_answer_chars: int = TOOL_DEFAULT_MAX_ANSWER_LENGTH) -> str:
        """
        Compress text using word frequency analysis and hash dictionary compression.
        
        This tool creates a dictionary of frequently used words and replaces them with shorter codes.
        It also applies common abbreviations for technical terms. The compressed text includes
        the dictionary information needed for decompression.
        
        :param text: The text to compress
        :param dictionary_name: Name of the dictionary to use (default: "default")
        :param max_answer_chars: Maximum length of the response
        :return: Compressed text with dictionary information
        """
        try:
            compressed, stats = _compression_service.compress_with_dictionary(text, dictionary_name)
            
            # Get dictionary info
            dict_info = _compression_service.get_dictionary_info(dictionary_name)
            
            # Format response with dictionary header
            response = f"""=== COMPRESSED TEXT ===
Dictionary: {dictionary_name} (hash: {dict_info['hash']})
Original size: {stats.original_size} chars
Compressed size: {stats.compressed_size} chars
Compression ratio: {stats.ratio:.1f}x
Dictionary size: {stats.dictionary_size} words
Timestamp: {stats.timestamp.isoformat()}

=== WORD DICTIONARY ===
# Format: ORIGINAL -> CODE (frequency)
"""
            
            # Add dictionary mappings (top 20 for brevity)
            for mapping in dict_info['mappings'][:20]:
                response += f"{mapping['original']} -> {mapping['code']} ({mapping['frequency']})\n"
            
            if len(dict_info['mappings']) > 20:
                response += f"... and {len(dict_info['mappings']) - 20} more mappings\n"
            
            response += f"""
=== ABBREVIATED TERMS ===
# Standard abbreviations used:
apiVersion: -> v:, metadata: -> m:, namespace: -> ns:, labels: -> l:
spec: -> s:, containers: -> c:, image: -> i:, resources: -> r:
kubernetes -> k8s, application -> app, configuration -> config
environment -> env, development -> dev, production -> prod
repository -> repo, pipeline -> pipe, FILE: -> F:

=== COMPRESSED CONTENT ===
{compressed}
"""
            
            return self._limit_length(response, max_answer_chars)
            
        except Exception as e:
            return f"Error compressing text: {str(e)}"


class DecompressTextTool(Tool, ToolMarkerDoesNotRequireActiveProject):
    """
    Decompresses text that was compressed using hash dictionary compression.
    """
    
    def apply(self, compressed_text: str, dictionary_name: str = "default", max_answer_chars: int = TOOL_DEFAULT_MAX_ANSWER_LENGTH) -> str:
        """
        Decompress text using the specified dictionary.
        
        :param compressed_text: The compressed text to decompress
        :param dictionary_name: Name of the dictionary to use (default: "default")
        :param max_answer_chars: Maximum length of the response
        :return: Decompressed text
        """
        try:
            decompressed, stats = _compression_service.decompress_with_dictionary(compressed_text, dictionary_name)
            
            response = f"""=== DECOMPRESSED TEXT ===
Dictionary: {dictionary_name}
Compressed size: {stats.original_size} chars
Decompressed size: {stats.compressed_size} chars
Expansion ratio: {stats.ratio:.1f}x
Timestamp: {stats.timestamp.isoformat()}

=== CONTENT ===
{decompressed}
"""
            
            return self._limit_length(response, max_answer_chars)
            
        except Exception as e:
            return f"Error decompressing text: {str(e)}"


class CompressionStatsTool(Tool, ToolMarkerDoesNotRequireActiveProject):
    """
    Get compression statistics and dictionary information.
    """
    
    def apply(self, dictionary_name: str = "", max_answer_chars: int = TOOL_DEFAULT_MAX_ANSWER_LENGTH) -> str:
        """
        Get compression statistics and dictionary information.
        
        :param dictionary_name: Specific dictionary to get info for (optional)
        :param max_answer_chars: Maximum length of the response
        :return: Statistics and dictionary information
        """
        try:
            response = "=== COMPRESSION STATISTICS ===\n"
            
            # Get overall stats
            stats = _compression_service.get_stats()
            if stats:
                response += f"Total operations: {len(stats)}\n"
                response += f"Recent operations:\n"
                for stat in stats[-5:]:  # Show last 5 operations
                    response += f"  {stat['operation']}: {stat['ratio']:.1f}x ({stat['timestamp']})\n"
            else:
                response += "No compression operations recorded yet.\n"
            
            response += "\n=== AVAILABLE DICTIONARIES ===\n"
            dictionaries = _compression_service.list_dictionaries()
            
            if dictionaries:
                for dict_name in dictionaries:
                    try:
                        info = _compression_service.get_dictionary_info(dict_name)
                        response += f"Dictionary: {dict_name}\n"
                        response += f"  Hash: {info['hash']}\n"
                        response += f"  Word count: {info['word_count']}\n"
                        
                        if dictionary_name == dict_name:
                            response += f"  Top mappings:\n"
                            for mapping in info['mappings'][:10]:
                                response += f"    {mapping['original']} -> {mapping['code']} ({mapping['frequency']})\n"
                        response += "\n"
                    except Exception as e:
                        response += f"  Error getting info: {str(e)}\n"
            else:
                response += "No dictionaries available.\n"
            
            return self._limit_length(response, max_answer_chars)
            
        except Exception as e:
            return f"Error getting compression stats: {str(e)}"


class ClearCompressionStatsTool(Tool, ToolMarkerDoesNotRequireActiveProject):
    """
    Clear compression statistics and optionally dictionaries.
    """
    
    def apply(self, clear_dictionaries: bool = False, max_answer_chars: int = TOOL_DEFAULT_MAX_ANSWER_LENGTH) -> str:
        """
        Clear compression statistics and optionally dictionaries.
        
        :param clear_dictionaries: Whether to also clear all dictionaries (default: False)
        :param max_answer_chars: Maximum length of the response
        :return: Status message
        """
        try:
            # Clear stats
            _compression_service.clear_stats()
            
            message = "Compression statistics cleared.\n"
            
            if clear_dictionaries:
                with _compression_service.lock:
                    _compression_service.dictionaries.clear()
                message += "All dictionaries cleared.\n"
            
            return message
            
        except Exception as e:
            return f"Error clearing compression data: {str(e)}"
