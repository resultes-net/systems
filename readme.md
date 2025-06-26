### Installation

Run the following commands in your Windows Command Prompt from the `pytrnsys_process` directory:

1. Create and activate a virtual environment:
   ```bash
   py -3.12 -m venv venv
   venv\Scripts\activate
   ```
   If you already have an environment, it may be best to deactivate it first.
   ```bash
   deactivate
   ```

2. Install dependencies:
   ```bash
   python -m pip install wheel
   python -m pip install -r requirements.txt
   ```

3. You're ready to use the `pytrnsys_process` API! 🎉