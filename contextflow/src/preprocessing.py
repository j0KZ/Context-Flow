"""
Preprocessing module with BWT and deduplication
Optimized for different data types
"""

import numpy as np
from typing import Tuple, List, Optional, Dict
import hashlib
from collections import deque

class BurrowsWheelerTransform:
    """Optimized BWT implementation with block processing"""

    def __init__(self, block_size: int = 10000):  # Reduced for performance
        self.block_size = block_size

    def transform(self, data: bytes) -> Tuple[bytes, List[int]]:
        """
        Apply BWT to input data

        Returns:
            (transformed_data, original_indices)
        """
        if len(data) <= self.block_size:
            return self._bwt_block(data)

        transformed = []
        indices = []

        for i in range(0, len(data), self.block_size):
            block = data[i:i + self.block_size]
            t_data, idx = self._bwt_block(block)
            transformed.append(t_data)
            indices.append(idx)

        return b''.join(transformed), indices

    def _bwt_block(self, data: bytes) -> Tuple[bytes, int]:
        """Apply BWT to a single block"""
        if not data:
            return b'', 0

        n = len(data)

        # Create all rotations
        rotations = []
        data_doubled = data + data

        for i in range(n):
            rotations.append(data_doubled[i:i+n])

        # Sort rotations and keep track of original position
        sorted_rotations = sorted(enumerate(rotations), key=lambda x: x[1])

        # Find where the original string ended up
        original_index = 0
        for i, (orig_idx, _) in enumerate(sorted_rotations):
            if orig_idx == 0:
                original_index = i
                break

        # Extract last column
        transformed = bytearray()
        for _, rotation in sorted_rotations:
            transformed.append(rotation[-1])

        return bytes(transformed), original_index

    def inverse_transform(self, data: bytes, indices: List[int]) -> bytes:
        """Inverse BWT transformation"""
        if isinstance(indices, int):
            indices = [indices]

        if len(indices) == 1:
            return self._inverse_bwt_block(data, indices[0])

        result = []
        block_size = len(data) // len(indices)

        for i, idx in enumerate(indices):
            start = i * block_size
            end = start + block_size if i < len(indices) - 1 else len(data)
            block = data[start:end]
            result.append(self._inverse_bwt_block(block, idx))

        return b''.join(result)

    def _inverse_bwt_block(self, data: bytes, original_index: int) -> bytes:
        """Inverse BWT for a single block"""
        if not data:
            return b''

        n = len(data)

        # Count occurrences of each byte
        counts = [0] * 256
        for byte in data:
            counts[byte] += 1

        # Calculate cumulative counts (starting positions)
        cumulative = [0] * 256
        total = 0
        for i in range(256):
            cumulative[i] = total
            total += counts[i]

        # Build transformation vector
        transform = [0] * n
        for i, byte in enumerate(data):
            transform[cumulative[byte]] = i
            cumulative[byte] += 1

        # Reconstruct original string
        result = bytearray()
        idx = original_index

        for _ in range(n):
            idx = transform[idx]
            result.append(data[idx])

        return bytes(result)


class SlidingWindowDeduplicator:
    """Fast sliding window deduplication with hash-based detection"""

    def __init__(self, window_size: int = 1024, min_match: int = 32):
        self.window_size = window_size
        self.min_match = min_match
        self.hash_table = {}

    def deduplicate(self, data: bytes) -> Tuple[bytes, List[Tuple[int, int, int]]]:
        """
        Find and encode duplicate sequences

        Returns:
            (deduplicated_data, references)
            references: List of (position, offset, length)
        """
        result = bytearray()
        references = []
        i = 0

        window = deque(maxlen=self.window_size)

        while i < len(data):
            match = self._find_longest_match(data, i, window)

            if match and match[1] >= self.min_match:
                offset, length = match
                references.append((len(result), offset, length))
                result.extend(b'\x00' * 3)
                i += length

                for j in range(length):
                    if i - length + j >= 0:
                        window.append(data[i - length + j])
            else:
                result.append(data[i])
                window.append(data[i])
                i += 1

        return bytes(result), references

    def _find_longest_match(self, data: bytes, pos: int, window: deque) -> Optional[Tuple[int, int]]:
        """Find longest matching sequence in window"""
        if pos + self.min_match > len(data):
            return None

        window_bytes = bytes(window)
        if len(window_bytes) < self.min_match:
            return None

        best_offset = 0
        best_length = 0

        target = data[pos:pos + self.min_match]

        for i in range(len(window_bytes) - self.min_match + 1):
            if window_bytes[i:i + self.min_match] == target:
                length = self.min_match
                while (i + length < len(window_bytes) and
                       pos + length < len(data) and
                       window_bytes[i + length] == data[pos + length]):
                    length += 1

                if length > best_length:
                    best_length = length
                    best_offset = len(window_bytes) - i

        if best_length >= self.min_match:
            return (best_offset, best_length)
        return None

    def restore(self, deduplicated: bytes, references: List[Tuple[int, int, int]]) -> bytes:
        """Restore original data from deduplicated form"""
        if not references:
            return deduplicated

        result = bytearray()
        dedup_idx = 0
        ref_idx = 0

        # Sort references by position
        sorted_refs = sorted(references, key=lambda x: x[0])

        while dedup_idx < len(deduplicated):
            if ref_idx < len(sorted_refs) and dedup_idx == sorted_refs[ref_idx][0]:
                # This is a reference position
                pos, offset, length = sorted_refs[ref_idx]

                # Copy from earlier in the result
                source_start = len(result) - offset
                if source_start >= 0:
                    for i in range(length):
                        if source_start + i < len(result):
                            result.append(result[source_start + i])
                        else:
                            # Self-referencing pattern
                            result.append(result[source_start + (i % offset)])

                # Skip the 3-byte marker in deduplicated data
                dedup_idx += 3
                ref_idx += 1
            else:
                # Regular byte
                result.append(deduplicated[dedup_idx])
                dedup_idx += 1

        return bytes(result)


