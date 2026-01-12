"""Top-level ingesters package.

This package contains ingester implementations that can be dynamically
discovered and loaded by the backend registry system.

Each ingester should:
1. Implement the Ingester protocol from backend.app.ingesters.protocol
2. Register itself using @Ingesters.register(key="<name>") decorator
3. Provide get_metadata() class method
4. Implement validate() and ingest() methods

Directory structure:
    ingesters/
        <ingester_name>/
            __init__.py
            ingester.py          # Main ingester class
            ... (other modules)
"""
