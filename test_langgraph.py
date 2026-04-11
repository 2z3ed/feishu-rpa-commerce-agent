"""
Test LangGraph Workflow

Simple test to verify the LangGraph workflow is working correctly.
"""
from app.graph.builder import graph as lang_graph


def test_langgraph_workflow():
    """Test the LangGraph workflow with a sample query."""
    print("=== Testing LangGraph Workflow ===")
    
    # Test case 1: product.query_sku_status
    initial_state = {
        "task_id": "TEST-001",
        "source_message_id": "test_msg_001",
        "source_chat_id": "test_chat_001",
        "user_open_id": "test_user_001",
        "raw_text": "查询 SKU A001 状态",
    }
    
    print(f"Input: {initial_state['raw_text']}")
    
    result = lang_graph.invoke(initial_state)
    
    print(f"Result status: {result.get('status')}")
    print(f"Result intent: {result.get('intent_code')}")
    print(f"Result summary: {result.get('result_summary')}")
    print(f"Result slots: {result.get('slots')}")
    
    # Test case 2: unknown intent
    print("\n=== Testing Unknown Intent ===")
    initial_state_2 = {
        "task_id": "TEST-002",
        "source_message_id": "test_msg_002",
        "source_chat_id": "test_chat_002",
        "user_open_id": "test_user_002",
        "raw_text": "你好",
    }
    
    print(f"Input: {initial_state_2['raw_text']}")
    
    result_2 = lang_graph.invoke(initial_state_2)
    
    print(f"Result status: {result_2.get('status')}")
    print(f"Result intent: {result_2.get('intent_code')}")
    print(f"Result summary: {result_2.get('result_summary')}")
    
    print("\n=== Test Complete ===")


if __name__ == "__main__":
    test_langgraph_workflow()
