"""
Data type detection and analysis module
Intelligently identifies data types for optimal compression strategy
"""

import re
import json
import numpy as np
from collections import Counter
from typing import Tuple, Dict, Optional
from enum import Enum

class DataType(Enum):
    TEXT = 'text'
    CODE = 'code'
    JSON_DATA = 'json'
    XML_DATA = 'xml'
    CSV_DATA = 'csv'
    BINARY = 'binary'
    MIXED = 'mixed'

class DataDetector:
    """Fast data type detection with pattern recognition"""

    def __init__(self):
        self.text_chars = set(range(32, 127)) | {9, 10, 13}
        self.code_keywords = {
            'python': ['def', 'class', 'import', 'from', 'return', 'if', 'else', 'elif'],
            'javascript': ['function', 'var', 'let', 'const', 'return', 'if', 'else'],
            'c': ['#include', 'int', 'void', 'return', 'if', 'else', 'struct'],
            'java': ['public', 'class', 'void', 'return', 'import', 'package'],
        }
        self.xml_pattern = re.compile(r'<[^>]+>')
        self.json_pattern = re.compile(r'[{}\[\]":,]')

    def detect(self, data: bytes, sample_size: int = 8192) -> Tuple[DataType, Dict]:
        """
        Detect data type and return type-specific metadata

        Args:
            data: Input bytes to analyze
            sample_size: Size of sample to analyze for large files

        Returns:
            (DataType, metadata dict)
        """
        if not data:
            return DataType.BINARY, {}

        sample = data[:min(len(data), sample_size)]

        byte_counts = Counter(sample)
        total_bytes = len(sample)

        text_ratio = sum(1 for b in sample if b in self.text_chars) / total_bytes

        # Check for null bytes - strong binary indicator
        null_ratio = sample.count(0) / total_bytes

        if null_ratio > 0.1:
            return DataType.BINARY, self._analyze_binary(sample)
        elif text_ratio > 0.95:
            return self._classify_text_data(sample, data)
        elif text_ratio > 0.85:
            return self._classify_structured_data(sample, data)
        elif text_ratio < 0.5:
            return DataType.BINARY, self._analyze_binary(sample)
        else:
            return DataType.MIXED, {'text_ratio': text_ratio}

    def _classify_text_data(self, sample: bytes, full_data: bytes) -> Tuple[DataType, Dict]:
        """Classify text-like data"""
        try:
            text_sample = sample.decode('utf-8', errors='ignore')
        except (UnicodeDecodeError, AttributeError):
            return DataType.BINARY, {}

        if self._is_code(text_sample):
            lang = self._detect_language(text_sample)
            return DataType.CODE, {'language': lang}

        if self._is_json(text_sample):
            return DataType.JSON_DATA, self._analyze_json(full_data)

        if self._is_xml(text_sample):
            return DataType.XML_DATA, self._analyze_xml(text_sample)

        if self._is_csv(text_sample):
            return DataType.CSV_DATA, self._analyze_csv(text_sample)

        return DataType.TEXT, self._analyze_text(text_sample)

    def _classify_structured_data(self, sample: bytes, full_data: bytes) -> Tuple[DataType, Dict]:
        """Classify potentially structured data"""
        try:
            text_sample = sample.decode('utf-8', errors='ignore')

            if self._is_json(text_sample):
                return DataType.JSON_DATA, self._analyze_json(full_data)
            elif self._is_xml(text_sample):
                return DataType.XML_DATA, self._analyze_xml(text_sample)
            else:
                return DataType.MIXED, {}
        except (KeyError, ValueError, TypeError):
            return DataType.MIXED, {}

    def _is_code(self, text: str) -> bool:
        """Check if text appears to be source code"""
        indicators = [
            text.count('{') > 2,
            text.count(';') > 2,
            text.count('(') > 3,
            bool(re.search(r'\b(def|class|function|public|private|void|import|return)\b', text)),
            bool(re.search(r'[=<>!]+', text)),
            text.count('\n') > 2 and '    ' in text or '\t' in text,  # indentation
        ]
        return sum(indicators) >= 2

    def _detect_language(self, text: str) -> Optional[str]:
        """Detect programming language"""
        words = text.lower().split()
        word_set = set(words)

        best_match = None
        best_score = 0

        for lang, keywords in self.code_keywords.items():
            score = sum(1 for kw in keywords if kw in word_set)
            if score > best_score:
                best_score = score
                best_match = lang

        return best_match

    def _is_json(self, text: str) -> bool:
        """Check if text is JSON"""
        if not (text.strip().startswith('{') or text.strip().startswith('[')):
            return False
        try:
            json.loads(text)
            return True
        except (json.JSONDecodeError, ValueError):
            return len(self.json_pattern.findall(text)) > len(text) / 50

    def _is_xml(self, text: str) -> bool:
        """Check if text is XML/HTML"""
        tags = self.xml_pattern.findall(text)
        return len(tags) > 3 and text.strip().startswith('<')

    def _is_csv(self, text: str) -> bool:
        """Check if text is CSV"""
        lines = text.split('\n')[:10]
        if len(lines) < 2:
            return False

        delimiters = [',', '\t', '|', ';']
        for delim in delimiters:
            counts = [line.count(delim) for line in lines if line.strip()]
            if counts and min(counts) > 0 and max(counts) == min(counts):
                return True
        return False

    def _analyze_json(self, data: bytes) -> Dict:
        """Analyze JSON structure"""
        try:
            text = data.decode('utf-8', errors='ignore')
            obj = json.loads(text)

            def analyze_structure(obj, depth=0):
                if isinstance(obj, dict):
                    return {'type': 'object', 'keys': len(obj), 'depth': depth}
                elif isinstance(obj, list):
                    return {'type': 'array', 'length': len(obj), 'depth': depth}
                else:
                    return {'type': 'value', 'depth': depth}

            return {
                'structure': analyze_structure(obj),
                'size': len(text),
                'minified': '\n' not in text
            }
        except (json.JSONDecodeError, ValueError, TypeError):
            return {}

    def _analyze_xml(self, text: str) -> Dict:
        """Analyze XML structure"""
        tags = self.xml_pattern.findall(text)
        tag_names = [tag.strip('<>/').split()[0] for tag in tags]
        tag_counts = Counter(tag_names)

        return {
            'unique_tags': len(tag_counts),
            'total_tags': len(tags),
            'most_common': tag_counts.most_common(5)
        }

    def _analyze_csv(self, text: str) -> Dict:
        """Analyze CSV structure"""
        lines = text.split('\n')

        for delim in [',', '\t', '|', ';']:
            counts = [line.count(delim) for line in lines[:10] if line.strip()]
            if counts and min(counts) == max(counts):
                return {
                    'delimiter': delim,
                    'columns': min(counts) + 1,
                    'rows': len([l for l in lines if l.strip()])
                }

        return {}

    def _analyze_text(self, text: str) -> Dict:
        """Analyze plain text"""
        words = text.split()
        chars = Counter(text)

        return {
            'words': len(words),
            'unique_words': len(set(words)),
            'avg_word_length': sum(len(w) for w in words) / max(len(words), 1),
            'entropy': self._calculate_entropy(chars)
        }

    def _analyze_binary(self, sample: bytes) -> Dict:
        """Analyze binary data"""
        byte_counts = Counter(sample)

        return {
            'entropy': self._calculate_entropy(byte_counts),
            'unique_bytes': len(byte_counts),
            'most_common': byte_counts.most_common(10),
            'zero_ratio': byte_counts.get(0, 0) / len(sample)
        }

    def _calculate_entropy(self, counts: Counter) -> float:
        """Calculate Shannon entropy"""
        total = sum(counts.values())
        if total == 0:
            return 0.0

        entropy = 0.0
        for count in counts.values():
            if count > 0:
                p = count / total
                entropy -= p * np.log2(p)

        return entropy