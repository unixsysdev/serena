"""
Generic text compression REST API with hash dictionary compression.
Designed to work standalone and integrate with any system.
"""

import json
import logging
import re
from collections import Counter
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import hashlib
import threading
from flask import Flask, request, jsonify
import socket


log = logging.getLogger(__name__)


@dataclass
class CompressionStats:
    """Statistics about compression operations"""
    original_size: int
    compressed_size: int
    ratio: float
    dictionary_size: int
    timestamp: datetime
    operation: str
    dictionary_name: str


class CompressionDictionary:
    """Generic compression dictionary for any text content"""
    
    def __init__(self, name: str = "default"):
        self.name = name
        self.word_to_code: Dict[str, str] = {}
        self.code_to_word: Dict[str, str] = {}
        self.word_frequencies: Dict[str, int] = {}
        self.dictionary_hash: Optional[str] = None
        self.created_at: datetime = datetime.now()
        
    def build_from_text(self, text: str, max_words: int = 300, min_word_length: int = 3) -> None:
        """Build dictionary from text using word frequency analysis"""
        # Extract words (configurable minimum length)
        pattern = rf'\b[a-zA-Z_][a-zA-Z0-9_-]{{{min_word_length-1},}}\b'
        words = re.findall(pattern, text)
        
        # Count frequencies
        word_counts = Counter(words)
        
        # Take top N most frequent words
        top_words = word_counts.most_common(max_words)
        
        # Clear existing mappings
        self.word_to_code.clear()
        self.code_to_word.clear()
        self.word_frequencies.clear()
        
        # Create tiered mappings (shorter codes for more frequent words)
        for i, (word, freq) in enumerate(top_words):
            if i < 62:  # a-z, A-Z, 0-9 (single char codes)
                if i < 26:
                    code = chr(ord('a') + i)
                elif i < 52:
                    code = chr(ord('A') + (i - 26))
                else:
                    code = str(i - 52)
            elif i < 124:  # Two character codes
                code = f"x{i-61}"
            elif i < 186:  # Three character codes
                code = f"y{i-123}"
            else:  # Four character codes
                code = f"z{i-185}"
                
            self.word_to_code[word] = code
            self.code_to_word[code] = word
            self.word_frequencies[word] = freq
        
        # Generate dictionary hash for versioning
        dict_str = json.dumps(self.word_to_code, sort_keys=True)
        self.dictionary_hash = hashlib.md5(dict_str.encode()).hexdigest()[:12]
    
    def compress_text(self, text: str) -> str:
        """Apply compression mappings to text"""
        if not self.word_to_code:
            return text
            
        compressed = text
        
        # Apply word replacements (most frequent words first for better compression)
        for word, code in self.word_to_code.items():
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(word) + r'\b'
            compressed = re.sub(pattern, code, compressed)
        
        # Apply whitespace compression
        compressed = re.sub(r'\n\s*\n\s*\n', '\n\n', compressed)  # Reduce multiple blank lines
        compressed = re.sub(r'[ \t]+', ' ', compressed)  # Reduce multiple spaces/tabs
        
        return compressed
    
    def decompress_text(self, compressed: str) -> str:
        """Decompress text using stored mappings"""
        if not self.code_to_word:
            return compressed
            
        decompressed = compressed
        
        # Reverse word mappings
        for code, word in self.code_to_word.items():
            pattern = r'\b' + re.escape(code) + r'\b'
            decompressed = re.sub(pattern, word, decompressed)
            
        return decompressed
    
    def get_info(self) -> Dict[str, Any]:
        """Get dictionary metadata"""
        return {
            'name': self.name,
            'hash': self.dictionary_hash,
            'word_count': len(self.word_to_code),
            'created_at': self.created_at.isoformat(),
            'top_mappings': [
                {'word': word, 'code': code, 'frequency': self.word_frequencies.get(word, 0)}
                for word, code in list(self.word_to_code.items())[:20]
            ],
            'compression_preview': {
                'single_char_codes': len([c for c in self.word_to_code.values() if len(c) == 1]),
                'two_char_codes': len([c for c in self.word_to_code.values() if len(c) == 2]),
                'three_char_codes': len([c for c in self.word_to_code.values() if len(c) == 3]),
                'four_char_codes': len([c for c in self.word_to_code.values() if len(c) == 4])
            }
        }


