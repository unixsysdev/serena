#!/usr/bin/env python3
"""
Test script for compression functionality
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from serena.tools.compression_tools import CompressTextTool

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
"""

if __name__ == "__main__":
    print("Testing compression tool...")
    
    # Create a mock tool instance for testing
    class MockTool:
        def _limit_length(self, text, max_len):
            return text[:max_len] if len(text) > max_len else text
    
    # Test the compression
    tool = CompressTextTool()
    tool._limit_length = MockTool()._limit_length
    
    try:
        result = tool.apply(test_text)
        print("SUCCESS: Compression tool works!")
        print(f"Result length: {len(result)}")
        print("First 500 chars:")
        print(result[:500])
        print("...")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
