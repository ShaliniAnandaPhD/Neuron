"""
NFL Data Pipeline - Data Source Integrations
Handles real-time data collection from multiple NFL data providers
Implements rate limiting, retry logic, and data normalization
"""

import asyncio
import aiohttp
import backoff
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from abc import ABC, abstractmethod
import json
import time
from bs4 import BeautifulSoup
import re
from dataclasses import asdict

# Import our data models (assuming they're in the same package)
from nfl_data_models import (
    PlayerUpdate, GameData, InjuryReport, DataSource, 
    StatCategory, GameStatus, InjuryStatus, Config
)


# ===== RATE LIMITING SYSTEM =====
class RateLimiter:
    """
    Advanced rate limiter using sliding window algorithm
    Prevents API rate limit violations while maximizing throughput
    """
    
    def __init__(self, redis_client, calls_per_minute: int = 300):
        """
        Initialize rate limiter with Redis backend for distributed rate limiting
        
        Args:
            redis_client: Redis client for storing rate limit data
            calls_per_minute: Maximum API calls allowed per minute
        """
        self.redis = redis_client
        self.calls_per_minute = calls_per_minute
        self.window_size = 60  # 60 seconds
        
    async def is_allowed(self, api_key: str) -> bool:
        """
        Check if API call is allowed under current rate limits
        Uses sliding window algorithm for accurate rate limiting
        
        Args:
            api_key: Unique identifier for the API being called
            
        Returns:
            True if call is allowed, False if rate limited
        """
        current_time = time.time()
        window_start = current_time - self.window_size
        
        # Redis pipeline for atomic operations
        pipe = self.redis.pipeline()
        
        # Remove expired entries (older than window)
        pipe.zremrangebyscore(f"rate_limit:{api_key}", 0, window_start)
        
        # Count current entries in window
        pipe.zcard(f"rate_limit:{api_key}")
        
        # Add current request timestamp
        pipe.zadd(f"rate_limit:{api_key}", {str(current_time): current_time})
        
        # Set expiry for cleanup
        pipe.expire(f"rate_limit:{api_key}", self.window_size + 10)
        
        # Execute pipeline
        results = await pipe.execute()
        current_count = results[1]  # Count from zcard operation
        
        # Allow if under limit
        return current_count < self.calls_per_minute
    
    async def wait_if_needed(self, api_key: str) -> None:
        """
        Wait if rate limit would be exceeded
        Calculates optimal wait time based on sliding window
        """
        if not await self.is_allowed(api_key):
            # Calculate wait time based on oldest entry in window
            oldest_entry = await self.redis.zrange(f"rate_limit:{api_key}", 0, 0)
            if oldest_entry:
                oldest_time = float(oldest_entry[0])
                wait_time = self.window_size - (time.time() - oldest_time) + 1
                await asyncio.sleep(max(0, wait_time))


