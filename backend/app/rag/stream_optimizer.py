"""
File: backend/app/rag/stream_optimizer.py
Purpose: Streaming Token Debouncer and Packet Compressor for High-Throughput SSE.
Why it exists: LLMs often emit single-character or tiny 2-byte token fragments at 50 Hz.
               Sending each 2-byte token as a separate HTTP chunk adds 40+ bytes of TCP/SSE framing overhead.
               The Stream Debouncer coalesces tiny fragments into natural word/syllable chunks (15-30 chars)
               reducing network packets by up to 80% while maintaining instant perceived responsiveness.
"""

import time
from typing import Generator, Iterator


def debounce_token_stream(
    token_generator: Iterator[str],
    batch_chars: int = 16,
    max_delay_ms: float = 40.0
) -> Generator[str, None, None]:
    """
    Coalesces rapid token fragments into word-sized chunks.
    Flushes when either `batch_chars` threshold is reached or `max_delay_ms` elapsed.
    """
    buffer = []
    current_chars = 0
    last_flush_t = time.perf_counter()

    for token in token_generator:
        buffer.append(token)
        current_chars += len(token)

        now = time.perf_counter()
        elapsed_ms = (now - last_flush_t) * 1000.0

        if current_chars >= batch_chars or elapsed_ms >= max_delay_ms:
            yield "".join(buffer)
            buffer.clear()
            current_chars = 0
            last_flush_t = now

    # Flush remaining buffer at end of stream
    if buffer:
        yield "".join(buffer)
