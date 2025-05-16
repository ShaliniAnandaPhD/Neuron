import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from scipy import stats
import datetime
from pathlib import Path
import os

class TimeSeriesAnalyzer:
    """
    A specialized class for analyzing time series performance data in the Neuron Evaluation Framework.
    Provides trend analysis, forecasting, and target achievement prediction.
    """
    
    def __init__(self, data_dir='data', output_dir='time_series_analysis'):
        """
        Initialize the time series analyzer.
        
        Args:
            data_dir (str): Directory containing test data files
            output_dir (str): Directory to save analysis outputs
        """
        self.data_dir = data_dir
        self.output_dir = output_dir
        self.performance_data = None
        self.analysis_results = {}
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Load the time series data
        self._load_data()
    
    def _load_data(self):
        """Load performance over time data from file."""
        file_path = Path(self.data_dir) / 'performance_over_time.txt'
        
        if file_path.exists():
            try:
                self.performance_data = pd.read_csv(file_path)
                print(f"Loaded performance data with {len(self.performance_data)} components.")
                
                # Get time points
                self.time_points = [col for col in self.performance_data.columns if col.startswith('week')]
                print(f"Found {len(self.time_points)} time points: {', '.join(self.time_points)}")
                
            except Exception as e:
                print(f"Error loading performance data: {e}")
        else:
            print(f"Performance data file not found: {file_path}")
    
    def _prepare_time_series_data(self):
        """
        Convert data to long format for time series analysis.
        
        Returns:
            pandas.DataFrame: Formatted time series data
        """
        if self.performance_data is None:
            print("No performance data available.")
            return None
        
        # Convert to long format
        ts_data = pd.melt(
            self.performance_data, 
            id_vars=['component', 'production_target'], 
            value_vars=self.time_points,
            var_name='time_point',
            value_name='score'
        )
        
        # Extract week number
        ts_data['week'] = ts_data['time_point'].str.replace('week', '').astype(int)
        
        # Sort by component and week
        ts_data = ts_data.sort_values(['component', 'week'])
        
        return ts_data
    
    def analyze_trends(self):
        """
        Analyze performance trends for each component.
        
        Returns:
            pandas.DataFrame: Trend analysis results
        """
        ts_data = self._prepare_time_series_data()
        if ts_data is None:
            return None
        
        # Create a DataFrame to store trend analysis results
        trend_results = []
        
        # Analyze each component
        for component, group in ts_data.groupby('component'):
            # Sort by week
            group = group.sort_values('week')
            
            # Extract scores and weeks
            scores = group['score'].values
            weeks = group['week'].values
            
            # Basic statistics
            latest_score = scores[-1]
            initial_score = scores[0]
            target_score = group['production_target'].iloc[0]
            overall_improvement = latest_score - initial_score
            
            # Calculate slope (improvement rate per week)
            slope, intercept, r_value, p_value, std_err = stats.linregress(weeks, scores)
            
            # Calculate weeks to target using the slope
            remaining_gap = target_score - latest_score
            
            if slope > 0:
                weeks_to_target = remaining_gap / slope
            else:
                weeks_to_target = float('inf')  # No improvement or negative trend
            
            # Calculate 'quality' of linear fit (R-squared)
            r_squared = r_value ** 2
            
            # Determine if trend is accelerating or decelerating
            # Compare first half slope to second half slope
            mid_point = len(weeks) // 2
            
            if mid_point > 1:  # Need at least 2 points for regression
                _, _, r_value1, _, _ = stats.linregress(weeks[:mid_point], scores[:mid_point])
                slope1, _, _, _, _ = stats.linregress(weeks[:mid_point], scores[:mid_point])
                
                _, _, r_value2, _, _ = stats.linregress(weeks[mid_point:], scores[mid_point:])
                slope2, _, _, _, _ = stats.linregress(weeks[mid_point:], scores[mid_point:])
                
                # Calculate acceleration
                acceleration = slope2 - slope1
                trend_direction = "Accelerating" if acceleration > 0 else "Decelerating"
            else:
                acceleration = 0
                trend_direction = "Unknown"
            
            # Calculate Target Achievement Probability (TAP)
            # Based on:
            # 1. Proximity to target (closer = higher probability)
            # 2. Consistency of improvement (higher R² = higher probability)
            # 3. Current improvement rate (higher slope = higher probability)
            
            # Normalize factors to 0-1 range
            proximity_factor = 1 - (remaining_gap / target_score if target_score > 0 else 0)
            consistency_factor = r_squared  # Already 0-1
            rate_factor = min(1, max(0, slope * 10))  # Scale and cap at 1
            
            # Weight factors
            tap = (proximity_factor * 0.4) + (consistency_factor * 0.3) + (rate_factor * 0.3)
            tap_percentage = tap * 100
            
            # Store results
            trend_results.append({
                'component': component,
                'latest_score': latest_score,
                'target_score': target_score,
                'remaining_gap': remaining_gap,
                'overall_improvement': overall_improvement,
                'improvement_rate': slope,
                'consistency_r_squared': r_squared,
                'weeks_to_target': weeks_to_target,
                'acceleration': acceleration,
                'trend_direction': trend_direction,
                'target_achievement_probability': tap_percentage
            })
        
        # Convert to DataFrame
        trend_df = pd.DataFrame(trend_results)
        
        # Add estimated completion date
        today = datetime.datetime.now().date()
        trend_df['est_completion_date'] = trend_df['weeks_to_target'].apply(
            lambda w: (today + datetime.timedelta(days=int(w * 7))).strftime('%Y-%m-%d') 
            if w > 0 and not np.isinf(w) else 'N/A'
        )
        
        # Add achievable status
        current_date = datetime.datetime.now().date()
        target_date = current_date + datetime.timedelta(days=90)  # 3 months from now
        
        def get_achievable_status(row):
            if row['remaining_gap'] <= 0:
                return "Already Achieved"
            elif row['improvement_rate'] <= 0:
                return "Not Achievable (No Progress)"
            else:
                est_date = datetime.datetime.strptime(row['est_completion_date'], '%Y-%m-%d').date()
                if est_date <= target_date:
                    return "Achievable on Schedule"
                else:
                    return "Achievable but Delayed"
        
        trend_df['achievable_status'] = trend_df.apply(get_achievable_status, axis=1)
        
        # Sort by weeks to target (ascending)
        trend_df = trend_df.sort_values('weeks_to_target')
        
        # Replace infinity with a large number for display purposes
        trend_df['weeks_to_target'] = trend_df['weeks_to_target'].replace([np.inf, -np.inf], 999)
        
        # Round numeric columns
        numeric_cols = [
            'latest_score', 'target_score', 'remaining_gap', 'overall_improvement',
            'improvement_rate', 'consistency_r_squared', 'weeks_to_target',
            'acceleration', 'target_achievement_probability'
        ]
        trend_df[numeric_cols] = trend_df[numeric_cols].round(2)
        
        # Save results
        self.analysis_results['trend_analysis'] = trend_df
        
        return trend_df
    
    def forecast_component_performance(self, forecast_weeks=16, components=None, method='arima'):
        """
        Forecast future performance for selected components.
        
        Args:
            forecast_weeks (int): Number of weeks to forecast
            components (list): List of components to forecast (None for all)
            method (str): Forecasting method ('arima', 'exponential_smoothing', or 'linear')
            
        Returns:
            dict: Dictionary of forecasts by component
        """
        ts_data = self._prepare_time_series_data()
        if ts_data is None:
            return None
        
        # If no components specified, use all
        if components is None:
            components = ts_data['component'].unique()
        elif isinstance(components, str):
            components = [components]  # Convert single component to list
        
        # Dictionary to store forecasts
        forecasts = {}
        
        # Forecast for each component
        for component in components:
            # Filter data for this component
            component_data = ts_data[ts_data['component'] == component]
            
            if len(component_data) == 0:
                print(f"Component {component} not found in data.")
                continue
            
            # Sort by week
            component_data = component_data.sort_values('week')
            
            # Extract scores and weeks
            scores = component_data['score'].values
            weeks = component_data['week'].values
            
            # Get target score
            target_score = component_data['production_target'].iloc[0]
            
            # Generate future weeks
            last_week = weeks[-1]
            future_weeks = np.arange(last_week + 1, last_week + forecast_weeks + 1)
            
            # Initialize forecast dictionary
            forecast = {
                'historical_weeks': weeks.tolist(),
                'historical_scores': scores.tolist(),
                'future_weeks': future_weeks.tolist(),
                'forecasted_scores': None,
                'confidence_intervals': None,
                'target_score': target_score,
                'target_week': None,
                'forecast_method': method
            }
            
            # Perform forecasting
            if method == 'linear':
                # Simple linear regression
                slope, intercept, _, _, _ = stats.linregress(weeks, scores)
                forecasted_scores = [intercept + slope * week for week in future_weeks]
                
                # Simple confidence intervals
                residuals = scores - (intercept + slope * weeks)
                std_residuals = np.std(residuals)
                confidence_intervals = [
                    [score - 1.96 * std_residuals, score + 1.96 * std_residuals]
                    for score in forecasted_scores
                ]
                
            elif method == 'exponential_smoothing':
                try:
                    # Holt-Winters Exponential Smoothing
                    model = ExponentialSmoothing(
                        scores, 
                        trend='add', 
                        seasonal=None, 
                        initialization_method="estimated"
                    )
                    fit = model.fit()
                    forecasted_scores = fit.forecast(forecast_weeks).tolist()
                    
                    # Generate confidence intervals
                    # Approximate with historical volatility
                    volatility = np.std(fit.resid)
                    confidence_intervals = [
                        [score - 1.96 * volatility * np.sqrt(i+1), 
                         score + 1.96 * volatility * np.sqrt(i+1)]
                        for i, score in enumerate(forecasted_scores)
                    ]
                except Exception as e:
                    print(f"Error with exponential smoothing for {component}: {e}")
                    # Fall back to linear regression
                    slope, intercept, _, _, _ = stats.linregress(weeks, scores)
                    forecasted_scores = [intercept + slope * week for week in future_weeks]
                    
                    # Simple confidence intervals
                    residuals = scores - (intercept + slope * weeks)
                    std_residuals = np.std(residuals)
                    confidence_intervals = [
                        [score - 1.96 * std_residuals, score + 1.96 * std_residuals]
                        for score in forecasted_scores
                    ]
            
            elif method == 'arima':
                try:
                    # ARIMA model
                    model = ARIMA(scores, order=(1, 1, 0))
                    fit = model.fit()
                    forecast_result = fit.get_forecast(steps=forecast_weeks)
                    forecasted_scores = forecast_result.predicted_mean.tolist()
                    
                    # Get confidence intervals
                    ci = forecast_result.conf_int()
                    confidence_intervals = [
                        [ci.iloc[i, 0], ci.iloc[i, 1]]
                        for i in range(len(ci))
                    ]
                except Exception as e:
                    print(f"Error with ARIMA for {component}: {e}")
                    # Fall back to linear regression
                    slope, intercept, _, _, _ = stats.linregress(weeks, scores)
                    forecasted_scores = [intercept + slope * week for week in future_weeks]
                    
                    # Simple confidence intervals
                    residuals = scores - (intercept + slope * weeks)
                    std_residuals = np.std(residuals)
                    confidence_intervals = [
                        [score - 1.96 * std_residuals, score + 1.96 * std_residuals]
                        for score in forecasted_scores
                    ]
            
            else:
                print(f"Unknown forecasting method: {method}")
                return None
            
            # Store forecasted scores and confidence intervals
            forecast['forecasted_scores'] = forecasted_scores
            forecast['confidence_intervals'] = confidence_intervals
            
            # Determine when target will be reached
            reached_target = False
            target_week = None
            
            for i, score in enumerate(forecasted_scores):
                if score >= target_score and not reached_target:
                    reached_target = True
                    target_week = future_weeks[i]
                    break
            
            forecast['target_week'] = target_week
            
            # Store forecast for this component
            forecasts[component] = forecast
        
        # Save results
        self.analysis_results['performance_forecasts'] = forecasts
        
        return forecasts
    
    def analyze_improvement_patterns(self):
        """
        Analyze patterns in how components improve over time.
        
        Returns:
            pandas.DataFrame: Improvement pattern analysis
        """
        ts_data = self._prepare_time_series_data()
        if ts_data is None:
            return None
        
        # Dictionary to store pattern results
        pattern_results = []
        
        # Analyze each component
        for component, group in ts_data.groupby('component'):
            # Sort by week
            group = group.sort_values('week')
            
            # Extract scores and weeks
            scores = group['score'].values
            weeks = group['week'].values
            
            # Skip if not enough data points
            if len(scores) < 3:
                continue
            
            # Calculate period-to-period changes
            changes = [scores[i] - scores[i-1] for i in range(1, len(scores))]
            change_weeks = weeks[1:]
            
            # Calculate acceleration (change in changes)
            accelerations = [changes[i] - changes[i-1] for i in range(1, len(changes))]
            acceleration_weeks = change_weeks[1:]
            
            # Determine improvement pattern
            
            # 1. Calculate average change and its standard deviation
            avg_change = np.mean(changes)
            std_change = np.std(changes)
            
            # 2. Determine if improvements are consistent or variable
            # High coefficient of variation indicates variable improvements
            if avg_change != 0:
                cv = std_change / abs(avg_change)
                improvement_consistency = "Variable" if cv > 0.5 else "Consistent"
            else:
                improvement_consistency = "No Change"
            
            # 3. Determine if accelerating, decelerating, or steady
            avg_acceleration = np.mean(accelerations) if accelerations else 0
            
            if abs(avg_acceleration) < 0.1:  # Small threshold for noise
                acceleration_pattern = "Steady"
            elif avg_acceleration > 0:
                acceleration_pattern = "Accelerating"
            else:
                acceleration_pattern = "Decelerating"
            
            # 4. Identify plateaus
            # Calculate running average to smooth noise
            window_size = min(3, len(scores))
            smoothed_scores = np.convolve(scores, np.ones(window_size)/window_size, mode='valid')
            
            # Define plateau as period where improvement rate drops significantly
            plateau_threshold = 0.2  # 20% of average improvement rate
            
            plateau_periods = []
            in_plateau = False
            plateau_start = None
            
            for i in range(1, len(smoothed_scores)):
                change = smoothed_scores[i] - smoothed_scores[i-1]
                
                if abs(change) < plateau_threshold * abs(avg_change):
                    if not in_plateau:
                        in_plateau = True
                        plateau_start = i + window_size - 1  # Adjust for convolution offset
                else:
                    if in_plateau:
                        in_plateau = False
                        plateau_end = i + window_size - 2  # Adjust for convolution offset
                        plateau_periods.append((plateau_start, plateau_end))
            
            # If still in plateau at the end
            if in_plateau:
                plateau_end = len(scores) - 1
                plateau_periods.append((plateau_start, plateau_end))
            
            # 5. Calculate the "efficiency" of improvement
            # (How much improvement per week compared to what's theoretically possible)
            initial_score = scores[0]
            latest_score = scores[-1]
            target_score = group['production_target'].iloc[0]
            
            # Maximum possible improvement
            max_possible = target_score - initial_score
            
            # Actual improvement
            actual_improvement = latest_score - initial_score
            
            # Improvement efficiency (as percentage of what's possible)
            if max_possible > 0:
                improvement_efficiency = (actual_improvement / max_possible) * 100
            else:
                improvement_efficiency = 100  # Already at or above target
            
            # Store results
            pattern_results.append({
                'component': component,
                'avg_improvement_rate': avg_change,
                'improvement_consistency': improvement_consistency,
                'acceleration_pattern': acceleration_pattern,
                'avg_acceleration': avg_acceleration,
                'plateau_count': len(plateau_periods),
                'plateau_weeks': '; '.join([f"{start}-{end}" for start, end in plateau_periods]),
                'improvement_efficiency': improvement_efficiency
            })
        
        # Convert to DataFrame
        pattern_df = pd.DataFrame(pattern_results)
        
        # Add improvement pattern classification
        def classify_pattern(row):
            if row['avg_improvement_rate'] <= 0:
                return "No Improvement"
            elif row['improvement_consistency'] == "Consistent" and row['acceleration_pattern'] == "Steady":
                return "Linear Improvement"
            elif row['acceleration_pattern'] == "Accelerating":
                return "Exponential Improvement"
            elif row['acceleration_pattern'] == "Decelerating":
                return "Logarithmic Improvement"
            elif row['plateau_count'] > 0:
                return "Stepped Improvement"
            else:
                return "Mixed Pattern"
            
        pattern_df['improvement_pattern'] = pattern_df.apply(classify_pattern, axis=1)
        
        # Sort by improvement efficiency (descending)
        pattern_df = pattern_df.sort_values('improvement_efficiency', ascending=False)
        
        # Round numeric columns
        numeric_cols = ['avg_improvement_rate', 'avg_acceleration', 'improvement_efficiency']
        pattern_df[numeric_cols] = pattern_df[numeric_cols].round(2)
        
        # Save results
        self.analysis_results['improvement_patterns'] = pattern_df
        
        return pattern_df
    
    def identify_correlations(self):
        """
        Identify correlations in improvement patterns across components.
        
        Returns:
            pandas.DataFrame: Correlation analysis results
        """
        ts_data = self._prepare_time_series_data()
        if ts_data is None:
            return None
        
        # Create a wide-format DataFrame with components as columns and weeks as rows
        components = ts_data['component'].unique()
        weeks = sorted(ts_data['week'].unique())
        
        # Initialize DataFrame
        wide_df = pd.DataFrame(index=weeks)
        
        # Fill with scores
        for component in components:
            component_data = ts_data[ts_data['component'] == component].sort_values('week')
            wide_df[component] = component_data.set_index('week')['score']
        
        # Calculate improvement rates
        improvements_df = wide_df.diff()
        
        # Calculate correlation matrix
        corr_matrix = improvements_df.corr()
        
        # Extract correlation pairs
        corr_pairs = []
        
        for i, comp1 in enumerate(components):
            for j, comp2 in enumerate(components):
                if i < j:  # Only include each pair once
                    correlation = corr_matrix.loc[comp1, comp2]
                    
                    # Exclude pairs with NaN correlation
                    if not np.isnan(correlation):
                        # Calculate mean improvement rates
                        mean_imp1 = improvements_df[comp1].mean()
                        mean_imp2 = improvements_df[comp2].mean()
                        
                        # Identify "co-plateaus" when both components stall
                        comp1_stalls = improvements_df[comp1].abs() < 0.1
                        comp2_stalls = improvements_df[comp2].abs() < 0.1
                        
                        co_plateaus = (comp1_stalls & comp2_stalls).sum()
                        
                        corr_pairs.append({
                            'component1': comp1,
                            'component2': comp2,
                            'correlation': correlation,
                            'mean_improvement1': mean_imp1,
                            'mean_improvement2': mean_imp2,
                            'co_plateau_count': co_plateaus
                        })
        
        # Convert to DataFrame
        corr_df = pd.DataFrame(corr_pairs)
        
        # Add correlation strength classification
        def classify_correlation(corr):
            if corr >= 0.8:
                return "Very Strong Positive"
            elif corr >= 0.6:
                return "Strong Positive"
            elif corr >= 0.4:
                return "Moderate Positive"
            elif corr >= 0.2:
                return "Weak Positive"
            elif corr > -0.2:
                return "Negligible"
            elif corr > -0.4:
                return "Weak Negative"
            elif corr > -0.6:
                return "Moderate Negative"
            elif corr > -0.8:
                return "Strong Negative"
            else:
                return "Very Strong Negative"
            
        corr_df['correlation_type'] = corr_df['correlation'].apply(classify_correlation)
        
        # Sort by absolute correlation (descending)
        corr_df['abs_correlation'] = corr_df['correlation'].abs()
        corr_df = corr_df.sort_values('abs_correlation', ascending=False)
        
        # Drop helper column
        corr_df = corr_df.drop(columns=['abs_correlation'])
        
        # Round numeric columns
        numeric_cols = ['correlation', 'mean_improvement1', 'mean_improvement2']
        corr_df[numeric_cols] = corr_df[numeric_cols].round(3)
        
        # Save results
        self.analysis_results['component_correlations'] = corr_df
        
        return corr_df
    
    def predict_system_readiness(self):
        """
        Predict when the overall system will be ready for production.
        
        Returns:
            dict: System readiness prediction
        """
        if 'trend_analysis' not in self.analysis_results:
            print("Run trend analysis first.")
            return None
        
        trend_df = self.analysis_results['trend_analysis']
        
        # Filter to only include components that haven't reached target
        pending_components = trend_df[trend_df['remaining_gap'] > 0]
        
        if len(pending_components) == 0:
            # All components have reached target
            return {
                'status': 'Ready for Production',
                'remaining_components': 0,
                'bottleneck_components': [],
                'earliest_completion_date': 'Now',
                'expected_completion_date': 'Now',
                'latest_completion_date': 'Now',
                'readiness_probability': 100
            }
        
        # Count components by achievable status
        status_counts = pending_components['achievable_status'].value_counts().to_dict()
        
        # Identify bottleneck components (those with longest time to target)
        bottlenecks = pending_components.nlargest(3, 'weeks_to_target')
        bottleneck_list = []
        
        for _, row in bottlenecks.iterrows():
            component_info = {
                'component': row['component'],
                'weeks_to_target': row['weeks_to_target'],
                'est_completion_date': row['est_completion_date'],
                'improvement_rate': row['improvement_rate'],
                'target_achievement_probability': row['target_achievement_probability']
            }
            bottleneck_list.append(component_info)
        
        # Get completion date ranges
        completion_dates = [
            datetime.datetime.strptime(date, '%Y-%m-%d').date() 
            for date in pending_components['est_completion_date'].values 
            if date != 'N/A'
        ]
        
        if completion_dates:
            earliest_date = min(completion_dates)
            latest_date = max(completion_dates)
            
            # Expected completion is the date by which most components will be ready
            # Find the median completion date
            median_date = np.median(
                [date.toordinal() for date in completion_dates]
            )
            expected_date = datetime.date.fromordinal(int(median_date))
        else:
            # No valid completion dates
            earliest_date = "Unknown"
            latest_date = "Unknown"
            expected_date = "Unknown"
        
        # Calculate overall readiness probability
        # Based on:
        # 1. Percentage of components already at target
        # 2. Average target achievement probability of pending components
        # 3. Presence of components with negative improvement rates
        
        total_components = len(trend_df)
        completed_components = total_components - len(pending_components)
        completion_percentage = (completed_components / total_components) * 100
        
        avg_probability = pending_components['target_achievement_probability'].mean()
        
        has_negative_trends = (pending_components['improvement_rate'] <= 0).any()
        
        # Weight the factors
        readiness_probability = (
            completion_percentage * 0.6 + 
            avg_probability * 0.4
        ) * (0.7 if has_negative_trends else 1.0)
        
        # Cap at 100%
        readiness_probability = min(100, readiness_probability)
        
        # Format dates as strings
        if isinstance(earliest_date, datetime.date):
            earliest_date = earliest_date.strftime('%Y-%m-%d')
        
        if isinstance(latest_date, datetime.date):
            latest_date = latest_date.strftime('%Y-%m-%d')
            
        if isinstance(expected_date, datetime.date):
            expected_date = expected_date.strftime('%Y-%m-%d')
        
        # Create prediction dictionary
        prediction = {
            'status': 'In Progress',
            'total_components': total_components,
            'completed_components': completed_components,
            'remaining_components': len(pending_components),
            'completion_percentage': round(completion_percentage, 2),
            'status_counts': status_counts,
            'bottleneck_components': bottleneck_list,
            'earliest_completion_date': earliest_date,
            'expected_completion_date': expected_date,
            'latest_completion_date': latest_date,
            'readiness_probability': round(readiness_probability, 2)
        }
        
        # Save results
        self.analysis_results['system_readiness'] = prediction
        
        return prediction
    
    def visualize_trends(self, components=None, include_forecast=True, forecast_weeks=16):
        """
        Visualize performance trends for selected components.
        
        Args:
            components (list): List of components to visualize (None for all)
            include_forecast (bool): Whether to include forecasts
            forecast_weeks (int): Number of weeks to forecast
            
        Returns:
            matplotlib.figure.Figure: The generated figure
        """
        ts_data = self._prepare_time_series_data()
        if ts_data is None:
            return None
        
        # If no components specified, use all
        if components is None:
            # Limit to a reasonable number
            if 'trend_analysis' in self.analysis_results:
                # Select most interesting components based on trend analysis
                trend_df = self.analysis_results['trend_analysis']
                
                # Get top 3 components closest to target
                close_to_target = trend_df.nsmallest(3, 'weeks_to_target')
                
                # Get top 3 components furthest from target
                far_from_target = trend_df.nlargest(3, 'weeks_to_target')
                
                # Combine and remove duplicates
                selected_components = pd.concat([close_to_target, far_from_target])
                components = selected_components['component'].unique().tolist()
            else:
                # Just take the first 6 components
                components = ts_data['component'].unique()[:6].tolist()
        elif isinstance(components, str):
            components = [components]  # Convert single component to list
        
        # Generate forecasts if needed
        if include_forecast and 'performance_forecasts' not in self.analysis_results:
            self.forecast_component_performance(
                forecast_weeks=forecast_weeks,
                components=components
            )
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Create color palette
        color_palette = sns.color_palette("husl", len(components))
        
        # Plot each component
        for i, component in enumerate(components):
            # Filter data for this component
            component_data = ts_data[ts_data['component'] == component]
            
            if len(component_data) == 0:
                print(f"Component {component} not found in data.")
                continue
            
            # Sort by week
            component_data = component_data.sort_values('week')
            
            # Extract scores, weeks, and target
            scores = component_data['score'].values
            weeks = component_data['week'].values
            target = component_data['production_target'].iloc[0]
            
            # Plot historical data
            ax.plot(
                weeks, 
                scores, 
                marker='o',
                linestyle='-',
                label=component,
                color=color_palette[i]
            )
            
            # Add target line
            ax.axhline(
                y=target,
                color=color_palette[i],
                linestyle='--',
                alpha=0.5
            )
            
            # Add forecast if available
            if include_forecast and 'performance_forecasts' in self.analysis_results:
                forecasts = self.analysis_results['performance_forecasts']
                
                if component in forecasts:
                    forecast = forecasts[component]
                    
                    # Plot forecast
                    ax.plot(
                        forecast['future_weeks'],
                        forecast['forecasted_scores'],
                        linestyle=':',
                        color=color_palette[i],
                        alpha=0.8
                    )
                    
                    # Add confidence intervals
                    ci = np.array(forecast['confidence_intervals'])
                    ax.fill_between(
                        forecast['future_weeks'],
                        ci[:, 0],
                        ci[:, 1],
                        color=color_palette[i],
                        alpha=0.2
                    )
                    
                    # Mark target achievement point
                    if forecast['target_week']:
                        target_week = forecast['target_week']
                        # Find score at target week
                        target_idx = forecast['future_weeks'].index(target_week)
                        target_score = forecast['forecasted_scores'][target_idx]
                        
                        ax.plot(
                            target_week,
                            target_score,
                            marker='*',
                            markersize=12,
                            color=color_palette[i]
                        )
        
        # Set chart properties
        ax.set_title('Component Performance Trends and Forecasts', fontsize=16, fontweight='bold')
        ax.set_xlabel('Week', fontsize=12)
        ax.set_ylabel('Performance Score', fontsize=12)
        ax.grid(True, linestyle='--', alpha=0.7)
        
        # Add legend
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        
        # Adjust limits
        ax.set_ylim(50, 100)  # Typical score range
        
        # Adjust x-axis to show forecast
        if include_forecast:
            ax.set_xlim(0, max(weeks) + forecast_weeks + 1)
            
            # Add a vertical line at the end of historical data
            ax.axvline(
                x=max(weeks),
                color='black',
                linestyle='-.',
                alpha=0.5,
                label='Forecast Start'
            )
            
            # Add "Historical" and "Forecast" labels
            ax.text(
                np.mean(weeks),
                52,
                'Historical',
                ha='center',
                fontsize=10,
                fontweight='bold'
            )
            
            ax.text(
                max(weeks) + forecast_weeks/2,
                52,
                'Forecast',
                ha='center',
                fontsize=10,
                fontweight='bold'
            )
        
        plt.tight_layout()
        
        # Save figure
        output_path = os.path.join(self.output_dir, 'performance_trends.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved performance trends visualization to {output_path}")
        
        return fig
    
    def visualize_improvement_patterns(self):
        """
        Visualize improvement patterns across components.
        
        Returns:
            matplotlib.figure.Figure: The generated figure
        """
        if 'improvement_patterns' not in self.analysis_results:
            print("Run analyze_improvement_patterns first.")
            return None
        
        pattern_df = self.analysis_results['improvement_patterns']
        
        # Create figure with multiple subplots
        fig, axs = plt.subplots(2, 2, figsize=(14, 12))
        
        # 1. Bar chart of improvement patterns
        pattern_counts = pattern_df['improvement_pattern'].value_counts()
        
        axs[0, 0].bar(
            pattern_counts.index,
            pattern_counts.values,
            color=sns.color_palette("viridis", len(pattern_counts))
        )
        
        axs[0, 0].set_title('Distribution of Improvement Patterns', fontweight='bold')
        axs[0, 0].set_ylabel('Number of Components')
        axs[0, 0].tick_params(axis='x', rotation=45)
        axs[0, 0].grid(axis='y', linestyle='--', alpha=0.7)
        
        # 2. Scatter plot of improvement rate vs. efficiency
        scatter = axs[0, 1].scatter(
            pattern_df['avg_improvement_rate'],
            pattern_df['improvement_efficiency'],
            c=pattern_df['improvement_pattern'].astype('category').cat.codes,
            cmap='viridis',
            alpha=0.8,
            s=100
        )
        
        # Add labels for key points
        for i, row in pattern_df.head(5).iterrows():
            axs[0, 1].annotate(
                row['component'],
                xy=(row['avg_improvement_rate'], row['improvement_efficiency']),
                xytext=(5, 5),
                textcoords='offset points',
                fontsize=9
            )
        
        axs[0, 1].set_title('Improvement Rate vs. Efficiency', fontweight='bold')
        axs[0, 1].set_xlabel('Average Improvement Rate')
        axs[0, 1].set_ylabel('Improvement Efficiency (%)')
        axs[0, 1].grid(True, linestyle='--', alpha=0.7)
        
        # Add legend
        legend1 = axs[0, 1].legend(
            scatter.legend_elements()[0],
            pattern_df['improvement_pattern'].unique(),
            loc='upper left',
            title='Pattern'
        )
        
        # 3. Bar chart of acceleration patterns
        accel_counts = pattern_df['acceleration_pattern'].value_counts()
        
        bars = axs[1, 0].bar(
            accel_counts.index,
            accel_counts.values,
            color=sns.color_palette("muted", len(accel_counts))
        )
        
        # Add counts as text
        for bar in bars:
            height = bar.get_height()
            axs[1, 0].text(
                bar.get_x() + bar.get_width()/2.,
                height,
                str(int(height)),
                ha='center',
                va='bottom'
            )
        
        axs[1, 0].set_title('Acceleration Patterns', fontweight='bold')
        axs[1, 0].set_ylabel('Number of Components')
        axs[1, 0].grid(axis='y', linestyle='--', alpha=0.7)
        
        # 4. Bar chart of top components by efficiency
        top_efficient = pattern_df.nlargest(10, 'improvement_efficiency')
        
        bars = axs[1, 1].barh(
            top_efficient['component'],
            top_efficient['improvement_efficiency'],
            color=top_efficient['avg_improvement_rate'],
            cmap='viridis'
        )
        
        # Add a colorbar
        sm = plt.cm.ScalarMappable(cmap='viridis', norm=plt.Normalize(
            top_efficient['avg_improvement_rate'].min(),
            top_efficient['avg_improvement_rate'].max()
        ))
        sm.set_array([])
        cbar = fig.colorbar(sm, ax=axs[1, 1])
        cbar.set_label('Improvement Rate')
        
        axs[1, 1].set_title('Top 10 Components by Improvement Efficiency', fontweight='bold')
        axs[1, 1].set_xlabel('Improvement Efficiency (%)')
        axs[1, 1].grid(axis='x', linestyle='--', alpha=0.7)
        
        # Set overall title
        fig.suptitle('Component Improvement Pattern Analysis', fontsize=16, fontweight='bold')
        
        plt.tight_layout()
        
        # Save figure
        output_path = os.path.join(self.output_dir, 'improvement_patterns.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved improvement patterns visualization to {output_path}")
        
        return fig
    
    def visualize_system_readiness(self):
        """
        Visualize system readiness prediction.
        
        Returns:
            matplotlib.figure.Figure: The generated figure
        """
        if 'system_readiness' not in self.analysis_results:
            print("Run predict_system_readiness first.")
            return None
        
        readiness = self.analysis_results['system_readiness']
        
        # Create figure
        fig, axs = plt.subplots(2, 2, figsize=(14, 12))
        
        # 1. Completion percentage gauge
        def gauge_chart(ax, value, title, min_val=0, max_val=100):
            # Define colors
            colors = ['#ff9999', '#ffcc99', '#ffff99', '#99ff99']
            thresholds = [25, 50, 75, 100]
            
            # Create gauge
            gauge_angle = np.pi / 2
            angles = np.linspace(0, gauge_angle, 100)
            
            # Plot gauge background
            for i, threshold in enumerate(thresholds):
                if i == 0:
                    start = min_val
                else:
                    start = thresholds[i-1]
                end = threshold
                
                mask = (np.linspace(min_val, max_val, 100) >= start) & (np.linspace(min_val, max_val, 100) <= end)
                ax.plot(np.cos(angles[mask]), np.sin(angles[mask]), color=colors[i], linewidth=20)
            
            # Calculate needle angle
            needle_angle = gauge_angle * (value - min_val) / (max_val - min_val)
            
            # Plot needle
            ax.arrow(
                0, 0, 
                0.8 * np.cos(needle_angle), 0.8 * np.sin(needle_angle),
                head_width=0.05, head_length=0.1, fc='black', ec='black'
            )
            
            # Add center circle
            circle = plt.Circle((0, 0), 0.1, fc='white', ec='black')
            ax.add_patch(circle)
            
            # Add value text
            ax.text(
                0, -0.2,
                f'{value:.1f}%',
                ha='center',
                va='center',
                fontsize=24,
                fontweight='bold'
            )
            
            # Set limits and remove axes
            ax.set_xlim(-1.1, 1.1)
            ax.set_ylim(-0.3, 1.1)
            ax.axis('off')
            
            # Add title
            ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        
        # Create gauge charts for completion and probability
        gauge_chart(axs[0, 0], readiness['completion_percentage'], 'Completion Percentage')
        gauge_chart(axs[0, 1], readiness['readiness_probability'], 'Readiness Probability')
        
        # 2. Component status breakdown
        if 'status_counts' in readiness:
            status_labels = list(readiness['status_counts'].keys())
            status_values = list(readiness['status_counts'].values())
            
            # Define colors based on status
            status_colors = {
                'Already Achieved': '#4CAF50',  # Green
                'Achievable on Schedule': '#8BC34A',  # Light Green
                'Achievable but Delayed': '#FFC107',  # Amber
                'Not Achievable (No Progress)': '#F44336'  # Red
            }
            
            colors = [status_colors.get(label, '#9E9E9E') for label in status_labels]
            
            bars = axs[1, 0].bar(status_labels, status_values, color=colors)
            
            # Add counts as text
            for bar in bars:
                height = bar.get_height()
                axs[1, 0].text(
                    bar.get_x() + bar.get_width()/2.,
                    height,
                    str(int(height)),
                    ha='center',
                    va='bottom'
                )
            
            axs[1, 0].set_title('Component Status Breakdown', fontweight='bold')
            axs[1, 0].set_ylabel('Number of Components')
            axs[1, 0].tick_params(axis='x', rotation=45)
            axs[1, 0].grid(axis='y', linestyle='--', alpha=0.7)
        else:
            axs[1, 0].text(
                0.5, 0.5,
                "No status data available",
                ha='center',
                va='center',
                fontsize=14
            )
            axs[1, 0].axis('off')
        
        # 3. Bottleneck analysis
        if 'bottleneck_components' in readiness and readiness['bottleneck_components']:
            bottlenecks = readiness['bottleneck_components']
            
            # Extract data
            bottleneck_names = [b['component'] for b in bottlenecks]
            weeks_to_target = [b['weeks_to_target'] for b in bottlenecks]
            probabilities = [b['target_achievement_probability'] for b in bottlenecks]
            
            # Create twin axis
            ax1 = axs[1, 1]
            ax2 = ax1.twinx()
            
            # Plot weeks to target
            bars1 = ax1.bar(
                bottleneck_names,
                weeks_to_target,
                color='#2196F3',
                alpha=0.7,
                label='Weeks to Target'
            )
            
            # Plot achievement probability
            bars2 = ax2.bar(
                bottleneck_names,
                probabilities,
                color='#FF9800',
                alpha=0.7,
                label='Achievement Probability (%)'
            )
            
            # Add labels to weeks bars
            for bar in bars1:
                height = bar.get_height()
                ax1.text(
                    bar.get_x() + bar.get_width()/2.,
                    height,
                    f'{height:.1f}',
                    ha='center',
                    va='bottom',
                    color='#2196F3'
                )
            
            # Add labels to probability bars
            for bar in bars2:
                height = bar.get_height()
                ax2.text(
                    bar.get_x() + bar.get_width()/2.,
                    height,
                    f'{height:.1f}%',
                    ha='center',
                    va='bottom',
                    color='#FF9800'
                )
            
            ax1.set_title('Bottleneck Components', fontweight='bold')
            ax1.set_ylabel('Weeks to Target', color='#2196F3')
            ax2.set_ylabel('Achievement Probability (%)', color='#FF9800')
            
            # Add legends
            ax1.legend(loc='upper left')
            ax2.legend(loc='upper right')
            
            ax1.grid(True, linestyle='--', alpha=0.7)
        else:
            axs[1, 1].text(
                0.5, 0.5,
                "No bottleneck data available",
                ha='center',
                va='center',
                fontsize=14
            )
            axs[1, 1].axis('off')
        
        # Add overall readiness prediction as text
        earliest_date = readiness.get('earliest_completion_date', 'Unknown')
        expected_date = readiness.get('expected_completion_date', 'Unknown')
        latest_date = readiness.get('latest_completion_date', 'Unknown')
        
        fig.text(
            0.5, 0.02,
            f"Expected System Readiness: {expected_date} (Earliest: {earliest_date}, Latest: {latest_date})",
            ha='center',
            fontsize=14,
            fontweight='bold'
        )
        
        # Set overall title
        fig.suptitle('System Readiness Prediction', fontsize=20, fontweight='bold')
        
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        
        # Save figure
        output_path = os.path.join(self.output_dir, 'system_readiness.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved system readiness visualization to {output_path}")
        
        return fig
    
    def run_all_analyses(self):
        """
        Run all time series analyses.
        
        Returns:
            dict: All analysis results
        """
        print("Running time series analyses...")
        
        # Run trend analysis
        trend_df = self.analyze_trends()
        print(f"Trend analysis complete with {len(trend_df)} components.")
        
        # Run forecasting
        forecasts = self.forecast_component_performance()
        print(f"Forecasting complete for {len(forecasts)} components.")
        
        # Run improvement pattern analysis
        patterns = self.analyze_improvement_patterns()
        print(f"Improvement pattern analysis complete with {len(patterns)} components.")
        
        # Run correlation analysis
        correlations = self.identify_correlations()
        print(f"Correlation analysis complete with {len(correlations)} component pairs.")
        
        # Run system readiness prediction
        prediction = self.predict_system_readiness()
        print("System readiness prediction complete.")
        
        # Create visualizations
        self.visualize_trends()
        self.visualize_improvement_patterns()
        self.visualize_system_readiness()
        
        print("All analyses and visualizations complete.")
        
        # Return all results
        return self.analysis_results
    
    def export_results(self, format='csv'):
        """
        Export analysis results to files.
        
        Args:
            format (str): Export format ('csv' or 'json')
        """
        if not self.analysis_results:
            print("No analysis results available. Run analyses first.")
            return
        
        print(f"Exporting time series analysis results as {format}...")
        
        if format == 'csv':
            # Export DataFrames as CSV
            for name, data in self.analysis_results.items():
                if isinstance(data, pd.DataFrame):
                    output_path = os.path.join(self.output_dir, f"{name}.csv")
                    data.to_csv(output_path)
                    print(f"Exported {name} to {output_path}")
                elif isinstance(data, dict) and name != 'performance_forecasts':
                    # Convert simple dict to DataFrame
                    try:
                        dict_df = pd.DataFrame([data])
                        output_path = os.path.join(self.output_dir, f"{name}.csv")
                        dict_df.to_csv(output_path, index=False)
                        print(f"Exported {name} to {output_path}")
                    except Exception as e:
                        print(f"Could not export {name} as CSV: {e}")
        
        elif format == 'json':
            import json
            
            # Process results for JSON serialization
            json_results = {}
            
            for name, data in self.analysis_results.items():
                if isinstance(data, pd.DataFrame):
                    # Convert DataFrame to dict
                    json_results[name] = json.loads(data.to_json(orient='records'))
                elif isinstance(data, dict):
                    # Handle nested objects
                    processed_dict = {}
                    
                    for k, v in data.items():
                        if isinstance(v, pd.DataFrame):
                            processed_dict[k] = json.loads(v.to_json(orient='records'))
                        elif isinstance(v, np.ndarray):
                            processed_dict[k] = v.tolist()
                        elif isinstance(v, (np.int64, np.float64)):
                            processed_dict[k] = float(v)
                        else:
                            processed_dict[k] = v
                    
                    json_results[name] = processed_dict
            
            # Write to file
            output_path = os.path.join(self.output_dir, "time_series_analysis.json")
            
            with open(output_path, 'w') as f:
                json.dump(json_results, f, indent=2, default=str)
            
            print(f"Exported all analysis results to {output_path}")
        
        else:
            print(f"Unsupported format: {format}. Use 'csv' or 'json'.")


# Example usage
if __name__ == "__main__":
    analyzer = TimeSeriesAnalyzer(data_dir='./data')
    analyzer.run_all_analyses()
    analyzer.export_results(format='json')
    
    print("Time series analysis complete!")

"""
SUMMARY:
This code implements a comprehensive Time Series Analyzer for the Neuron Evaluation Framework. The analyzer provides detailed analysis of performance trends over time and forecasts future performance. Key functionality includes:

1. Trend Analysis - Examines performance trends for each component, calculating improvement rates, consistency, and time to target.

2. Performance Forecasting - Uses statistical models (ARIMA, exponential smoothing, linear regression) to forecast future performance and estimate when targets will be reached.

3. Improvement Pattern Analysis - Identifies patterns in how components improve over time, such as linear, exponential, logarithmic, or stepped improvements.

4. Component Correlation Analysis - Detects correlations between components to identify which ones tend to improve together or impede each other.

5. System Readiness Prediction - Forecasts when the overall system will be ready for production based on component readiness and bottlenecks.

6. Visualization - Creates detailed visualizations of trends, patterns, and system readiness for easy interpretation.

This analyzer provides valuable insights for project planning, identifying bottlenecks, and predicting when the Neuron Framework will be ready for production. It helps prioritize development efforts by showing which components are most critical to overall system readiness.
"""