# ===== ABSTRACT BASE CLASS FOR DATA SOURCES =====
class NFLDataSource(ABC):
    """
    Abstract base class for all NFL data sources
    Defines common interface and functionality for data providers
    """
    
    def __init__(self, session: aiohttp.ClientSession, rate_limiter: RateLimiter):
        """
        Initialize data source with HTTP session and rate limiter
        
        Args:
            session: aiohttp session for making HTTP requests
            rate_limiter: Rate limiter instance for API throttling
        """
        self.session = session
        self.rate_limiter = rate_limiter
        self.source_name = DataSource.ESPN  # Override in subclasses
        self.base_url = ""
        self.headers = {
            "User-Agent": "NFL-Pipeline/1.0",
            "Accept": "application/json"
        }
        
    @abstractmethod
    async def get_game_data(self, game_id: str) -> Optional[GameData]:
        """Fetch real-time game data"""
        pass
    
    @abstractmethod
    async def get_player_stats(self, game_id: str) -> List[PlayerUpdate]:
        """Fetch player statistics for a game"""
        pass
    
    @abstractmethod
    async def get_injury_reports(self, team: str = None) -> List[InjuryReport]:
        """Fetch injury reports"""
        pass
    
    async def _make_request(self, url: str, params: Dict = None, timeout: int = 5) -> Optional[Dict]:
        """
        Make rate-limited HTTP request with retry logic
        
        Args:
            url: Request URL
            params: Query parameters
            timeout: Request timeout in seconds
            
        Returns:
            JSON response data or None if failed
        """
        # Apply rate limiting
        await self.rate_limiter.wait_if_needed(self.source_name.value)
        
        try:
            async with self.session.get(
                url, 
                params=params, 
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:
                    # Rate limited - wait and retry
                    logging.warning(f"{self.source_name.value} API rate limited")
                    await asyncio.sleep(2)
                    return None
                elif response.status == 404:
                    logging.warning(f"Resource not found: {url}")
                    return None
                else:
                    logging.error(f"HTTP {response.status} for {url}")
                    return None
                    
        except asyncio.TimeoutError:
            logging.error(f"Timeout requesting {url}")
            return None
        except Exception as e:
            logging.error(f"Request error for {url}: {e}")
            return None


# ===== ESPN DATA SOURCE IMPLEMENTATION =====
class ESPNDataSource(NFLDataSource):
    """
    ESPN API integration for real-time NFL data
    Primary source for live game data and player statistics
    """
    
    def __init__(self, session: aiohttp.ClientSession, rate_limiter: RateLimiter):
        super().__init__(session, rate_limiter)
        self.source_name = DataSource.ESPN
        self.base_url = Config.ESPN_API_BASE
        
    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=3,
        max_time=10
    )
    async def get_game_data(self, game_id: str) -> Optional[GameData]:
        """
        Fetch real-time game data from ESPN API
        Includes score, time, down/distance, and game context
        
        Args:
            game_id: ESPN game identifier
            
        Returns:
            GameData object or None if failed
        """
        url = f"{self.base_url}/scoreboard/{game_id}"
        data = await self._make_request(url)
        
        if not data or 'events' not in data:
            return None
            
        try:
            return self._parse_espn_game_data(data)
        except Exception as e:
            logging.error(f"Error parsing ESPN game data: {e}")
            return None
    
    async def get_player_stats(self, game_id: str) -> List[PlayerUpdate]:
        """
        Fetch player statistics from ESPN game summary
        Extracts passing, rushing, receiving stats for all players
        
        Args:
            game_id: ESPN game identifier
            
        Returns:
            List of PlayerUpdate objects
        """
        url = f"{self.base_url}/summary"
        params = {"event": game_id}
        data = await self._make_request(url, params)
        
        if not data:
            return []
            
        try:
            return self._parse_espn_player_stats(data, game_id)
        except Exception as e:
            logging.error(f"Error parsing ESPN player stats: {e}")
            return []
    
    async def get_injury_reports(self, team: str = None) -> List[InjuryReport]:
        """
        ESPN doesn't provide comprehensive injury reports
        Returns empty list - injury data comes from other sources
        """
        return []
    
    def _parse_espn_game_data(self, data: Dict) -> GameData:
        """
        Parse ESPN scoreboard API response into GameData object
        Handles nested JSON structure and missing fields gracefully
        """
        event = data.get('events', [{}])[0]
        competition = event.get('competitions', [{}])[0]
        status = competition.get('status', {})
        competitors = competition.get('competitors', [])
        
        # Extract team information
        home_team = away_team = ""
        home_score = away_score = 0
        
        for competitor in competitors:
            team_abbr = competitor.get('team', {}).get('abbreviation', '')
            score = int(competitor.get('score', 0))
            
            if competitor.get('homeAway') == 'home':
                home_team = team_abbr
                home_score = score
            else:
                away_team = team_abbr
                away_score = score
        
        # Parse game status
        status_type = status.get('type', {}).get('name', 'scheduled')
        game_status = self._normalize_game_status(status_type)
        
        # Extract timing information
        quarter = status.get('period', None)
        time_remaining = status.get('displayClock', None)
        
        # Get weather data if available
        weather_data = competition.get('weather', {})
        temperature = weather_data.get('temperature', None)
        
        return GameData(
            game_id=event.get('id', ''),
            week=event.get('week', {}).get('number', 0),
            season=event.get('season', {}).get('year', 2024),
            home_team=home_team,
            away_team=away_team,
            home_score=home_score,
            away_score=away_score,
            quarter=quarter,
            time_remaining=time_remaining,
            status=game_status,
            temperature=temperature,
            timestamp=datetime.now(),
            source=self.source_name
        )
    
    def _parse_espn_player_stats(self, data: Dict, game_id: str) -> List[PlayerUpdate]:
        """
        Parse ESPN player statistics from game summary
        Extracts individual player performance data
        """
        updates = []
        
        # ESPN organizes stats by team and category
        teams = data.get('boxscore', {}).get('teams', [])
        
        for team in teams:
            team_abbr = team.get('team', {}).get('abbreviation', '')
            statistics = team.get('statistics', [])
            
            for stat_category in statistics:
                category_name = stat_category.get('name', '').lower()
                
                if category_name == 'passing':
                    updates.extend(self._parse_passing_stats(
                        stat_category, team_abbr, game_id
                    ))
                elif category_name == 'rushing':
                    updates.extend(self._parse_rushing_stats(
                        stat_category, team_abbr, game_id
                    ))
                elif category_name == 'receiving':
                    updates.extend(self._parse_receiving_stats(
                        stat_category, team_abbr, game_id
                    ))
        
        return updates
    
    def _parse_passing_stats(self, stats: Dict, team: str, game_id: str) -> List[PlayerUpdate]:
        """Parse quarterback passing statistics"""
        updates = []
        
        for athlete in stats.get('athletes', []):
            player_name = athlete.get('athlete', {}).get('displayName', '')
            player_id = athlete.get('athlete', {}).get('id', '')
            stats_data = athlete.get('stats', [])
            
            # Map ESPN stat indices to values
            stat_values = {i: stat for i, stat in enumerate(stats_data)}
            
            updates.append(PlayerUpdate(
                player_id=player_id,
                player_name=player_name,
                team=team,
                game_id=game_id,
                category=StatCategory.PASSING,
                stat_name="completions",
                stat_value=stat_values.get(0, 0),
                timestamp=datetime.now(),
                source=self.source_name
            ))
            
            updates.append(PlayerUpdate(
                player_id=player_id,
                player_name=player_name,
                team=team,
                game_id=game_id,
                category=StatCategory.PASSING,
                stat_name="attempts",
                stat_value=stat_values.get(1, 0),
                timestamp=datetime.now(),
                source=self.source_name
            ))
            
            updates.append(PlayerUpdate(
                player_id=player_id,
                player_name=player_name,
                team=team,
                game_id=game_id,
                category=StatCategory.PASSING,
                stat_name="yards",
                stat_value=stat_values.get(2, 0),
                timestamp=datetime.now(),
                source=self.source_name
            ))
            
            updates.append(PlayerUpdate(
                player_id=player_id,
                player_name=player_name,
                team=team,
                game_id=game_id,
                category=StatCategory.PASSING,
                stat_name="touchdowns",
                stat_value=stat_values.get(3, 0),
                timestamp=datetime.now(),
                source=self.source_name
            ))
        
        return updates
    
    def _parse_rushing_stats(self, stats: Dict, team: str, game_id: str) -> List[PlayerUpdate]:
        """Parse running back rushing statistics"""
        updates = []
        
        for athlete in stats.get('athletes', []):
            player_name = athlete.get('athlete', {}).get('displayName', '')
            player_id = athlete.get('athlete', {}).get('id', '')
            stats_data = athlete.get('stats', [])
            
            stat_values = {i: stat for i, stat in enumerate(stats_data)}
            
            updates.append(PlayerUpdate(
                player_id=player_id,
                player_name=player_name,
                team=team,
                game_id=game_id,
                category=StatCategory.RUSHING,
                stat_name="carries",
                stat_value=stat_values.get(0, 0),
                timestamp=datetime.now(),
                source=self.source_name
            ))
            
            updates.append(PlayerUpdate(
                player_id=player_id,
                player_name=player_name,
                team=team,
                game_id=game_id,
                category=StatCategory.RUSHING,
                stat_name="yards",
                stat_value=stat_values.get(1, 0),
                timestamp=datetime.now(),
                source=self.source_name
            ))
            
            updates.append(PlayerUpdate(
                player_id=player_id,
                player_name=player_name,
                team=team,
                game_id=game_id,
                category=StatCategory.RUSHING,
                stat_name="touchdowns",
                stat_value=stat_values.get(2, 0),
                timestamp=datetime.now(),
                source=self.source_name
            ))
        
        return updates
    
    def _parse_receiving_stats(self, stats: Dict, team: str, game_id: str) -> List[PlayerUpdate]:
        """Parse wide receiver/tight end receiving statistics"""
        updates = []
        
        for athlete in stats.get('athletes', []):
            player_name = athlete.get('athlete', {}).get('displayName', '')
            player_id = athlete.get('athlete', {}).get('id', '')
            stats_data = athlete.get('stats', [])
            
            stat_values = {i: stat for i, stat in enumerate(stats_data)}
            
            updates.append(PlayerUpdate(
                player_id=player_id,
                player_name=player_name,
                team=team,
                game_id=game_id,
                category=StatCategory.RECEIVING,
                stat_name="receptions",
                stat_value=stat_values.get(0, 0),
                timestamp=datetime.now(),
                source=self.source_name
            ))
            
            updates.append(PlayerUpdate(
                player_id=player_id,
                player_name=player_name,
                team=team,
                game_id=game_id,
                category=StatCategory.RECEIVING,
                stat_name="yards",
                stat_value=stat_values.get(1, 0),
                timestamp=datetime.now(),
                source=self.source_name
            ))
            
            updates.append(PlayerUpdate(
                player_id=player_id,
                player_name=player_name,
                team=team,
                game_id=game_id,
                category=StatCategory.RECEIVING,
                stat_name="touchdowns",
                stat_value=stat_values.get(2, 0),
                timestamp=datetime.now(),
                source=self.source_name
            ))
        
        return updates
    
    def _normalize_game_status(self, espn_status: str) -> GameStatus:
        """Convert ESPN status strings to standardized GameStatus enum"""
        status_map = {
            'scheduled': GameStatus.SCHEDULED,
            'in': GameStatus.IN_PROGRESS,
            'halftime': GameStatus.HALFTIME,
            'final': GameStatus.FINAL,
            'postponed': GameStatus.POSTPONED,
            'canceled': GameStatus.CANCELED
        }
        return status_map.get(espn_status.lower(), GameStatus.SCHEDULED)


