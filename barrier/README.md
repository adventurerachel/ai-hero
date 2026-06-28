# App

This is a Streamlit application that answers questions based on the documentation for Barrier.

Barrier is software that mimics the functionality of a KVM switch, which historically would allow you to use a single keyboard and mouse to control multiple computers by physically turning a dial on the box to switch the machine you're controlling at any given moment. Barrier does this in software, allowing you to tell it which machine to control by moving your mouse to the edge of the screen, or by using a keypress to switch focus to a different system.

Feel free to interact with the app to find out more about Barrier and how to use it on your own setup.

## Running locally

Install dependencies:

```bash
uv sync
"streamlit>=1.58.0"