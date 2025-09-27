"""
ContextFlow REST API Service
Q4 2024 - Production-ready API for compression service
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Query
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import io
import base64
import hashlib
import time
import os
import sys
from pathlib import Path
from enum import Enum

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import ContextFlow components
from contextflow.src.advanced_compressor import AdvancedCompressor
from contextflow.src.turbo_compressor import TurboCompressor

# Initialize FastAPI app
app = FastAPI(
    title="ContextFlow API",
    description="High-performance compression service with advanced features",
    version="4.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Initialize compressors
advanced_compressor = AdvancedCompressor()
turbo_compressor = TurboCompressor(level=6)

# Store for async jobs
jobs: Dict[str, Dict[str, Any]] = {}


# ============================================================================
# Models
# ============================================================================

class CompressionMode(str, Enum):
    """Available compression modes"""
    STANDARD = "standard"
    TURBO = "turbo"
    STREAMING = "stream"
    DELTA = "delta"
    SECURE = "secure"
    RECOVERY = "recovery"
    FORMAT = "format"


class CompressionRequest(BaseModel):
    """Compression request model"""
    data: str = Field(..., description="Base64 encoded data to compress")
    mode: CompressionMode = CompressionMode.STANDARD
    password: Optional[str] = None
    base_data: Optional[str] = Field(None, description="Base64 encoded base data for delta mode")
    filename: Optional[str] = Field(None, description="Filename for format-specific mode")
    level: int = Field(6, ge=1, le=9)


class CompressionResponse(BaseModel):
    """Compression response model"""
    compressed: str = Field(..., description="Base64 encoded compressed data")
    original_size: int
    compressed_size: int
    ratio: float
    mode: str
    time_ms: float


class JobStatus(BaseModel):
    """Job status model"""
    job_id: str
    status: str
    progress: float
    result: Optional[CompressionResponse] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    uptime: float
    memory_mb: float


# ============================================================================
# Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "ContextFlow API",
        "version": "4.0.0",
        "endpoints": {
            "compress": "/compress",
            "decompress": "/decompress",
            "compress_file": "/compress/file",
            "batch": "/batch",
            "health": "/health",
            "docs": "/docs"
        }
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    import psutil
    process = psutil.Process()

    return HealthResponse(
        status="healthy",
        version="4.0.0",
        uptime=time.time() - process.create_time(),
        memory_mb=process.memory_info().rss / (1024 * 1024)
    )


@app.post("/compress", response_model=CompressionResponse)
async def compress(request: CompressionRequest):
    """Compress data with specified mode"""
    try:
        # Decode input
        data = base64.b64decode(request.data)

        # Start timer
        start = time.perf_counter()

        # Compress based on mode
        if request.mode == CompressionMode.TURBO:
            compressed = turbo_compressor.compress(data)
        elif request.mode == CompressionMode.DELTA:
            if not request.base_data:
                raise HTTPException(400, "base_data required for delta mode")
            base = base64.b64decode(request.base_data)
            compressed = advanced_compressor.compress(data, mode="delta", base=base)
        elif request.mode == CompressionMode.SECURE:
            if not request.password:
                raise HTTPException(400, "password required for secure mode")
            compressed = advanced_compressor.compress(data, mode="secure", password=request.password)
        elif request.mode == CompressionMode.FORMAT:
            compressed = advanced_compressor.compress(
                data,
                mode="format",
                filename=request.filename or "file.bin"
            )
        else:
            compressed = advanced_compressor.compress(data, mode=request.mode.value)

        # Calculate metrics
        elapsed = (time.perf_counter() - start) * 1000

        return CompressionResponse(
            compressed=base64.b64encode(compressed).decode(),
            original_size=len(data),
            compressed_size=len(compressed),
            ratio=len(data) / len(compressed) if len(compressed) > 0 else 0,
            mode=request.mode.value,
            time_ms=elapsed
        )

    except Exception as e:
        raise HTTPException(500, f"Compression failed: {str(e)}")


@app.post("/decompress")
async def decompress(
    compressed: str = Field(..., description="Base64 encoded compressed data"),
    mode: Optional[CompressionMode] = None,
    password: Optional[str] = None,
    base_data: Optional[str] = None
):
    """Decompress data"""
    try:
        # Decode input
        data = base64.b64decode(compressed)

        # Prepare kwargs
        kwargs = {}
        if password:
            kwargs['password'] = password
        if base_data:
            kwargs['base'] = base64.b64decode(base_data)

        # Decompress
        decompressed = advanced_compressor.decompress(
            data,
            mode=mode.value if mode else "standard",
            **kwargs
        )

        return {
            "decompressed": base64.b64encode(decompressed).decode(),
            "size": len(decompressed)
        }

    except Exception as e:
        raise HTTPException(500, f"Decompression failed: {str(e)}")


@app.post("/compress/file")
async def compress_file(
    file: UploadFile = File(..., description="File to compress"),
    mode: CompressionMode = CompressionMode.STANDARD,
    level: int = Query(6, ge=1, le=9)
):
    """Compress uploaded file"""
    try:
        # Read file
        content = await file.read()

        # Compress
        start = time.perf_counter()

        if mode == CompressionMode.TURBO:
            compressed = turbo_compressor.compress(content)
        elif mode == CompressionMode.FORMAT:
            compressed = advanced_compressor.compress(
                content,
                mode="format",
                filename=file.filename
            )
        else:
            compressed = advanced_compressor.compress(content, mode=mode.value)

        elapsed = (time.perf_counter() - start) * 1000

        # Return as downloadable file
        output = io.BytesIO(compressed)
        output.seek(0)

        return StreamingResponse(
            output,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{file.filename}.ctx"',
                "X-Original-Size": str(len(content)),
                "X-Compressed-Size": str(len(compressed)),
                "X-Compression-Ratio": f"{len(content)/len(compressed):.2f}",
                "X-Time-Ms": f"{elapsed:.2f}"
            }
        )

    except Exception as e:
        raise HTTPException(500, f"File compression failed: {str(e)}")


@app.post("/batch")
async def batch_compress(
    files: List[UploadFile] = File(..., description="Files to compress"),
    mode: CompressionMode = CompressionMode.STANDARD
):
    """Compress multiple files into archive"""
    try:
        # Collect files
        file_data = {}
        for file in files:
            content = await file.read()
            file_data[file.filename] = content

        # Create archive
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.ctxarc', delete=False) as tmp:
            archive_path = tmp.name

        stats = advanced_compressor.create_archive(file_data, archive_path)

        # Read archive
        with open(archive_path, 'rb') as f:
            archive_data = f.read()

        # Clean up
        os.unlink(archive_path)

        # Return archive
        output = io.BytesIO(archive_data)
        output.seek(0)

        return StreamingResponse(
            output,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": 'attachment; filename="archive.ctxarc"',
                "X-Files": str(stats['files']),
                "X-Total-Size": str(stats['total_size']),
                "X-Compressed-Size": str(stats['compressed_size'])
            }
        )

    except Exception as e:
        raise HTTPException(500, f"Batch compression failed: {str(e)}")


@app.post("/job/start")
async def start_job(
    request: CompressionRequest,
    background_tasks: BackgroundTasks
):
    """Start async compression job"""
    # Generate job ID
    job_id = hashlib.sha256(f"{time.time()}{request.data[:100]}".encode()).hexdigest()[:16]

    # Initialize job
    jobs[job_id] = {
        "status": "pending",
        "progress": 0.0,
        "result": None,
        "error": None
    }

    # Start background task
    background_tasks.add_task(process_job, job_id, request)

    return {"job_id": job_id}


@app.get("/job/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get job status"""
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")

    job = jobs[job_id]

    return JobStatus(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        result=job["result"],
        error=job["error"]
    )


