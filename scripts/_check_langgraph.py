#!/usr/bin/env python3
"""Quick LangGraph install verify."""
from importlib.metadata import version
print("langgraph:", version("langgraph"))
print("langchain-openai:", version("langchain-openai"))
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
print("Imports OK")
