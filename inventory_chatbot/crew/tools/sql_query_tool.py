# inventory_chatbot/crew/tools/sql_query_tool.py
"""
Text-to-SQL tool for converting natural language to SQL queries.
Uses Groq LLM to generate SQL and executes on inventory dataset.
"""

import sqlite3
import pandas as pd
from typing import Dict, Any, Optional, Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from inventory_chatbot.config import settings


class SQLQueryToolInput(BaseModel):
    """Input schema for SQLQueryTool."""
    natural_query: str = Field(..., description="Natural language query to convert to SQL")


class SQLQueryTool(BaseTool):
    """
    Tool for converting natural language to SQL and executing queries.
    """
    
    name: str = "SQL Query Tool"
    description: str = (
        "Converts natural language queries to SQL and executes them on the inventory dataset. "
        "Use this for data retrieval, filtering, aggregations, and analysis queries. "
        "Returns structured query results."
    )
    args_schema: Type[BaseModel] = SQLQueryToolInput
    
    # Class attributes for shared state
    dataframe: Optional[pd.DataFrame] = None
    conn: Optional[sqlite3.Connection] = None
    schema_info: Optional[Dict[str, Any]] = None
    llm: Optional[ChatGroq] = None
    
    def _initialize_database(self):
        """Initialize SQLite in-memory database from DataFrame."""
        if self.conn is None and self.dataframe is not None:
            # Create in-memory SQLite database
            self.conn = sqlite3.connect(':memory:', check_same_thread=False)
            
            # Load DataFrame into SQLite
            self.dataframe.to_sql('inventory', self.conn, index=False, if_exists='replace')
            
            # Store schema information
            self.schema_info = {
                'table_name': 'inventory',
                'columns': list(self.dataframe.columns),
                'dtypes': {col: str(dtype) for col, dtype in self.dataframe.dtypes.items()},
                'row_count': len(self.dataframe),
                'sample_values': {}
            }
            
            # Get sample values for each column
            for col in self.dataframe.columns:
                unique_vals = self.dataframe[col].unique()[:5].tolist()
                self.schema_info['sample_values'][col] = unique_vals
    
    def _initialize_llm(self):
        """Initialize Groq LLM if not already initialized."""
        if self.llm is None:
            self.llm = ChatGroq(
                api_key=settings.GROQ_API_KEY,
                model_name=settings.GROQ_MODEL,
                temperature=0.1,  # Low temperature for precise SQL generation
                max_tokens=500
            )

    def set_llm(self, llm: ChatGroq):
        """Inject an external LLM instance."""
        self.llm = llm
    
    def _generate_sql(self, natural_query: str) -> str:
        """
        Generate SQL query from natural language using LLM.
        
        Args:
            natural_query: User's natural language query
            
        Returns:
            Generated SQL query string
        """
        self._initialize_llm()
        
        # Build schema description
        schema_desc = f"""Table: {self.schema_info['table_name']}
Columns: {', '.join(self.schema_info['columns'])}

Column Details:
"""
        for col, dtype in self.schema_info['dtypes'].items():
            sample_vals = self.schema_info['sample_values'].get(col, [])
            schema_desc += f"- {col} ({dtype}): Sample values: {sample_vals}\n"
        
        prompt = f"""You are a SQL expert. Convert the natural language query to a valid SQLite query.

DATABASE SCHEMA:
{schema_desc}

RULES:
1. Use ONLY SELECT statements (no INSERT, UPDATE, DELETE, DROP)
2. Use the exact column names from the schema
3. Return ONLY the SQL query, no explanations or markdown formatting
4. Use proper SQLite syntax
5. COLUMN MAPPING RULES:
   - If asked for "sales" or "total sales", always aggregate the `Daily_Sales` column (e.g., SUM(Daily_Sales)). DO NOT sum Quantity.
   - If asked for "demand", aggregate the `Demand` column.
   - If asked for "quantity", aggregate the `Quantity` column.
   - ALWAYS use explicit ALIASES for aggregated columns (e.g., `SELECT SUM(Daily_Sales) AS total_sales`).
6. FILTERING INFERENCE:
   - If a query mentions specific IDs like "item 1", "store 2", ensure you include `WHERE Item = 1 AND Store = 2`.
   - IMPORTANT: If a query asks for "across all stores" or "for all items", DO NOT include filters for specific stores or items even if they were mentioned in previous conversation context.
7. AGGREGATION ALIGNMENT:
   - For aggregations (SUM, AVG, MIN, MAX), ensure proper GROUP BY clauses for any non-aggregated selected columns.
8. COUNTING:
   - "How many stores" -> SELECT COUNT(DISTINCT Store) AS store_count FROM inventory
   - "How many items" -> SELECT COUNT(DISTINCT Item) AS item_count FROM inventory
   - "How many rows" or "How many records" -> SELECT COUNT(*) AS record_count FROM inventory

EXAMPLES:
Query: "What is the total sum of daily sales for item 1 in store 1?"
SQL: SELECT SUM(Daily_Sales) AS total_sales FROM inventory WHERE Item = 1 AND Store = 1;

Query: "What is the average demand across all items?"
SQL: SELECT AVG(Demand) AS avg_demand FROM inventory;

Query: "How many different items does store 1 carry?"
SQL: SELECT COUNT(DISTINCT Item) AS item_count FROM inventory WHERE Store = 1;

Query: "What are the total sales for store 2?"
SQL: SELECT SUM(Daily_Sales) AS total_sales FROM inventory WHERE Store = 2;

Query: "Total sales for item 1 across all stores"
SQL: SELECT SUM(Daily_Sales) AS total_sales FROM inventory WHERE Item = 1;

USER QUERY: {natural_query}

SQL QUERY:"""
        
        messages = [{"role": "user", "content": prompt}]
        response = self.llm.invoke(messages)
        
        # Extract SQL from response
        sql = response.content.strip()
        
        # Remove markdown code blocks if present
        if sql.startswith('```'):
            sql = sql.split('```')[1]
            if sql.startswith('sql'):
                sql = sql[3:]
            sql = sql.strip()
        
        return sql
    
    def _validate_sql(self, sql: str) -> tuple[bool, str]:
        """
        Validate SQL query for safety.
        
        Args:
            sql: SQL query to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        sql_upper = sql.upper().strip()
        
        # Check for dangerous operations
        forbidden_keywords = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE', 'TRUNCATE']
        for keyword in forbidden_keywords:
            if keyword in sql_upper:
                return False, f"Forbidden operation: {keyword} is not allowed"
        
        # Must be a SELECT query
        if not sql_upper.startswith('SELECT'):
            return False, "Only SELECT queries are allowed"
        
        return True, ""
    
    def _execute_sql(self, sql: str) -> Dict[str, Any]:
        """
        Execute SQL query and return results.
        
        Args:
            sql: SQL query to execute
            
        Returns:
            Dictionary with results or error
        """
        try:
            # Execute query
            cursor = self.conn.cursor()
            cursor.execute(sql)
            
            # Get column names
            columns = [desc[0] for desc in cursor.description]
            
            # Fetch results
            rows = cursor.fetchall()
            
            # Convert to list of dicts
            results = []
            for row in rows:
                results.append(dict(zip(columns, row)))
            
            return {
                'success': True,
                'row_count': len(results),
                'columns': columns,
                'data': results,
                'sql': sql
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'sql': sql
            }
    
    def _run(self, natural_query: str) -> Dict[str, Any]:
        """
        Main execution method for the tool.
        
        Args:
            natural_query: User's natural language query
            
        Returns:
            Query results or error information
        """
        try:
            # Initialize database if needed
            self._initialize_database()
            
            # Generate SQL from natural language
            sql = self._generate_sql(natural_query)
            
            # Validate SQL
            is_valid, error_msg = self._validate_sql(sql)
            if not is_valid:
                return {
                    'success': False,
                    'error': f"Invalid SQL: {error_msg}",
                    'generated_sql': sql
                }
            
            # Execute SQL
            result = self._execute_sql(sql)
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': f"SQL tool error: {str(e)}"
            }
