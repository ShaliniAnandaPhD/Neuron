#!/usr/bin/env python3
"""
Synthetic Market Data Generator
Realistic financial market data simulation for pipeline testing

This module generates:
- Realistic stock price movements
- Market volatility patterns
- Trading volume simulation
- Market condition transitions
- Real-time streaming data
"""

import asyncio
import random
import time
import math
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, AsyncGenerator
from dataclasses import dataclass
from enum import Enum
import uuid

from .config_manager import PipelineConfig


class MarketCondition(Enum):
    """Market condition types"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    VOLATILE = "volatile"
    STABLE = "stable"
    CRASH = "crash"
    RECOVERY = "recovery"


@dataclass
class MarketMessage:
    """Individual market data message"""
    message_id: str
    symbol: str
    price: float
    volume: int
    timestamp: datetime
    market_condition: MarketCondition
    change_percent: float
    bid_ask_spread: float
    
    # Additional market data
    high_24h: float
    low_24h: float
    volume_24h: int
    market_cap: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "message_id": self.message_id,
            "symbol": self.symbol,
            "price": self.price,
            "volume": self.volume,
            "timestamp": self.timestamp.isoformat(),
            "market_condition": self.market_condition.value,
            "change_percent": self.change_percent,
            "bid_ask_spread": self.bid_ask_spread,
            "high_24h": self.high_24h,
            "low_24h": self.low_24h,
            "volume_24h": self.volume_24h,
            "market_cap": self.market_cap
        }


@dataclass
class StockState:
    """Internal state for stock simulation"""
    symbol: str
    current_price: float
    base_price: float
    volatility: float
    trend: float
    volume_base: int
    last_update: datetime
    
    # Price history for realistic movements
    price_history: List[float]
    volume_history: List[int]
    
    # Market making parameters
    bid_ask_spread_pct: float = 0.01  # 1% spread
    
    def __post_init__(self):
        if not self.price_history:
            self.price_history = [self.current_price]
        if not self.volume_history:
            self.volume_history = [self.volume_base]


class MarketSimulator:
    """Advanced market simulation engine"""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Market state
        self.current_condition = MarketCondition.STABLE
        self.condition_start_time = datetime.now()
        self.condition_duration = timedelta(seconds=config.market_condition_change_interval_seconds)
        
        # Volatility settings
        self.volatility_enabled = config.market_volatility_enabled
        self.global_volatility_multiplier = 1.0
        
        # Initialize stock universe
        self.stocks = self._initialize_stock_universe()
        
        # Market events
        self.scheduled_events: List[Dict[str, Any]] = []
        self._schedule_market_events()
        
        self.logger.info(f"Market simulator initialized with {len(self.stocks)} symbols")
    
    def _initialize_stock_universe(self) -> Dict[str, StockState]:
        """Initialize realistic stock universe"""
        
        # Major stocks with realistic parameters
        stock_configs = [
            # Tech Giants
            ("AAPL", 150.0, 0.25, 1000000),   # Apple
            ("GOOGL", 140.0, 0.28, 800000),   # Google
            ("MSFT", 330.0, 0.24, 900000),    # Microsoft
            ("AMZN", 130.0, 0.30, 600000),    # Amazon
            ("TSLA", 200.0, 0.45, 1200000),   # Tesla
            ("META", 300.0, 0.35, 700000),    # Meta
            
            # Financial
            ("JPM", 140.0, 0.20, 500000),     # JPMorgan
            ("BAC", 30.0, 0.22, 800000),      # Bank of America
            ("WFC", 45.0, 0.24, 600000),      # Wells Fargo
            
            # Healthcare
            ("JNJ", 160.0, 0.15, 400000),     # Johnson & Johnson
            ("PFE", 35.0, 0.25, 900000),      # Pfizer
            ("UNH", 480.0, 0.18, 200000),     # UnitedHealth
            
            # Consumer
            ("KO", 60.0, 0.12, 700000),       # Coca-Cola
            ("PG", 140.0, 0.14, 300000),      # Procter & Gamble
            ("WMT", 160.0, 0.16, 800000),     # Walmart
            
            # Energy
            ("XOM", 110.0, 0.35, 600000),     # ExxonMobil
            ("CVX", 150.0, 0.32, 400000),     # Chevron
            
            # Crypto-related (higher volatility)
            ("COIN", 80.0, 0.60, 1500000),    # Coinbase
            ("MSTR", 180.0, 0.70, 800000),    # MicroStrategy
            
            # Meme stocks (very volatile)
            ("GME", 25.0, 0.80, 2000000),     # GameStop
        ]
        
        stocks = {}
        
        # Use configured number of symbols or all available
        symbols_to_use = min(self.config.market_symbols_count, len(stock_configs))
        
        for symbol, base_price, volatility, volume_base in stock_configs[:symbols_to_use]:
            # Add some randomness to starting prices
            current_price = base_price * random.uniform(0.95, 1.05)
            
            stocks[symbol] = StockState(
                symbol=symbol,
                current_price=current_price,
                base_price=base_price,
                volatility=volatility,
                trend=random.uniform(-0.1, 0.1),  # Initial trend
                volume_base=volume_base,
                last_update=datetime.now(),
                price_history=[current_price],
                volume_history=[volume_base]
            )
        
        return stocks
    
    def _schedule_market_events(self):
        """Schedule realistic market events"""
        current_time = datetime.now()
        
        # Schedule various market events
        events = [
            # Earnings announcements (cause volatility spikes)
            {
                "time": current_time + timedelta(minutes=random.randint(5, 30)),
                "type": "earnings",
                "symbol": random.choice(list(self.stocks.keys())),
                "impact": random.choice(["positive", "negative", "mixed"])
            },
            
            # Market news events
            {
                "time": current_time + timedelta(minutes=random.randint(10, 45)),
                "type": "news",
                "impact": "market_wide",
                "sentiment": random.choice(["positive", "negative"])
            },
            
            # Sector rotation
            {
                "time": current_time + timedelta(minutes=random.randint(15, 60)),
                "type": "sector_rotation",
                "from_sector": "tech",
                "to_sector": "financials"
            }
        ]
        
        self.scheduled_events.extend(events)
    
    def update_market_condition(self):
        """Update overall market condition"""
        now = datetime.now()
        
        # Check if condition should change
        if now - self.condition_start_time > self.condition_duration:
            # Transition probabilities based on current condition
            transitions = {
                MarketCondition.STABLE: {
                    MarketCondition.BULLISH: 0.3,
                    MarketCondition.BEARISH: 0.3,
                    MarketCondition.VOLATILE: 0.2,
                    MarketCondition.STABLE: 0.2
                },
                MarketCondition.BULLISH: {
                    MarketCondition.STABLE: 0.4,
                    MarketCondition.VOLATILE: 0.3,
                    MarketCondition.BEARISH: 0.2,
                    MarketCondition.BULLISH: 0.1
                },
                MarketCondition.BEARISH: {
                    MarketCondition.STABLE: 0.4,
                    MarketCondition.VOLATILE: 0.3,
                    MarketCondition.CRASH: 0.1,
                    MarketCondition.RECOVERY: 0.1,
                    MarketCondition.BEARISH: 0.1
                },
                MarketCondition.VOLATILE: {
                    MarketCondition.STABLE: 0.3,
                    MarketCondition.BULLISH: 0.2,
                    MarketCondition.BEARISH: 0.2,
                    MarketCondition.CRASH: 0.05,
                    MarketCondition.VOLATILE: 0.25
                },
                MarketCondition.CRASH: {
                    MarketCondition.RECOVERY: 0.6,
                    MarketCondition.BEARISH: 0.3,
                    MarketCondition.CRASH: 0.1
                },
                MarketCondition.RECOVERY: {
                    MarketCondition.BULLISH: 0.4,
                    MarketCondition.STABLE: 0.3,
                    MarketCondition.VOLATILE: 0.2,
                    MarketCondition.RECOVERY: 0.1
                }
            }
            
            # Select new condition
            current_transitions = transitions[self.current_condition]
            rand = random.random()
            cumulative = 0.0
            
            for condition, probability in current_transitions.items():
                cumulative += probability
                if rand <= cumulative:
                    old_condition = self.current_condition
                    self.current_condition = condition
                    self.condition_start_time = now
                    
                    # Update global volatility based on condition
                    self._update_global_volatility()
                    
                    # Randomize next condition duration
                    base_duration = self.config.market_condition_change_interval_seconds
                    self.condition_duration = timedelta(
                        seconds=base_duration * random.uniform(0.5, 2.0)
                    )
                    
                    if old_condition != condition:
                        self.logger.info(f"Market condition changed: {old_condition.value} → {condition.value}")
                    
                    break
    
    def _update_global_volatility(self):
        """Update global volatility multiplier based on market condition"""
        volatility_multipliers = {
            MarketCondition.STABLE: 0.5,
            MarketCondition.BULLISH: 0.7,
            MarketCondition.BEARISH: 1.2,
            MarketCondition.VOLATILE: 2.0,
            MarketCondition.CRASH: 3.5,
            MarketCondition.RECOVERY: 1.5
        }
        
        self.global_volatility_multiplier = volatility_multipliers.get(
            self.current_condition, 1.0
        )
    
    def _process_scheduled_events(self):
        """Process any scheduled market events"""
        current_time = datetime.now()
        
        # Check for events that should trigger
        triggered_events = [
            event for event in self.scheduled_events
            if event["time"] <= current_time
        ]
        
        for event in triggered_events:
            self._execute_market_event(event)
            self.scheduled_events.remove(event)
        
        # Schedule new events to maintain activity
        if len(self.scheduled_events) < 3:
            self._schedule_market_events()
    
    def _execute_market_event(self, event: Dict[str, Any]):
        """Execute a market event"""
        event_type = event["type"]
        
        if event_type == "earnings":
            symbol = event["symbol"]
            impact = event["impact"]
            
            if symbol in self.stocks:
                stock = self.stocks[symbol]
                
                # Earnings impact
                if impact == "positive":
                    price_change = random.uniform(0.03, 0.15)  # 3-15% gain
                    volume_multiplier = random.uniform(2.0, 5.0)
                elif impact == "negative":
                    price_change = random.uniform(-0.15, -0.03)  # 3-15% loss
                    volume_multiplier = random.uniform(1.5, 4.0)
                else:  # mixed
                    price_change = random.uniform(-0.05, 0.05)
                    volume_multiplier = random.uniform(1.2, 2.5)
                
                # Apply changes
                stock.current_price *= (1 + price_change)
                stock.volume_base = int(stock.volume_base * volume_multiplier)
                stock.volatility *= 1.5  # Temporary volatility increase
                
                self.logger.info(f"Earnings event for {symbol}: {impact} impact, {price_change:.2%} price change")
        
        elif event_type == "news":
            # Market-wide news impact
            sentiment = event["sentiment"]
            impact_magnitude = random.uniform(0.01, 0.05)  # 1-5% market move
            
            for stock in self.stocks.values():
                if sentiment == "positive":
                    stock.trend += impact_magnitude * random.uniform(0.5, 1.5)
                else:
                    stock.trend -= impact_magnitude * random.uniform(0.5, 1.5)
                
                # Clamp trends
                stock.trend = max(-0.3, min(0.3, stock.trend))
            
            self.logger.info(f"Market news event: {sentiment} sentiment")
        
        elif event_type == "sector_rotation":
            # Simplified sector rotation (would be more complex in reality)
            tech_symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "META"]
            finance_symbols = ["JPM", "BAC", "WFC"]
            
            for symbol in tech_symbols:
                if symbol in self.stocks:
                    self.stocks[symbol].trend -= random.uniform(0.02, 0.08)
            
            for symbol in finance_symbols:
                if symbol in self.stocks:
                    self.stocks[symbol].trend += random.uniform(0.02, 0.08)
            
            self.logger.info("Sector rotation event: Tech → Financials")
    
    def generate_realistic_price_movement(self, stock: StockState) -> float:
        """Generate realistic price movement using multiple factors"""
        
        # Base random walk
        random_component = random.gauss(0, 1) * 0.001  # Small random movements
        
        # Trend component
        trend_component = stock.trend * 0.0001
        
        # Mean reversion component
        price_deviation = (stock.current_price - stock.base_price) / stock.base_price
        mean_reversion = -price_deviation * 0.0005  # Pull back to base price
        
        # Volatility clustering (higher volatility after volatile periods)
        recent_volatility = self._calculate_recent_volatility(stock)
        volatility_multiplier = 1 + (recent_volatility * 0.1)
        
        # Market condition influence
        condition_influence = self._get_condition_influence()
        
        # Combine all factors
        total_change = (
            random_component + 
            trend_component + 
            mean_reversion + 
            condition_influence
        ) * stock.volatility * self.global_volatility_multiplier * volatility_multiplier
        
        # Apply bounds to prevent extreme movements
        max_change = 0.1  # 10% max move per update
        total_change = max(-max_change, min(max_change, total_change))
        
        return total_change
    
    def _calculate_recent_volatility(self, stock: StockState) -> float:
        """Calculate recent volatility for volatility clustering"""
        if len(stock.price_history) < 5:
            return 0.0
        
        recent_prices = stock.price_history[-5:]
        returns = [
            (recent_prices[i] - recent_prices[i-1]) / recent_prices[i-1]
            for i in range(1, len(recent_prices))
        ]
        
        if not returns:
            return 0.0
        
        # Calculate standard deviation of returns
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        return math.sqrt(variance)
    
    def _get_condition_influence(self) -> float:
        """Get market condition influence on price movements"""
        influences = {
            MarketCondition.STABLE: 0.0,
            MarketCondition.BULLISH: 0.0005,
            MarketCondition.BEARISH: -0.0005,
            MarketCondition.VOLATILE: random.gauss(0, 0.002),
            MarketCondition.CRASH: -0.002,
            MarketCondition.RECOVERY: 0.001
        }
        
        return influences.get(self.current_condition, 0.0)
    
    def generate_volume(self, stock: StockState, price_change_pct: float) -> int:
        """Generate realistic trading volume"""
        
        # Base volume with some randomness
        base_volume = stock.volume_base * random.uniform(0.3, 1.8)
        
        # Volume tends to increase with larger price movements
        volume_multiplier = 1 + (abs(price_change_pct) * 10)
        
        # Market condition affects volume
        condition_multipliers = {
            MarketCondition.STABLE: 0.8,
            MarketCondition.BULLISH: 1.2,
            MarketCondition.BEARISH: 1.1,
            MarketCondition.VOLATILE: 1.8,
            MarketCondition.CRASH: 3.0,
            MarketCondition.RECOVERY: 1.5
        }
        
        condition_mult = condition_multipliers.get(self.current_condition, 1.0)
        
        final_volume = int(base_volume * volume_multiplier * condition_mult)
        
        # Keep some reasonable bounds
        min_volume = stock.volume_base // 10
        max_volume = stock.volume_base * 20
        
        return max(min_volume, min(max_volume, final_volume))
    
    def update_stock_state(self, symbol: str) -> MarketMessage:
        """Update stock state and generate market message"""
        stock = self.stocks[symbol]
        
        # Generate price movement
        price_change_pct = self.generate_realistic_price_movement(stock)
        old_price = stock.current_price
        new_price = old_price * (1 + price_change_pct)
        
        # Update stock state
        stock.current_price = new_price
        stock.last_update = datetime.now()
        
        # Update history (maintain limited history)
        stock.price_history.append(new_price)
        if len(stock.price_history) > 100:
            stock.price_history = stock.price_history[-50:]  # Keep last 50
        
        # Generate volume
        volume = self.generate_volume(stock, price_change_pct)
        stock.volume_history.append(volume)
        if len(stock.volume_history) > 100:
            stock.volume_history = stock.volume_history[-50:]
        
        # Calculate 24h high/low (simplified - use recent history)
        recent_prices = stock.price_history[-24:] if len(stock.price_history) >= 24 else stock.price_history
        high_24h = max(recent_prices) if recent_prices else new_price
        low_24h = min(recent_prices) if recent_prices else new_price
        
        # Calculate 24h volume
        recent_volumes = stock.volume_history[-24:] if len(stock.volume_history) >= 24 else stock.volume_history
        volume_24h = sum(recent_volumes) if recent_volumes else volume
        
        # Calculate bid-ask spread (varies with volatility and market condition)
        base_spread = stock.bid_ask_spread_pct
        volatility_spread = abs(price_change_pct) * 5  # Higher spread with volatility
        condition_spread_multiplier = {
            MarketCondition.STABLE: 0.5,
            MarketCondition.BULLISH: 0.8,
            MarketCondition.BEARISH: 1.2,
            MarketCondition.VOLATILE: 2.0,
            MarketCondition.CRASH: 3.0,
            MarketCondition.RECOVERY: 1.5
        }.get(self.current_condition, 1.0)
        
        bid_ask_spread = (base_spread + volatility_spread) * condition_spread_multiplier
        bid_ask_spread = min(bid_ask_spread, 0.05)  # Max 5% spread
        
        # Create market message
        message = MarketMessage(
            message_id=str(uuid.uuid4()),
            symbol=symbol,
            price=new_price,
            volume=volume,
            timestamp=datetime.now(),
            market_condition=self.current_condition,
            change_percent=price_change_pct * 100,
            bid_ask_spread=bid_ask_spread,
            high_24h=high_24h,
            low_24h=low_24h,
            volume_24h=volume_24h,
            market_cap=new_price * random.randint(1000000, 10000000000)  # Simplified market cap
        )
        
        return message


class MarketDataGenerator:
    """
    High-performance market data generator
    
    Generates realistic financial market data streams for testing
    the high-velocity pipeline under realistic conditions.
    """
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize market simulator
        self.market_simulator = MarketSimulator(config)
        
        # Generation settings
        self.message_rate_per_second = config.target_throughput
        self.burst_mode = False
        self.burst_multiplier = 1.0
        
        # Symbol rotation for realistic distribution
        self.symbols = list(self.market_simulator.stocks.keys())
        self.symbol_weights = self._calculate_symbol_weights()
        
        # Statistics
        self.messages_generated = 0
        self.start_time = datetime.now()
        
        self.logger.info(f"Market data generator initialized: {len(self.symbols)} symbols")
    
    def _calculate_symbol_weights(self) -> Dict[str, float]:
        """Calculate realistic trading frequency weights for symbols"""
        # Some symbols trade more frequently than others
        high_volume_symbols = ["AAPL", "TSLA", "AMZN", "GOOGL", "MSFT"]
        medium_volume_symbols = ["META", "JPM", "BAC", "COIN", "GME"]
        
        weights = {}
        for symbol in self.symbols:
            if symbol in high_volume_symbols:
                weights[symbol] = 3.0  # 3x normal frequency
            elif symbol in medium_volume_symbols:
                weights[symbol] = 2.0  # 2x normal frequency
            else:
                weights[symbol] = 1.0  # Normal frequency
        
        # Normalize weights
        total_weight = sum(weights.values())
        return {symbol: weight / total_weight for symbol, weight in weights.items()}
    
    def select_random_symbol(self) -> str:
        """Select symbol based on realistic trading frequencies"""
        rand = random.random()
        cumulative = 0.0
        
        for symbol, weight in self.symbol_weights.items():
            cumulative += weight
            if rand <= cumulative:
                return symbol
        
        # Fallback
        return random.choice(self.symbols)
    
    async def generate_realtime_stream(self) -> AsyncGenerator[MarketMessage, None]:
        """Generate real-time market data stream"""
        self.logger.info("Starting real-time market data stream")
        
        # Calculate sleep time between messages
        base_sleep_time = 1.0 / self.message_rate_per_second
        
        message_count = 0
        last_condition_update = datetime.now()
        last_event_process = datetime.now()
        
        try:
            while True:
                loop_start = time.time()
                
                # Update market conditions periodically
                if datetime.now() - last_condition_update > timedelta(seconds=5):
                    self.market_simulator.update_market_condition()
                    last_condition_update = datetime.now()
                
                # Process scheduled events
                if datetime.now() - last_event_process > timedelta(seconds=2):
                    self.market_simulator._process_scheduled_events()
                    last_event_process = datetime.now()
                
                # Generate message
                symbol = self.select_random_symbol()
                message = self.market_simulator.update_stock_state(symbol)
                
                # Update statistics
                self.messages_generated += 1
                message_count += 1
                
                yield message
                
                # Dynamic sleep adjustment for target throughput
                processing_time = time.time() - loop_start
                sleep_time = max(0, base_sleep_time - processing_time)
                
                # Add some jitter to make it more realistic
                jitter = random.uniform(-0.1, 0.1) * sleep_time
                sleep_time = max(0, sleep_time + jitter)
                
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                
                # Log progress periodically
                if message_count % 1000 == 0:
                    elapsed = (datetime.now() - self.start_time).total_seconds()
                    rate = self.messages_generated / elapsed if elapsed > 0 else 0
                    self.logger.debug(f"Generated {self.messages_generated} messages ({rate:.1f}/sec)")
        
        except asyncio.CancelledError:
            self.logger.info("Market data stream cancelled")
        except Exception as e:
            self.logger.error(f"Market data generation error: {e}")
            raise
    
    async def generate_batch(self, batch_size: int) -> List[MarketMessage]:
        """Generate a batch of market messages"""
        messages = []
        
        for _ in range(batch_size):
            symbol = self.select_random_symbol()
            message = self.market_simulator.update_stock_state(symbol)
            messages.append(message)
            
            # Small delay between messages in batch
            await asyncio.sleep(0.001)
        
        self.messages_generated += batch_size
        return messages
    
    def get_market_statistics(self) -> Dict[str, Any]:
        """Get comprehensive market statistics"""
        current_time = datetime.now()
        elapsed = (current_time - self.start_time).total_seconds()
        generation_rate = self.messages_generated / elapsed if elapsed > 0 else 0
        
        # Get current stock prices
        stock_prices = {
            symbol: {
                "price": stock.current_price,
                "change_24h": ((stock.current_price - stock.base_price) / stock.base_price) * 100,
                "volume": stock.volume_base,
                "volatility": stock.volatility
            }
            for symbol, stock in self.market_simulator.stocks.items()
        }
        
        return {
            "generation_stats": {
                "messages_generated": self.messages_generated,
                "generation_rate_per_sec": generation_rate,
                "elapsed_seconds": elapsed,
                "target_rate": self.message_rate_per_second
            },
            "market_state": {
                "current_condition": self.market_simulator.current_condition.value,
                "global_volatility_multiplier": self.market_simulator.global_volatility_multiplier,
                "condition_start_time": self.market_simulator.condition_start_time.isoformat(),
                "scheduled_events_count": len(self.market_simulator.scheduled_events)
            },
            "symbol_count": len(self.symbols),
            "stock_prices": stock_prices
        }
    
    def adjust_generation_rate(self, new_rate: float):
        """Dynamically adjust message generation rate"""
        old_rate = self.message_rate_per_second
        self.message_rate_per_second = max(1.0, new_rate)  # Minimum 1 msg/sec
        
        self.logger.info(f"Generation rate adjusted: {old_rate:.1f} → {new_rate:.1f} msg/sec")
    
    def trigger_market_event(self, event_type: str, **kwargs):
        """Manually trigger a market event for testing"""
        event = {
            "time": datetime.now(),
            "type": event_type,
            **kwargs
        }
        
        self.market_simulator._execute_market_event(event)
        self.logger.info(f"Triggered market event: {event_type}")
    
    def reset_market_state(self):
        """Reset market to initial state"""
        self.market_simulator = MarketSimulator(self.config)
        self.messages_generated = 0
        self.start_time = datetime.now()
        
        self.logger.info("Market state reset to initial conditions")