# ===== NFL.COM DATA SOURCE IMPLEMENTATION =====
class NFLComDataSource(NFLDataSource):
    """
    NFL.com official data source
    Provides authoritative injury reports and roster information
    """
    
    def __init__(self, session: aiohttp.ClientSession, rate_limiter: RateLimiter):
        super().__init__(session, rate_limiter)
        self.source_name = DataSource.NFL_COM
        self.base_url = Config.NFL_API_BASE
        
    async def get_game_data(self, game_id: str) -> Optional[GameData]:
        """
        NFL.com focuses on official data, less real-time game updates
        Returns basic game info when available
        """
        url = f"{self.base_url}/games/{game_id}"
        data = await self._make_request(url)
        
        if not data:
            return None
            
        try:
            return self._parse_nfl_game_data(data)
        except Exception as e:
            logging.error(f"Error parsing NFL.com game data: {e}")
            return None
    
    async def get_player_stats(self, game_id: str) -> List[PlayerUpdate]:
        """
        NFL.com player stats - official but may be delayed
        """
        url = f"{self.base_url}/games/{game_id}/stats"
        data = await self._make_request(url)
        
        if not data:
            return []
            
        try:
            return self._parse_nfl_player_stats(data, game_id)
        except Exception as e:
            logging.error(f"Error parsing NFL.com player stats: {e}")
            return []
    
    async def get_injury_reports(self, team: str = None) -> List[InjuryReport]:
        """
        Fetch official NFL injury reports
        Most authoritative source for injury status
        """
        if team:
            url = f"{self.base_url}/teams/{team}/injuries"
        else:
            url = f"{self.base_url}/injuries"
            
        data = await self._make_request(url)
        
        if not data:
            return []
            
        try:
            return self._parse_nfl_injury_reports(data)
        except Exception as e:
            logging.error(f"Error parsing NFL.com injury reports: {e}")
            return []
    
    def _parse_nfl_game_data(self, data: Dict) -> GameData:
        """Parse NFL.com game data format"""
        game_detail = data.get('gameDetail', {})
        
        return GameData(
            game_id=str(game_detail.get('id', '')),
            week=game_detail.get('week', 0),
            season=game_detail.get('season', 2024),
            home_team=game_detail.get('homeTeam', {}).get('abbreviation', ''),
            away_team=game_detail.get('visitorTeam', {}).get('abbreviation', ''),
            home_score=game_detail.get('homePointsTotal', 0),
            away_score=game_detail.get('visitorPointsTotal', 0),
            quarter=game_detail.get('quarter', None),
            time_remaining=game_detail.get('gameClock', None),
            status=self._normalize_nfl_status(game_detail.get('phase', 'PREGAME')),
            temperature=game_detail.get('weather', {}).get('currentTemp', None),
            timestamp=datetime.now(),
            source=self.source_name
        )
    
    def _parse_nfl_player_stats(self, data: Dict, game_id: str) -> List[PlayerUpdate]:
        """Parse NFL.com player statistics"""
        updates = []
        
        stats = data.get('stats', {})
        
        # Process passing stats
        passing = stats.get('passing', {})
        for team_abbr, team_stats in passing.items():
            for player_id, player_stats in team_stats.items():
                player_name = player_stats.get('playerName', '')
                
                for stat_name, stat_value in player_stats.items():
                    if stat_name != 'playerName':
                        updates.append(PlayerUpdate(
                            player_id=player_id,
                            player_name=player_name,
                            team=team_abbr,
                            game_id=game_id,
                            category=StatCategory.PASSING,
                            stat_name=stat_name,
                            stat_value=stat_value,
                            timestamp=datetime.now(),
                            source=self.source_name
                        ))
        
        # Process rushing stats
        rushing = stats.get('rushing', {})
        for team_abbr, team_stats in rushing.items():
            for player_id, player_stats in team_stats.items():
                player_name = player_stats.get('playerName', '')
                
                for stat_name, stat_value in player_stats.items():
                    if stat_name != 'playerName':
                        updates.append(PlayerUpdate(
                            player_id=player_id,
                            player_name=player_name,
                            team=team_abbr,
                            game_id=game_id,
                            category=StatCategory.RUSHING,
                            stat_name=stat_name,
                            stat_value=stat_value,
                            timestamp=datetime.now(),
                            source=self.source_name
                        ))
        
        # Process receiving stats
        receiving = stats.get('receiving', {})
        for team_abbr, team_stats in receiving.items():
            for player_id, player_stats in team_stats.items():
                player_name = player_stats.get('playerName', '')
                
                for stat_name, stat_value in player_stats.items():
                    if stat_name != 'playerName':
                        updates.append(PlayerUpdate(
                            player_id=player_id,
                            player_name=player_name,
                            team=team_abbr,
                            game_id=game_id,
                            category=StatCategory.RECEIVING,
                            stat_name=stat_name,
                            stat_value=stat_value,
                            timestamp=datetime.now(),
                            source=self.source_name
                        ))
        
        return updates
    
    def _parse_nfl_injury_reports(self, data: Dict) -> List[InjuryReport]:
        """Parse official NFL injury reports"""
        reports = []
        
        for team_data in data.get('teams', []):
            team_abbr = team_data.get('abbr', '')
            
            for player in team_data.get('players', []):
                reports.append(InjuryReport(
                    player_id=str(player.get('esbId', '')),
                    player_name=player.get('displayName', ''),
                    team=team_abbr,
                    injury_status=self._normalize_injury_status(
                        player.get('injuryStatus', '')
                    ),
                    body_part=player.get('injuryBodyPart', ''),
                    description=player.get('injuryNotes', ''),
                    date_reported=self._parse_injury_date(
                        player.get('injuryStartDate', '')
                    ),
                    source=self.source_name
                ))
        
        return reports
    
    def _normalize_nfl_status(self, nfl_status: str) -> GameStatus:
        """Convert NFL.com status to GameStatus enum"""
        status_map = {
            'PREGAME': GameStatus.SCHEDULED,
            'INGAME': GameStatus.IN_PROGRESS,
            'HALFTIME': GameStatus.HALFTIME,
            'FINAL': GameStatus.FINAL,
            'FINAL_OVERTIME': GameStatus.FINAL,
            'POSTPONED': GameStatus.POSTPONED,
            'CANCELED': GameStatus.CANCELED
        }
        return status_map.get(nfl_status, GameStatus.SCHEDULED)
    
    def _normalize_injury_status(self, status: str) -> InjuryStatus:
        """Convert NFL injury status to InjuryStatus enum"""
        status_map = {
            'Out': InjuryStatus.OUT,
            'Doubtful': InjuryStatus.DOUBTFUL,
            'Questionable': InjuryStatus.QUESTIONABLE,
            'Probable': InjuryStatus.PROBABLE,
            'Limited': InjuryStatus.LIMITED,
            'Full': InjuryStatus.HEALTHY,
            'Did Not Practice': InjuryStatus.DNP,
            'Practice Squad': InjuryStatus.PRACTICE_SQUAD
        }
        return status_map.get(status, InjuryStatus.UNKNOWN)
    
    def _parse_injury_date(self, date_str: str) -> Optional[datetime]:
        """Parse NFL injury date format"""
        if not date_str:
            return None
            
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            return None


