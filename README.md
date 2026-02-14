# 🚀 SETJA - Real-time AI Screen Translator

**SETJA** is a high-performance, fully offline screen translation tool designed specifically to translate instantly from your screen.

It uses a custom C++/DirectX engine for ultra-fast capture and runs entirely locally on your machine—ensuring privacy and zero latency.

## ✨ Key Features

*   **⚡ Ultra-Fast Capture:** Built with a custom **C++ & DirectX (DXGI)** engine for millisecond-level screen capture latency.
*   **🧠 Fully Offline AI:**
    *   **OCR:** Optimized **PaddleOCR** engine for accurate **English** text recognition.
    *   **Translation:** **CTranslate2 & MarianMT** neural models specialized for **English -> Arabic** translation.
*   **🎨 Modern Overlay UI:**
    *   **Acrylic/Blur Effect:** A beautiful floating window that blends with Windows 11/10 aesthetics.
    *   **Click-Through Mode:** The overlay stays on top but lets you click through it (perfect for gaming).
    *   **Smart Behavior:** Auto-hides when no text is detected.
*   **🎮 GPU Accelerated:** Optimized for NVIDIA GPUs (CUDA) to ensure smooth performance.

## ⚠️ Current Limitations
*   **Language Support:** This version currently supports **English to Arabic** translation only.

## 🛠️ Tech Stack
*   **Core:** Python 3.x & C++
*   **GUI:** PySide6 (Qt)
*   **AI Engines:** PaddleOCR, CTranslate2
*   **Capture:** Windows DXGI Desktop Duplication API

## 📦 How to Run
1.  Download the `SETJA_v1.0.zip` file below.
2.  Extract the folder.
3.  Run `Setup_Env.exe`.
4.  Run `main.cmd`.
5.  Select the screen area containing **English text**.
6.  Enjoy instant Arabic translation!

---
*Note 1: Requires an NVIDIA GPU for optimal performance.*
*Note 2: The Virtual Environment requires approximately **7 GB** of disk space.*
*Note 3: This is the initial release. Please report any bugs in the Issues tab.*
