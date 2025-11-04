"""
Feature flag system with user-based controls and A/B testing framework.
"""

from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime
from .database import engine
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


class FeatureFlag(Enum):
    """Enumeration of all feature flags available in the system."""
    ENHANCED_ONBOARDING = "enhanced_onboarding"
    SMART_NOTIFICATIONS = "smart_notifications"
    CONTENT_SUGGESTIONS = "content_suggestions"
    GAMIFICATION = "gamification"
    DYNAMIC_TRANSLATIONS = "dynamic_translations"
    SMART_HELP = "smart_help"
    PREMIUM_UPSELL = "premium_upsell"
    ACHIEVEMENTS = "achievements"


class FeatureFlagManager:
    """Manages feature flags with user-based controls and A/B testing."""
    
    def __init__(self):
        self._initialize_flag_table()
        self._default_flags = {
            FeatureFlag.ENHANCED_ONBOARDING: True,
            FeatureFlag.SMART_NOTIFICATIONS: True,
            FeatureFlag.CONTENT_SUGGESTIONS: True,
            FeatureFlag.GAMIFICATION: True,
            FeatureFlag.DYNAMIC_TRANSLATIONS: False,
            FeatureFlag.SMART_HELP: True,  # Changed from False to True to enable smart help by default
            FeatureFlag.PREMIUM_UPSELL: True,
            FeatureFlag.ACHIEVEMENTS: True,
        }

    def _initialize_flag_table(self):
        """Initialize the feature flags table if it doesn't exist."""
        try:
            with engine.connect() as conn:
                # Create feature_flags table if it doesn't exist
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS feature_flags (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        flag_name VARCHAR(100) UNIQUE NOT NULL,
                        is_enabled BOOLEAN DEFAULT TRUE,
                        rollout_percentage INTEGER DEFAULT 100,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                # Create user_feature_flags table if it doesn't exist
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS user_feature_flags (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        flag_name VARCHAR(100) NOT NULL,
                        is_enabled BOOLEAN DEFAULT TRUE,
                        assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id)
                    )
                """))
                
                # Create indexes
                try:
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_feature_flags_name ON feature_flags(flag_name)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_user_feature_flags_user ON user_feature_flags(user_id)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_user_feature_flags_flag ON user_feature_flags(flag_name)"))
                except Exception as e:
                    # Index may already exist, which is fine
                    pass
                
                conn.commit()
                logger.info("✅ Feature flags tables initialized")
        except Exception as e:
            logger.error(f"❌ Error initializing feature flags tables: {e}")
            raise

    def set_feature_flag(self, flag: FeatureFlag, enabled: bool, rollout_percentage: int = 100):
        """Set a global feature flag with rollout percentage."""
        try:
            with engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO feature_flags (flag_name, is_enabled, rollout_percentage)
                    VALUES (:flag_name, :is_enabled, :rollout_percentage)
                    ON CONFLICT(flag_name) DO UPDATE SET 
                        is_enabled = :is_enabled,
                        rollout_percentage = :rollout_percentage,
                        updated_at = CURRENT_TIMESTAMP
                """), {
                    'flag_name': flag.value,
                    'is_enabled': enabled,
                    'rollout_percentage': rollout_percentage
                })
                conn.commit()
                logger.info(f"✅ Feature flag {flag.value} set to {enabled}, rollout: {rollout_percentage}%")
        except Exception as e:
            logger.error(f"❌ Error setting feature flag {flag.value}: {e}")

    def get_feature_flag(self, flag: FeatureFlag) -> Dict[str, Any]:
        """Get the configuration for a specific feature flag."""
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT is_enabled, rollout_percentage
                    FROM feature_flags
                    WHERE flag_name = :flag_name
                """), {'flag_name': flag.value}).first()

                if result:
                    return {
                        'is_enabled': result[0],
                        'rollout_percentage': result[1]
                    }
                else:
                    # Return default if not set
                    return {
                        'is_enabled': self._default_flags.get(flag, True),
                        'rollout_percentage': 100
                    }
        except Exception as e:
            logger.error(f"❌ Error getting feature flag {flag.value}: {e}")
            return {
                'is_enabled': self._default_flags.get(flag, True),
                'rollout_percentage': 100
            }

    def is_feature_enabled(self, flag: FeatureFlag, user_id: Optional[int] = None) -> bool:
        """
        Check if a feature is enabled for a specific user.
        If user_id is provided, applies user-specific logic including A/B testing.
        """
        flag_config = self.get_feature_flag(flag)
        
        if not flag_config['is_enabled']:
            return False

        # If no specific user, or rollout is 100%, return global setting
        if not user_id or flag_config['rollout_percentage'] == 100:
            return flag_config['is_enabled']

        # Apply rollout percentage based on user ID
        # Using user ID as deterministic input for consistent rollout
        user_rollout_percentage = user_id % 100
        return user_rollout_percentage < flag_config['rollout_percentage']

    def enable_for_user(self, user_id: int, flag: FeatureFlag, enabled: bool = True):
        """Enable or disable a feature flag for a specific user."""
        try:
            with engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO user_feature_flags (user_id, flag_name, is_enabled)
                    VALUES (:user_id, :flag_name, :is_enabled)
                    ON CONFLICT(user_id, flag_name) DO UPDATE SET 
                        is_enabled = :is_enabled,
                        assigned_at = CURRENT_TIMESTAMP
                """), {
                    'user_id': user_id,
                    'flag_name': flag.value,
                    'is_enabled': enabled
                })
                conn.commit()
                logger.info(f"✅ Feature {flag.value} set to {enabled} for user {user_id}")
        except Exception as e:
            logger.error(f"❌ Error setting user feature flag for user {user_id}: {e}")

    def is_feature_enabled_for_user(self, user_id: int, flag: FeatureFlag) -> bool:
        """Check if a feature is specifically enabled for a user, overriding global settings."""
        try:
            with engine.connect() as conn:
                # First, check if there's a user-specific setting
                result = conn.execute(text("""
                    SELECT is_enabled
                    FROM user_feature_flags
                    WHERE user_id = :user_id AND flag_name = :flag_name
                """), {
                    'user_id': user_id,
                    'flag_name': flag.value
                }).first()

                if result:
                    return result[0]
                
                # Otherwise, fall back to global flag with rollout percentage
                return self.is_feature_enabled(flag, user_id)
        except Exception as e:
            logger.error(f"❌ Error checking user feature flag for user {user_id}: {e}")
            return self.is_feature_enabled(flag, user_id)

    def get_ab_test_variant(self, user_id: int, experiment_name: str, variants: list = ['A', 'B']) -> str:
        """
        Assign a user to a specific variant in an A/B test based on user ID and experiment name.
        This ensures consistent assignment for the same user/experiment combination.
        """
        # Create a hash from user_id and experiment_name for consistent assignment
        import hashlib
        hash_input = f"{experiment_name}:{user_id}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        
        # Map the hash to one of the available variants
        variant_index = hash_value % len(variants)
        return variants[variant_index]

    def get_onboarding_variant(self, user_id: int) -> str:
        """Get the onboarding variant for a user (A, B, C, or D)."""
        return self.get_ab_test_variant(user_id, 'onboarding', ['A', 'B', 'C', 'D'])


# Global instance for easy access
feature_flag_manager = FeatureFlagManager()