import asyncio
import logging
import os
import json
import aiosqlite
from pathlib import Path
from typing import Optional, Dict, List
from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global MCP instance
mcp = FastMCP("bi-assistant")

class BIAssistantServer:
    def __init__(self):
        self.db: Optional[aiosqlite.Connection] = None
        self.db_path = self._get_db_path()
        self._setup_tools()
        self._setup_resources()
    
    def _get_db_path(self) -> str:
        """Get database path from environment or use default"""
        # Use current directory (where server is run from) as default
        script_dir = Path(__file__).parent
        default_db = str(script_dir / "bi_assistant.db")
        db_url = os.getenv('DATABASE_URL', f'sqlite:///{default_db}')
        # Remove sqlite:// prefix if present
        return db_url.replace("sqlite:///", "").replace("sqlite://", "")
    
    async def _init_db(self):
        """Initialize SQLite connection if not already connected"""
        if not self.db:
            try:
                self.db = await aiosqlite.connect(self.db_path)
                self.db.row_factory = aiosqlite.Row
                logger.info(f"Connected to SQLite database: {self.db_path}")
            except Exception as e:
                logger.error(f"Failed to connect to database: {e}")
                raise

    def _setup_tools(self):
        """Register MCP tools for BI analysis"""
        
        @mcp.tool()
        async def get_schema() -> Dict:
            """Get database schema with table structures and sample data"""
            try:
                await self._init_db()
                schema_info = {}
                
                # Get all tables except system tables
                async with self.db.execute("SELECT name FROM sqlite_master WHERE type='table'") as cursor:
                    tables = await cursor.fetchall()
                
                for table in tables:
                    table_name = table["name"]
                    if table_name.startswith("sqlite_"):
                        continue
                    
                    schema_info[table_name] = {"columns": [], "sample_data": None}

                    # Get column information
                    async with self.db.execute(f"PRAGMA table_info({table_name})") as cursor:
                        columns = await cursor.fetchall()
                        for col in columns:
                            schema_info[table_name]["columns"].append({
                                "name": col[1],
                                "type": col[2],
                                "nullable": not col[3],
                                "default": col[4]
                            })

                    # Get sample data
                    try:
                        async with self.db.execute(f"SELECT * FROM {table_name} LIMIT 3") as cursor:
                            rows = await cursor.fetchall()
                            schema_info[table_name]["sample_data"] = [dict(row) for row in rows]
                    except Exception as e:
                        logger.warning(f"Could not fetch sample data for {table_name}: {e}")

                return {
                    "tables": schema_info,
                    "views": {
                        "campaign_performance": "Comprehensive view with calculated marketing metrics"
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

            except Exception as e:
                logger.error(f"Error getting schema: {e}")
                return {"error": f"Schema retrieval failed: {str(e)}"}

        @mcp.tool()
        async def run_sql(query: str) -> Dict:
            """Execute SELECT SQL queries against the database"""
            if not query.strip():
                return {"error": "Empty query provided"}
            
            # Security check - only allow SELECT queries
            query_upper = query.strip().upper()
            if not (query_upper.startswith("SELECT") or query_upper.startswith("WITH")):
                return {"error": "Only SELECT and WITH queries are allowed"}
            
            try:
                await self._init_db()
                async with self.db.execute(query) as cursor:
                    rows = await cursor.fetchall()
                    result = [dict(row) for row in rows]
                
                return {"data": result, "row_count": len(result)}
            
            except Exception as e:
                logger.error(f"SQL execution error: {e}")
                return {"error": f"SQL Error: {str(e)}"}

        @mcp.tool()
        async def get_campaign_metrics(product: str = "", month: int = None, year: int = 2024) -> Dict:
            """Get campaign performance metrics with optional filtering"""
            try:
                await self._init_db()
                
                conditions = ["year = ?"]
                params = [year]
                
                if product:
                    conditions.append("LOWER(product_name) = LOWER(?)")
                    params.append(product)
                
                if month:
                    conditions.append("month_number = ?")
                    params.append(month)
                
                where_clause = " AND ".join(conditions)
                query = f"""
                SELECT * FROM campaign_performance 
                WHERE {where_clause} 
                ORDER BY product_name, month_number
                """
                
                async with self.db.execute(query, params) as cursor:
                    rows = await cursor.fetchall()
                    result = [dict(row) for row in rows]
                
                return {"data": result, "row_count": len(result)}
            
            except Exception as e:
                logger.error(f"Error getting campaign metrics: {e}")
                return {"error": str(e)}

        @mcp.tool()
        async def calculate_metric(product: str, month: int, metric: str, year: int = 2024) -> Dict:
            """Calculate a specific metric for a product/month combination"""
            if not all([product, month, metric]):
                return {"error": "product, month, and metric are required"}
            
            # Validate metric name
            valid_metrics = ["roas", "roi", "ctr_percentage", "cpa", "cpc", "cpm"]
            if metric.lower() not in valid_metrics:
                return {"error": f"Invalid metric. Valid options: {', '.join(valid_metrics)}"}
            
            try:
                await self._init_db()
                
                query = f"""
                SELECT product_name, month_number, year, campaign_name,
                       impressions, clicks, conversions, revenue, actual_spend, {metric}
                FROM campaign_performance
                WHERE LOWER(product_name) = LOWER(?) AND month_number = ? AND year = ?
                """
                
                async with self.db.execute(query, (product, month, year)) as cursor:
                    row = await cursor.fetchone()
                
                if not row:
                    return {"error": f"No data found for {product} month {month}/{year}"}
                
                return dict(row)
            
            except Exception as e:
                logger.error(f"Error calculating metric: {e}")
                return {"error": f"Metric calculation failed: {str(e)}"}

    def _setup_resources(self):
        """Setup MCP resources for documentation"""
        
        @mcp.resource("bi://schema")
        def schema_resource() -> str:
            """Database schema documentation"""
            return json.dumps({
                "description": "BI database contains marketing campaign performance data",
                "tables": ["products", "campaign_months", "marketing_metrics", "budgets"],
                "main_view": "campaign_performance",
                "purpose": "Track and analyze marketing campaign effectiveness"
            }, indent=2)

        @mcp.resource("bi://examples")
        def examples_resource() -> str:
            """Query examples for the BI database"""
            return """
# BI Assistant Query Examples

## Basic Operations
- get_schema() - View database structure
- get_campaign_metrics("Product A", 3, 2024) - Get specific campaign data
- calculate_metric("Product A", 5, "roas", 2024) - Calculate ROAS for Product A, Month 5

## SQL Queries
- run_sql("SELECT * FROM campaign_performance LIMIT 5")
- run_sql("SELECT product_name, AVG(roas) FROM campaign_performance GROUP BY product_name")
- run_sql("SELECT * FROM campaign_performance WHERE roas > 2.0 ORDER BY roas DESC")

## Available Metrics
- ROAS (Return on Ad Spend)
- ROI (Return on Investment)  
- CTR (Click-Through Rate)
- CPA (Cost Per Acquisition)
- CPC (Cost Per Click)
- CPM (Cost Per Mille)
            """.strip()

        @mcp.resource("bi://metrics")
        def metrics_resource() -> str:
            """Metrics definitions and formulas"""
            return """
# Marketing Metrics Definitions

## Performance Metrics
- **ROAS**: Revenue / Actual Spend
- **ROI**: (Revenue - Actual Spend) / Actual Spend
- **CTR**: (Clicks / Impressions) × 100

## Cost Metrics  
- **CPA**: Actual Spend / Conversions
- **CPC**: Actual Spend / Clicks
- **CPM**: (Actual Spend / Impressions) × 1000

## Usage
All metrics are pre-calculated in the campaign_performance view.
Use calculate_metric() for specific calculations or run_sql() for custom queries.
            """.strip()

    def run(self):
        """Start the MCP server"""
        logger.info("🚀 Starting BI Assistant MCP Server")
        logger.info(f"📊 Database: {self.db_path}")
        logger.info("🔧 Available tools: get_schema, run_sql, get_campaign_metrics, calculate_metric")
        logger.info("📚 Available resources: bi://schema, bi://examples, bi://metrics")
        
        mcp.run()

def main():
    """Main entry point"""
    server = BIAssistantServer()
    server.run()

if __name__ == "__main__":
    main()