# ===== YAHOO SPORTS DATA SOURCE =====
class YahooSportsDataSource(NFLDataSource):
    """
    Yahoo Sports fantasy-focused data source
    Excellent for player projections and fantasy-relevant stats
    """
    
    def __init__(self, session: aiohttp.ClientSession, rate_limiter: RateLimiter):
        super().__init__(session, rate_limiter)
        self.source_name = DataSource.YAHOO_SPORTS
        self.base_url = Config.YAHOO_API_BASE
        
    async def get_game_data(self, game_id: str) -> Optional[GameData]:
        """Yahoo Sports game data - basic coverage"""
        url = f"{self.base_url}/games/{game_id}"
        data = await self._make_request(url)
        
        if not data:
            return None
            
        try:
            return self._parse_yahoo_game_data(data)
        except Exception as e:
            logging.error(f"Error parsing Yahoo game data: {e}")
            return None
    
    async def get_player_stats(self, game_id: str) -> List[PlayerUpdate]:
        """Yahoo Sports player stats with fantasy context"""
        url = f"{self.base_url}/games/{game_id}/fantasy"
        data = await self._make_request(url)
        
        if not data:
            return []
            
        try:
            return self._parse_yahoo_player_stats(data, game_id)
        except Exception as e:
            logging.error(f"Error parsing Yahoo player stats: {e}")
            return []
    
    async def get_injury_reports(self, team: str = None) -> List[InjuryReport]:
        """Yahoo injury reports with fantasy impact analysis"""
        url = f"{self.base_url}/injuries"
        if team:
            url += f"?team={team}"
            
        data = await self._make_request(url)
        
        if not data:
            return []
            
        try:
            return self._parse_yahoo_injury_reports(data)
        except Exception as e:
            logging.error(f"Error parsing Yahoo injury reports: {e}")
            return []
    
    def _parse_yahoo_game_data(self, data: Dict) -> GameData:
        """Parse Yahoo Sports game data"""
        game = data.get('game', {})
        
        return GameData(
            game_id=str(game.get('game_id', '')),
            week=game.get('week', 0),
            season=game.get('season', 2024),
            home_team=game.get('home_team', ''),
            away_team=game.get('away_team', ''),
            home_score=game.get('home_score', 0),
            away_score=game.get('away_score', 0),
            quarter=game.get('quarter', None),
            time_remaining=game.get('time_remaining', None),
            status=self._normalize_yahoo_status(game.get('status', 'scheduled')),
            temperature=None,  # Yahoo doesn't provide weather
            timestamp=datetime.now(),
            source=self.source_name
        )
    
    def _parse_yahoo_player_stats(self, data: Dict, game_id: str) -> List[PlayerUpdate]:
        """Parse Yahoo fantasy-focused player stats"""
        updates = []
        
        for player_data in data.get('players', []):
            player_id = str(player_data.get('player_id', ''))
            player_name = player_data.get('name', '')
            team = player_data.get('team', '')
            stats = player_data.get('stats', {})
            
            # Yahoo provides fantasy-relevant stats
            for stat_name, stat_value in stats.items():
                category = self._determine_stat_category(stat_name)
                
                updates.append(PlayerUpdate(
                    player_id=player_id,
                    player_name=player_name,
                    team=team,
                    game_id=game_id,
                    category=category,
                    stat_name=stat_name,
                    stat_value=stat_value,
                    timestamp=datetime.now(),
                    source=self.source_name
                ))
        
        return updates
    
    def _parse_yahoo_injury_reports(self, data: Dict) -> List[InjuryReport]:
        """Parse Yahoo injury reports with fantasy context"""
        reports = []
        
        for injury_data in data.get('injuries', []):
            reports.append(InjuryReport(
                player_id=str(injury_data.get('player_id', '')),
                player_name=injury_data.get('player_name', ''),
                team=injury_data.get('team', ''),
                injury_status=self._normalize_injury_status(
                    injury_data.get('status', '')
                ),
                body_part=injury_data.get('injury', ''),
                description=injury_data.get('note', ''),
                date_reported=self._parse_yahoo_date(
                    injury_data.get('date', '')
                ),
                source=self.source_name
            ))
        
        return reports
    
    def _normalize_yahoo_status(self, yahoo_status: str) -> GameStatus:
        """Convert Yahoo status to GameStatus enum"""
        status_map = {
            'scheduled': GameStatus.SCHEDULED,
            'live': GameStatus.IN_PROGRESS,
            'halftime': GameStatus.HALFTIME,
            'final': GameStatus.FINAL,
            'postponed': GameStatus.POSTPONED,
            'canceled': GameStatus.CANCELED
        }
        return status_map.get(yahoo_status.lower(), GameStatus.SCHEDULED)
    
    def _determine_stat_category(self, stat_name: str) -> StatCategory:
        """Determine stat category from Yahoo stat name"""
        stat_name_lower = stat_name.lower()
        
        if any(word in stat_name_lower for word in ['pass', 'completion', 'attempt']):
            return StatCategory.PASSING
        elif any(word in stat_name_lower for word in ['rush', 'carry', 'run']):
            return StatCategory.RUSHING
        elif any(word in stat_name_lower for word in ['rec', 'catch', 'target']):
            return StatCategory.RECEIVING
        elif any(word in stat_name_lower for word in ['kick', 'fg', 'pat']):
            return StatCategory.KICKING
        elif any(word in stat_name_lower for word in ['def', 'tackle', 'sack', 'int']):
            return StatCategory.DEFENSE
        else:
            return StatCategory.PASSING  # Default fallback
    
    def _parse_yahoo_date(self, date_str: str) -> Optional[datetime]:
        """Parse Yahoo date format"""
        if not date_str:
            return None
            
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            try:
                return datetime.strptime(date_str, '%m/%d/%Y')
            except ValueError:
                return None


