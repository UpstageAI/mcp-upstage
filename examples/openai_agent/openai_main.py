"""
OpenAI Integration with Upstage MCP Server Example

This example demonstrates how to use OpenAI's Agents SDK to connect to the
Upstage MCP Server for document processing and information extraction.
"""

import os
import asyncio
import json
from pathlib import Path

# Import OpenAI and agents SDK
from openai import OpenAI
from agents import Agent, Runner, trace
from agents.mcp import MCPServerStdio

async def main():
    # Check for API keys
    upstage_api_key = os.environ.get("UPSTAGE_API_KEY")
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    
    if not upstage_api_key:
        upstage_api_key = input("Enter your Upstage API Key: ")
        os.environ["UPSTAGE_API_KEY"] = upstage_api_key
    
    if not openai_api_key:
        openai_api_key = input("Enter your OpenAI API Key: ")
        os.environ["OPENAI_API_KEY"] = openai_api_key
    
    # Get document path from user
    document_path = input("Enter the path to a document to analyze (PDF, image, or Office file): ")
    document_path = os.path.abspath(document_path)
    
    if not os.path.exists(document_path):
        print(f"Error: File not found at {document_path}")
        return

    # Connect to the Upstage MCP Server
    print(f"Connecting to Upstage MCP Server...")
    
    # Start the server as a subprocess using uvx
    async with MCPServerStdio(
        cache_tools_list=True,  # Cache the tools list for better performance
        params={
            "command": "uvx",
            "args": ["upstage-mcp-server"],
            "env": {
                "UPSTAGE_API_KEY": upstage_api_key,
            }
        }
    ) as server:
        # Print available tools from the server
        tools = await server.list_tools()
        print(f"Available tools: {[tool.name for tool in tools]}")
        
        # Create an agent with access to the MCP server
        agent = Agent(
            name="Document Analysis Assistant",
            instructions=f"""You are an expert at analyzing documents.
            
You can:
1. Parse documents to extract their full content using parse_document
2. Extract specific information from documents using extract_information
            
When analyzing documents, always be thorough and detailed. If extracting information,
specify what fields you're looking for.

The current document is located at: {document_path}
            """,
            mcp_servers=[server],
        )
        
        # Use tracing to see what's happening
        with trace(workflow_name="Upstage Document Analysis"):
            # Example 1: Parse the document
            print("\n" + "-" * 60)
            print("Task 1: Parsing the document")
            parsing_result = await Runner.run(
                starting_agent=agent,
                input=f"Parse the document at {document_path} and provide a detailed summary of its contents."
            )
            print(parsing_result.final_output)
            
            # Example 2: Extract specific information
            print("\n" + "-" * 60)
            print("Task 2: Extracting specific information")
            extraction_result = await Runner.run(
                starting_agent=agent,
                input=f"Extract key information from the document at {document_path}. If it's an invoice, get the invoice number, date, total amount, and vendor details. If it's another type of document, extract the most important fields."
            )
            print(extraction_result.final_output)
            
            # Example 3: Ask for a custom analysis
            print("\n" + "-" * 60)
            print("Task 3: Custom analysis")
            user_query = input("Enter your own query about the document: ")
            if user_query:
                custom_result = await Runner.run(
                    starting_agent=agent,
                    input=user_query
                )
                print(custom_result.final_output)

if __name__ == "__main__":
    asyncio.run(main())