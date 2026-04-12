"""
LangGraph Builder

Builds the LangGraph workflow for task execution.
"""
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages
from app.graph.state import GraphState
from app.graph.nodes.load_task_context import load_task_context
from app.graph.nodes.parse_command import parse_command
from app.graph.nodes.resolve_intent import resolve_intent
from app.graph.nodes.rag_command_interpretation import rag_command_interpretation
from app.graph.nodes.rag_rule_augment import rag_rule_augment
from app.graph.nodes.execute_action import execute_action
from app.graph.nodes.finalize_result import finalize_result
from app.core.logging import logger


def build_graph() -> StateGraph:
    """
    Build the LangGraph workflow.
    
    Returns:
        Compiled StateGraph
    """
    # Create the graph
    graph_builder = StateGraph(dict)
    
    # Add nodes
    graph_builder.add_node("load_task_context", load_task_context)
    graph_builder.add_node("parse_command", parse_command)
    graph_builder.add_node("resolve_intent", resolve_intent)
    graph_builder.add_node("rag_command_interpretation", rag_command_interpretation)
    graph_builder.add_node("rag_rule_augment", rag_rule_augment)
    graph_builder.add_node("execute_action", execute_action)
    graph_builder.add_node("finalize_result", finalize_result)
    
    # Set entry point
    graph_builder.set_entry_point("load_task_context")
    
    # Add edges (sequential flow)
    graph_builder.add_edge("load_task_context", "parse_command")
    graph_builder.add_edge("parse_command", "resolve_intent")
    graph_builder.add_edge("resolve_intent", "rag_command_interpretation")
    graph_builder.add_edge("rag_command_interpretation", "rag_rule_augment")
    graph_builder.add_edge("rag_rule_augment", "execute_action")
    graph_builder.add_edge("execute_action", "finalize_result")
    graph_builder.add_edge("finalize_result", END)
    
    # Compile the graph
    graph = graph_builder.compile()
    
    logger.info("LangGraph workflow built successfully")
    
    return graph


# Singleton graph instance
graph = build_graph()