# ===== THE ATHLETIC DATA SOURCE =====
class TheAthleticDataSource(NFLDataSource):
    """
    The Athletic premium sports content
    Provides in-depth analysis and insider injury information
    """
    
    def __init__(self, session: aiohttp.ClientSession, rate_limiter: RateLimiter):
        super().__init__(session, rate_limiter)
        self.source_name = DataSource.THE_ATHLETIC
        self.base_url = Config.ATHLETIC_API_BASE
        self.headers.update({
            "Authorization": f"Bearer {Config.ATHLETIC_API_KEY}"
        })
        
    async def get_game_data(self, game_id: str) -> Optional[GameData]:
        """The Athletic focuses on analysis rather than live scores"""
        return None  # Not a primary use case for The Athletic
    
    async def get_player_stats(self, game_id: str) -> List[PlayerUpdate]:
        """The Athletic doesn't provide real-time stats"""
        return []  # Not a primary use case for The Athletic
    
    async def get_injury_reports(self, team: str = None) -> List[InjuryReport]:
        """
        The Athletic insider injury reports
        Premium content with detailed analysis
        """
        url = f"{self.base_url}/nfl/injuries"
        if team:
            url += f"?team={team}"
            
        data = await self._make_request(url)
        
        if not data:
            return []
            
        try:
            return self._parse_athletic_injury_reports(data)
        except Exception as e:
            logging.error(f"Error parsing Athletic injury reports: {e}")
            return []
    
    def _parse_athletic_injury_reports(self, data: Dict) -> List[InjuryReport]:
        """Parse The Athletic detailed injury reports"""
        reports = []
        
        for report in data.get('injury_reports', []):
            reports.append(InjuryReport(
                player_id=str(report.get('player_id', '')),
                player_name=report.get('player_name', ''),
                team=report.get('team_abbr', ''),
                injury_status=self._normalize_injury_status(
                    report.get('status', '')
                ),
                body_part=report.get('injury_type', ''),
                description=report.get('detailed_analysis', ''),
                date_reported=self._parse_athletic_date(
                    report.get('report_date', '')
                ),
                source=self.source_name
            ))
        
        return reports
    
    def _parse_athletic_date(self, date_str: str) -> Optional[datetime]:
        """Parse The Athletic date format"""
        if not date_str:
            return None
            
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except ValueError:
            return None


