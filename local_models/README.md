# Local Models Directory

This directory stores offline model weights, face detection cascades/DNN weights, and optional local LLM configurations.

## Optional Components
- **Ollama**: If running locally, install Ollama from [https://ollama.ai](https://ollama.ai) and pull models such as `llama3:8b` or `mistral`.
- **MediaPipe / OpenCV**: Default face detection utilizes local MediaPipe Face Mesh / Face Detection or OpenCV Haar Cascades / DNN models with no cloud dependencies.
- **Whisper / Offline ASR**: Optional offline speech transcription using local faster-whisper or whisper.cpp can place model checkpoints here.

Runtime operation is fully offline and defaults to deterministic rule-based engines if no local models are installed.
