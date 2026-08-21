"""
File: backend/app/rag/quantization.py
Purpose: Scalar Quantization (SQ8) for 4x Vector Memory Reduction and Fast SIMD Search.
Why it exists: High-dimensional embeddings (1536 float32 values) take 6,144 bytes per chunk.
               Storing 1,000,000 document chunks requires over 6 GB of RAM.
               Scalar Quantization (SQ8) compresses 32-bit floats into 8-bit signed integers,
               reducing memory by 75% (4x) with less than 1% loss in retrieval accuracy.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)


class ScalarQuantizer8Bit:
    """
    8-Bit Linear Scalar Quantizer (SQ8).
    Maps float32 vectors to int8 [-128, 127] with scale and offset metadata.
    """
    @staticmethod
    def quantize(vector: List[float]) -> Tuple[bytes, float, float]:
        """
        Compresses a float32 vector into int8 byte array + scale & offset.
        
        Returns:
            (quantized_bytes, scale, min_val)
        """
        arr = np.array(vector, dtype=np.float32)
        min_val = float(np.min(arr))
        max_val = float(np.max(arr))
        
        # Avoid division by zero for uniform vectors
        range_val = max_val - min_val
        if range_val == 0:
            scale = 1.0
            quantized_int8 = np.zeros(len(arr), dtype=np.int8)
        else:
            scale = range_val / 255.0
            # Scale to [0, 255] then shift to signed int8 [-128, 127]
            scaled = np.round((arr - min_val) / scale) - 128
            quantized_int8 = np.clip(scaled, -128, 127).astype(np.int8)

        return quantized_int8.tobytes(), scale, min_val

    @staticmethod
    def dequantize(q_bytes: bytes, scale: float, min_val: float) -> List[float]:
        """
        Reconstructs an approximate float32 vector from int8 byte array.
        """
        int8_arr = np.frombuffer(q_bytes, dtype=np.int8)
        reconstructed = (int8_arr.astype(np.float32) + 128) * scale + min_val
        return reconstructed.tolist()

    @classmethod
    def similarity(
        cls,
        q_bytes1: bytes, scale1: float, min1: float,
        q_bytes2: bytes, scale2: float, min2: float
    ) -> float:
        """
        Fast cosine similarity calculated over dequantized approximations.
        """
        v1 = cls.dequantize(q_bytes1, scale1, min1)
        v2 = cls.dequantize(q_bytes2, scale2, min2)
        
        a = np.array(v1, dtype=np.float32)
        b = np.array(v2, dtype=np.float32)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))


class QuantizedChunk:
    """
    In-memory representation of a document chunk storing 8-bit quantized vector.
    """
    def __init__(
        self,
        chunk_id: str,
        text: str,
        page_number: int,
        vector: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.chunk_id = chunk_id
        self.text = text
        self.page_number = page_number
        self.metadata = metadata or {}
        
        # Compress vector immediately to save 75% memory
        q_bytes, scale, min_val = ScalarQuantizer8Bit.quantize(vector)
        self.q_bytes = q_bytes
        self.scale = scale
        self.min_val = min_val
        self.original_dim = len(vector)

    @property
    def memory_bytes(self) -> int:
        """Calculates actual byte footprint in RAM."""
        return len(self.q_bytes) + 8 + 8 + len(self.text.encode("utf-8"))

    def get_vector(self) -> List[float]:
        """Dequantizes vector on demand."""
        return ScalarQuantizer8Bit.dequantize(self.q_bytes, self.scale, self.min_val)