# ===== WEB SCRAPER DATA SOURCE =====
class WebScraperDataSource(NFLDataSource):
    """
    Web scraper for sites without APIs
    Handles various NFL information websites with BeautifulSoup
    """
    
    def __init__(self, session: aiohttp.ClientSession, rate_limiter: RateLimiter):
        super().__init__(session, rate_limiter)
        self.source_name = DataSource.WEB_SCRAPER
        self.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        
    async def get_game_data(self, game_id: str) -> Optional[GameData]:
        """Scrape game data from various NFL sites"""
        # Implementation depends on target websites
        return None
    
    async def get_player_stats(self, game_id: str) -> List[PlayerUpdate]:
        """Scrape player stats from various sources"""
        return []
    
    async def get_injury_reports(self, team: str = None) -> List[InjuryReport]:
        """
        Scrape injury reports from multiple sources
        Useful for aggregating information not available via APIs
        """
        reports = []
        
        # Example: Scrape from Pro Football Reference
        pfr_reports = await self._scrape_pro_football_reference_injuries(team)
        reports.extend(pfr_reports)
        
        # Example: Scrape from other sources
        # Add more scraping targets as needed
        
        return reports
    
    async def _scrape_pro_football_reference_injuries(self, team: str = None) -> List[InjuryReport]:
        """Scrape injury data from Pro Football Reference"""
        url = "https://www.pro-football-reference.com/years/2024/injuries.htm"
        
        try:
            async with self.session.get(url, headers=self.headers) as response:
                if response.status != 200:
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Find injury table
                injury_table = soup.find('table', {'id': 'injuries'})
                if not injury_table:
                    return []
                
                reports = []
                rows = injury_table.find('tbody').find_all('tr')
                
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) < 6:
                        continue
                    
                    player_name = cells[0].get_text(strip=True)
                    team_abbr = cells[1].get_text(strip=True)
                    injury_desc = cells[2].get_text(strip=True)
                    status = cells[3].get_text(strip=True)
                    date_str = cells[4].get_text(strip=True)
                    
                    # Skip if team filter doesn't match
                    if team and team.upper() != team_abbr.upper():
                        continue
                    
                    # Parse injury body part from description
                    body_part = self._extract_body_part(injury_desc)
                    
                    reports.append(InjuryReport(
                        player_id="",  # PFR doesn't provide player IDs
                        player_name=player_name,
                        team=team_abbr,
                        injury_status=self._normalize_pfr_status(status),
                        body_part=body_part,
                        description=injury_desc,
                        date_reported=self._parse_pfr_date(date_str),
                        source=self.source_name
                    ))
                
                return reports
                
        except Exception as e:
            logging.error(f"Error scraping Pro Football Reference: {e}")
            return []
    
    def _extract_body_part(self, injury_desc: str) -> str:
        """Extract body part from injury description"""
        body_parts = [
            'knee', 'ankle', 'shoulder', 'hamstring', 'groin', 'back',
            'concussion', 'head', 'neck', 'wrist', 'hand', 'finger',
            'hip', 'thigh', 'calf', 'foot', 'toe', 'elbow', 'arm',
            'chest', 'ribs', 'abdomen', 'quad', 'achilles'
        ]
        
        injury_lower = injury_desc.lower()
        for part in body_parts:
            if part in injury_lower:
                return part.title()
        
        return "Unknown"
    
    def _normalize_pfr_status(self, status: str) -> InjuryStatus:
        """Normalize Pro Football Reference injury status"""
        status_lower = status.lower()
        
        if 'out' in status_lower:
            return InjuryStatus.OUT
        elif 'doubtful' in status_lower:
            return InjuryStatus.DOUBTFUL
        elif 'questionable' in status_lower:
            return InjuryStatus.QUESTIONABLE
        elif 'probable' in status_lower:
            return InjuryStatus.PROBABLE
        else:
            return InjuryStatus.UNKNOWN
    
    def _parse_pfr_date(self, date_str: str) -> Optional[datetime]:
        """Parse Pro Football Reference date format"""
        if not date_str or date_str == '--':
            return None
            
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            try:
                return datetime.strptime(date_str, '%m/%d')
                # Assume current year if only month/day provided
            except ValueError:
                return None


