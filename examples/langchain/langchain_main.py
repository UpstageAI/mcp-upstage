"""
LangChain Integration with Upstage MCP Server Example

This example demonstrates how to use LangChain with Upstage's Solar LLM
and the MCP adapters to work with the Upstage MCP Server for document processing.
"""

import os
import asyncio
from pathlib import Path

# LangChain imports
from langchain_upstage import ChatUpstage  
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import ChatPromptTemplate

# MCP adapter imports
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    # Check for Upstage API key
    upstage_api_key = os.environ.get("UPSTAGE_API_KEY")
    
    if not upstage_api_key:
        upstage_api_key = input("Enter your Upstage API Key: ")
        os.environ["UPSTAGE_API_KEY"] = upstage_api_key
    
    # Get document path from user
    document_path = input("Enter the path to a document to analyze (PDF, image, or Office file): ")
    document_path = os.path.abspath(document_path)
    
    if not os.path.exists(document_path):
        print(f"Error: File not found at {document_path}")
        return
    
    # Create an LLM with Upstage Solar - using the correct class
    model = ChatUpstage(
        model_name="solar-pro",  
        temperature=0
    )
    
    # Connect to the Upstage MCP Server
    print(f"Connecting to Upstage MCP Server...")
    
    # Set up parameters for the MCP server
    server_params = StdioServerParameters(
        command="uvx",
        args=["upstage-mcp-server"],
        env={
            "UPSTAGE_API_KEY": upstage_api_key
        }
    )
    
    # Connect to the MCP server
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()
            
            # Load tools from the MCP server
            tools = await load_mcp_tools(session)
            
            # Print available tools
            print(f"Available tools: {[tool.name for tool in tools]}")
            
            # Create a prompt for the agent
            prompt = ChatPromptTemplate.from_messages([
                ("system", f"""You are an expert document analysis assistant.
                
You can:
1. Parse documents to extract their full content using the parse_document tool
2. Extract specific information from documents using the extract_information tool
                
Be thorough and detailed in your analysis. When extracting information,
specify what fields you're looking for.

The current document is located at: {document_path}
                """),
                ("human", "{input}")
            ])
            
            # Create a ReAct agent
            agent = create_react_agent(model, tools, prompt)
            
            # Create an agent executor
            agent_executor = AgentExecutor(
                agent=agent,
                tools=tools,
                verbose=True,  # Set to True to see the agent's thought process
                max_iterations=10,
                early_stopping_method="generate"
            )
            
            # Example 1: Parse the document
            print("\n" + "-" * 60)
            print("Task 1: Parsing the document")
            parsing_result = await agent_executor.ainvoke({
                "input": f"Parse the document at {document_path} and provide a detailed summary of its contents."
            })
            print("\nFinal Result:")
            print(parsing_result["output"])
            
            # Example 2: Extract specific information
            print("\n" + "-" * 60)
            print("Task 2: Extracting specific information")
            extraction_result = await agent_executor.ainvoke({
                "input": f"Extract key information from the document at {document_path}. If it's an invoice, get the invoice number, date, total amount, and vendor details. If it's another type of document, extract the most important fields."
            })
            print("\nFinal Result:")
            print(extraction_result["output"])
            
            # Example 3: Ask for a custom analysis
            print("\n" + "-" * 60)
            print("Task 3: Custom analysis")
            user_query = input("Enter your own query about the document: ")
            if user_query:
                custom_result = await agent_executor.ainvoke({
                    "input": user_query
                })
                print("\nFinal Result:")
                print(custom_result["output"])

if __name__ == "__main__":
    asyncio.run(main())
