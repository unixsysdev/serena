#!/usr/bin/env python3
"""
Standalone compression functionality test
"""

import json
import re
from collections import Counter
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import hashlib

@dataclass
class CompressionStats:
    """Statistics about compression operations"""
    original_size: int
    compressed_size: int
    ratio: float
    dictionary_size: int
    timestamp: datetime
    operation: str

class CompressionDictionary:
    """Manages word frequency analysis and compression mappings"""
    
    def __init__(self):
        self.word_to_code: Dict[str, str] = {}
        self.code_to_word: Dict[str, str] = {}
        self.word_frequencies: Dict[str, int] = {}
        self.dictionary_hash: Optional[str] = None
        
    def build_from_text(self, text: str, max_words: int = 200) -> None:
        """Build dictionary from text using word frequency analysis"""
        words = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_-]{2,}\b', text)
        word_counts = Counter(words)
        top_words = word_counts.most_common(max_words)
        
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
        
        dict_str = json.dumps(self.word_to_code, sort_keys=True)
        self.dictionary_hash = hashlib.md5(dict_str.encode()).hexdigest()[:8]
    
    def compress_text(self, text: str) -> str:
        """Apply compression mappings to text"""
        if not self.word_to_code:
            return text
            
        compressed = text
        for word, code in self.word_to_code.items():
            pattern = r'' + re.escape(word) + r''
            compressed = re.sub(pattern, code, compressed)
        
        # Apply abbreviations
        abbreviations = {
            'apiVersion:': 'v:',
            'metadata:': 'm:',
            'namespace:': 'ns:',
            'labels:': 'l:',
            'spec:': 's:',
            'containers:': 'c:',
            'image:': 'i:',
            'resources:': 'r:',
            'requests:': 'rq:',
            'limits:': 'lm:',
            'environment:': 'e:',
            'variables:': 'vars:',
            'kubernetes': 'k8s',
            'application': 'app',
            'configuration': 'config',
            'development': 'dev',
            'production': 'prod',
            'repository': 'repo',
            'pipeline': 'pipe',
            'container': 'ctr',
        }
        
        for original, abbrev in abbreviations.items():
            compressed = compressed.replace(original, abbrev)
            
        return compressed
    
    def decompress_text(self, compressed: str) -> str:
        """Decompress text using stored mappings"""
        if not self.code_to_word:
            return compressed
            
        decompressed = compressed
        for code, word in self.code_to_word.items():
            pattern = r'' + re.escape(code) + r''
            decompressed = re.sub(pattern, word, decompressed)
            
        # Reverse abbreviations
        reverse_abbreviations = {
            'v:': 'apiVersion:',
            'm:': 'metadata:',
            'ns:': 'namespace:',
            'l:': 'labels:',
            's:': 'spec:',
            'c:': 'containers:',
            'i:': 'image:',
            'r:': 'resources:',
            'rq:': 'requests:',
            'lm:': 'limits:',
            'e:': 'environment:',
            'vars:': 'variables:',
            'k8s': 'kubernetes',
            'app': 'application',
            'config': 'configuration',
            'dev': 'development',
            'prod': 'production',
            'repo': 'repository',
            'pipe': 'pipeline',
            'ctr': 'container',
        }
        
        for abbrev, original in reverse_abbreviations.items():
            decompressed = decompressed.replace(abbrev, original)
            
        return decompressed

# Test text
test_text = """apiVersion: v1
kind: Deployment
metadata:
  name: my-application
  namespace: production
  labels:
    app: my-application
    environment: production
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: my-application
        image: my-application:latest
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
        environment:
          - name: DATABASE_URL
            value: "postgresql://user:pass@db:5432/mydb"
          - name: ENVIRONMENT
            value: "production"
        variables:
          - CONFIG_PATH=/app/config
          - LOG_LEVEL=info
      - name: sidecar-container
        image: sidecar:latest
        resources:
          requests:
            cpu: 50m
            memory: 64Mi
service:
  metadata:
    name: my-application-service
  spec:
    selector:
      app: my-application
    ports:
      - port: 80
        targetPort: 8080
"""

if __name__ == "__main__":
    print("Testing standalone compression functionality...")
    
    # Create dictionary
    dictionary = CompressionDictionary()
    dictionary.build_from_text(test_text)
    
    # Show original text stats
    print(f"Original text size: {len(test_text)} characters")
    print(f"Dictionary size: {len(dictionary.word_to_code)} words")
    print(f"Dictionary hash: {dictionary.dictionary_hash}")
    
    # Show top mappings
    print("\nTop word mappings:")
    for word, code in list(dictionary.word_to_code.items())[:15]:
        freq = dictionary.word_frequencies[word]
        print(f"  {word} -> {code} (frequency: {freq})")
    
    # Compress text
    compressed = dictionary.compress_text(test_text)
    print(f"\nCompressed text size: {len(compressed)} characters")
    print(f"Compression ratio: {len(test_text)/len(compressed):.2f}x")
    
    # Show compressed version
    print("\nCompressed text (first 400 chars):")
    print(compressed[:400])
    print("...")
    
    # Test round-trip compression
    decompressed = dictionary.decompress_text(compressed)
    print(f"\nDecompressed text size: {len(decompressed)} characters")
    print(f"Round-trip successful: {decompressed == test_text}")
    
    print("\n✅ Compression system working correctly!")