async def process_job(job_id: str, request: CompressionRequest):
    """Process compression job in background"""
    try:
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["progress"] = 0.1

        # Decode input
        data = base64.b64decode(request.data)

        jobs[job_id]["progress"] = 0.3

        # Compress
        start = time.perf_counter()

        if request.mode == CompressionMode.TURBO:
            compressed = turbo_compressor.compress(data)
        else:
            compressed = advanced_compressor.compress(data, mode=request.mode.value)

        elapsed = (time.perf_counter() - start) * 1000

        jobs[job_id]["progress"] = 0.9

        # Store result
        result = CompressionResponse(
            compressed=base64.b64encode(compressed).decode(),
            original_size=len(data),
            compressed_size=len(compressed),
            ratio=len(data) / len(compressed) if len(compressed) > 0 else 0,
            mode=request.mode.value,
            time_ms=elapsed
        )

        jobs[job_id]["result"] = result
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 1.0

    except Exception as e:
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["status"] = "failed"


@app.get("/stats")
async def get_stats():
    """Get API statistics"""
    import psutil
    process = psutil.Process()

    return {
        "uptime_seconds": time.time() - process.create_time(),
        "memory_mb": process.memory_info().rss / (1024 * 1024),
        "cpu_percent": process.cpu_percent(),
        "active_jobs": len([j for j in jobs.values() if j["status"] == "processing"]),
        "completed_jobs": len([j for j in jobs.values() if j["status"] == "completed"]),
        "failed_jobs": len([j for j in jobs.values() if j["status"] == "failed"]),
    }


# ============================================================================
# WebSocket Support (for streaming)
# ============================================================================

from fastapi import WebSocket, WebSocketDisconnect

@app.websocket("/ws/compress")
async def websocket_compress(websocket: WebSocket):
    """WebSocket endpoint for streaming compression"""
    await websocket.accept()

    try:
        while True:
            # Receive data
            data = await websocket.receive_bytes()

            # Compress
            compressed = turbo_compressor.compress(data)

            # Send back
            await websocket.send_bytes(compressed)

    except WebSocketDisconnect:
        pass


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Resource not found"}
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )


# ============================================================================
# Startup/Shutdown
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    print("ContextFlow API v4.0.0 starting...")
    print("Ready to handle requests")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("ContextFlow API shutting down...")
    # Clean up any resources


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, workers=4)