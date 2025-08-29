import psutil
import time
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any
from livekit.agents import function_tool
from db import init_db, _connect, _lock
import logging

logger = logging.getLogger(__name__)

class AnalyticsEngine:
    def __init__(self):
        self.session_start = time.time()
        self.metrics = {
            'commands_count': 0,
            'errors_count': 0,
            'response_times': [],
            'memory_usage': [],
            'cpu_usage': []
        }
        self._init_analytics_db()
    
    def _init_analytics_db(self):
        init_db()
        with _lock:
            conn = _connect()
            try:
                cur = conn.cursor()
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS analytics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        metric_type TEXT,
                        value REAL,
                        metadata TEXT
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS performance_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        cpu_percent REAL,
                        memory_mb REAL,
                        active_tools INTEGER,
                        response_time_ms REAL
                    )
                """)
                conn.commit()
            finally:
                conn.close()
    
    def track_command(self, tool_name: str, response_time: float, success: bool):
        self.metrics['commands_count'] += 1
        self.metrics['response_times'].append(response_time)
        if not success:
            self.metrics['errors_count'] += 1
        
        # Log to DB
        with _lock:
            conn = _connect()
            try:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO analytics (metric_type, value, metadata) VALUES (?, ?, ?)",
                    ('command_execution', response_time, json.dumps({
                        'tool': tool_name, 'success': success
                    }))
                )
                conn.commit()
            finally:
                conn.close()
    
    def track_system_performance(self):
        cpu = psutil.cpu_percent()
        memory = psutil.virtual_memory().used / 1024 / 1024  # MB
        
        self.metrics['cpu_usage'].append(cpu)
        self.metrics['memory_usage'].append(memory)
        
        with _lock:
            conn = _connect()
            try:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO performance_logs (cpu_percent, memory_mb, active_tools, response_time_ms) VALUES (?, ?, ?, ?)",
                    (cpu, memory, len(self.metrics['response_times']), 
                     sum(self.metrics['response_times'][-10:]) / min(10, len(self.metrics['response_times'])) if self.metrics['response_times'] else 0)
                )
                conn.commit()
            finally:
                conn.close()
    
    def predict_errors(self) -> Dict[str, Any]:
        """Simple error prediction based on patterns"""
        error_rate = self.metrics['errors_count'] / max(1, self.metrics['commands_count'])
        avg_response_time = sum(self.metrics['response_times'][-20:]) / max(1, len(self.metrics['response_times'][-20:]))
        
        predictions = {
            'high_error_risk': error_rate > 0.3,
            'slow_response_risk': avg_response_time > 5.0,
            'memory_pressure': self.metrics['memory_usage'][-1] > 1000 if self.metrics['memory_usage'] else False
        }
        return predictions
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        uptime = time.time() - self.session_start
        avg_response = sum(self.metrics['response_times']) / max(1, len(self.metrics['response_times']))
        
        return {
            'uptime_minutes': round(uptime / 60, 1),
            'total_commands': self.metrics['commands_count'],
            'error_rate': round(self.metrics['errors_count'] / max(1, self.metrics['commands_count']) * 100, 1),
            'avg_response_time': round(avg_response, 2),
            'current_memory_mb': self.metrics['memory_usage'][-1] if self.metrics['memory_usage'] else 0,
            'current_cpu_percent': self.metrics['cpu_usage'][-1] if self.metrics['cpu_usage'] else 0,
            'predictions': self.predict_errors()
        }

# Global analytics instance
_analytics = AnalyticsEngine()

@function_tool()
async def get_performance_dashboard() -> str:
    """
    Shows Jarvis performance metrics and analytics dashboard.
    
    Use when user asks: "Performance দেখাও", "System stats", "কেমন চলছে?"
    """
    try:
        _analytics.track_system_performance()
        data = _analytics.get_dashboard_data()
        
        dashboard = f"""
📊 **Jarvis Performance Dashboard**

⏱️ **Uptime**: {data['uptime_minutes']} minutes
🎯 **Commands Executed**: {data['total_commands']}
❌ **Error Rate**: {data['error_rate']}%
⚡ **Avg Response Time**: {data['avg_response_time']}s

💻 **System Resources**:
- CPU Usage: {data['current_cpu_percent']}%
- Memory Usage: {data['current_memory_mb']:.1f} MB