class CompressionService:
    """Service for managing compression operations and statistics"""
    
    def __init__(self):
        self.dictionaries: Dict[str, CompressionDictionary] = {}
        self.stats: List[CompressionStats] = []
        self.lock = threading.Lock()
        
    def create_dictionary(self, name: str, text: str, max_words: int = 300, min_word_length: int = 3) -> Dict[str, Any]:
        """Create a new compression dictionary"""
        with self.lock:
            dictionary = CompressionDictionary(name)
            dictionary.build_from_text(text, max_words, min_word_length)
            self.dictionaries[name] = dictionary
            return dictionary.get_info()
    
    def compress_text(self, text: str, dictionary_name: str = "default", auto_create: bool = True) -> Tuple[str, CompressionStats]:
        """Compress text using specified dictionary"""
        with self.lock:
            # Create dictionary if it doesn't exist and auto_create is True
            if dictionary_name not in self.dictionaries:
                if auto_create:
                    self.create_dictionary(dictionary_name, text)
                else:
                    raise ValueError(f"Dictionary '{dictionary_name}' not found")
            
            dictionary = self.dictionaries[dictionary_name]
            compressed = dictionary.compress_text(text)
            
            # Create stats
            stats = CompressionStats(
                original_size=len(text),
                compressed_size=len(compressed),
                ratio=len(text) / len(compressed) if len(compressed) > 0 else 1.0,
                dictionary_size=len(dictionary.word_to_code),
                timestamp=datetime.now(),
                operation='compress',
                dictionary_name=dictionary_name
            )
            
            self.stats.append(stats)
            return compressed, stats
    
    def decompress_text(self, compressed: str, dictionary_name: str = "default") -> Tuple[str, CompressionStats]:
        """Decompress text using specified dictionary"""
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
                operation='decompress',
                dictionary_name=dictionary_name
            )
            
            self.stats.append(stats)
            return decompressed, stats
    
    def get_dictionary_info(self, dictionary_name: str) -> Dict[str, Any]:
        """Get information about a specific dictionary"""
        with self.lock:
            if dictionary_name not in self.dictionaries:
                raise ValueError(f"Dictionary '{dictionary_name}' not found")
            return self.dictionaries[dictionary_name].get_info()
    
    def list_dictionaries(self) -> List[Dict[str, Any]]:
        """List all available dictionaries"""
        with self.lock:
            return [
                {
                    'name': name,
                    'word_count': len(dictionary.word_to_code),
                    'hash': dictionary.dictionary_hash,
                    'created_at': dictionary.created_at.isoformat()
                }
                for name, dictionary in self.dictionaries.items()
            ]
    
    def get_stats(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get compression statistics"""
        with self.lock:
            recent_stats = self.stats[-limit:] if limit > 0 else self.stats
            return [
                {
                    'original_size': stat.original_size,
                    'compressed_size': stat.compressed_size,
                    'ratio': stat.ratio,
                    'dictionary_size': stat.dictionary_size,
                    'timestamp': stat.timestamp.isoformat(),
                    'operation': stat.operation,
                    'dictionary_name': stat.dictionary_name
                }
                for stat in recent_stats
            ]
    
    def clear_stats(self) -> None:
        """Clear compression statistics"""
        with self.lock:
            self.stats.clear()
    
    def delete_dictionary(self, dictionary_name: str) -> None:
        """Delete a dictionary"""
        with self.lock:
            if dictionary_name not in self.dictionaries:
                raise ValueError(f"Dictionary '{dictionary_name}' not found")
            del self.dictionaries[dictionary_name]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get service summary"""
        with self.lock:
            return {
                'total_dictionaries': len(self.dictionaries),
                'total_operations': len(self.stats),
                'dictionaries': list(self.dictionaries.keys()),
                'recent_operations': len([s for s in self.stats if (datetime.now() - s.timestamp).seconds < 3600])
            }


# Global compression service instance
compression_service = CompressionService()


class CompressionAPI:
    """REST API for generic text compression"""
    
    def __init__(self, service: CompressionService):
        self.service = service
        self.app = Flask(__name__)
        self.app.config['JSON_SORT_KEYS'] = False
        self._setup_routes()
        
    def _setup_routes(self) -> None:
        """Setup Flask routes"""
        
        @self.app.route('/health', methods=['GET'])
        def health():
            """Health check endpoint"""
            return jsonify({
                'status': 'healthy',
                'service': 'generic-compression-api',
                'timestamp': datetime.now().isoformat()
            })
        
        @self.app.route('/summary', methods=['GET'])
        def get_summary():
            """Get service summary"""
            try:
                return jsonify(self.service.get_summary())
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/dictionaries', methods=['GET'])
        def list_dictionaries():
            """List all dictionaries"""
            try:
                return jsonify({'dictionaries': self.service.list_dictionaries()})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/dictionaries', methods=['POST'])
        def create_dictionary():
            """Create a new dictionary"""
            try:
                data = request.get_json()
                if not data or 'name' not in data or 'text' not in data:
                    return jsonify({'error': 'Missing name or text parameter'}), 400
                    
                name = data['name']
                text = data['text']
                max_words = data.get('max_words', 300)
                min_word_length = data.get('min_word_length', 3)
                
                info = self.service.create_dictionary(name, text, max_words, min_word_length)
                return jsonify({'message': 'Dictionary created', 'dictionary': info})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/dictionaries/<name>', methods=['GET'])
        def get_dictionary(name):
            """Get dictionary information"""
            try:
                info = self.service.get_dictionary_info(name)
                return jsonify({'dictionary': info})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/dictionaries/<name>', methods=['DELETE'])
        def delete_dictionary(name):
            """Delete a dictionary"""
            try:
                self.service.delete_dictionary(name)
                return jsonify({'message': f'Dictionary {name} deleted'})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/compress', methods=['POST'])
        def compress():
            """Compress text"""
            try:
                data = request.get_json()
                if not data or 'text' not in data:
                    return jsonify({'error': 'Missing text parameter'}), 400
                    
                text = data['text']
                dictionary_name = data.get('dictionary_name', 'default')
                auto_create = data.get('auto_create', True)
                
                compressed, stats = self.service.compress_text(text, dictionary_name, auto_create)
                
                return jsonify({
                    'compressed_text': compressed,
                    'stats': {
                        'original_size': stats.original_size,
                        'compressed_size': stats.compressed_size,
                        'ratio': stats.ratio,
                        'dictionary_size': stats.dictionary_size,
                        'dictionary_name': stats.dictionary_name,
                        'timestamp': stats.timestamp.isoformat()
                    }
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/decompress', methods=['POST'])
        def decompress():
            """Decompress text"""
            try:
                data = request.get_json()
                if not data or 'compressed_text' not in data:
                    return jsonify({'error': 'Missing compressed_text parameter'}), 400
                    
                compressed = data['compressed_text']
                dictionary_name = data.get('dictionary_name', 'default')
                
                decompressed, stats = self.service.decompress_text(compressed, dictionary_name)
                
                return jsonify({
                    'decompressed_text': decompressed,
                    'stats': {
                        'original_size': stats.original_size,
                        'compressed_size': stats.compressed_size,
                        'ratio': stats.ratio,
                        'dictionary_size': stats.dictionary_size,
                        'dictionary_name': stats.dictionary_name,
                        'timestamp': stats.timestamp.isoformat()
                    }
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/stats', methods=['GET'])
        def get_stats():
            """Get compression statistics"""
            try:
                limit = request.args.get('limit', 50, type=int)
                stats = self.service.get_stats(limit)
                return jsonify({'stats': stats})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/stats', methods=['DELETE'])
        def clear_stats():
            """Clear compression statistics"""
            try:
                self.service.clear_stats()
                return jsonify({'message': 'Statistics cleared'})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
    
    @staticmethod
    def find_free_port(start_port: int = 5001) -> int:
        """Find the first available port"""
        port = start_port
        while port <= 65535:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.bind(("localhost", port))
                    return port
            except OSError:
                port += 1
        raise RuntimeError(f"No free ports found starting from {start_port}")
    
    def run(self, host: str = "localhost", port: int = 5001, debug: bool = False) -> None:
        """Run the compression API server"""
        print(f"Starting Generic Compression API on http://{host}:{port}")
        print(f"Health check: http://{host}:{port}/health")
        print(f"API documentation: http://{host}:{port}/summary")
        
        self.app.run(host=host, port=port, debug=debug, use_reloader=False, threaded=True)
    
    def run_in_thread(self, host: str = "localhost", start_port: int = 5001) -> Tuple[threading.Thread, int]:
        """Run the compression API in a separate daemon thread"""
        port = self.find_free_port(start_port)
        thread = threading.Thread(
            target=lambda: self.run(host=host, port=port, debug=False),
            daemon=True,
            name=f"CompressionAPI-{port}"
        )
        thread.start()
        return thread, port


class MemoryService:
    """Enhanced memory management with tags and semantic operations"""
    
    def __init__(self):
        self.memories: Dict[str, Dict[str, Any]] = {}
        self.tags_index: Dict[str, List[str]] = {}  # tag -> list of memory_ids
        self.memory_lock = threading.Lock()
        
    def store_memory(self, content: str, tags: List[str] = None, memory_id: str = None) -> str:
        """Store memory with optional tags"""
        with self.memory_lock:
            if memory_id is None:
                memory_id = hashlib.md5(content.encode()).hexdigest()[:16]
            
            tags = tags or []
            
            # Compress the content
            compressed, _ = compression_service.compress_text(content, "memory_dict", auto_create=True)
            
            memory = {
                'id': memory_id,
                'content': content,
                'compressed_content': compressed,
                'tags': tags,
                'created_at': datetime.now().isoformat(),
                'size': len(content),
                'compressed_size': len(compressed)
            }
            
            self.memories[memory_id] = memory
            
            # Update tags index
            for tag in tags:
                if tag not in self.tags_index:
                    self.tags_index[tag] = []
                if memory_id not in self.tags_index[tag]:
                    self.tags_index[tag].append(memory_id)
                    
            return memory_id
    
    def retrieve_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve memory by ID"""
        with self.memory_lock:
            return self.memories.get(memory_id)
    
    def search_by_tag(self, tags: List[str], logic: str = "OR") -> List[Dict[str, Any]]:
        """Search memories by tags with OR/AND logic"""
        with self.memory_lock:
            if logic.upper() == "OR":
                memory_ids = set()
                for tag in tags:
                    memory_ids.update(self.tags_index.get(tag, []))
            else:  # AND logic
                memory_ids = set(self.tags_index.get(tags[0], []))
                for tag in tags[1:]:
                    memory_ids.intersection_update(self.tags_index.get(tag, []))
            
            return [self.memories[mid] for mid in memory_ids if mid in self.memories]
    
    def delete_memory(self, memory_id: str) -> bool:
        """Delete memory by ID"""
        with self.memory_lock:
            if memory_id not in self.memories:
                return False
                
            memory = self.memories[memory_id]
            
            # Remove from tags index
            for tag in memory['tags']:
                if tag in self.tags_index:
                    self.tags_index[tag] = [mid for mid in self.tags_index[tag] if mid != memory_id]
                    if not self.tags_index[tag]:
                        del self.tags_index[tag]
            
            del self.memories[memory_id]
            return True
    
    def delete_by_tag(self, tags: List[str], logic: str = "OR") -> int:
        """Delete memories by tags"""
        memories_to_delete = self.search_by_tag(tags, logic)
        count = 0
        for memory in memories_to_delete:
            if self.delete_memory(memory['id']):
                count += 1
        return count
    
    def cleanup_duplicates(self) -> int:
        """Remove duplicate memories based on content hash"""
        with self.memory_lock:
            content_hashes = {}
            duplicates = []
            
            for memory_id, memory in self.memories.items():
                content_hash = hashlib.md5(memory['content'].encode()).hexdigest()
                if content_hash in content_hashes:
                    duplicates.append(memory_id)
                else:
                    content_hashes[content_hash] = memory_id
            
            count = 0
            for memory_id in duplicates:
                if self.delete_memory(memory_id):
                    count += 1
                    
            return count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        with self.memory_lock:
            total_size = sum(m['size'] for m in self.memories.values())
            total_compressed_size = sum(m['compressed_size'] for m in self.memories.values())
            
            return {
                'total_memories': len(self.memories),
                'total_tags': len(self.tags_index),
                'total_size': total_size,
                'total_compressed_size': total_compressed_size,
                'compression_ratio': total_size / total_compressed_size if total_compressed_size > 0 else 1.0,
                'unique_tags': list(self.tags_index.keys()),
                'average_memory_size': total_size / len(self.memories) if self.memories else 0
            }


# Global instances
memory_service = MemoryService()


def setup_memory_routes(app: Flask):
    """Setup memory management routes"""
    
    @app.route('/memory', methods=['POST'])
    def store_memory():
        """Store new memory with optional tags"""
        try:
            data = request.get_json()
            if not data or 'content' not in data:
                return jsonify({'error': 'Missing content parameter'}), 400
            
            content = data['content']
            tags = data.get('tags', [])
            memory_id = data.get('memory_id')
            
            stored_id = memory_service.store_memory(content, tags, memory_id)
            return jsonify({'memory_id': stored_id, 'message': 'Memory stored successfully'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/memory/<memory_id>', methods=['GET'])
    def get_memory(memory_id):
        """Retrieve memory by ID"""
        try:
            memory = memory_service.retrieve_memory(memory_id)
            if not memory:
                return jsonify({'error': 'Memory not found'}), 404
            return jsonify({'memory': memory})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/memory/<memory_id>', methods=['DELETE'])
    def delete_memory(memory_id):
        """Delete memory by ID"""
        try:
            if memory_service.delete_memory(memory_id):
                return jsonify({'message': 'Memory deleted successfully'})
            return jsonify({'error': 'Memory not found'}), 404
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/memory/search', methods=['POST'])
    def search_memories():
        """Search memories by tags"""
        try:
            data = request.get_json()
            if not data or 'tags' not in data:
                return jsonify({'error': 'Missing tags parameter'}), 400
            
            tags = data['tags']
            logic = data.get('logic', 'OR')
            
            memories = memory_service.search_by_tag(tags, logic)
            return jsonify({'memories': memories, 'count': len(memories)})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/memory/delete_by_tag', methods=['POST'])
    def delete_by_tag():
        """Delete memories by tags"""
        try:
            data = request.get_json()
            if not data or 'tags' not in data:
                return jsonify({'error': 'Missing tags parameter'}), 400
            
            tags = data['tags']
            logic = data.get('logic', 'OR')
            
            count = memory_service.delete_by_tag(tags, logic)
            return jsonify({'deleted_count': count, 'message': f'Deleted {count} memories'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/memory/cleanup', methods=['POST'])
    def cleanup_duplicates():
        """Clean up duplicate memories"""
        try:
            count = memory_service.cleanup_duplicates()
            return jsonify({'deleted_count': count, 'message': f'Removed {count} duplicates'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/memory/stats', methods=['GET'])
    def get_memory_stats():
        """Get memory statistics"""
        try:
            stats = memory_service.get_stats()
            return jsonify({'stats': stats})
        except Exception as e:
            return jsonify({'error': str(e)}), 500


class CompressionAPI:
    """REST API for generic text compression with memory management"""
    
    def __init__(self, service: CompressionService):
        self.service = service
        self.app = Flask(__name__)
        self.app.config['JSON_SORT_KEYS'] = False
        self._setup_routes()
        setup_memory_routes(self.app)
        
    def _setup_routes(self) -> None:
        """Setup Flask routes"""
        
        @self.app.route('/health', methods=['GET'])
        def health():
            """Health check endpoint"""
            return jsonify({
                'status': 'healthy',
                'service': 'generic-compression-api-v2',
                'timestamp': datetime.now().isoformat(),
                'features': ['compression', 'memory_management', 'tag_search']
            })
        
        @self.app.route('/summary', methods=['GET'])
        def get_summary():
            """Get service summary"""
            try:
                compression_summary = self.service.get_summary()
                memory_stats = memory_service.get_stats()
                
                return jsonify({
                    'compression': compression_summary,
                    'memory': memory_stats,
                    'endpoints': {
                        'compression': ['/compress', '/decompress', '/dictionaries'],
                        'memory': ['/memory', '/memory/search', '/memory/delete_by_tag', '/memory/cleanup']
                    }
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/dictionaries', methods=['GET'])
        def list_dictionaries():
            """List all dictionaries"""
            try:
                return jsonify({'dictionaries': self.service.list_dictionaries()})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/dictionaries', methods=['POST'])
        def create_dictionary():
            """Create a new dictionary"""
            try:
                data = request.get_json()
                if not data or 'name' not in data or 'text' not in data:
                    return jsonify({'error': 'Missing name or text parameter'}), 400
                    
                name = data['name']
                text = data['text']
                max_words = data.get('max_words', 300)
                min_word_length = data.get('min_word_length', 3)
                
                info = self.service.create_dictionary(name, text, max_words, min_word_length)
                return jsonify({'message': 'Dictionary created', 'dictionary': info})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/dictionaries/<name>', methods=['GET'])
        def get_dictionary(name):
            """Get dictionary information"""
            try:
                info = self.service.get_dictionary_info(name)
                return jsonify({'dictionary': info})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/dictionaries/<name>', methods=['DELETE'])
        def delete_dictionary(name):
            """Delete a dictionary"""
            try:
                self.service.delete_dictionary(name)
                return jsonify({'message': f'Dictionary {name} deleted'})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/compress', methods=['POST'])
        def compress():
            """Compress text"""
            try:
                data = request.get_json()
                if not data or 'text' not in data:
                    return jsonify({'error': 'Missing text parameter'}), 400
                    
                text = data['text']
                dictionary_name = data.get('dictionary_name', 'default')
                auto_create = data.get('auto_create', True)
                store_as_memory = data.get('store_as_memory', False)
                memory_tags = data.get('memory_tags', [])
                
                compressed, stats = self.service.compress_text(text, dictionary_name, auto_create)
                
                result = {
                    'compressed_text': compressed,
                    'stats': {
                        'original_size': stats.original_size,
                        'compressed_size': stats.compressed_size,
                        'ratio': stats.ratio,
                        'dictionary_size': stats.dictionary_size,
                        'dictionary_name': stats.dictionary_name,
                        'timestamp': stats.timestamp.isoformat()
                    }
                }
                
                # Store as memory if requested
                if store_as_memory:
                    memory_id = memory_service.store_memory(compressed, memory_tags + ['compressed'])
                    result['memory_id'] = memory_id
                
                return jsonify(result)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/decompress', methods=['POST'])
        def decompress():
            """Decompress text"""
            try:
                data = request.get_json()
                if not data or 'compressed_text' not in data:
                    return jsonify({'error': 'Missing compressed_text parameter'}), 400
                    
                compressed = data['compressed_text']
                dictionary_name = data.get('dictionary_name', 'default')
                store_as_memory = data.get('store_as_memory', False)
                memory_tags = data.get('memory_tags', [])
                
                decompressed, stats = self.service.decompress_text(compressed, dictionary_name)
                
                result = {
                    'decompressed_text': decompressed,
                    'stats': {
                        'original_size': stats.original_size,
                        'compressed_size': stats.compressed_size,
                        'ratio': stats.ratio,
                        'dictionary_size': stats.dictionary_size,
                        'dictionary_name': stats.dictionary_name,
                        'timestamp': stats.timestamp.isoformat()
                    }
                }
                
                # Store as memory if requested
                if store_as_memory:
                    memory_id = memory_service.store_memory(decompressed, memory_tags + ['decompressed'])
                    result['memory_id'] = memory_id
                
                return jsonify(result)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/stats', methods=['GET'])
        def get_stats():
            """Get compression statistics"""
            try:
                limit = request.args.get('limit', 50, type=int)
                stats = self.service.get_stats(limit)
                return jsonify({'stats': stats})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/stats', methods=['DELETE'])
        def clear_stats():
            """Clear compression statistics"""
            try:
                self.service.clear_stats()
                return jsonify({'message': 'Statistics cleared'})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
    
    @staticmethod
    def find_free_port(start_port: int = 5001) -> int:
        """Find the first available port"""
        port = start_port
        while port <= 65535:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.bind(("localhost", port))
                    return port
            except OSError:
                port += 1
        raise RuntimeError(f"No free ports found starting from {start_port}")
    
    def run(self, host: str = "localhost", port: int = 5001, debug: bool = False) -> None:
        """Run the compression API server"""
        print(f"🚀 Starting Generic Compression API v2 on http://{host}:{port}")
        print(f"📋 Health check: http://{host}:{port}/health")
        print(f"📊 Summary: http://{host}:{port}/summary")
        print(f"🗜️  Compression: POST http://{host}:{port}/compress")
        print(f"🧠 Memory: POST http://{host}:{port}/memory")
        print(f"🔍 Search: POST http://{host}:{port}/memory/search")
        
        self.app.run(host=host, port=port, debug=debug, use_reloader=False, threaded=True)
    
    def run_in_thread(self, host: str = "localhost", start_port: int = 5001) -> Tuple[threading.Thread, int]:
        """Run the compression API in a separate daemon thread"""
        port = self.find_free_port(start_port)
        thread = threading.Thread(
            target=lambda: self.run(host=host, port=port, debug=False),
            daemon=True,
            name=f"CompressionAPI-{port}"
        )
        thread.start()
        return thread, port


def main():
    """Main entry point for standalone execution"""
    api = CompressionAPI(compression_service)
    
    # Add some test data
    test_text = """
    This is a sample text for testing compression functionality.
    The compression system should identify frequently used words and create
    shorter codes for them. This text contains many repeated words like
    compression, system, words, and functionality to test the effectiveness
    of the compression algorithm.
    """
    
    compression_service.create_dictionary("test", test_text)
    
    # Add test memory
    memory_service.store_memory("Test memory content about compression", ["test", "compression"])
    memory_service.store_memory("Another memory about API development", ["test", "api", "development"])
    
    try:
        port = CompressionAPI.find_free_port(5001)
        print(f"🚀 Starting Generic Compression API v2 on port {port}")
        api.run(port=port)
    except KeyboardInterrupt:
        print("\n👋 Compression API stopped")


if __name__ == "__main__":
    main()
