"""
Context modeling system with efficient hash tables
Supports multiple context orders and data-specific contexts
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from collections import defaultdict, deque
import struct

class HashTable:
    """Cache-aligned hash table for fast context lookup"""

    def __init__(self, size: int = 1 << 20, cache_line: int = 64):
        self.size = size
        self.mask = size - 1
        self.cache_line = cache_line
        self.table = np.zeros((size, 2), dtype=np.uint32)
        self.counts = np.zeros(size, dtype=np.uint16)

    def hash_context(self, context: bytes) -> int:
        """Fast hash function optimized for context lookup"""
        h = 0x811c9dc5

        for byte in context:
            h ^= byte
            h = (h * 0x01000193) & 0xffffffff

        return h & self.mask

    def update(self, context: bytes, symbol: int, count: int = 1):
        """Update context with symbol occurrence"""
        idx = self.hash_context(context)
        self.table[idx, 0] = symbol
        self.table[idx, 1] = min(self.table[idx, 1] + count, 65535)
        self.counts[idx] = min(self.counts[idx] + 1, 65535)

    def get_prediction(self, context: bytes) -> Tuple[int, float]:
        """Get predicted symbol and confidence"""
        idx = self.hash_context(context)
        symbol = self.table[idx, 0]
        total = max(self.counts[idx], 1)
        confidence = self.table[idx, 1] / total if total > 0 else 0.0

        return int(symbol), confidence


class ContextModel:
    """Multi-order context modeling with specialized contexts"""

    def __init__(self, max_order: int = 4, table_size: int = 1 << 20):
        self.max_order = max_order
        self.contexts = {}

        for order in range(max_order + 1):
            self.contexts[f'order_{order}'] = HashTable(table_size >> order)

        self.word_context = HashTable(table_size >> 2)
        self.structure_context = HashTable(table_size >> 3)

        self.recent_bytes = deque(maxlen=max_order)
        self.recent_words = deque(maxlen=10)

        self.weights = np.ones(max_order + 3) / (max_order + 3)

    def update(self, byte: int, data_type: str = 'binary'):
        """Update all contexts with new byte"""
        for order in range(min(len(self.recent_bytes) + 1, self.max_order + 1)):
            context = bytes(list(self.recent_bytes)[-order:]) if order > 0 else b''
            self.contexts[f'order_{order}'].update(context, byte)

        if data_type in ['text', 'code']:
            self._update_word_context(byte)

        if data_type in ['json', 'xml', 'csv']:
            self._update_structure_context(byte)

        self.recent_bytes.append(byte)

    def predict(self, data_type: str = 'binary') -> np.ndarray:
        """Get probability distribution for next byte"""
        predictions = np.zeros(256)
        confidences = []

        for order in range(min(len(self.recent_bytes) + 1, self.max_order + 1)):
            context = bytes(list(self.recent_bytes)[-order:]) if order > 0 else b''
            symbol, confidence = self.contexts[f'order_{order}'].get_prediction(context)

            pred = np.zeros(256)
            pred[symbol] = confidence
            predictions += pred * self.weights[order]
            confidences.append(confidence)

        if data_type in ['text', 'code']:
            word_pred = self._get_word_prediction()
            predictions += word_pred * self.weights[self.max_order + 1]
            confidences.append(np.max(word_pred))

        if data_type in ['json', 'xml', 'csv']:
            struct_pred = self._get_structure_prediction()
            predictions += struct_pred * self.weights[self.max_order + 2]
            confidences.append(np.max(struct_pred))

        if np.sum(predictions) > 0:
            predictions /= np.sum(predictions)
        else:
            predictions = np.ones(256) / 256

        return predictions

    def _update_word_context(self, byte: int):
        """Update word-level context for text"""
        if byte in [32, 10, 13, 9]:
            if self.recent_bytes:
                word = bytes(self.recent_bytes)
                if len(word) > 1:
                    self.recent_words.append(word)
                    if len(self.recent_words) >= 2:
                        context = self.recent_words[-2] if len(self.recent_words) >= 2 else b''
                        self.word_context.update(context, byte)
                self.recent_bytes.clear()

    def _get_word_prediction(self) -> np.ndarray:
        """Get word-level prediction"""
        pred = np.zeros(256)

        if self.recent_words:
            context = self.recent_words[-1] if self.recent_words else b''
            symbol, confidence = self.word_context.get_prediction(context)
            pred[symbol] = confidence

        return pred

    def _update_structure_context(self, byte: int):
        """Update structure-aware context"""
        structure_chars = {ord('{'): 1, ord('}'): 2, ord('['): 3, ord(']'): 4,
                          ord('"'): 5, ord(','): 6, ord(':'): 7}

        if byte in structure_chars:
            if len(self.recent_bytes) >= 2:
                prev_struct = bytes([b for b in self.recent_bytes if b in structure_chars][-2:])
                self.structure_context.update(prev_struct, byte)

    def _get_structure_prediction(self) -> np.ndarray:
        """Get structure-aware prediction"""
        pred = np.zeros(256)
        structure_chars = {ord('{'): 1, ord('}'): 2, ord('['): 3, ord(']'): 4,
                          ord('"'): 5, ord(','): 6, ord(':'): 7}

        recent_struct = bytes([b for b in self.recent_bytes if b in structure_chars][-2:])
        if recent_struct:
            symbol, confidence = self.structure_context.get_prediction(recent_struct)
            pred[symbol] = confidence

        return pred

    def adapt_weights(self, prediction_error: float):
        """Adapt context weights based on prediction error"""
        learning_rate = 0.01
        self.weights *= (1 - learning_rate * prediction_error)
        self.weights = np.clip(self.weights, 0.001, 1.0)
        self.weights /= np.sum(self.weights)

    def reset_if_needed(self):
        """Reset context model if needed"""
        # Clear recent bytes if they get too large
        if len(self.recent_bytes) > self.max_order * 2:
            self.recent_bytes = deque(list(self.recent_bytes)[-self.max_order:], maxlen=self.max_order)

        # Reset weights periodically
        if np.min(self.weights) < 0.001:
            self.weights = np.ones(self.max_order + 3) / (self.max_order + 3)


class SpecializedContexts:
    """Specialized contexts for different data types"""

    def __init__(self):
        self.code_context = CodeContext()
        self.json_context = JSONContext()
        self.binary_context = BinaryContext()

    def get_context(self, data_type: str):
        """Get specialized context for data type"""
        if data_type == 'code':
            return self.code_context
        elif data_type in ['json', 'xml']:
            return self.json_context
        elif data_type == 'binary':
            return self.binary_context
        else:
            return None


class CodeContext:
    """Context model specialized for source code"""

    def __init__(self):
        self.keyword_table = HashTable(1 << 16)
        self.identifier_table = HashTable(1 << 18)
        self.operator_table = HashTable(1 << 14)
        self.current_token = bytearray()
        self.last_keyword = b''
        self.indent_level = 0

    def update(self, byte: int):
        """Update code-specific contexts"""
        if byte in [32, 10, 13, 9]:
            if self.current_token:
                token = bytes(self.current_token)
                if self._is_keyword(token):
                    self.keyword_table.update(self.last_keyword, byte)
                    self.last_keyword = token
                elif self._is_identifier(token):
                    self.identifier_table.update(token[:8], byte)

                self.current_token.clear()

            if byte == 9:
                self.indent_level += 1
            elif byte == 10:
                self.indent_level = 0
        elif byte in [ord(c) for c in '(){}[];,.<>=+-*/%&|!']:
            if self.current_token:
                self.operator_table.update(bytes([byte]), self.current_token[0] if self.current_token else 0)
            self.current_token.clear()
        else:
            self.current_token.append(byte)

    def get_prediction(self) -> np.ndarray:
        """Get code-specific prediction"""
        pred = np.zeros(256)

        if self.last_keyword:
            symbol, conf = self.keyword_table.get_prediction(self.last_keyword)
            pred[symbol] = conf * 0.3

        if self.current_token and len(self.current_token) >= 2:
            symbol, conf = self.identifier_table.get_prediction(bytes(self.current_token[-8:]))
            pred[symbol] += conf * 0.3

        return pred

    def _is_keyword(self, token: bytes) -> bool:
        """Check if token is a common keyword"""
        keywords = [b'if', b'else', b'for', b'while', b'def', b'class', b'return',
                   b'import', b'function', b'var', b'let', b'const', b'public', b'private']
        return token in keywords

    def _is_identifier(self, token: bytes) -> bool:
        """Check if token looks like an identifier"""
        if not token:
            return False
        first = token[0]
        return (first >= ord('a') and first <= ord('z')) or \
               (first >= ord('A') and first <= ord('Z')) or \
               first == ord('_')


class JSONContext:
    """Context model specialized for JSON/XML"""

    def __init__(self):
        self.key_table = HashTable(1 << 18)
        self.value_table = HashTable(1 << 18)
        self.depth_stack = []
        self.in_key = False
        self.in_value = False
        self.current_key = bytearray()
        self.last_key = b''

    def update(self, byte: int):
        """Update JSON-specific contexts"""
        if byte == ord('"'):
            if not self.in_key and not self.in_value:
                self.in_key = True
            elif self.in_key:
                self.in_key = False
                self.last_key = bytes(self.current_key)
                self.current_key.clear()
            elif self.in_value:
                self.in_value = False

        elif byte == ord(':'):
            self.in_value = True

        elif byte in [ord('{'), ord('[')]:
            self.depth_stack.append(byte)

        elif byte in [ord('}'), ord(']')]:
            if self.depth_stack:
                self.depth_stack.pop()

        if self.in_key:
            self.current_key.append(byte)
            if len(self.current_key) >= 2:
                self.key_table.update(bytes(self.current_key[-8:]), byte)

        if self.in_value and self.last_key:
            self.value_table.update(self.last_key[:8], byte)

    def get_prediction(self) -> np.ndarray:
        """Get JSON-specific prediction"""
        pred = np.zeros(256)

        if self.in_key and len(self.current_key) >= 2:
            symbol, conf = self.key_table.get_prediction(bytes(self.current_key[-8:]))
            pred[symbol] = conf * 0.4

        if self.in_value and self.last_key:
            symbol, conf = self.value_table.get_prediction(self.last_key[:8])
            pred[symbol] += conf * 0.3

        if self.depth_stack:
            if self.depth_stack[-1] == ord('{'):
                pred[ord('}')] += 0.1
                pred[ord('"')] += 0.1
                pred[ord(',')] += 0.1
            elif self.depth_stack[-1] == ord('['):
                pred[ord(']')] += 0.1
                pred[ord(',')] += 0.1

        return pred


class BinaryContext:
    """Context model specialized for binary data"""

    def __init__(self):
        self.byte_pair_table = HashTable(1 << 16)
        self.aligned_table = HashTable(1 << 14)
        self.position = 0
        self.last_bytes = deque(maxlen=4)

    def update(self, byte: int):
        """Update binary-specific contexts"""
        if len(self.last_bytes) >= 2:
            pair = bytes(list(self.last_bytes)[-2:])
            self.byte_pair_table.update(pair, byte)

        if self.position % 4 == 0:
            if len(self.last_bytes) == 4:
                aligned = bytes(self.last_bytes)
                self.aligned_table.update(aligned, byte)

        self.last_bytes.append(byte)
        self.position += 1

    def get_prediction(self) -> np.ndarray:
        """Get binary-specific prediction"""
        pred = np.zeros(256)

        if len(self.last_bytes) >= 2:
            pair = bytes(list(self.last_bytes)[-2:])
            symbol, conf = self.byte_pair_table.get_prediction(pair)
            pred[symbol] = conf * 0.5

        if self.position % 4 == 0 and len(self.last_bytes) == 4:
            aligned = bytes(self.last_bytes)
            symbol, conf = self.aligned_table.get_prediction(aligned)
            pred[symbol] += conf * 0.3

        return pred