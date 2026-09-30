#!/usr/bin/env python3
"""Experimental loopback HTTP transport for the official non-generative Decider GGUF SDK.

The upstream Decider HTTP server does not serve GGUF. This wrapper changes only
transport: model probabilities and calibration remain Decider.system_one outputs.
"""
import argparse
from contextlib import asynccontextmanager
from importlib.metadata import version
from pathlib import Path
from threading import Lock

from fastapi import FastAPI, HTTPException
import uvicorn


def create_app(model_dir: Path, gguf_file: str, context_tokens: int, revision: str):
    lock = Lock()  # llama.cpp context is single-sequence; serialize concurrent HTTP callers.

    @asynccontextmanager
    async def lifespan(app):
        from decider.infer import Decider
        app.state.engine = Decider(str(model_dir), gguf_file=gguf_file,
                                   gguf_options={"n_ctx": context_tokens, "n_batch": context_tokens,
                                                 "n_gpu_layers": -1, "n_seq_max": 1})
        yield
        del app.state.engine

    app = FastAPI(lifespan=lifespan)

    @app.get("/health")
    def health():
        from llama_cpp import llama_supports_gpu_offload
        return {"ok": True, "model": app.state.engine.name, "revision": revision,
                "transport": "experimental SDK wrapper, not upstream decider.serve",
                "runtime": "llama.cpp", "gpuOffloadAvailable": llama_supports_gpu_offload(),
                "requestedGpuLayers": -1, "contextTokens": context_tokens,
                "deciderVersion": version("decider-ai"), "llamaCppPythonVersion": version("llama-cpp-python")}

    @app.post("/v1/systemone")
    def systemone(payload: dict):
        engine = app.state.engine
        if payload.get("state") is None or not isinstance(payload.get("questions"), dict):
            raise HTTPException(400, "state and questions are required")
        if payload.get("model") not in (None, engine.name, Path(gguf_file).stem):
            raise HTTPException(400, "Requested model is not the loaded checkpoint")
        maximum = payload.get("max_len", context_tokens)
        if not isinstance(maximum, int) or not 1 <= maximum <= context_tokens:
            raise HTTPException(400, "max_len must be within the configured context limit")
        try:
            with lock:
                return engine.system_one(payload["state"], payload["questions"], max_state_tokens=maximum)
        except (ValueError, KeyError, TypeError) as error:
            raise HTTPException(422, str(error)) from error

    return app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, required=True, help="Pinned local snapshot including calibration config")
    parser.add_argument("--revision", required=True, help="Recorded immutable checkpoint revision")
    parser.add_argument("--gguf-file", default="decider-2b-v11-Q4_K_M.gguf")
    parser.add_argument("--context-tokens", type=int, default=8192)
    parser.add_argument("--port", type=int, default=18743)
    args = parser.parse_args()
    if not (args.model_dir / args.gguf_file).is_file():
        parser.error("Pinned GGUF file is absent; download explicitly before starting")
    if args.context_tokens < 1:
        parser.error("context-tokens must be positive")
    uvicorn.run(create_app(args.model_dir, args.gguf_file, args.context_tokens, args.revision),
                host="127.0.0.1", port=args.port, workers=1)


if __name__ == "__main__":
    main()
