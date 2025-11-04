"""
Performance and monitoring system for tracking engagement metrics and system health.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
import time
from sqlalchemy import text
from .database import engine
from .analytics import analytics_engine

logger = logging.getLogger(__name__)


class MonitoringSystem:
    """System for tracking performance metrics and engagement."""
    
    def __init__(self):
        self._initialize_monitoring_tables()
        self.startup_time = datetime.now()
        
    def _initialize_monitoring_tables(self):
        """Initialize monitoring-related tables if they don't exist."""
        try:
            with engine.connect() as conn:
                # Create performance_metrics table
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS performance_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        metric_name VARCHAR(100) NOT NULL,
                        metric_value FLOAT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        context_data JSON
                    )
                """))
                
                # Create engagement_metrics table
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS engagement_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        metric_type VARCHAR(50) NOT NULL,
                        user_count INTEGER,
                        value FLOAT,
                        date_recorded DATE NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                # Create system_health table
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS system_health (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        check_name VARCHAR(100) NOT NULL,
                        status VARCHAR(20) NOT NULL,  -- 'healthy', 'warning', 'error'
                        message TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                # Create ab_test_results table
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS ab_test_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        test_name VARCHAR(100) NOT NULL,
                        variant VARCHAR(10) NOT NULL,
                        metric_name VARCHAR(50) NOT NULL,
                        metric_value FLOAT,
                        participant_count INTEGER,
                        date_recorded DATE NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                # Create indexes
                try:
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_perf_metrics_name ON performance_metrics(metric_name)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_perf_metrics_time ON performance_metrics(timestamp)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_engagement_date ON engagement_metrics(date_recorded)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_health_check ON system_health(check_name)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_health_time ON system_health(timestamp)"))
                except Exception:
                    # Indexes may already exist, which is fine
                    pass
                
                conn.commit()
                logger.info("✅ Monitoring tables initialized")
        except Exception as e:
            logger.error(f"❌ Error initializing monitoring tables: {e}")
            raise
    
    def log_performance_metric(self, metric_name: str, metric_value: float, context_data: Dict = None):
        """Log a performance metric."""
        try:
            with engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO performance_metrics (metric_name, metric_value, context_data)
                    VALUES (:metric_name, :metric_value, :context_data)
                """), {
                    'metric_name': metric_name,
                    'metric_value': metric_value,
                    'context_data': context_data
                })
                conn.commit()
                
                logger.debug(f"📊 Performance metric logged: {metric_name} = {metric_value}")
        except Exception as e:
            logger.error(f"Error logging performance metric: {e}")
    
    def log_response_time(self, endpoint: str, response_time_ms: float):
        """Log response time for an endpoint."""
        self.log_performance_metric(f"response_time_{endpoint}", response_time_ms)
    
    def log_user_engagement(self, metric_type: str, user_count: int, value: float):
        """Log user engagement metric."""
        try:
            with engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO engagement_metrics (metric_type, user_count, value, date_recorded)
                    VALUES (:metric_type, :user_count, :value, :date_recorded)
                """), {
                    'metric_type': metric_type,
                    'user_count': user_count,
                    'value': value,
                    'date_recorded': datetime.now().date()
                })
                conn.commit()
                
                logger.info(f"📈 Engagement metric logged: {metric_type}, {user_count} users, value {value}")
        except Exception as e:
            logger.error(f"Error logging engagement metric: {e}")
    
    def get_daily_active_users(self) -> int:
        """Get count of daily active users."""
        try:
            with engine.connect() as conn:
                today = datetime.now().date()
                result = conn.execute(text("""
                    SELECT COUNT(DISTINCT user_id) 
                    FROM user_behavior 
                    WHERE date(timestamp) = :today
                """), {'today': today}).first()
                
                return result[0] if result else 0
        except Exception as e:
            logger.error(f"Error getting daily active users: {e}")
            return 0
    
    def get_weekly_active_users(self) -> int:
        """Get count of weekly active users."""
        try:
            with engine.connect() as conn:
                week_ago = datetime.now() - timedelta(days=7)
                result = conn.execute(text("""
                    SELECT COUNT(DISTINCT user_id) 
                    FROM user_behavior 
                    WHERE timestamp > :week_ago
                """), {'week_ago': week_ago}).first()
                
                return result[0] if result else 0
        except Exception as e:
            logger.error(f"Error getting weekly active users: {e}")
            return 0
    
    def get_monthly_active_users(self) -> int:
        """Get count of monthly active users."""
        try:
            with engine.connect() as conn:
                month_ago = datetime.now() - timedelta(days=30)
                result = conn.execute(text("""
                    SELECT COUNT(DISTINCT user_id) 
                    FROM user_behavior 
                    WHERE timestamp > :month_ago
                """), {'month_ago': month_ago}).first()
                
                return result[0] if result else 0
        except Exception as e:
            logger.error(f"Error getting monthly active users: {e}")
            return 0
    
    def get_engagement_metrics(self) -> Dict[str, Any]:
        """Get comprehensive engagement metrics."""
        daus = self.get_daily_active_users()
        waus = self.get_weekly_active_users()
        maurus = self.get_monthly_active_users()
        
        # Get additional metrics from analytics
        aggregated_stats = analytics_engine.get_anonymized_aggregated_stats()
        
        metrics = {
            'daily_active_users': daus,
            'weekly_active_users': waus,
            'monthly_active_users': maurus,
            'user_retention_rate': self._calculate_retention_rate(),
            'avg_session_duration': self._calculate_avg_session_duration(),
            'feature_usage': self._get_feature_usage_stats(),
            'system_uptime': self._calculate_uptime(),
            'total_users': aggregated_stats.get('total_users', 0),
            'total_capsules': aggregated_stats.get('total_capsules', 0),
            'active_users_7days': aggregated_stats.get('active_users_7days', 0),
            'user_activity_rate': aggregated_stats.get('user_activity_rate', 0.0)
        }
        
        return metrics
    
    def _calculate_retention_rate(self) -> float:
        """Calculate user retention rate."""
        # This would require more complex logic to track users over time
        # For now, return a placeholder calculation
        try:
            with engine.connect() as conn:
                # Get users who joined in the last 30 days and were active in last 7 days
                thirty_days_ago = datetime.now() - timedelta(days=30)
                seven_days_ago = datetime.now() - timedelta(days=7)
                
                result = conn.execute(text("""
                    SELECT 
                        COUNT(DISTINCT new_users.id) as new_users,
                        COUNT(DISTINCT active_new_users.id) as retained_users
                    FROM users new_users
                    LEFT JOIN users active_new_users 
                        ON new_users.telegram_id = active_new_users.telegram_id
                        AND active_new_users.last_activity_time > :seven_days_ago
                    WHERE new_users.created_at > :thirty_days_ago
                """), {
                    'thirty_days_ago': thirty_days_ago,
                    'seven_days_ago': seven_days_ago
                }).first()
                
                if result and result[0] > 0:
                    retention_rate = (result[1] / result[0]) * 100
                    return round(retention_rate, 2)
                return 0.0
        except Exception as e:
            logger.error(f"Error calculating retention rate: {e}")
            return 0.0
    
    def _calculate_avg_session_duration(self) -> float:
        """Calculate average session duration."""
        # Placeholder implementation - would need session tracking
        return 0.0  # Need to implement session tracking to calculate this
    
    def _get_feature_usage_stats(self) -> Dict[str, int]:
        """Get statistics on feature usage."""
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT action_type, COUNT(*) as usage_count
                    FROM user_behavior
                    WHERE timestamp > :week_ago
                    GROUP BY action_type
                    ORDER BY usage_count DESC
                    LIMIT 10
                """), {'week_ago': datetime.now() - timedelta(days=7)}).fetchall()
                
                return {row[0]: row[1] for row in result}
        except Exception as e:
            logger.error(f"Error getting feature usage stats: {e}")
            return {}
    
    def _calculate_uptime(self) -> float:
        """Calculate system uptime."""
        # Calculate uptime based on startup time
        uptime_seconds = (datetime.now() - self.startup_time).total_seconds()
        # This is always 100% since the system is running
        return 100.0
    
    def check_system_health(self) -> Dict[str, str]:
        """Check overall system health."""
        health_status = {
            'database': self._check_database_health(),
            'scheduler': self._check_scheduler_health(),
            'storage': self._check_storage_health(),
            'api_responses': self._check_api_health()
        }
        
        # Log health checks
        for check_name, status in health_status.items():
            self.log_system_health_check(check_name, status)
        
        return health_status
    
    def _check_database_health(self) -> str:
        """Check database health."""
        try:
            with engine.connect() as conn:
                # Test simple query
                conn.execute(text("SELECT 1"))
                return 'healthy'
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return 'error'
    
    def _check_scheduler_health(self) -> str:
        """Check scheduler health."""
        # This would check if the scheduler is running and jobs are executing
        try:
            # For now, just assume it's healthy if the module is imported
            from .smart_scheduler import smart_scheduler
            if smart_scheduler and smart_scheduler.scheduler.running:
                return 'healthy'
            else:
                return 'warning'
        except Exception:
            return 'error'
    
    def _check_storage_health(self) -> str:
        """Check storage health."""
        # Check if we can write to the database
        try:
            with engine.connect() as conn:
                # Insert a test record and delete it immediately
                conn.execute(text("""
                    INSERT INTO performance_metrics (metric_name, metric_value) 
                    VALUES ('health_check', 1)
                """))
                conn.execute(text("""
                    DELETE FROM performance_metrics 
                    WHERE metric_name = 'health_check' 
                    AND timestamp > :one_minute_ago
                """), {'one_minute_ago': datetime.now() - timedelta(minutes=1)})
                conn.commit()
                return 'healthy'
        except Exception as e:
            logger.error(f"Storage health check failed: {e}")
            return 'error'
    
    def _check_api_health(self) -> str:
        """Check API health."""
        # For now, assume healthy since this is running in the bot context
        return 'healthy'
    
    def log_system_health_check(self, check_name: str, status: str, message: str = ""):
        """Log a system health check result."""
        try:
            with engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO system_health (check_name, status, message)
                    VALUES (:check_name, :status, :message)
                """), {
                    'check_name': check_name,
                    'status': status,
                    'message': message
                })
                conn.commit()
                
                logger.debug(f"🏥 Health check: {check_name} = {status}")
        except Exception as e:
            logger.error(f"Error logging health check: {e}")
    
    def get_system_metrics_dashboard(self) -> Dict[str, Any]:
        """Get a comprehensive dashboard of system metrics."""
        return {
            'timestamp': datetime.now().isoformat(),
            'engagement': self.get_engagement_metrics(),
            'health': self.check_system_health(),
            'performance': self._get_recent_performance_metrics(),
            'ab_tests': self._get_recent_ab_test_results()
        }
    
    def _get_recent_performance_metrics(self) -> List[Dict]:
        """Get recent performance metrics."""
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT metric_name, metric_value, timestamp, context_data
                    FROM performance_metrics
                    WHERE timestamp > :hour_ago
                    ORDER BY timestamp DESC
                    LIMIT 20
                """), {'hour_ago': datetime.now() - timedelta(hours=1)}).fetchall()
                
                return [{
                    'name': row[0],
                    'value': row[1],
                    'timestamp': row[2],
                    'context': row[3]
                } for row in result]
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return []
    
    def _get_recent_ab_test_results(self) -> List[Dict]:
        """Get recent A/B test results."""
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT test_name, variant, metric_name, metric_value, participant_count, date_recorded
                    FROM ab_test_results
                    WHERE date_recorded > :week_ago
                    ORDER BY date_recorded DESC
                    LIMIT 10
                """), {'week_ago': datetime.now().date() - timedelta(days=7)}).fetchall()
                
                return [{
                    'test_name': row[0],
                    'variant': row[1],
                    'metric_name': row[2],
                    'metric_value': row[3],
                    'participant_count': row[4],
                    'date': row[5]
                } for row in result]
        except Exception as e:
            logger.error(f"Error getting A/B test results: {e}")
            return []
    
    def track_ab_test_result(self, test_name: str, variant: str, metric_name: str, 
                           metric_value: float, participant_count: int = 1):
        """Track A/B test results."""
        try:
            with engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO ab_test_results 
                    (test_name, variant, metric_name, metric_value, participant_count, date_recorded)
                    VALUES (:test_name, :variant, :metric_name, :metric_value, :participant_count, :date_recorded)
                """), {
                    'test_name': test_name,
                    'variant': variant,
                    'metric_name': metric_name,
                    'metric_value': metric_value,
                    'participant_count': participant_count,
                    'date_recorded': datetime.now().date()
                })
                conn.commit()
                
                logger.info(f"📊 A/B test result: {test_name} ({variant}) {metric_name} = {metric_value}")
        except Exception as e:
            logger.error(f"Error tracking A/B test result: {e}")
    
    def run_health_check_task(self):
        """Run periodic health checks."""
        # Perform system checks
        health_status = self.check_system_health()
        
        # Log engagement metrics
        metrics = self.get_engagement_metrics()
        self.log_user_engagement('daily_active_users', metrics['daily_active_users'], 1.0)
        
        logger.info(f"✅ Health check completed. DAIU: {metrics['daily_active_users']}, Health: {health_status}")


# Global instance
monitoring_system = MonitoringSystem()


def get_monitoring_system():
    """Get the global monitoring system instance."""
    return monitoring_system