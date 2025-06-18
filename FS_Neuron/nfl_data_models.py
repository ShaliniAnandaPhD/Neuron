"""
NFL Data Pipeline - Core Data Models and Configuration
Defines all data structures, enums, and configuration for the real-time NFL pipeline
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import hashlib
import json


# ===== CONFIGURATION CLASS =====
class Config:
    """
    Central configuration for the NFL data pipeline system
    Contains all performance targets, API endpoints, and operational parameters
    """
    # Database connection strings
    REDIS_URL = "redis://localhost:6379"
    POSTGRES_URL = "postgresql://user:pass@localhost:5432/nfl_data"
    
    # External API endpoints for data sources
    ESPN_API_BASE = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"
    NFL_COM_BASE = "https://api.nfl.com/v1"
    PFR_BASE = "https://www.pro-football-reference.com"
    
    # Performance and reliability targets
    MAX_LATENCY_MS = 200                    # Target latency from source to processing
    DAILY_UPDATE_VOLUME = 10000             # Expected player updates per game day
    TARGET_UPTIME = 99.9                    # Uptime percentage during NFL Sundays
    RATE_LIMIT_PER_MINUTE = 300             # API calls per minute limit
    
    # Processing configuration
    MAX_RETRIES = 3                         # Maximum retry attempts for failed requests
    BATCH_SIZE = 1000                       # Batch size for bulk operations
    UPDATE_THRESHOLD_SECONDS = 30           # Real-time update frequency
    HISTORICAL_SEASONS = 3                  # Seasons of historical data to maintain
    
    # Data validation thresholds
    CONFIDENCE_THRESHOLD = 0.85             # Minimum confidence for stat validation
    DEVIATION_THRESHOLD = 0.10              # Maximum allowed variance between sources
    
    # Queue configuration
    HIGH_PRIORITY_QUEUE = "nfl:queue:high"
    NORMAL_PRIORITY_QUEUE = "nfl:queue:normal"
    LOW_PRIORITY_QUEUE = "nfl:queue:low"


# ===== ENUMS =====
class DataSource(Enum):
    """
    Enumeration of all supported data sources with reliability weights
    Used for data validation and source prioritization
    """
    ESPN = "espn"
    NFL_COM = "nfl_com"
    PRO_FOOTBALL_REFERENCE = "pfr"
    PRO_FOOTBALL_FOCUS = "pff"
    FANTASY_PROS = "fantasy_pros"


class StatCategory(Enum):
    """
    Categories of NFL statistics for proper routing and processing
    """
    PASSING = "passing"
    RUSHING = "rushing"
    RECEIVING = "receiving"
    DEFENSE = "defense"
    KICKING = "kicking"
    SPECIAL_TEAMS = "special_teams"


class GameStatus(Enum):
    """
    Possible game states for real-time processing prioritization
    """
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    HALFTIME = "halftime"
    FINAL = "final"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"


class InjuryStatus(Enum):
    """
    Standard NFL injury report designations
    """
    HEALTHY = "healthy"
    QUESTIONABLE = "questionable"
    DOUBTFUL = "doubtful"
    OUT = "out"
    INJURED_RESERVE = "ir"
    PHYSICALLY_UNABLE = "pup"


class TrendDirection(Enum):
    """
    Statistical trend analysis directions
    """
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    VOLATILE = "volatile"


# ===== CORE DATA MODELS =====
@dataclass
class PlayerUpdate:
    """
    Represents a single player statistic update from any data source
    Contains all relevant information for processing and validation
    """
    # Player identification
    player_id: str
    name: str
    team: str
    position: str
    
    # Game context
    game_id: Optional[str] = None
    week: Optional[int] = None
    season: Optional[int] = None
    
    # Core statistics (flexible dict for different stat types)
    stats: Dict[str, Any] = field(default_factory=dict)
    
    # Advanced metrics
    snap_count: Optional[int] = None
    team_snaps: Optional[int] = None
    targets: Optional[int] = None
    air_yards: Optional[int] = None
    
    # Injury and status information
    injury_status: Optional[str] = None
    active_status: bool = True
    
    # Data provenance and quality
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = DataSource.ESPN.value
    confidence_score: float = 1.0
    
    def to_hash(self) -> str:
        """
        Generate unique hash for deduplication
        Used to prevent duplicate processing of identical updates
        """
        # Create content string for hashing (exclude timestamp for consistency)
        content = f"{self.player_id}_{self.game_id}_{json.dumps(self.stats, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get_fantasy_points(self, scoring_system: str = "ppr") -> float:
        """
        Calculate fantasy points based on stats and scoring system
        Supports PPR, Half-PPR, and Standard scoring
        """
        points = 0.0
        
        # Passing points
        if "passing_yards" in self.stats:
            points += self.stats["passing_yards"] * 0.04  # 1 point per 25 yards
        if "passing_tds" in self.stats:
            points += self.stats["passing_tds"] * 4
        if "interceptions" in self.stats:
            points -= self.stats["interceptions"] * 2
            
        # Rushing points
        if "rushing_yards" in self.stats:
            points += self.stats["rushing_yards"] * 0.1  # 1 point per 10 yards
        if "rushing_tds" in self.stats:
            points += self.stats["rushing_tds"] * 6
            
        # Receiving points
        if "receiving_yards" in self.stats:
            points += self.stats["receiving_yards"] * 0.1
        if "receiving_tds" in self.stats:
            points += self.stats["receiving_tds"] * 6
        if "receptions" in self.stats and scoring_system == "ppr":
            points += self.stats["receptions"]  # PPR bonus
        elif "receptions" in self.stats and scoring_system == "half_ppr":
            points += self.stats["receptions"] * 0.5
            
        return round(points, 2)


@dataclass
class GameData:
    """
    Real-time game information and context
    Essential for understanding player performance context
    """
    # Game identification
    game_id: str
    week: int
    season: int
    
    # Team information
    home_team: str
    away_team: str
    home_score: int = 0
    away_score: int = 0
    
    # Game state
    status: str = GameStatus.SCHEDULED.value
    quarter: Optional[int] = None
    time_remaining: Optional[str] = None
    down: Optional[int] = None
    distance: Optional[int] = None
    field_position: Optional[str] = None
    
    # Environmental factors
    weather: Optional[Dict[str, Any]] = None
    temperature: Optional[int] = None
    wind_speed: Optional[int] = None
    precipitation: Optional[str] = None
    
    # Data tracking
    last_updated: datetime = field(default_factory=datetime.now)
    data_sources: List[str] = field(default_factory=list)
    
    def is_active(self) -> bool:
        """Check if game is currently in progress and needs real-time updates"""
        return self.status in [GameStatus.IN_PROGRESS.value, GameStatus.HALFTIME.value]
    
    def get_game_context(self) -> Dict[str, Any]:
        """Get contextual information for player performance analysis"""
        return {
            "is_divisional": self._is_divisional_matchup(),
            "is_primetime": self._is_primetime_game(),
            "weather_impact": self._assess_weather_impact(),
            "pace_factor": self._calculate_pace_factor()
        }
    
    def _is_divisional_matchup(self) -> bool:
        """Determine if this is a divisional game (affects player performance)"""
        divisions = {
            "AFC East": ["NE", "BUF", "MIA", "NYJ"],
            "AFC North": ["PIT", "BAL", "CLE", "CIN"],
            "AFC South": ["IND", "TEN", "HOU", "JAX"],
            "AFC West": ["KC", "LV", "LAC", "DEN"],
            "NFC East": ["DAL", "PHI", "NYG", "WAS"],
            "NFC North": ["GB", "MIN", "CHI", "DET"],
            "NFC South": ["NO", "TB", "ATL", "CAR"],
            "NFC West": ["SF", "SEA", "LAR", "ARI"]
        }
        
        for division_teams in divisions.values():
            if self.home_team in division_teams and self.away_team in division_teams:
                return True
        return False
    
    def _is_primetime_game(self) -> bool:
        """Check if this is a primetime game (SNF, MNF, TNF)"""
        # This would be determined by game time/day
        # Simplified implementation
        return self.game_id.endswith("_prime")
    
    def _assess_weather_impact(self) -> str:
        """Assess weather impact on game (affects passing/kicking)"""
        if not self.weather:
            return "none"
        
        if self.wind_speed and self.wind_speed > 15:
            return "high"
        elif self.precipitation and self.precipitation != "none":
            return "medium"
        elif self.temperature and self.temperature < 32:
            return "medium"
        else:
            return "low"
    
    def _calculate_pace_factor(self) -> float:
        """Calculate game pace factor based on score differential and time"""
        # Simplified pace calculation
        score_diff = abs(self.home_score - self.away_score)
        if score_diff > 14:
            return 1.2  # Fast pace due to comeback situation
        elif score_diff < 3:
            return 0.9  # Slower pace in close game
        else:
            return 1.0  # Normal pace


@dataclass
class InjuryReport:
    """
    Player injury status and related information
    Critical for lineup decisions and performance expectations
    """
    player_id: str
    player_name: str
    team: str
    
    # Injury details
    status: str  # Using InjuryStatus enum values
    injury_type: str
    body_part: str
    severity: Optional[str] = None
    
    # Timeline information
    injury_date: Optional[datetime] = None
    expected_return: Optional[datetime] = None
    weeks_out: Optional[int] = None
    
    # Practice participation
    wednesday_practice: Optional[str] = None  # DNP, Limited, Full
    thursday_practice: Optional[str] = None
    friday_practice: Optional[str] = None
    
    # Data tracking
    updated_at: datetime = field(default_factory=datetime.now)
    source: str = DataSource.NFL_COM.value
    reliability_score: float = 1.0
    
    def get_game_probability(self) -> float:
        """
        Estimate probability of player participating in upcoming game
        Based on injury status and practice participation
        """
        if self.status == InjuryStatus.OUT.value:
            return 0.0
        elif self.status == InjuryStatus.DOUBTFUL.value:
            return 0.25
        elif self.status == InjuryStatus.QUESTIONABLE.value:
            # Adjust based on practice participation
            if self.friday_practice == "Full":
                return 0.75
            elif self.friday_practice == "Limited":
                return 0.50
            elif self.friday_practice == "DNP":
                return 0.25
            else:
                return 0.50  # Default for questionable
        else:
            return 1.0  # Healthy or probable


@dataclass
class PlayerSeasonStats:
    """
    Comprehensive season-long statistics and analytics for a player
    Includes advanced metrics, trends, and fantasy relevance
    """
    # Player identification
    player_id: str
    name: str
    team: str
    position: str
    season: int
    
    # Game participation
    games_played: int = 0
    games_started: int = 0
    total_snaps: int = 0
    snap_percentage: float = 0.0
    
    # Core statistics (accumulated over season)
    total_stats: Dict[str, Any] = field(default_factory=dict)
    
    # Fantasy metrics
    total_fantasy_points: float = 0.0
    fantasy_ppg: float = 0.0
    fantasy_rank_position: Optional[int] = None
    fantasy_rank_overall: Optional[int] = None
    
    # Advanced receiving metrics (for skill position players)
    target_share: float = 0.0
    air_yards_share: float = 0.0
    red_zone_targets: int = 0
    red_zone_target_share: float = 0.0
    
    # Efficiency metrics
    yards_per_target: float = 0.0
    yards_after_contact: float = 0.0
    drop_rate: float = 0.0
    
    # Trend analysis
    last_4_weeks_avg: float = 0.0
    last_8_weeks_avg: float = 0.0
    trend_direction: str = TrendDirection.STABLE.value
    consistency_score: float = 0.0  # Lower variance = higher consistency
    
    # Weekly performance history
    weekly_scores: List[float] = field(default_factory=list)
    weekly_snaps: List[int] = field(default_factory=list)
    weekly_targets: List[int] = field(default_factory=list)
    
    # Data quality and validation
    last_updated: datetime = field(default_factory=datetime.now)
    data_sources: List[str] = field(default_factory=list)
    confidence_score: float = 1.0
    
    def calculate_consistency(self) -> float:
        """
        Calculate player consistency score based on weekly performance variance
        Higher score = more consistent performance
        """
        if len(self.weekly_scores) < 4:
            return 0.0
        
        scores_array = np.array(self.weekly_scores)
        mean_score = np.mean(scores_array)
        std_score = np.std(scores_array)
        
        # Coefficient of variation (lower is more consistent)
        if mean_score > 0:
            cv = std_score / mean_score
            # Convert to 0-1 scale where 1 is most consistent
            consistency = max(0.0, 1.0 - (cv / 2.0))
        else:
            consistency = 0.0
            
        return round(consistency, 3)
    
    def get_trend_analysis(self) -> Dict[str, Any]:
        """
        Analyze recent performance trends
        Returns trend direction and statistical significance
        """
        if len(self.weekly_scores) < 6:
            return {"trend": "insufficient_data", "confidence": 0.0}
        
        recent_scores = self.weekly_scores[-6:]  # Last 6 weeks
        weeks = list(range(len(recent_scores)))
        
        # Linear regression for trend
        correlation = np.corrcoef(weeks, recent_scores)[0, 1]
        
        if correlation > 0.3:
            trend = TrendDirection.INCREASING.value
        elif correlation < -0.3:
            trend = TrendDirection.DECREASING.value
        else:
            # Check for volatility
            cv = np.std(recent_scores) / (np.mean(recent_scores) + 0.01)
            if cv > 0.5:
                trend = TrendDirection.VOLATILE.value
            else:
                trend = TrendDirection.STABLE.value
        
        return {
            "trend": trend,
            "correlation": correlation,
            "confidence": abs(correlation),
            "recent_avg": np.mean(recent_scores),
            "season_avg": self.fantasy_ppg
        }


@dataclass
class ValidationResult:
    """
    Result of cross-source data validation
    Used to ensure data accuracy and reliability
    """
    stat_name: str
    player_id: str
    
    # Validation outcome
    is_valid: bool
    confidence_score: float
    consensus_value: float
    
    # Source comparison
    source_values: Dict[str, float]
    outlier_sources: List[str]
    deviation_percentage: float
    
    # Statistical analysis
    mean_value: float
    median_value: float
    standard_deviation: float
    
    # Decision rationale
    validation_method: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    def get_recommended_value(self) -> float:
        """
        Get the recommended value to use based on validation results
        Prioritizes consensus while accounting for source reliability
        """
        if self.is_valid and self.confidence_score >= Config.CONFIDENCE_THRESHOLD:
            return self.consensus_value
        elif self.median_value:
            return self.median_value  # Fallback to median for outlier resistance
        else:
            return self.mean_value  # Final fallback


# ===== MESSAGE QUEUE MODELS =====
@dataclass
class QueueMessage:
    """
    Standardized message format for internal queue system
    Ensures consistent processing across all pipeline components
    """
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message_type: str = "player_update"
    priority: int = 1  # 1=high, 2=normal, 3=low
    
    # Message content
    data: Dict[str, Any] = field(default_factory=dict)
    
    # Processing metadata
    created_at: datetime = field(default_factory=datetime.now)
    retry_count: int = 0
    max_retries: int = Config.MAX_RETRIES
    
    # Routing information
    source_component: str = ""
    target_component: str = ""
    
    def to_json(self) -> str:
        """Serialize message for queue storage"""
        message_dict = asdict(self)
        # Convert datetime to ISO string
        message_dict["created_at"] = self.created_at.isoformat()
        return json.dumps(message_dict)
    
    @classmethod
    def from_json(cls, json_str: str) -> "QueueMessage":
        """Deserialize message from queue storage"""
        data = json.loads(json_str)
        # Convert ISO string back to datetime
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)
    
    def can_retry(self) -> bool:
        """Check if message can be retried on failure"""
        return self.retry_count < self.max_retries
    
    def increment_retry(self) -> None:
        """Increment retry counter"""
        self.retry_count += 1


"""
SUMMARY:
This module defines the core data models and configuration for the NFL real-time data pipeline.

Key Components:
1. Config class - Central configuration with performance targets (<200ms latency, 10K+ updates/day, 99.9% uptime)
2. Enums - Type-safe definitions for data sources, stat categories, game statuses, etc.
3. PlayerUpdate - Individual stat updates with deduplication hashing and fantasy point calculation
4. GameData - Real-time game context with environmental factors and pace analysis
5. InjuryReport - Injury status tracking with game participation probability
6. PlayerSeasonStats - Comprehensive season analytics with trend analysis and consistency scoring
7. ValidationResult - Cross-source data validation with confidence scoring
8. QueueMessage - Standardized internal messaging format

The models support the target requirements:
- Real-time updates with <30 second freshness
- Multi-source data validation for accuracy
- 3+ seasons of historical depth for trend analysis
- Fantasy-relevant metrics (PPG, target share, snap %, red zone usage)
- Data quality tracking and confidence scoring

All models include proper typing, default values, and utility methods for processing efficiency.
"""