# ===== DATA SOURCE MANAGER =====
class DataSourceManager:
    """
    Manages multiple NFL data sources
    Handles failover, data aggregation, and source prioritization
    """
    
    def __init__(self, redis_client):
        """
        Initialize with Redis client for rate limiting
        
        Args:
            redis_client: Redis client for distributed rate limiting
        """
        self.rate_limiter = RateLimiter(redis_client)
        self.session = None
        self.sources = {}
        
    async def initialize(self):
        """Initialize HTTP session and data sources"""
        connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=30,
            keepalive_timeout=30
        )
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=10)
        )
        
        # Initialize all data sources
        self.sources = {
            DataSource.ESPN: ESPNDataSource(self.session, self.rate_limiter),
            DataSource.NFL_COM: NFLComDataSource(self.session, self.rate_limiter),
            DataSource.YAHOO_SPORTS: YahooSportsDataSource(self.session, self.rate_limiter),
            DataSource.THE_ATHLETIC: TheAthleticDataSource(self.session, self.rate_limiter),
            DataSource.WEB_SCRAPER: WebScraperDataSource(self.session, self.rate_limiter)
        }
    
    async def close(self):
        """Clean up HTTP session"""
        if self.session:
            await self.session.close()
    
    async def get_game_data(
        self, 
        game_id: str, 
        preferred_sources: List[DataSource] = None
    ) -> Optional[GameData]:
        """
        Fetch game data with source failover
        
        Args:
            game_id: Game identifier
            preferred_sources: Ordered list of preferred sources
            
        Returns:
            GameData from first successful source
        """
        if not preferred_sources:
            preferred_sources = [DataSource.ESPN, DataSource.NFL_COM, DataSource.YAHOO_SPORTS]
        
        for source in preferred_sources:
            if source not in self.sources:
                continue
                
            try:
                data = await self.sources[source].get_game_data(game_id)
                if data:
                    logging.info(f"Got game data for {game_id} from {source.value}")
                    return data
            except Exception as e:
                logging.warning(f"Failed to get game data from {source.value}: {e}")
                continue
        
        logging.error(f"Failed to get game data for {game_id} from all sources")
        return None
    
    async def get_player_stats(
        self, 
        game_id: str, 
        preferred_sources: List[DataSource] = None
    ) -> List[PlayerUpdate]:
        """
        Fetch player stats with source aggregation
        Combines data from multiple sources for comprehensive coverage
        """
        if not preferred_sources:
            preferred_sources = [DataSource.ESPN, DataSource.NFL_COM, DataSource.YAHOO_SPORTS]
        
        all_updates = []
        
        for source in preferred_sources:
            if source not in self.sources:
                continue
                
            try:
                updates = await self.sources[source].get_player_stats(game_id)
                all_updates.extend(updates)
                logging.info(f"Got {len(updates)} player updates from {source.value}")
            except Exception as e:
                logging.warning(f"Failed to get player stats from {source.value}: {e}")
                continue
        
        # Deduplicate and merge updates
        return self._merge_player_updates(all_updates)
    
    async def get_injury_reports(
        self, 
        team: str = None, 
        preferred_sources: List[DataSource] = None
    ) -> List[InjuryReport]:
        """
        Fetch injury reports from multiple sources
        Aggregates data for comprehensive injury coverage
        """
        if not preferred_sources:
            preferred_sources = [
                DataSource.NFL_COM, 
                DataSource.THE_ATHLETIC, 
                DataSource.WEB_SCRAPER,
                DataSource.YAHOO_SPORTS
            ]
        
        all_reports = []
        
        for source in preferred_sources:
            if source not in self.sources:
                continue
                
            try:
                reports = await self.sources[source].get_injury_reports(team)
                all_reports.extend(reports)
                logging.info(f"Got {len(reports)} injury reports from {source.value}")
            except Exception as e:
                logging.warning(f"Failed to get injury reports from {source.value}: {e}")
                continue
        
        # Deduplicate and merge reports
        return self._merge_injury_reports(all_reports)
    
    def _merge_player_updates(self, updates: List[PlayerUpdate]) -> List[PlayerUpdate]:
        """
        Merge player updates from multiple sources
        Prioritizes more recent updates and authoritative sources
        """
        # Group by player + stat combination
        update_groups = {}
        
        for update in updates:
            key = f"{update.player_id}_{update.stat_name}_{update.game_id}"
            
            if key not in update_groups:
                update_groups[key] = []
            
            update_groups[key].append(update)
        
        # Select best update from each group
        merged_updates = []
        
        for group in update_groups.values():
            # Sort by source priority and timestamp
            group.sort(key=lambda x: (
                self._get_source_priority(x.source),
                x.timestamp
            ), reverse=True)
            
            merged_updates.append(group[0])
        
        return merged_updates
    
    def _merge_injury_reports(self, reports: List[InjuryReport]) -> List[InjuryReport]:
        """
        Merge injury reports from multiple sources
        Combines information and prioritizes authoritative sources
        """
        # Group by player
        report_groups = {}
        
        for report in reports:
            key = f"{report.player_name}_{report.team}".lower()
            
            if key not in report_groups:
                report_groups[key] = []
            
            report_groups[key].append(report)
        
        # Merge reports for each player
        merged_reports = []
        
        for group in report_groups.values():
            # Sort by source priority
            group.sort(key=lambda x: self._get_source_priority(x.source))
            
            # Take the most authoritative report as base
            base_report = group[0]
            
            # Merge additional details from other sources
            for additional_report in group[1:]:
                if not base_report.description and additional_report.description:
                    base_report.description = additional_report.description
                
                if not base_report.body_part and additional_report.body_part:
                    base_report.body_part = additional_report.body_part
            
            merged_reports.append(base_report)
        
        return merged_reports
    
    def _get_source_priority(self, source: DataSource) -> int:
        """
        Get source priority for merging decisions
        Higher numbers = higher priority
        """
        priority_map = {
            DataSource.NFL_COM: 5,      # Official source
            DataSource.ESPN: 4,         # Major sports network
            DataSource.THE_ATHLETIC: 3, # Premium content
            DataSource.YAHOO_SPORTS: 2, # Fantasy focus
            DataSource.WEB_SCRAPER: 1   # Scraped data
        }
        
        return priority_map.get(source, 0)


