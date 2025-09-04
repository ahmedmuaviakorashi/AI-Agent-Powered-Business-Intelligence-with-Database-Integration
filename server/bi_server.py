import asyncio
import logging
import os
from typing import Any, Dict, Optional, List
import json
import aiosqlite
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp import Context

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Create global MCP instance for CLI compatibility
mcp = FastMCP("bi-assistant")

class BIAssistantServer:
    def __init__(self):
        self.mcp = mcp  # Use the global instance
        self.db: Optional[aiosqlite.Connection] = None
        self.setup_tools()
        self.setup_resources()
    
    async def initialize_db(self):
        """Initialize SQLite connection"""
        try:
            database_url = os.getenv(
                'DATABASE_URL',
                'sqlite:///D:/Confiz/Project 8- AI Powered BI Bot/model/db/bi_assistant.db'
            )
            # Remove sqlite:/// prefix if present
            db_path = database_url.replace("sqlite:///", "")
            self.db = await aiosqlite.connect(db_path)
            self.db.row_factory = aiosqlite.Row
            logger.info(f"SQLite database connected: {db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize SQLite DB: {e}")
            raise

    def setup_tools(self):
        """Register MCP tools for BI analysis"""
        
        @self.mcp.tool()
        async def get_schema() -> dict:
            """
            Discover database schema for BI analysis.
            Returns table structures, relationships, and sample data.
            """
            try:
                if not self.db:
                    await self.initialize_db()
                
                schema_info = {}
                # Get table names
                async with self.db.execute("SELECT name FROM sqlite_master WHERE type='table'") as cursor:
                    tables = await cursor.fetchall()
                
                for t in tables:
                    table_name = t["name"]
                    if table_name.startswith("sqlite_"):  # Skip system tables
                        continue
                    schema_info[table_name] = {"columns": [], "sample_data": None}

                    # Get column info
                    async with self.db.execute(f"PRAGMA table_info({table_name})") as cur:
                        cols = await cur.fetchall()
                        for col in cols:
                            schema_info[table_name]["columns"].append({
                                "name": col[1],
                                "type": col[2],
                                "nullable": not col[3],
                                "default": col[4]
                            })

                    # Sample data
                    try:
                        async with self.db.execute(f"SELECT * FROM {table_name} LIMIT 3") as cur:
                            rows = await cur.fetchall()
                            schema_info[table_name]["sample_data"] = [dict(row) for row in rows]
                    except Exception as e:
                        logger.warning(f"Could not fetch sample data for {table_name}: {e}")

                result = {
                    "tables": schema_info,
                    "views": {
                        "campaign_performance": "Comprehensive view joining all tables with calculated metrics"
                    },
                    "key_metrics": {
                        "ROAS": "Return on Ad Spend (revenue / actual_spend)",
                        "ROI": "Return on Investment ((revenue - actual_spend) / actual_spend)",
                        "CTR": "Click-Through Rate (clicks / impressions * 100)",
                        "CPA": "Cost Per Acquisition (actual_spend / conversions)",
                        "CPC": "Cost Per Click (actual_spend / clicks)",
                        "CPM": "Cost Per Mille (actual_spend / impressions * 1000)"
                    }
                }
                return result

            except Exception as e:
                logger.error(f"Error getting schema: {e}")
                return {"error": f"Error retrieving schema: {str(e)}"}

        @self.mcp.tool()
        async def run_sql(query: str) -> dict:
            """Execute SQL query against SQLite DB. Only SELECT allowed."""
            query = query.strip()
            if not query:
                return {"error": "No query provided"}
            if not query.upper().startswith("SELECT") and not query.upper().startswith("WITH"):
                return {"error": "Only SELECT queries are allowed"}
            try:
                if not self.db:
                    await self.initialize_db()
                async with self.db.execute(query) as cur:
                    rows = await cur.fetchall()
                    result = [dict(row) for row in rows]
                return {"data": result, "row_count": len(result)}
            except Exception as e:
                logger.error(f"Error executing SQL: {e}")
                return {"error": f"SQL Error: {str(e)}"}

        @self.mcp.tool()
        async def compute_metric(product: str, month: int, metric: str, year: int = 2024) -> dict:
            """Compute a metric from campaign_performance view"""
            if not all([product, month, metric]):
                return {"error": "product, month, metric required"}
            try:
                if not self.db:
                    await self.initialize_db()
                query = f"""
                    SELECT product_name, month_number, year, campaign_name,
                           impressions, clicks, conversions, revenue, actual_spend, {metric}
                    FROM campaign_performance
                    WHERE LOWER(product_name) = LOWER(?) AND month_number = ? AND year = ?
                """
                async with self.db.execute(query, (product, month, year)) as cur:
                    row = await cur.fetchone()
                if not row:
                    return {"error": f"No data found for {product} {month}/{year}"}
                result = {k: row[k] for k in row.keys()}
                return result
            except Exception as e:
                logger.error(f"Error computing metric: {e}")
                return {"error": f"Error computing metric: {str(e)}"}

        @self.mcp.tool()
        async def aggregate_campaign(product: str = "", month: int = None, year: int = 2024) -> dict:
            """Aggregate campaign performance data"""
            try:
                if not self.db:
                    await self.initialize_db()
                conditions, params = [], []
                if product:
                    conditions.append("LOWER(product_name) = LOWER(?)")
                    params.append(product)
                if month:
                    conditions.append("month_number = ?")
                    params.append(month)
                conditions.append("year = ?")
                params.append(year)
                where = " AND ".join(conditions) if conditions else "1=1"
                query = f"SELECT * FROM campaign_performance WHERE {where} ORDER BY product_name, month_number"
                async with self.db.execute(query, tuple(params)) as cur:
                    rows = await cur.fetchall()
                result = [dict(r) for r in rows]
                return {"data": result, "row_count": len(result)}
            except Exception as e:
                logger.error(f"Error aggregating campaign: {e}")
                return {"error": str(e)}

    def setup_resources(self):
        """Resources (schema, examples, metrics docs)"""
        @self.mcp.resource("bi://schema")
        def get_schema_resource() -> str:
            """Database schema and structure"""
            schema = {
                "tables": ["products", "campaign_months", "marketing_metrics", "budgets", "campaign_performance"],
                "description": "BI database contains marketing campaign performance data"
            }
            return json.dumps(schema, indent=2)

        @self.mcp.resource("bi://examples") 
        def get_examples_resource() -> str:
            """Query examples for the BI database"""
            examples = """
# BI Assistant Query Examples

## Basic Queries
- `run_sql("SELECT * FROM campaign_performance LIMIT 5")`
- `get_schema()` - Get full database structure
- `aggregate_campaign("Product A", 3, 2024)` - Get March 2024 data for Product A

## Metrics Available
- ROAS, ROI, CTR, CPA, CPC, CPM
- Use compute_metric() for specific calculations

## Sample Queries
```sql
SELECT product_name, SUM(revenue) as total_revenue 
FROM campaign_performance 
WHERE year = 2024 
GROUP BY product_name;
```
            """
            return examples.strip()

        @self.mcp.resource("bi://metrics")
        def get_metrics_resource() -> str:
            """Metrics documentation"""
            metrics = """
# BI Metrics Documentation

## Key Performance Indicators

- **ROAS** (Return on Ad Spend): revenue / actual_spend
- **ROI** (Return on Investment): (revenue - actual_spend) / actual_spend  
- **CTR** (Click-Through Rate): clicks / impressions * 100
- **CPA** (Cost Per Acquisition): actual_spend / conversions
- **CPC** (Cost Per Click): actual_spend / clicks
- **CPM** (Cost Per Mille): actual_spend / impressions * 1000

## Usage
Use these metrics with the compute_metric() tool or in SQL queries.
            """
            return metrics.strip()

    def run(self):
        """Run the FastMCP server"""
        logger.info("Starting BI Assistant MCP Server...")
        logger.info("Server is ready and waiting for MCP client connections")
        logger.info("Available tools: get_schema, run_sql, compute_metric, aggregate_campaign")
        logger.info("Available resources: bi://schema, bi://examples, bi://metrics")
        
        # FastMCP's run() method handles the async event loop internally
        self.mcp.run()


def main():
    """Main entry point"""
    server = BIAssistantServer()
    server.run()


if __name__ == "__main__":
    main()