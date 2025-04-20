"""Basic tests for the Upstage MCP Server."""
import unittest
import os
import sys

# Add src to path for testing without installation
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from upstage_mcp import __version__

class TestUpstageServer(unittest.TestCase):
    """Test the Upstage MCP Server."""
    
    def test_version(self):
        """Test that the version is a string."""
        self.assertIsInstance(__version__, str)
        
if __name__ == "__main__":
    unittest.main()