class StructureDetector:
    """Detect and mark structure boundaries for better compression"""

    def __init__(self):
        self.markers = {
            'json_open': b'\x01',
            'json_close': b'\x02',
            'xml_open': b'\x03',
            'xml_close': b'\x04',
            'csv_delim': b'\x05',
            'code_block': b'\x06'
        }

    def mark_boundaries(self, data: bytes, data_type: str) -> Tuple[bytes, Dict]:
        """Mark structure boundaries in data"""
        if data_type == 'json':
            return self._mark_json_boundaries(data)
        elif data_type == 'xml':
            return self._mark_xml_boundaries(data)
        elif data_type == 'csv':
            return self._mark_csv_boundaries(data)
        elif data_type == 'code':
            return self._mark_code_boundaries(data)
        else:
            return data, {}

    def _mark_json_boundaries(self, data: bytes) -> Tuple[bytes, Dict]:
        """Mark JSON structure boundaries"""
        result = bytearray()
        depth = 0
        in_string = False
        escape_next = False
        boundaries = []

        for i, byte in enumerate(data):
            result.append(byte)

            if not escape_next:
                if byte == ord('"') and not in_string:
                    in_string = True
                elif byte == ord('"') and in_string:
                    in_string = False
                elif not in_string:
                    if byte in (ord('{'), ord('[')):
                        depth += 1
                        boundaries.append((i, 'open', depth))
                    elif byte in (ord('}'), ord(']')):
                        depth -= 1
                        boundaries.append((i, 'close', depth))

                if byte == ord('\\'):
                    escape_next = True
            else:
                escape_next = False

        return bytes(result), {'boundaries': boundaries, 'max_depth': max(b[2] for b in boundaries) if boundaries else 0}

    def _mark_xml_boundaries(self, data: bytes) -> Tuple[bytes, Dict]:
        """Mark XML structure boundaries"""
        result = bytearray()
        tag_stack = []
        i = 0

        while i < len(data):
            if data[i] == ord('<'):
                tag_start = i
                i += 1
                while i < len(data) and data[i] != ord('>'):
                    i += 1

                if i < len(data):
                    tag = data[tag_start:i + 1]
                    result.extend(tag)

                    if not tag.startswith(b'</'):
                        tag_name = tag[1:-1].split()[0] if b' ' in tag else tag[1:-1]
                        tag_stack.append(tag_name)
                    else:
                        if tag_stack:
                            tag_stack.pop()
            else:
                result.append(data[i])

            i += 1

        return bytes(result), {'depth': len(tag_stack)}

    def _mark_csv_boundaries(self, data: bytes) -> Tuple[bytes, Dict]:
        """Mark CSV field boundaries"""
        lines = data.split(b'\n')
        delimiter = self._detect_csv_delimiter(lines[:10])

        result = []
        for line in lines:
            marked_line = line.replace(delimiter, self.markers['csv_delim'] + delimiter)
            result.append(marked_line)

        return b'\n'.join(result), {'delimiter': delimiter}

    def _mark_code_boundaries(self, data: bytes) -> Tuple[bytes, Dict]:
        """Mark code block boundaries"""
        try:
            text = data.decode('utf-8', errors='ignore')
            lines = text.split('\n')
            result = []

            for line in lines:
                stripped = line.lstrip()
                if stripped.startswith(('def ', 'class ', 'function ', 'public ', 'private ')):
                    result.append(self.markers['code_block'] + line.encode('utf-8'))
                else:
                    result.append(line.encode('utf-8'))

            return b'\n'.join(result), {'blocks_marked': sum(1 for r in result if r.startswith(self.markers['code_block']))}
        except (AttributeError, TypeError, ValueError):
            # Return original data if code marking fails
            return data, {}

    def _detect_csv_delimiter(self, lines: List[bytes]) -> bytes:
        """Detect CSV delimiter"""
        for delim in [b',', b'\t', b'|', b';']:
            counts = [line.count(delim) for line in lines if line.strip()]
            if counts and min(counts) == max(counts) and min(counts) > 0:
                return delim
        return b','


class Preprocessor:
    """Main preprocessing pipeline"""

    def __init__(self):
        self.bwt = BurrowsWheelerTransform()
        self.dedup = SlidingWindowDeduplicator()
        self.structure = StructureDetector()

    def preprocess(self, data: bytes, data_type: str) -> Tuple[bytes, Dict]:
        """
        Apply preprocessing based on data type

        Returns:
            (processed_data, metadata)
        """
        metadata = {'data_type': data_type, 'original_size': len(data)}

        # Skip BWT for now to avoid performance issues
        # Can be re-enabled with optimized implementation
        if data_type in ['json', 'xml', 'csv']:
            marked, struct_meta = self.structure.mark_boundaries(data, data_type)
            processed = marked
            metadata['structure'] = struct_meta
        else:
            processed = data

        # Skip deduplication for now - needs more debugging
        return processed, metadata

    def restore(self, data: bytes, metadata: Dict) -> bytes:
        """Restore original data from preprocessed form"""
        if not metadata:
            return data

        # First restore from deduplication
        restored = self.dedup.restore(data, metadata.get('dedup_references', []))

        # Then inverse BWT if it was applied
        if 'bwt_index' in metadata:
            bwt_index = metadata['bwt_index']
            # Handle case where bwt_index might be a list or single value
            if not isinstance(bwt_index, list):
                bwt_index = [bwt_index]
            restored = self.bwt.inverse_transform(restored, bwt_index)

        return restored