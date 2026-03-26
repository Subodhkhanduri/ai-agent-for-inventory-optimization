# inventory_chatbot/crew/simple_orchestrator.py
"""
Simple agent orchestrator using only Groq LLM - NO OpenAI dependencies.
This replaces the CrewAI framework with a lightweight implementation.
"""

import os
import logging
from typing import Dict, Any
import pandas as pd
from langchain_groq import ChatGroq

from inventory_chatbot.config import settings
from inventory_chatbot.crew.tools.data_tools import DataQueryTool, StatisticsTool, ColumnInfoTool
from inventory_chatbot.crew.tools.forecast_tools import ForecastTool
from inventory_chatbot.crew.tools.viz_tools import ChartGeneratorTool, TrendPlotTool
from inventory_chatbot.crew.tools.sql_query_tool import SQLQueryTool
from inventory_chatbot.crew.tools.inventory_tools import InventoryStatusTool

logger = logging.getLogger(__name__)


class SimpleInventoryOrchestrator:
    """
    Simple orchestrator that processes queries without CrewAI.
    Uses only Groq LLM (FREE) - no OpenAI dependencies.
    """
    
    def __init__(self, dataframe: pd.DataFrame, user_role: str = "viewer", 
                 session_id: str = None, conversation_history: list = None):
        """Initialize orchestrator with context."""
        self.dataframe = dataframe
        self.user_role = user_role
        self.session_id = session_id
        self.conversation_history = conversation_history or []
        
        # Initialize Groq LLM only
        self.llm = ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model_name=settings.GROQ_MODEL,
            temperature=0.15,
            max_tokens=800
        )
        
        # Initialize tools
        self.tools = self._initialize_tools()
    
    def _initialize_tools(self) -> Dict[str, Any]:
        """Initialize all tools with dataframe context."""
        # SQL Query Tool (primary for data queries)
        sql_query_tool = SQLQueryTool()
        sql_query_tool.dataframe = self.dataframe
        sql_query_tool.set_llm(self.llm)  # Share the existing LLM instance
        
        data_query_tool = DataQueryTool()
        data_query_tool.dataframe = self.dataframe
        
        statistics_tool = StatisticsTool()
        statistics_tool.dataframe = self.dataframe
        
        column_info_tool = ColumnInfoTool()
        column_info_tool.dataframe = self.dataframe
        
        forecast_tool = ForecastTool()
        forecast_tool.dataframe = self.dataframe
        forecast_tool.user_role = self.user_role
        
        chart_generator_tool = ChartGeneratorTool()
        chart_generator_tool.dataframe = self.dataframe
        
        trend_plot_tool = TrendPlotTool()
        trend_plot_tool.dataframe = self.dataframe
        
        inventory_status_tool = InventoryStatusTool()
        inventory_status_tool.dataframe = self.dataframe
        
        return {
            "sql_query_tool": sql_query_tool,
            "data_query_tool": data_query_tool,
            "statistics_tool": statistics_tool,
            "column_info_tool": column_info_tool,
            "forecast_tool": forecast_tool,
            "chart_generator_tool": chart_generator_tool,
            "trend_plot_tool": trend_plot_tool,
            "inventory_status_tool": inventory_status_tool,
        }
    
    def execute(self, query: str) -> Dict[str, Any]:
        """
        Execute query processing with SQL-first approach.
        
        Args:
            query: User's natural language query
            
        Returns:
            Dict containing response, chart_b64, forecast_values, etc.
        """
        try:
            # Step 1: Classify query type
            query_type = self._classify_query_type(query)
            
            # Step 2: Execute based on classification
            data_result = None
            forecast_result = None
            viz_result = None
            sql_used = False
            
            query_lower = query.lower()
            inventory_result = None
            
            # Dataset information queries - use existing method
            if any(phrase in query_lower for phrase in ["about dataset", "about the dataset", "dataset info", 
                                                          "what is this dataset", "describe dataset", 
                                                          "dataset details", "tell me about data", 
                                                          "what data", "columns", "what's in the dataset"]):
                data_result = self._get_dataset_info()
            
            # SQL-first approach for data queries
            elif query_type == "SQL":
                sql_result = self._execute_sql_query(query)
                if sql_result.get('success'):
                    data_result = sql_result
                    sql_used = True
                else:
                    # SQL failed, fall back to LLM/traditional methods
                    data_result = self._execute_data_query_fallback(query_lower)
            
            # Check for forecast requests
            if "forecast" in query_lower or "predict" in query_lower:
                forecast_result = self._execute_forecast(query)
            
            # Check for visualization requests (but skip if forecast already has a chart)
            if (not forecast_result or not forecast_result.get('chart_base64')) and \
               any(word in query_lower for word in ["trend", "plot", "chart", "visual", "show", "graph"]):
                viz_result = self._execute_visualization(query)
            
            # Check for inventory status/ROP requests
            if any(word in query_lower for word in ["status", "stock", "reorder", "rop", "inventory"]):
                inventory_result = self._execute_inventory_status(query)
            
            # Step 3: Generate response using LLM
            final_response = self._generate_response(
                query=query,
                query_type=query_type,
                data_result=data_result,
                forecast_result=forecast_result,
                viz_result=viz_result,
                inventory_result=inventory_result,
                sql_used=sql_used
            )
            
            return final_response
            
        except Exception as e:
            return {
                "response": f"Error processing query: {str(e)}",
                "status": "error",
                "session_id": self.session_id
            }
    
    def _classify_query_type(self, query: str) -> str:
        """
        Classify query to determine if it should use SQL or LLM.
        
        Returns:
            "SQL" for data queries, "LLM" for general questions
        """
        try:
            prompt = f"""Classify this inventory management query into one category:

Query: {query}

Categories:
- SQL: Questions about data (counts, sums, records, filters, specific items/stores, averages, comparisons, listings, trends from data)
- LLM: General advice, explanations, recommendations, "how to" questions, forecasting strategy, business advice, what is

Rules:
- If asking for DATA from the inventory → SQL
- If asking "how many", "show me", "which stores", "total sales", "sum", "records exist" → SQL
- If asking for ADVICE or EXPLANATION (e.g. "what is EOQ", "how does safety stock work") → LLM
- If asking "what should I do" → LLM

Respond with ONLY: SQL or LLM"""
            
            messages = [{"role": "user", "content": prompt}]
            response = self.llm.invoke(messages)
            classification = response.content.strip().upper()
            
            # Ensure valid response
            if classification in ["SQL", "LLM"]:
                return classification
            return "LLM"  # Default fallback
            
        except:
            return "LLM"

    
    def _get_dataset_info(self) -> Dict[str, Any]:
        """Get comprehensive information about the uploaded dataset."""
        try:
            info = {
                "row_count": len(self.dataframe),
                "columns": list(self.dataframe.columns),
                "column_types": {col: str(dtype) for col, dtype in self.dataframe.dtypes.items()},
                "shape": f"{self.dataframe.shape[0]} rows × {self.dataframe.shape[1]} columns",
                "sample_data": self.dataframe.head(3).to_dict('records'),
            }
            
            # Add basic statistics for numeric columns
            numeric_cols = self.dataframe.select_dtypes(include=['int64', 'float64']).columns
            if len(numeric_cols) > 0:
                stats = {}
                for col in numeric_cols:
                    stats[col] = {
                        "min": float(self.dataframe[col].min()),
                        "max": float(self.dataframe[col].max()),
                        "mean": float(self.dataframe[col].mean()),
                    }
                info["statistics"] = stats
            
            return info
        except Exception as e:
            return {"error": f"Failed to get dataset info: {str(e)}"}


    def _execute_sql_query(self, query: str) -> Dict[str, Any]:
        """Execute query using SQL tool with conversation context."""
        try:
            # Build context-aware query if we have conversation history
            contextual_query = query
            if self.conversation_history:
                # Add last 2 exchanges for context
                context_str = "Previous conversation:\n"
                for msg in self.conversation_history[-2:]:
                    context_str += f"Q: {msg['query']}\nA: {msg['response']}\n"
                contextual_query = f"{context_str}\nCurrent query: {query}"
            
            return self.tools["sql_query_tool"]._run(natural_query=contextual_query)
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _execute_data_query_fallback(self, query_lower: str) -> Any:
        """Execute data queries using traditional tools (fallback when SQL fails)."""
        try:
            if "how many" in query_lower or "count" in query_lower:
                return self.tools["data_query_tool"]._run(intent="COUNT_ROWS")
            elif "total" in query_lower and "sales" in query_lower:
                return self.tools["data_query_tool"]._run(intent="TOTAL_SALES")
            elif "average" in query_lower or "mean" in query_lower:
                return self.tools["statistics_tool"]._run(operation="mean", column="Demand")
            elif "sum" in query_lower:
                return self.tools["data_query_tool"]._run(intent="TOTAL_SALES")
            else:
                return self.tools["column_info_tool"]._run()
        except Exception as e:
            return {"error": str(e)}

    
    def _extract_item_store(self, query: str) -> tuple[int | None, int | None]:
        """
        Extract item and store from query and conversation history.
        
        Returns:
            Tuple of (item_id, store_id)
        """
        import re
        query_lower = query.lower()
        item = None
        store = None
        
        # 1. Try regex extraction from CURRENT query
        item_match = re.search(r'item\s+(\d+)', query_lower)
        store_match = re.search(r'store\s+(\d+)', query_lower)
        
        if item_match:
            item = int(item_match.group(1))
        if store_match:
            store = int(store_match.group(1))
            
        # 2. If not found, check conversation history (context awareness)
        if (not item or not store) and self.conversation_history:
            for msg in reversed(self.conversation_history[-3:]):
                combined = (msg.get('query', '') + ' ' + msg.get('response', '')).lower()
                
                if not item:
                    m = re.search(r'item\s+(\d+)', combined)
                    if m:
                        item = int(m.group(1))
                
                if not store:
                    m = re.search(r'store\s+(\d+)', combined)
                    if m:
                        store = int(m.group(1))
                
                if item and store:
                    break
                    
        return item, store

    def _execute_forecast(self, query: str) -> Any:
        """Execute forecasting with context awareness."""
        try:
            item, store = self._extract_item_store(query)
            
            logger.info(f"Forecast request - extracted item={item}, store={store}")
            
            # Execute forecast if we have both item and store
            if item is not None and store is not None:
                result = self.tools["forecast_tool"]._run(
                    item=item,
                    store=store,
                    periods=10
                )
                logger.info(f"Forecast tool result keys: {result.keys() if isinstance(result, dict) else type(result)}")
                if isinstance(result, dict) and 'error' in result:
                    logger.error(f"Forecast error: {result['error']}")
                return result
            else:
                missing = []
                if item is None:
                    missing.append("item number")
                if store is None:
                    missing.append("store number")
                logger.warning(f"Missing forecast parameters: {missing}")
                return {"error": f"Please specify {' and '.join(missing)} (e.g., 'forecast item 1 store 2')"}
                
        except Exception as e:
            logger.error(f"Exception in _execute_forecast: {e}", exc_info=True)
            return {"error": str(e)}
    
    def _execute_visualization(self, query: str) -> Any:
        """Execute visualization generation with context awareness."""
        try:
            # Try to extract item/store context
            item_num, store_num = self._extract_item_store(query)
            
            filtered_df = self.dataframe.copy()
            context_info = []
            
            # Filter dataframe based on context
            if item_num is not None and 'Item' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['Item'] == item_num]
                context_info.append(f"Item {item_num}")
            
            if store_num is not None and 'Store' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['Store'] == store_num]
                context_info.append(f"Store {store_num}")
            
            # Update tool's dataframe temporarily
            original_df = self.tools["trend_plot_tool"].dataframe
            self.tools["trend_plot_tool"].dataframe = filtered_df
            
            result = self.tools["trend_plot_tool"]._run()
            
            # Restore original dataframe
            self.tools["trend_plot_tool"].dataframe = original_df
            
            # Add context information to result
            if result and not result.get('error') and context_info:
                result['description'] = f"Sales trend for {' - '.join(context_info)}"
            
            return result
            
        except Exception as e:
            return {"error": str(e)}

    def _execute_inventory_status(self, query: str) -> Any:
        """Execute inventory status check with context awareness."""
        try:
            item, store = self._extract_item_store(query)
            
            if item is not None and store is not None:
                return self.tools["inventory_status_tool"]._run(
                    item=item,
                    store=store
                )
            else:
                missing = []
                if item is None:
                    missing.append("item number")
                if store is None:
                    missing.append("store number")
                return {"error": f"Please specify {' and '.join(missing)} to check inventory status."}
                
        except Exception as e:
            return {"error": str(e)}
    
    def _generate_response(self, query: str, query_type: str, data_result: Any,
                          forecast_result: Any, viz_result: Any, 
                          inventory_result: Any = None, sql_used: bool = False) -> Dict[str, Any]:
        """Generate final response using LLM."""
        try:
            # Build context for LLM
            context = f"User Query: {query}\n\n"
            
            # Handle SQL query results specially
            if sql_used and data_result and isinstance(data_result, dict) and data_result.get('success'):
                context += "SQL Query Result:\n"
                context += f"Generated SQL: {data_result.get('sql', 'N/A')}\n"
                context += f"Rows returned: {data_result.get('row_count', 0)}\n\n"
                
                # Format the data
                if data_result.get('data'):
                    context += "Query Results:\n"
                    for row in data_result['data'][:10]:  # Limit to 10 rows for context
                        context += f"{row}\n"
                    
                    if data_result.get('row_count', 0) > 10:
                        context += f"\n... and {data_result['row_count'] - 10} more rows\n"
                    context += "\n"
            
            # Handle dataset information specially
            elif data_result and isinstance(data_result, dict) and "row_count" in data_result:
                context += "Dataset Information:\n"
                context += f"- Shape: {data_result.get('shape', 'N/A')}\n"
                context += f"- Total Records: {data_result.get('row_count', 'N/A')}\n"
                context += f"- Columns ({len(data_result.get('columns', []))}): {', '.join(data_result.get('columns', []))}\n\n"
                
                if "statistics" in data_result:
                    context += "Key Statistics:\n"
                    for col, stats in data_result['statistics'].items():
                        context += f"- {col}: min={stats['min']:.2f}, max={stats['max']:.2f}, mean={stats['mean']:.2f}\n"
                    context += "\n"
                
                if "sample_data" in data_result and len(data_result['sample_data']) > 0:
                    context += f"Sample Data (first 3 rows):\n{data_result['sample_data']}\n\n"
            
            elif data_result:
                if isinstance(data_result, dict) and "error" not in data_result:
                    context += f"Data Analysis Result: {data_result}\n\n"
                elif not isinstance(data_result, dict):
                    context += f"Data Result: {data_result}\n\n"
            
            if forecast_result and isinstance(forecast_result, dict) and "error" not in forecast_result:
                context += "Forecast Results:\n"
                if "model_used" in forecast_result:
                    context += f"Model Used: {forecast_result['model_used']}\n"
                if "forecast_values" in forecast_result and forecast_result['forecast_values']:
                    context += f"Number of predictions: {len(forecast_result['forecast_values'])}\n"
                    context += "Forecasted values:\n"
                    for i, pred in enumerate(forecast_result['forecast_values'][:10], 1):
                        date = pred.get('Date', f'Day {i}')
                        demand = pred.get('Forecasted_Demand', 'N/A')
                        context += f"  Day {i}: {demand} units\n"
                context += "\n"
            
            if viz_result and isinstance(viz_result, dict) and "error" not in viz_result:
                context += f"Visualization created successfully\n\n"
            
            if inventory_result and isinstance(inventory_result, dict) and "error" not in inventory_result:
                res = inventory_result.get('raw_data', {})
                context += (
                    "Inventory Status Check (Periodic Review):\n"
                    f"- Item: {res.get('item')}, Store: {res.get('store')}\n"
                    f"- Current On-Hand: {res.get('current_on_hand')}\n"
                    f"- Inventory Position (Ip): {res.get('inventory_position_Ip')}\n"
                    f"- Target Level (T): {res.get('target_level_T')}\n"
                    f"- Safety Stock (Ss): {res.get('safety_stock_Ss')}\n"
                    f"- Order Quantity (Q): {res.get('calculated_order_quantity_Q')}\n"
                    f"- Should Order: {res.get('should_order')}\n"
                    f"- Summary: {inventory_result.get('summary')}\n\n"
                )
            
            # Add conversation history for context-aware responses
            if self.conversation_history:
                context += "Previous Conversation (for context):\n"
                for msg in self.conversation_history[-3:]:  # Last 3 exchanges
                    context += f"User: {msg['query']}\n"
                    context += f"Assistant: {msg['response'][:200]}...\n\n"  # Truncate long responses
            
            # Generate natural language response
            prompt = f"""{context}

Based on the above information about the user's uploaded inventory dataset, generate a clear, concise, and helpful response.

FORMATTING GUIDELINES:

1. **For Data / SQL Queries**:
   - If a SQL Query Result is provided, explicitly state the direct answer to the user's question first (e.g., "The total sales are X", "There are Y rows").
   - Do NOT wrap data answers in an "Inventory Analysis" or "Periodic Review" format. Just answer the specific question asked.

2. **For Inventory Status (Periodic Review)** (ONLY if Inventory Status Check is provided):
   - Use a clear header like **Inventory Analysis**
   - Use emojis to indicate status: 🟢 (Healthy), ⚠️ (Low Stock), 🔴 (Order Required)
   - Explicitly state: **Current Stock: X** vs **Target Stock (T): Y**
   - Show: **Safety Stock (Ss): Z** and **Order Quantity (Q): W**
   - Provide a clear recommendation: **Action: [Place Order for Q units / No Action Needed]**

3. **For Forecast Queries**:
   - State the model used (e.g., "Forecast generated using LightGBM")
   - Summarize the trend (increasing, decreasing, stable)
   - Use a bullet list for key insights

4. **General Rules**:
   - **Conciseness**: Get straight to the point.
   - **Tone**: Professional and confident.
"""
            
            messages = [{"role": "user", "content": prompt}]
            llm_response = self.llm.invoke(messages)
            
            # Build final response dict
            response = {
                "response": llm_response.content,
                "session_id": self.session_id
            }
            
            # Add forecast data if available
            if forecast_result and isinstance(forecast_result, dict):
                if "forecast_values" in forecast_result:
                    response["forecast_values"] = forecast_result["forecast_values"]
                if "chart_base64" in forecast_result:
                    response["chart_b64"] = forecast_result["chart_base64"]
            
            # Add visualization if available
            if viz_result and isinstance(viz_result, dict):
                if "chart_base64" in viz_result:
                    response["chart_b64"] = viz_result["chart_base64"]
            
            return response
            
        except Exception as e:
            return {
                "response": f"Generated results but couldn't format response: {str(e)}",
                "session_id": self.session_id
            }