# ===== ASYNC CONTEXT MANAGER =====
async def create_data_source_manager(redis_client) -> DataSourceManager:
    """
    Factory function to create and initialize DataSourceManager
    
    Args:
        redis_client: Redis client for rate limiting
        
    Returns:
        Initialized DataSourceManager
    """
    manager = DataSourceManager(redis_client)
    await manager.initialize()
    return manager


# ===== USAGE EXAMPLE =====
async def example_usage():
    """
    Example of how to use the NFL data source system
    """
    import redis.asyncio as redis
    
    # Initialize Redis connection
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
    
    # Create and initialize data source manager
    manager = await create_data_source_manager(redis_client)
    
    try:
        # Fetch game data with failover
        game_data = await manager.get_game_data("401547439")
        if game_data:
            print(f"Game: {game_data.away_team} @ {game_data.home_team}")
            print(f"Score: {game_data.away_score} - {game_data.home_score}")
            print(f"Status: {game_data.status}")
        
        # Fetch player stats from multiple sources
        player_stats = await manager.get_player_stats("401547439")
        print(f"Retrieved {len(player_stats)} player stat updates")
        
        # Fetch injury reports
        injury_reports = await manager.get_injury_reports("KC")
        print(f"Retrieved {len(injury_reports)} injury reports for KC")
        
        for report in injury_reports[:3]:  # Show first 3
            print(f"{report.player_name}: {report.injury_status} ({report.body_part})")
        
    finally:
        # Clean up
        await manager.close()
        await redis_client.close()


if __name__ == "__main__":
    # Run example
    asyncio.run(example_usage())
