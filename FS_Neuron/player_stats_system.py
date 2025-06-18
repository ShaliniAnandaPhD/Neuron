"""
Player Statistics Aggregation System
Metrics: PPG, target share %, snap count %, red zone usage
Real-time updates: <30 seconds, 3+ seasons historical depth
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import logging
import json
from collections import defaultdict
from sqlalchemy import create_engine, text, MetaData, Table, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
import redis.asyncio as redis
from concurrent.futures import ThreadPoolExecutor
import aiohttp
from scipy import stats
import warnings
warnings.filterwarnings('ignore')


# Configuration
class Config:
    REDIS_URL = "redis://localhost:6379"
    POSTGRES_URL = "postgresql://user:pass@localhost:5432/nfl_data"
    CLICKHOUSE_URL = "clickhouse://localhost:9000/nfl_analytics"
    UPDATE_THRESHOLD_SECONDS = 30
    HISTORICAL_SEASONS = 3
    CONFIDENCE_THRESHOLD = 0.85
    BATCH_SIZE = 1000


# Data Models
@dataclass
class PlayerSeasonStats:
    player_id: int
    season: int
    week: int
    games_played: int
    
    # Core fantasy metrics
    fantasy_points: float
    ppg: float
    
    # Target metrics (WR/TE/RB)
    targets: int = 0
    target_share_pct: float = 0.0
    target_share_rank: int = 0
    
    # Snap count metrics
    snaps_played: int = 0
    team_snaps: int = 0
    snap_pct: float = 0.0
    snap_rank: int = 0
    
    # Red zone metrics
    rz_targets: int = 0
    rz_carries: int = 0
    rz_touches: int = 0
    rz_usage_pct: float = 0.0
    rz_tds: int = 0
    rz_efficiency: float = 0.0
    
    # Advanced metrics
    air_yards: int = 0
    air_yards_share: float = 0.0
    yards_after_contact: float = 0.0
    target_separation: float = 0.0
    
    # Trend analysis
    rolling_3_avg: float = 0.0
    rolling_8_avg: float = 0.0
    trend_direction: str = "stable"  # increasing, decreasing, stable
    consistency_score: float = 0.0
    
    # Data quality
    last_updated: datetime = field(default_factory=datetime.now)
    data_sources: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
    

@dataclass
class ValidationResult:
    is_valid: bool
    confidence: float
    consensus_value: float
    source_values: Dict[str, float]
    outliers: List[str]
    deviation_pct: float


class StatType(Enum):
    FANTASY_POINTS = "fantasy_points"
    TARGETS = "targets"
    SNAPS = "snaps"
    RZ_TOUCHES = "rz_touches"
    PPG = "ppg"


class DataSource(Enum):
    ESPN = "espn"
    NFL_COM = "nfl_com"
    PFR = "pro_football_reference"
    PFF = "pro_football_focus"
    FANTASY_PROS = "fantasy_pros"


# Data Validation Engine
class StatValidator:
    def __init__(self):
        self.source_weights = {
            DataSource.NFL_COM: 0.35,      # Official source
            DataSource.ESPN: 0.25,         # Real-time accuracy
            DataSource.PFR: 0.20,          # Historical reliability
            DataSource.PFF: 0.15,          # Advanced metrics
            DataSource.FANTASY_PROS: 0.05   # Aggregated data
        }
        self.deviation_threshold = 0.10  # 10% variance allowed
        
    async def validate_stat(self, player_id: int, stat_type: StatType, 
                          source_values: Dict[DataSource, float]) -> ValidationResult:
        """Cross-reference multiple sources for stat validation"""
        
        if len(source_values) < 2:
            return ValidationResult(
                is_valid=False,
                confidence=0.0,
                consensus_value=0.0,
                source_values={},
                outliers=[],
                deviation_pct=0.0
            )
        
        values = list(source_values.values())
        sources = list(source_values.keys())
        
        # Calculate weighted consensus
        weighted_sum = sum(val * self.source_weights.get(src, 0.1) 
                          for src, val in source_values.items())
        weight_total = sum(self.source_weights.get(src, 0.1) 
                          for src in source_values.keys())
        consensus_value = weighted_sum / weight_total
        
        # Identify outliers
        outliers = []
        deviations = []
        
        for source, value in source_values.items():
            if consensus_value > 0:
                deviation = abs(value - consensus_value) / consensus_value
                deviations.append(deviation)
                
                if deviation > self.deviation_threshold:
                    outliers.append(source.value)
        
        # Calculate confidence
        avg_deviation = np.mean(deviations) if deviations else 0
        confidence = max(0.0, 1.0 - (avg_deviation / self.deviation_threshold))
        
        # Validation passes if majority sources agree
        is_valid = len(outliers) <= len(source_values) // 2
        
        return ValidationResult(
            is_valid=is_valid,
            confidence=confidence,
            consensus_value=consensus_value,
            source_values={src.value: val for src, val in source_values.items()},
            outliers=outliers,
            deviation_pct=avg_deviation * 100
        )


# Data Source Integrations
class ESPNStatsProvider:
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.base_url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"
        
    async def get_player_season_stats(self, player_id: int, season: int) -> Dict[str, float]:
        """Fetch player season stats from ESPN"""
        url = f"{self.base_url}/athletes/{player_id}/stats"
        
        try:
            async with self.session.get(url, params={'season': season}) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_espn_stats(data)
        except Exception as e:
            logging.error(f"ESPN API error for player {player_id}: {e}")
            
        return {}
        
    def _parse_espn_stats(self, data: Dict) -> Dict[str, float]:
        """Parse ESPN stats response"""
        stats = {}
        
        # This would parse the actual ESPN response structure
        # Mock implementation for now
        if 'splits' in data and 'categories' in data['splits'][0]:
            categories = data['splits'][0]['categories']
            
            for category in categories:
                if category['name'] == 'receiving':
                    for stat in category['stats']:
                        if stat['name'] == 'targets':
                            stats['targets'] = float(stat['value'])
                        elif stat['name'] == 'receptions':
                            stats['receptions'] = float(stat['value'])
                            
        return stats


class NFLComStatsProvider:
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        
    async def get_player_snap_counts(self, player_id: int, week: int, season: int) -> Dict[str, int]:
        """Get snap count data from NFL.com"""
        # This would scrape or use NFL.com API
        return {
            'snaps_played': 65,
            'team_snaps': 78,
            'snap_percentage': 83.3
        }


class PFRStatsProvider:
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.base_url = "https://www.pro-football-reference.com"
        
    async def get_player_stats(self, player_id: int, season: int) -> Dict[str, float]:
        """Fetch comprehensive stats from Pro Football Reference"""
        try:
            # PFR requires web scraping - this is a mock implementation
            url = f"{self.base_url}/players/{player_id}/gamelog/{season}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    return self._parse_pfr_stats(html)
        except Exception as e:
            logging.error(f"PFR scraping error for player {player_id}: {e}")
            
        return {}
    
    def _parse_pfr_stats(self, html: str) -> Dict[str, float]:
        """Parse PFR HTML for stats"""
        # Mock implementation - would use BeautifulSoup or similar
        return {
            'fantasy_points': 18.4,
            'targets': 8,
            'receptions': 6,
            'receiving_yards': 84,
            'touchdowns': 1
        }


class PFFStatsProvider:
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.api_key = None  # Would need PFF subscription
        
    async def get_advanced_metrics(self, player_id: int, season: int) -> Dict[str, float]:
        """Fetch advanced metrics from PFF"""
        if not self.api_key:
            logging.warning("PFF API key not configured")
            return {}
            
        try:
            # Mock PFF API call
            return {
                'target_separation': 2.8,
                'yards_after_contact': 4.2,
                'pff_grade': 74.5,
                'snap_count': 65
            }
        except Exception as e:
            logging.error(f"PFF API error for player {player_id}: {e}")
            return {}


class FantasyProStatsProvider:
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        
    async def get_consensus_rankings(self, player_id: int, week: int) -> Dict[str, float]:
        """Get consensus rankings and projections"""
        try:
            # Mock FantasyPros API
            return {
                'projected_points': 16.8,
                'consensus_rank': 24,
                'target_share_projection': 22.5
            }
        except Exception as e:
            logging.error(f"FantasyPros API error for player {player_id}: {e}")
            return {}


# Database Layer
class DatabaseManager:
    def __init__(self):
        self.postgres_engine = create_engine(Config.POSTGRES_URL)
        self.redis_client = None
        
    async def init_connections(self):
        """Initialize async connections"""
        self.redis_client = redis.from_url(Config.REDIS_URL)
        
    async def cache_player_stats(self, player_id: int, stats: PlayerSeasonStats):
        """Cache player stats in Redis with TTL"""
        cache_key = f"player:{player_id}:week:{stats.week}:season:{stats.season}"
        
        stats_dict = {
            'fantasy_points': stats.fantasy_points,
            'ppg': stats.ppg,
            'targets': stats.targets,
            'target_share_pct': stats.target_share_pct,
            'snap_pct': stats.snap_pct,
            'rz_touches': stats.rz_touches,
            'confidence_score': stats.confidence_score,
            'last_updated': stats.last_updated.isoformat()
        }
        
        await self.redis_client.setex(
            cache_key, 
            Config.UPDATE_THRESHOLD_SECONDS,
            json.dumps(stats_dict)
        )
        
    async def get_cached_stats(self, player_id: int, week: int, season: int) -> Optional[PlayerSeasonStats]:
        """Retrieve cached stats if still valid"""
        cache_key = f"player:{player_id}:week:{week}:season:{season}"
        
        cached_data = await self.redis_client.get(cache_key)
        if cached_data:
            data = json.loads(cached_data)
            
            # Check if data is still fresh
            last_updated = datetime.fromisoformat(data['last_updated'])
            if (datetime.now() - last_updated).seconds < Config.UPDATE_THRESHOLD_SECONDS:
                return self._dict_to_player_stats(data, player_id, season, week)
                
        return None
    
    def _dict_to_player_stats(self, data: Dict, player_id: int, season: int, week: int) -> PlayerSeasonStats:
        """Convert dict back to PlayerSeasonStats object"""
        return PlayerSeasonStats(
            player_id=player_id,
            season=season,
            week=week,
            games_played=week,
            fantasy_points=data['fantasy_points'],
            ppg=data['ppg'],
            targets=data['targets'],
            target_share_pct=data['target_share_pct'],
            snap_pct=data['snap_pct'],
            rz_touches=data['rz_touches'],
            confidence_score=data['confidence_score'],
            last_updated=datetime.fromisoformat(data['last_updated'])
        )
        
    async def save_player_stats(self, stats: PlayerSeasonStats):
        """Persist stats to PostgreSQL"""
        query = """
        INSERT INTO player_season_stats (
            player_id, season, week, games_played, fantasy_points, ppg,
            targets, target_share_pct, snap_pct, rz_touches, confidence_score,
            last_updated
        ) VALUES (
            :player_id, :season, :week, :games_played, :fantasy_points, :ppg,
            :targets, :target_share_pct, :snap_pct, :rz_touches, :confidence_score,
            :last_updated
        ) ON CONFLICT (player_id, season, week) DO UPDATE SET
            fantasy_points = EXCLUDED.fantasy_points,
            ppg = EXCLUDED.ppg,
            targets = EXCLUDED.targets,
            target_share_pct = EXCLUDED.target_share_pct,
            snap_pct = EXCLUDED.snap_pct,
            rz_touches = EXCLUDED.rz_touches,
            confidence_score = EXCLUDED.confidence_score,
            last_updated = EXCLUDED.last_updated
        """
        
        with self.postgres_engine.connect() as conn:
            conn.execute(text(query), {
                'player_id': stats.player_id,
                'season': stats.season,
                'week': stats.week,
                'games_played': stats.games_played,
                'fantasy_points': stats.fantasy_points,
                'ppg': stats.ppg,
                'targets': stats.targets,
                'target_share_pct': stats.target_share_pct,
                'snap_pct': stats.snap_pct,
                'rz_touches': stats.rz_touches,
                'confidence_score': stats.confidence_score,
                'last_updated': stats.last_updated
            })
            conn.commit()


# Trend Analysis Engine
class TrendAnalyzer:
    def __init__(self):
        self.min_games_for_trend = 3
        
    def calculate_trends(self, historical_stats: List[PlayerSeasonStats]) -> Dict[str, Any]:
        """Calculate rolling averages and trend direction"""
        if len(historical_stats) < self.min_games_for_trend:
            return {
                'rolling_3_avg': 0.0,
                'rolling_8_avg': 0.0,
                'trend_direction': 'stable',
                'consistency_score': 0.0
            }
        
        # Sort by week
        sorted_stats = sorted(historical_stats, key=lambda x: x.week)
        fantasy_points = [stat.fantasy_points for stat in sorted_stats]
        
        # Calculate rolling averages
        rolling_3 = self._rolling_average(fantasy_points, 3)
        rolling_8 = self._rolling_average(fantasy_points, 8)
        
        # Determine trend direction
        trend_direction = self._calculate_trend_direction(fantasy_points)
        
        # Calculate consistency score (inverse of coefficient of variation)
        consistency_score = self._calculate_consistency(fantasy_points)
        
        return {
            'rolling_3_avg': rolling_3,
            'rolling_8_avg': rolling_8,
            'trend_direction': trend_direction,
            'consistency_score': consistency_score
        }
    
    def _rolling_average(self, values: List[float], window: int) -> float:
        """Calculate rolling average for the last N values"""
        if len(values) < window:
            return np.mean(values)
        return np.mean(values[-window:])
    
    def _calculate_trend_direction(self, values: List[float]) -> str:
        """Determine if player is trending up, down, or stable"""
        if len(values) < 4:
            return 'stable'
        
        # Use linear regression to determine trend
        x = np.arange(len(values))
        slope, _, r_value, p_value, _ = stats.linregress(x, values)
        
        # Only consider significant trends (p < 0.1 and r² > 0.3)
        if p_value > 0.1 or r_value**2 < 0.3:
            return 'stable'
        
        if slope > 0.5:
            return 'increasing'
        elif slope < -0.5:
            return 'decreasing'
        else:
            return 'stable'
    
    def _calculate_consistency(self, values: List[float]) -> float:
        """Calculate consistency score (0-1, higher is more consistent)"""
        if len(values) < 2:
            return 0.0
        
        mean_val = np.mean(values)
        if mean_val == 0:
            return 0.0
        
        cv = np.std(values) / mean_val  # Coefficient of variation
        return max(0.0, 1.0 - cv)  # Inverse, capped at 0


# Main Aggregation Engine
class PlayerStatsAggregator:
    def __init__(self):
        self.validator = StatValidator()
        self.db_manager = DatabaseManager()
        self.trend_analyzer = TrendAnalyzer()
        self.session = None
        
        # Data providers
        self.providers = {}
        
    async def initialize(self):
        """Initialize all components"""
        await self.db_manager.init_connections()
        
        # Initialize HTTP session
        self.session = aiohttp.ClientSession()
        
        # Initialize data providers
        self.providers = {
            DataSource.ESPN: ESPNStatsProvider(self.session),
            DataSource.NFL_COM: NFLComStatsProvider(self.session),
            DataSource.PFR: PFRStatsProvider(self.session),
            DataSource.PFF: PFFStatsProvider(self.session),
            DataSource.FANTASY_PROS: FantasyProStatsProvider(self.session)
        }
        
        logging.info("PlayerStatsAggregator initialized successfully")
    
    async def aggregate_player_stats(self, player_id: int, season: int, week: int) -> PlayerSeasonStats:
        """Main aggregation method - combines all data sources"""
        
        # Check cache first
        cached_stats = await self.db_manager.get_cached_stats(player_id, week, season)
        if cached_stats and cached_stats.confidence_score >= Config.CONFIDENCE_THRESHOLD:
            logging.info(f"Returning cached stats for player {player_id}")
            return cached_stats
        
        # Collect data from all sources
        source_data = await self._collect_from_all_sources(player_id, season, week)
        
        # Validate and aggregate each stat type
        aggregated_stats = await self._validate_and_aggregate(player_id, source_data)
        
        # Get historical data for trend analysis
        historical_stats = await self._get_historical_stats(player_id, season, week)
        
        # Calculate trends
        trend_data = self.trend_analyzer.calculate_trends(historical_stats)
        
        # Create final PlayerSeasonStats object
        player_stats = PlayerSeasonStats(
            player_id=player_id,
            season=season,
            week=week,
            games_played=week,
            fantasy_points=aggregated_stats.get('fantasy_points', 0.0),
            ppg=aggregated_stats.get('fantasy_points', 0.0) / max(week, 1),
            targets=int(aggregated_stats.get('targets', 0)),
            target_share_pct=aggregated_stats.get('target_share_pct', 0.0),
            snaps_played=int(aggregated_stats.get('snaps_played', 0)),
            snap_pct=aggregated_stats.get('snap_pct', 0.0),
            rz_touches=int(aggregated_stats.get('rz_touches', 0)),
            rolling_3_avg=trend_data['rolling_3_avg'],
            rolling_8_avg=trend_data['rolling_8_avg'],
            trend_direction=trend_data['trend_direction'],
            consistency_score=trend_data['consistency_score'],
            confidence_score=aggregated_stats.get('confidence_score', 0.0),
            data_sources=list(source_data.keys()),
            last_updated=datetime.now()
        )
        
        # Cache and persist
        await self.db_manager.cache_player_stats(player_id, player_stats)
        await self.db_manager.save_player_stats(player_stats)
        
        return player_stats
    
    async def _collect_from_all_sources(self, player_id: int, season: int, week: int) -> Dict[str, Dict[str, float]]:
        """Collect data from all configured sources concurrently"""
        source_data = {}
        
        # Create tasks for all providers
        tasks = []
        for source, provider in self.providers.items():
            if source == DataSource.ESPN:
                tasks.append(self._safe_call(provider.get_player_season_stats, player_id, season))
            elif source == DataSource.NFL_COM:
                tasks.append(self._safe_call(provider.get_player_snap_counts, player_id, week, season))
            elif source == DataSource.PFR:
                tasks.append(self._safe_call(provider.get_player_stats, player_id, season))
            elif source == DataSource.PFF:
                tasks.append(self._safe_call(provider.get_advanced_metrics, player_id, season))
            elif source == DataSource.FANTASY_PROS:
                tasks.append(self._safe_call(provider.get_consensus_rankings, player_id, week))
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Map results back to sources
        for i, (source, _) in enumerate(self.providers.items()):
            if not isinstance(results[i], Exception) and results[i]:
                source_data[source.value] = results[i]
        
        return source_data
    
    async def _safe_call(self, func, *args):
        """Safely call a provider function with error handling"""
        try:
            return await func(*args)
        except Exception as e:
            logging.error(f"Provider error: {e}")
            return {}
    
    async def _validate_and_aggregate(self, player_id: int, source_data: Dict[str, Dict[str, float]]) -> Dict[str, float]:
        """Validate and aggregate stats from multiple sources"""
        aggregated = {}
        
        # Define which stats to aggregate
        stats_to_aggregate = [
            'fantasy_points', 'targets', 'snaps_played', 'snap_pct', 
            'rz_touches', 'target_share_pct'
        ]
        
        total_confidence = 0.0
        confidence_count = 0
        
        for stat_name in stats_to_aggregate:
            # Collect values for this stat from all sources
            source_values = {}
            
            for source_name, data in source_data.items():
                if stat_name in data:
                    # Map source name to DataSource enum
                    for source_enum in DataSource:
                        if source_enum.value == source_name:
                            source_values[source_enum] = data[stat_name]
                            break
            
            if source_values:
                # Validate this stat
                stat_type = StatType.FANTASY_POINTS  # Default, would map properly
                validation_result = await self.validator.validate_stat(
                    player_id, stat_type, source_values
                )
                
                if validation_result.is_valid:
                    aggregated[stat_name] = validation_result.consensus_value
                    total_confidence += validation_result.confidence
                    confidence_count += 1
                else:
                    # Use simple average if validation fails
                    aggregated[stat_name] = np.mean(list(source_values.values()))
        
        # Calculate overall confidence score
        if confidence_count > 0:
            aggregated['confidence_score'] = total_confidence / confidence_count
        else:
            aggregated['confidence_score'] = 0.0
        
        return aggregated
    
    async def _get_historical_stats(self, player_id: int, season: int, current_week: int) -> List[PlayerSeasonStats]:
        """Retrieve historical stats for trend analysis"""
        # This would query the database for historical data
        # Mock implementation for now
        historical = []
        
        for week in range(max(1, current_week - 8), current_week):
            # Mock historical data
            mock_stats = PlayerSeasonStats(
                player_id=player_id,
                season=season,
                week=week,
                games_played=week,
                fantasy_points=15.0 + np.random.normal(0, 3),
                ppg=15.0
            )
            historical.append(mock_stats)
        
        return historical
    
    async def batch_update_players(self, player_ids: List[int], season: int, week: int):
        """Update multiple players in batches"""
        logging.info(f"Starting batch update for {len(player_ids)} players")
        
        # Process in batches to avoid overwhelming APIs
        for i in range(0, len(player_ids), Config.BATCH_SIZE):
            batch = player_ids[i:i + Config.BATCH_SIZE]
            
            tasks = [
                self.aggregate_player_stats(player_id, season, week)
                for player_id in batch
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Log results
            successful = sum(1 for r in results if not isinstance(r, Exception))
            failed = len(results) - successful
            
            logging.info(f"Batch {i//Config.BATCH_SIZE + 1}: {successful} successful, {failed} failed")
    
    async def close(self):
        """Clean up resources"""
        if self.session:
            await self.session.close()
        if self.db_manager.redis_client:
            await self.db_manager.redis_client.close()


# CLI and Testing
async def main():
    """Main function for testing"""
    logging.basicConfig(level=logging.INFO)
    
    aggregator = PlayerStatsAggregator()
    
    try:
        await aggregator.initialize()
        
        # Test single player aggregation
        player_stats = await aggregator.aggregate_player_stats(
            player_id=12345, 
            season=2024, 
            week=10
        )
        
        print(f"Player {player_stats.player_id} Stats:")
        print(f"  Fantasy Points: {player_stats.fantasy_points:.1f}")
        print(f"  PPG: {player_stats.ppg:.1f}")
        print(f"  Target Share: {player_stats.target_share_pct:.1f}%")
        print(f"  Snap %: {player_stats.snap_pct:.1f}%")
        print(f"  Trend: {player_stats.trend_direction}")
        print(f"  Confidence: {player_stats.confidence_score:.2f}")
        
    finally:
        await aggregator.close()


if __name__ == "__main__":
    asyncio.run(main())
