"""
LangGraph Multi-Agent Workflow definition and compilation for ResolveAI.
Assembles the state machine graph, registers conditional edges, and compiles the workflow.
"""

from typing import Any, Dict, Optional
from langgraph.graph import StateGraph, START, END

from app.core.logging_config import logger
from app.workflows.state import WorkflowState, initialize_workflow_state
from app.workflows.nodes import (
    initialize_case_node,
    analyze_complaint_node,
    investigate_order_node,
    retrieve_policy_evidence_node,
    recommend_resolution_node,
    verify_resolution_node,
    attempt_recovery_node,
    handle_missing_information_node,
    customer_clarification_node,
    escalate_case_node,
    supervisor_review_node,
    record_resolution_node,
    finalize_response_node,
)
from app.workflows.routing import (
    route_after_init,
    route_after_verification,
    route_after_supervisor_review,
    route_after_customer_clarification,
)
from app.workflows.checkpointer import get_checkpointer


def create_resolution_graph(checkpointer: Optional[Any] = None) -> Any:
    """
    Constructs and compiles the LangGraph multi-agent customer resolution workflow.
    Registers all 11 Level 4 nodes plus Level 5 supervisor_review node.
    Compiles with persistent SQLite-backed checkpointer.
    """
    builder = StateGraph(WorkflowState)

    # 1. Register all nodes (preserves all 11 original nodes + supervisor_review)
    builder.add_node("initialize_case", initialize_case_node)
    builder.add_node("analyze_complaint", analyze_complaint_node)
    builder.add_node("investigate_order", investigate_order_node)
    builder.add_node("retrieve_policy_evidence", retrieve_policy_evidence_node)
    builder.add_node("recommend_resolution", recommend_resolution_node)
    builder.add_node("verify_resolution", verify_resolution_node)
    builder.add_node("attempt_recovery", attempt_recovery_node)
    builder.add_node("handle_missing_information", handle_missing_information_node)
    builder.add_node("customer_clarification", customer_clarification_node)
    builder.add_node("escalate_case", escalate_case_node)
    builder.add_node("supervisor_review", supervisor_review_node)
    builder.add_node("record_resolution", record_resolution_node)
    builder.add_node("finalize_response", finalize_response_node)

    # 2. Add edges from START
    builder.add_edge(START, "initialize_case")

    # 3. Conditional routing after initialization (short-circuits empty input)
    builder.add_conditional_edges(
        "initialize_case",
        route_after_init,
        {
            "analyze_complaint": "analyze_complaint",
            "finalize_response": "finalize_response",
        },
    )

    # 4. Standard linear agent analysis pipeline
    builder.add_edge("analyze_complaint", "investigate_order")
    builder.add_edge("investigate_order", "retrieve_policy_evidence")
    builder.add_edge("retrieve_policy_evidence", "recommend_resolution")
    builder.add_edge("recommend_resolution", "verify_resolution")

    # 5. Core conditional evaluation & branching after verification
    builder.add_conditional_edges(
        "verify_resolution",
        route_after_verification,
        {
            "attempt_recovery": "attempt_recovery",
            "handle_missing_information": "handle_missing_information",
            "escalate_case": "escalate_case",
            "record_resolution": "record_resolution",
        },
    )

    # 6. Bounded recovery loops back to verify_resolution
    builder.add_edge("attempt_recovery", "verify_resolution")

    # 7. Level 5 Human-in-the-Loop review routing
    builder.add_edge("escalate_case", "supervisor_review")
    builder.add_conditional_edges(
        "supervisor_review",
        route_after_supervisor_review,
        {
            "record_resolution": "record_resolution",
            "finalize_response": "finalize_response",
        },
    )

    # 8. Missing information interruption and clarification loop
    builder.add_edge("handle_missing_information", "customer_clarification")
    builder.add_conditional_edges(
        "customer_clarification",
        route_after_customer_clarification,
        {
            "investigate_order": "investigate_order",
            "finalize_response": "finalize_response",
        },
    )
    builder.add_edge("record_resolution", "finalize_response")

    # 9. Terminate at END
    builder.add_edge("finalize_response", END)

    # Compile the graph with persistent checkpointer
    cp = checkpointer if checkpointer is not None else get_checkpointer()
    compiled_graph = builder.compile(checkpointer=cp)
    return compiled_graph


# Cached compiled singleton graph
_compiled_graph = None


def get_resolution_graph(checkpointer: Optional[Any] = None) -> Any:
    """Returns the cached compiled resolution graph, building it on first access."""
    global _compiled_graph
    if checkpointer is not None:
        return create_resolution_graph(checkpointer=checkpointer)
    if _compiled_graph is None:
        logger.info("Compiling ResolveAI LangGraph multi-agent workflow with SQLite checkpointer...")
        _compiled_graph = create_resolution_graph()
    return _compiled_graph


def run_resolution_workflow(
    complaint_text: str,
    order_number: Optional[str] = None,
    case_number: Optional[str] = None,
    case_id: Optional[int] = None,
    customer_id: Optional[int] = None,
    category: Optional[str] = None,
    seller_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    thread_id: Optional[str] = None,
    max_retries: int = 1,
    checkpointer: Optional[Any] = None,
) -> WorkflowState:
    """
    Executes the multi-agent resolution workflow end-to-end.
    Persists checkpoints under thread_id.
    Pauses at supervisor_review if human review is required.
    Returns the typed WorkflowState dictionary.
    """
    initial_state = initialize_workflow_state(
        complaint_text=complaint_text,
        order_number=order_number,
        case_number=case_number,
        case_id=case_id,
        customer_id=customer_id,
        category=category,
        seller_id=seller_id,
        workflow_id=workflow_id,
        thread_id=thread_id,
        max_retries=max_retries,
    )

    graph = get_resolution_graph(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": initial_state["thread_id"]}}
    final_state = graph.invoke(initial_state, config=config)
    return final_state