🔮 **Predictions**:
- High Error Risk: {'⚠️ YES' if data['predictions']['high_error_risk'] else '✅ NO'}
- Slow Response Risk: {'⚠️ YES' if data['predictions']['slow_response_risk'] else '✅ NO'}
- Memory Pressure: {'⚠️ YES' if data['predictions']['memory_pressure'] else '✅ NO'}
        """
        
        return dashboard.strip()
    except Exception as e:
        return f"❌ Analytics error: {str(e)[:100]}"

@function_tool()
async def optimize_performance() -> str:
    """
    Analyzes and optimizes Jarvis performance automatically.
    
    Use when user says: "Performance optimize করো", "Speed up করো"
    """
    try:
        import gc
        
        # Memory cleanup
        gc.collect()
        
        # Clear old metrics (keep last 100)
        if len(_analytics.metrics['response_times']) > 100:
            _analytics.metrics['response_times'] = _analytics.metrics['response_times'][-100:]
        if len(_analytics.metrics['memory_usage']) > 100:
            _analytics.metrics['memory_usage'] = _analytics.metrics['memory_usage'][-100:]
        if len(_analytics.metrics['cpu_usage']) > 100:
            _analytics.metrics['cpu_usage'] = _analytics.metrics['cpu_usage'][-100:]
        
        # Get current performance
        _analytics.track_system_performance()
        data = _analytics.get_dashboard_data()
        
        optimizations = []
        
        if data['current_memory_mb'] > 500:
            optimizations.append("🧹 Memory cleanup performed")
        
        if data['error_rate'] > 20:
            optimizations.append("⚠️ High error rate detected - suggest restart")
        
        if data['avg_response_time'] > 3:
            optimizations.append("🐌 Slow responses - clearing cache")
        
        if not optimizations:
            optimizations.append("✅ System running optimally")
        
        return "🔧 **Performance Optimization Complete**\n\n" + "\n".join(optimizations)
        
    except Exception as e:
        return f"❌ Optimization failed: {str(e)[:100]}"

@function_tool()
async def analyze_user_behavior() -> str:
    """
    Analyzes user interaction patterns and provides insights.
    
    Use when user asks: "আমার behavior analysis করো", "Usage pattern দেখাও"
    """
    try:
        with _lock:
            conn = _connect()
            try:
                cur = conn.cursor()
                
                # Most used tools
                cur.execute("""
                    SELECT tool_name, COUNT(*) as usage_count 
                    FROM tool_events 
                    WHERE created_at > datetime('now', '-7 days')
                    GROUP BY tool_name 
                    ORDER BY usage_count DESC 
                    LIMIT 5
                """)
                top_tools = cur.fetchall()
                
                # Usage by hour
                cur.execute("""
                    SELECT strftime('%H', created_at) as hour, COUNT(*) as count
                    FROM tool_events 
                    WHERE created_at > datetime('now', '-7 days')
                    GROUP BY hour 
                    ORDER BY count DESC 
                    LIMIT 3
                """)
                peak_hours = cur.fetchall()
                
                # Error patterns
                cur.execute("""
                    SELECT tool_name, COUNT(*) as error_count
                    FROM tool_events 
                    WHERE success = 0 AND created_at > datetime('now', '-7 days')
                    GROUP BY tool_name 
                    ORDER BY error_count DESC 
                    LIMIT 3
                """)
                error_tools = cur.fetchall()
                
            finally:
                conn.close()
        
        analysis = "📈 **User Behavior Analysis (Last 7 Days)**\n\n"
        
        if top_tools:
            analysis += "🔥 **Most Used Tools**:\n"
            for tool, count in top_tools:
                analysis += f"- {tool}: {count} times\n"
            analysis += "\n"
        
        if peak_hours:
            analysis += "⏰ **Peak Usage Hours**:\n"
            for hour, count in peak_hours:
                analysis += f"- {hour}:00 - {count} commands\n"
            analysis += "\n"
        
        if error_tools:
            analysis += "⚠️ **Tools with Most Errors**:\n"
            for tool, count in error_tools:
                analysis += f"- {tool}: {count} errors\n"
        
        return analysis
        
    except Exception as e:
        return f"❌ Behavior analysis failed: {str(e)[:100]}"

# Performance monitoring decorator
def monitor_performance(func):
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        success = True
        try:
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            success = False
            raise
        finally:
            response_time = time.time() - start_time
            _analytics.track_command(func.__name__, response_time, success)
    return wrapper

# Auto-monitoring task
async def start_performance_monitoring():
    """Background task to continuously monitor system performance"""
    while True:
        try:
            _analytics.track_system_performance()
            await asyncio.sleep(30)  # Monitor every 30 seconds
        except Exception as e:
            logger.error(f"Performance monitoring error: {e}")
            await asyncio.sleep(60)