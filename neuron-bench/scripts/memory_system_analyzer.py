import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import os
import re
from sklearn.preprocessing import MinMaxScaler
from sklearn.cluster import KMeans

class MemmorySystemAnalyzer:
    """
    A specialized class for analyzing memory system performance in the Neuron Evaluation Framework.
    Focuses on memory retention, decay patterns, and optimization opportunities.
    """
    
    def __init__(self, data_dir='data', output_dir='memory_analysis'):
        """
        Initialize the memory system analyzer.
        
        Args:
            data_dir (str): Directory containing test data files
            output_dir (str): Directory to save analysis outputs
        """
        self.data_dir = data_dir
        self.output_dir = output_dir
        self.memory_data = None
        self.component_data = None
        self.error_data = None
        self.analysis_results = {}
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Load the memory data
        self._load_data()
    
    def _load_data(self):
        """Load memory retention data and related datasets."""
        # Load memory retention timeframe tests
        memory_file = Path(self.data_dir) / 'memory_retention_timeframe_tests.txt'
        
        if memory_file.exists():
            try:
                self.memory_data = pd.read_csv(memory_file)
                print(f"Loaded memory retention data with {len(self.memory_data)} test records.")
            except Exception as e:
                print(f"Error loading memory retention data: {e}")
        else:
            print(f"Memory retention data file not found: {memory_file}")
        
        # Load target gap analysis for memory component info
        gap_file = Path(self.data_dir) / 'target_gap_analysis.txt'
        
        if gap_file.exists():
            try:
                gap_df = pd.read_csv(gap_file)
                # Filter for memory-related components
                memory_components = gap_df[gap_df['component'].str.contains('Memory', case=False, na=False)]
                self.component_data = memory_components
                print(f"Loaded memory component data with {len(memory_components)} components.")
            except Exception as e:
                print(f"Error loading target gap analysis: {e}")
        
        # Load error analysis for memory-related errors
        error_file = Path(self.data_dir) / 'error_analysis_dataset.txt'
        
        if error_file.exists():
            try:
                error_df = pd.read_csv(error_file)
                # Filter for memory-related errors
                memory_errors = error_df[error_df['area'].str.contains('Memory', case=False, na=False)]
                self.error_data = memory_errors
                print(f"Loaded memory error data with {len(memory_errors)} error records.")
            except Exception as e:
                print(f"Error loading error analysis dataset: {e}")
    
    def analyze_retention_decay(self):
        """
        Analyze memory retention decay patterns across different timeframes and fact types.
        
        Returns:
            pandas.DataFrame: Retention decay analysis results
        """
        if self.memory_data is None:
            print("No memory data available.")
            return None
        
        # Group data by retention timeframe and fact type
        grouped = self.memory_data.groupby(['retention_timeframe', 'fact_type'])
        
        # Calculate average metrics for each group
        retention_stats = grouped.agg({
            'entities_recalled_pct': ['mean', 'std', 'min', 'max'],
            'relations_recalled_pct': ['mean', 'std', 'min', 'max'],
            'context_preserved_pct': ['mean', 'std', 'min', 'max'],
            'retrieval_accuracy': ['mean', 'std', 'min', 'max']
        })
        
        # Reset index for easier manipulation
        retention_stats = retention_stats.reset_index()
        
        # Flatten column names
        retention_stats.columns = ['_'.join(col).strip() if col[1] else col[0] for col in retention_stats.columns.values]
        
        # Extract numerical timeframe values
        def extract_timeframe_value(timeframe):
            # Pattern for timeframes like "10 minutes", "3 days", etc.
            match = re.match(r'(\d+)\s+(\w+)', timeframe)
            if match:
                value, unit = match.groups()
                # Convert to hours for easier comparison
                value = int(value)
                if 'minute' in unit:
                    return value / 60  # minutes to hours
                elif 'hour' in unit:
                    return value  # already in hours
                elif 'day' in unit:
                    return value * 24  # days to hours
                else:
                    return value  # default, keep as is
            return 0  # default if no match
        
        retention_stats['timeframe_hours'] = retention_stats['retention_timeframe'].apply(extract_timeframe_value)
        
        # Calculate overall retention score (weighted average of metrics)
        retention_stats['overall_retention_score'] = (
            retention_stats['entities_recalled_pct_mean'] * 0.3 +
            retention_stats['relations_recalled_pct_mean'] * 0.3 +
            retention_stats['context_preserved_pct_mean'] * 0.2 +
            retention_stats['retrieval_accuracy_mean'] * 0.2
        )
        
        # Calculate decay rate (change in retention per hour)
        # Group by fact type
        fact_types = retention_stats['fact_type'].unique()
        
        # Calculate decay rates for each fact type
        decay_rates = []
        
        for fact_type in fact_types:
            # Filter data for this fact type
            type_data = retention_stats[retention_stats['fact_type'] == fact_type].sort_values('timeframe_hours')
            
            # Calculate rate of change for each metric
            for i in range(1, len(type_data)):
                prev_row = type_data.iloc[i-1]
                curr_row = type_data.iloc[i]
                
                # Time difference in hours
                time_diff = curr_row['timeframe_hours'] - prev_row['timeframe_hours']
                
                if time_diff > 0:
                    # Calculate decay rates for each metric (percentage points per hour)
                    entities_decay = (prev_row['entities_recalled_pct_mean'] - curr_row['entities_recalled_pct_mean']) / time_diff
                    relations_decay = (prev_row['relations_recalled_pct_mean'] - curr_row['relations_recalled_pct_mean']) / time_diff
                    context_decay = (prev_row['context_preserved_pct_mean'] - curr_row['context_preserved_pct_mean']) / time_diff
                    accuracy_decay = (prev_row['retrieval_accuracy_mean'] - curr_row['retrieval_accuracy_mean']) / time_diff
                    
                    # Calculate overall decay rate
                    overall_decay = (prev_row['overall_retention_score'] - curr_row['overall_retention_score']) / time_diff
                    
                    # Store decay information
                    decay_rates.append({
                        'fact_type': fact_type,
                        'start_timeframe': prev_row['retention_timeframe'],
                        'end_timeframe': curr_row['retention_timeframe'],
                        'time_diff_hours': time_diff,
                        'entities_decay_rate': entities_decay,
                        'relations_decay_rate': relations_decay,
                        'context_decay_rate': context_decay,
                        'accuracy_decay_rate': accuracy_decay,
                        'overall_decay_rate': overall_decay
                    })
        
        # Convert decay rates to DataFrame
        decay_df = pd.DataFrame(decay_rates)
        
        # Categorize decay phases
        def categorize_decay(row):
            # Higher values indicate faster decay
            rate = row['overall_decay_rate']
            
            if rate < 0.05:  # Very slow decay
                return "Stable Phase"
            elif rate < 0.2:  # Slow decay
                return "Slow Decay Phase"
            elif rate < 0.5:  # Moderate decay
                return "Moderate Decay Phase"
            else:  # Rapid decay
                return "Rapid Decay Phase"
        
        decay_df['decay_phase'] = decay_df.apply(categorize_decay, axis=1)
        
        # Sort by fact type and start timeframe
        decay_df = decay_df.sort_values(['fact_type', 'start_timeframe'])
        
        # Round numeric columns for readability
        numeric_cols = [col for col in decay_df.columns if 'rate' in col or 'diff' in col]
        decay_df[numeric_cols] = decay_df[numeric_cols].round(4)
        
        # Save results
        self.analysis_results['retention_decay'] = decay_df
        
        # Also compute and save the retention stats
        self.analysis_results['retention_stats'] = retention_stats
        
        return decay_df
    
    def model_memory_curve(self):
        """
        Model memory retention curve using mathematical models (exponential decay, etc.).
        
        Returns:
            dict: Memory curve modeling results
        """
        if self.memory_data is None:
            print("No memory data available.")
            return None
        
        # Get unique fact types
        fact_types = self.memory_data['fact_type'].unique()
        
        # Models for each fact type
        models = {}
        
        for fact_type in fact_types:
            # Filter data for this fact type
            type_data = self.memory_data[self.memory_data['fact_type'] == fact_type].copy()
            
            # Extract timeframe in hours
            def timeframe_to_hours(timeframe):
                match = re.match(r'(\d+)\s+(\w+)', timeframe)
                if match:
                    value, unit = match.groups()
                    value = int(value)
                    if 'minute' in unit:
                        return value / 60  # minutes to hours
                    elif 'hour' in unit:
                        return value  # already in hours
                    elif 'day' in unit:
                        return value * 24  # days to hours
                    else:
                        return value  # default, keep as is
                return 0  # default if no match
            
            type_data['hours'] = type_data['retention_timeframe'].apply(timeframe_to_hours)
            
            # Sort by hours
            type_data = type_data.sort_values('hours')
            
            # Calculate average retention metrics
            avg_metrics = {
                'hours': type_data['hours'].values,
                'entities': type_data['entities_recalled_pct'].values,
                'relations': type_data['relations_recalled_pct'].values,
                'context': type_data['context_preserved_pct'].values,
                'accuracy': type_data['retrieval_accuracy'].values
            }
            
            # Fit exponential decay model (y = a * e^(-b*x) + c)
            # For each metric
            model_results = {}
            
            for metric in ['entities', 'relations', 'context', 'accuracy']:
                try:
                    # Initial parameter guesses
                    p0 = [100, 0.01, 0]  # Initial values for a, b, c
                    
                    # Try different models
                    
                    # 1. Exponential decay: y = a * e^(-b*x) + c
                    from scipy.optimize import curve_fit
                    
                    def exp_decay(x, a, b, c):
                        return a * np.exp(-b * x) + c
                    
                    x_data = avg_metrics['hours']
                    y_data = avg_metrics[metric]
                    
                    # Fit the model
                    try:
                        popt, pcov = curve_fit(exp_decay, x_data, y_data, p0=p0, bounds=([0, 0, 0], [100, 1, 100]))
                        a, b, c = popt
                        
                        # Calculate R-squared
                        y_pred = exp_decay(x_data, a, b, c)
                        ss_tot = np.sum((y_data - np.mean(y_data))**2)
                        ss_res = np.sum((y_data - y_pred)**2)
                        r_squared = 1 - (ss_res / ss_tot)
                        
                        model_results[metric] = {
                            'model_type': 'exponential_decay',
                            'parameters': {
                                'a': a,
                                'b': b,
                                'c': c
                            },
                            'formula': f'y = {a:.2f} * e^(-{b:.6f}*x) + {c:.2f}',
                            'r_squared': r_squared,
                            'half_life_hours': np.log(2) / b if b > 0 else float('inf')
                        }
                    except Exception as e:
                        print(f"Error fitting exponential decay for {fact_type}, {metric}: {e}")
                        model_results[metric] = {
                            'model_type': 'failed',
                            'error': str(e)
                        }
                    
                    # 2. Try power law decay: y = a * x^(-b) + c
                    def power_decay(x, a, b, c):
                        # Add small epsilon to avoid division by zero
                        return a * np.power(x + 1e-10, -b) + c
                    
                    try:
                        popt, pcov = curve_fit(power_decay, x_data, y_data, p0=p0, bounds=([0, 0, 0], [100, 10, 100]))
                        a, b, c = popt
                        
                        # Calculate R-squared
                        y_pred = power_decay(x_data, a, b, c)
                        ss_tot = np.sum((y_data - np.mean(y_data))**2)
                        ss_res = np.sum((y_data - y_pred)**2)
                        power_r_squared = 1 - (ss_res / ss_tot)
                        
                        # Only replace if power law gives better fit
                        if power_r_squared > model_results[metric].get('r_squared', 0):
                            model_results[metric] = {
                                'model_type': 'power_law',
                                'parameters': {
                                    'a': a,
                                    'b': b,
                                    'c': c
                                },
                                'formula': f'y = {a:.2f} * x^(-{b:.4f}) + {c:.2f}',
                                'r_squared': power_r_squared
                            }
                    except Exception as e:
                        print(f"Error fitting power law for {fact_type}, {metric}: {e}")
                        # Keep existing model if power law fails
                
                except Exception as e:
                    print(f"Error modeling {fact_type}, {metric}: {e}")
                    model_results[metric] = {
                        'model_type': 'failed',
                        'error': str(e)
                    }
            
            # Store model for this fact type
            models[fact_type] = model_results
        
        # Save the models
        self.analysis_results['memory_models'] = models
        
        return models
    
    def analyze_critical_thresholds(self):
        """
        Identify critical retention thresholds where performance significantly degrades.
        
        Returns:
            pandas.DataFrame: Critical threshold analysis
        """
        if self.memory_data is None:
            print("No memory data available.")
            return None
        
        # Initialize results
        thresholds = []
        
        # Analyze by fact type
        for fact_type in self.memory_data['fact_type'].unique():
            # Filter data for this fact type
            type_data = self.memory_data[self.memory_data['fact_type'] == fact_type].copy()
            
            # Convert timeframe to hours for consistent comparison
            def timeframe_to_hours(timeframe):
                match = re.match(r'(\d+)\s+(\w+)', timeframe)
                if match:
                    value, unit = match.groups()
                    value = int(value)
                    if 'minute' in unit:
                        return value / 60  # minutes to hours
                    elif 'hour' in unit:
                        return value  # already in hours
                    elif 'day' in unit:
                        return value * 24  # days to hours
                    else:
                        return value  # default, keep as is
                return 0  # default if no match
            
            type_data['hours'] = type_data['retention_timeframe'].apply(timeframe_to_hours)
            
            # Sort by hours
            type_data = type_data.sort_values('hours')
            
            # Calculate weighted retention score
            type_data['retention_score'] = (
                type_data['entities_recalled_pct'] * 0.3 +
                type_data['relations_recalled_pct'] * 0.3 +
                type_data['context_preserved_pct'] * 0.2 +
                type_data['retrieval_accuracy'] * 0.2
            )
            
            # Look for significant drops in retention score
            for i in range(1, len(type_data)):
                prev_row = type_data.iloc[i-1]
                curr_row = type_data.iloc[i]
                
                # Calculate drop amount and rate
                drop_amount = prev_row['retention_score'] - curr_row['retention_score']
                time_diff = curr_row['hours'] - prev_row['hours']
                
                if time_diff > 0:
                    drop_rate = drop_amount / time_diff
                    
                    # If this is a significant drop (>5 percentage points and >2x the average rate)
                    if drop_amount > 5:
                        # Calculate average drop rate for comparison
                        avg_rate = 0
                        count = 0
                        
                        for j in range(1, len(type_data)):
                            if j != i:  # Skip the current pair
                                diff = type_data.iloc[j-1]['retention_score'] - type_data.iloc[j]['retention_score']
                                time = type_data.iloc[j]['hours'] - type_data.iloc[j-1]['hours']
                                if time > 0:
                                    avg_rate += diff / time
                                    count += 1
                        
                        if count > 0:
                            avg_rate /= count
                        
                        # Check if this drop is a critical threshold
                        is_critical = (drop_rate > 2 * avg_rate) if avg_rate > 0 else (drop_rate > 0.5)
                        
                        # Store the threshold
                        thresholds.append({
                            'fact_type': fact_type,
                            'start_timeframe': prev_row['retention_timeframe'],
                            'end_timeframe': curr_row['retention_timeframe'],
                            'start_hours': prev_row['hours'],
                            'end_hours': curr_row['hours'],
                            'start_score': prev_row['retention_score'],
                            'end_score': curr_row['retention_score'],
                            'drop_amount': drop_amount,
                            'drop_rate': drop_rate,
                            'avg_drop_rate': avg_rate,
                            'is_critical_threshold': is_critical
                        })
        
        # Convert to DataFrame
        threshold_df = pd.DataFrame(thresholds)
        
        if len(threshold_df) > 0:
            # Sort by fact type and start timeframe
            threshold_df = threshold_df.sort_values(['fact_type', 'start_hours'])
            
            # Round numeric columns for readability
            numeric_cols = ['start_hours', 'end_hours', 'start_score', 'end_score', 
                           'drop_amount', 'drop_rate', 'avg_drop_rate']
            threshold_df[numeric_cols] = threshold_df[numeric_cols].round(2)
            
            # Save results
            self.analysis_results['critical_thresholds'] = threshold_df
            
            return threshold_df
        else:
            print("No significant thresholds identified.")
            return pd.DataFrame()
    
    def analyze_recall_asymmetry(self):
        """
        Analyze asymmetry in recall between different memory aspects (entities, relations, context).
        
        Returns:
            pandas.DataFrame: Recall asymmetry analysis
        """
        if self.memory_data is None:
            print("No memory data available.")
            return None
        
        # Calculate asymmetry metrics for each test
        asymmetry_data = []
        
        for _, row in self.memory_data.iterrows():
            # Calculate differences between recall metrics
            entity_relation_diff = row['entities_recalled_pct'] - row['relations_recalled_pct']
            entity_context_diff = row['entities_recalled_pct'] - row['context_preserved_pct']
            relation_context_diff = row['relations_recalled_pct'] - row['context_preserved_pct']
            
            # Calculate overall recall score
            recall_score = (
                row['entities_recalled_pct'] * 0.3 +
                row['relations_recalled_pct'] * 0.3 +
                row['context_preserved_pct'] * 0.2 +
                row['retrieval_accuracy'] * 0.2
            )
            
            # Calculate asymmetry index (sum of absolute differences)
            asymmetry_index = (
                abs(entity_relation_diff) + 
                abs(entity_context_diff) + 
                abs(relation_context_diff)
            ) / 3
            
            # Determine dominant recall aspect
            recall_aspects = {
                'entities': row['entities_recalled_pct'],
                'relations': row['relations_recalled_pct'],
                'context': row['context_preserved_pct']
            }
            dominant_aspect = max(recall_aspects, key=recall_aspects.get)
            
            # Store asymmetry data
            asymmetry_data.append({
                'test_id': row['test_id'],
                'fact_type': row['fact_type'],
                'retention_timeframe': row['retention_timeframe'],
                'entity_relation_diff': entity_relation_diff,
                'entity_context_diff': entity_context_diff,
                'relation_context_diff': relation_context_diff,
                'asymmetry_index': asymmetry_index,
                'dominant_aspect': dominant_aspect,
                'recall_score': recall_score
            })
        
        # Convert to DataFrame
        asymmetry_df = pd.DataFrame(asymmetry_data)
        
        # Convert timeframe to hours for consistent comparison
        def timeframe_to_hours(timeframe):
            match = re.match(r'(\d+)\s+(\w+)', timeframe)
            if match:
                value, unit = match.groups()
                value = int(value)
                if 'minute' in unit:
                    return value / 60  # minutes to hours
                elif 'hour' in unit:
                    return value  # already in hours
                elif 'day' in unit:
                    return value * 24  # days to hours
                else:
                    return value  # default, keep as is
            return 0  # default if no match
        
        asymmetry_df['hours'] = asymmetry_df['retention_timeframe'].apply(timeframe_to_hours)
        
        # Calculate average asymmetry by timeframe
        timeframe_asymmetry = asymmetry_df.groupby('retention_timeframe').agg({
            'hours': 'first',
            'asymmetry_index': 'mean',
            'entity_relation_diff': 'mean',
            'entity_context_diff': 'mean',
            'relation_context_diff': 'mean'
        }).reset_index()
        
        # Sort by hours
        timeframe_asymmetry = timeframe_asymmetry.sort_values('hours')
        
        # Calculate average asymmetry by fact type
        facttype_asymmetry = asymmetry_df.groupby('fact_type').agg({
            'asymmetry_index': 'mean',
            'entity_relation_diff': 'mean',
            'entity_context_diff': 'mean',
            'relation_context_diff': 'mean'
        }).reset_index()
        
        # Identify aspects that degrade faster
        # Group by fact type and timeframe
        degradation_analysis = []
        
        for fact_type in asymmetry_df['fact_type'].unique():
            # Filter data for this fact type
            type_data = asymmetry_df[asymmetry_df['fact_type'] == fact_type].sort_values('hours')
            
            # Calculate correlation between hours and each difference
            from scipy.stats import pearsonr
            
            entity_relation_corr, _ = pearsonr(type_data['hours'], type_data['entity_relation_diff'])
            entity_context_corr, _ = pearsonr(type_data['hours'], type_data['entity_context_diff'])
            relation_context_corr, _ = pearsonr(type_data['hours'], type_data['relation_context_diff'])
            
            # Positive correlation means the difference increases with time
            # (i.e., the first aspect degrades slower than the second)
            
            # Determine relative degradation rates
            degradation_order = []
            
            # Entity vs relation degradation
            if entity_relation_corr > 0.2:
                degradation_order.append("entities degrade slower than relations")
            elif entity_relation_corr < -0.2:
                degradation_order.append("relations degrade slower than entities")
            
            # Entity vs context degradation
            if entity_context_corr > 0.2:
                degradation_order.append("entities degrade slower than context")
            elif entity_context_corr < -0.2:
                degradation_order.append("context degrades slower than entities")
            
            # Relation vs context degradation
            if relation_context_corr > 0.2:
                degradation_order.append("relations degrade slower than context")
            elif relation_context_corr < -0.2:
                degradation_order.append("context degrades slower than relations")
            
            # Store analysis
            degradation_analysis.append({
                'fact_type': fact_type,
                'entity_relation_correlation': entity_relation_corr,
                'entity_context_correlation': entity_context_corr,
                'relation_context_correlation': relation_context_corr,
                'degradation_patterns': '; '.join(degradation_order)
            })
        
        # Convert to DataFrame
        degradation_df = pd.DataFrame(degradation_analysis)
        
        # Round numeric columns
        numeric_cols = [col for col in asymmetry_df.columns if 'diff' in col or 'index' in col or 'score' in col]
        asymmetry_df[numeric_cols] = asymmetry_df[numeric_cols].round(2)
        
        numeric_cols = [col for col in timeframe_asymmetry.columns if 'diff' in col or 'index' in col]
        timeframe_asymmetry[numeric_cols] = timeframe_asymmetry[numeric_cols].round(2)
        
        numeric_cols = [col for col in facttype_asymmetry.columns if 'diff' in col or 'index' in col]
        facttype_asymmetry[numeric_cols] = facttype_asymmetry[numeric_cols].round(2)
        
        numeric_cols = [col for col in degradation_df.columns if 'correlation' in col]
        degradation_df[numeric_cols] = degradation_df[numeric_cols].round(2)
        
        # Save results
        self.analysis_results['recall_asymmetry'] = asymmetry_df
        self.analysis_results['timeframe_asymmetry'] = timeframe_asymmetry
        self.analysis_results['facttype_asymmetry'] = facttype_asymmetry
        self.analysis_results['degradation_analysis'] = degradation_df
        
        # Return main asymmetry DataFrame
        return asymmetry_df
    
    def identify_memory_optimization_strategies(self):
        """
        Identify potential strategies for optimizing memory system based on analysis results.
        
        Returns:
            pandas.DataFrame: Memory optimization strategies
        """
        # Check if we have the necessary analyses
        required_analyses = ['retention_decay', 'critical_thresholds', 'recall_asymmetry']
        missing = [a for a in required_analyses if a not in self.analysis_results]
        
        if missing:
            print(f"Missing required analyses: {', '.join(missing)}")
            print("Run all analyses first.")
            return None
        
        # Initialize strategies
        strategies = []
        
        # 1. Strategies based on critical thresholds
        if 'critical_thresholds' in self.analysis_results:
            thresholds = self.analysis_results['critical_thresholds']
            critical_thresholds = thresholds[thresholds['is_critical_threshold']]
            
            if not critical_thresholds.empty:
                # Find the earliest critical threshold for each fact type
                for fact_type, group in critical_thresholds.groupby('fact_type'):
                    earliest = group.sort_values('start_hours').iloc[0]
                    
                    # Suggest reinforcement before this threshold
                    strategies.append({
                        'strategy_type': 'Targeted Reinforcement',
                        'fact_type': fact_type,
                        'timeframe': f"Before {earliest['start_timeframe']}",
                        'expected_impact': 'High',
                        'description': f"Add memory reinforcement mechanisms before the critical threshold at {earliest['start_timeframe']} to prevent significant decay for {fact_type} information."
                    })
                    
                    # Suggest compression if later thresholds
                    later_thresholds = group[group['start_hours'] > earliest['start_hours'] * 2]
                    
                    if not later_thresholds.empty:
                        # Suggest more aggressive compression for long-term storage
                        strategies.append({
                            'strategy_type': 'Semantic Compression',
                            'fact_type': fact_type,
                            'timeframe': f"After {earliest['end_timeframe']}",
                            'expected_impact': 'Medium',
                            'description': f"Implement semantic compression for {fact_type} after {earliest['end_timeframe']} to preserve essential information while reducing storage requirements."
                        })
        
        # 2. Strategies based on recall asymmetry
        if 'facttype_asymmetry' in self.analysis_results and 'degradation_analysis' in self.analysis_results:
            asymmetry = self.analysis_results['facttype_asymmetry']
            degradation = self.analysis_results['degradation_analysis']
            
            # For each fact type with high asymmetry
            for _, row in asymmetry.iterrows():
                if row['asymmetry_index'] > 5:  # Significant asymmetry
                    fact_type = row['fact_type']
                    
                    # Find degradation pattern for this fact type
                    degradation_row = degradation[degradation['fact_type'] == fact_type]
                    
                    if not degradation_row.empty:
                        degradation_pattern = degradation_row.iloc[0]['degradation_patterns']
                        
                        # Suggest strategies based on asymmetric degradation
                        if 'context' in degradation_pattern and 'degrades faster' in degradation_pattern:
                            strategies.append({
                                'strategy_type': 'Context Preservation',
                                'fact_type': fact_type,
                                'timeframe': 'All timeframes',
                                'expected_impact': 'High',
                                'description': f"Implement additional context binding mechanisms for {fact_type} to address faster degradation of contextual information compared to entities and relations."
                            })
                        
                        if 'relation' in degradation_pattern and 'degrades faster' in degradation_pattern:
                            strategies.append({
                                'strategy_type': 'Relation Strengthening',
                                'fact_type': fact_type,
                                'timeframe': 'All timeframes',
                                'expected_impact': 'Medium',
                                'description': f"Add relation reinforcement mechanisms for {fact_type} to address faster degradation of relational information compared to entities."
                            })
                        
                        if 'entities' in degradation_pattern and 'degrades faster' in degradation_pattern:
                            strategies.append({
                                'strategy_type': 'Entity Anchoring',
                                'fact_type': fact_type,
                                'timeframe': 'All timeframes',
                                'expected_impact': 'Medium',
                                'description': f"Implement stronger entity anchoring for {fact_type} to address faster degradation of entity information compared to relations and context."
                            })
        
        # 3. Strategies based on memory models
        if 'memory_models' in self.analysis_results:
            models = self.analysis_results['memory_models']
            
            for fact_type, metrics in models.items():
                # Check model types and parameters
                exponential_models = [m for m in metrics.values() if m.get('model_type') == 'exponential_decay']
                
                # Look for rapid decay models
                for metric_model in exponential_models:
                    if 'half_life_hours' in metric_model and metric_model['half_life_hours'] < 72:  # Less than 3 days
                        strategies.append({
                            'strategy_type': 'Decay Rate Optimization',
                            'fact_type': fact_type,
                            'timeframe': 'Long-term',
                            'expected_impact': 'High',
                            'description': f"Optimize decay parameters for {fact_type} to increase half-life beyond 72 hours (currently {metric_model['half_life_hours']:.1f} hours)."
                        })
                        break
        
        # 4. General strategies based on error data
        if self.error_data is not None:
            # Look for most frequent error types
            error_counts = self.error_data['error_type'].value_counts()
            
            for error_type, count in error_counts.items():
                if count >= 2:  # Occurs multiple times
                    # Get details for this error type
                    error_rows = self.error_data[self.error_data['error_type'] == error_type]
                    
                    # Average frequency and severity
                    avg_impact = error_rows['impact_severity'].mode()[0]
                    
                    if 'Overwriting' in error_type:
                        strategies.append({
                            'strategy_type': 'Overwrite Protection',
                            'fact_type': 'All types',
                            'timeframe': 'All timeframes',
                            'expected_impact': 'High' if avg_impact == 'High' else 'Medium',
                            'description': f"Implement protection mechanisms to prevent premature overwriting of important memory information."
                        })
                    elif 'Decay' in error_type:
                        strategies.append({
                            'strategy_type': 'Decay Rate Adjustment',
                            'fact_type': 'All types',
                            'timeframe': 'Long-term',
                            'expected_impact': 'High' if avg_impact == 'High' else 'Medium',
                            'description': f"Adjust decay parameters to slow down the rate of memory degradation over extended timeframes."
                        })
                    elif 'Retrieval' in error_type:
                        strategies.append({
                            'strategy_type': 'Retrieval Mechanism Enhancement',
                            'fact_type': 'All types',
                            'timeframe': 'All timeframes',
                            'expected_impact': 'Medium',
                            'description': f"Enhance memory retrieval mechanisms to improve recall accuracy under various conditions."
                        })
                    elif 'Association' in error_type:
                        strategies.append({
                            'strategy_type': 'Association Strengthening',
                            'fact_type': 'All types',
                            'timeframe': 'All timeframes',
                            'expected_impact': 'Medium',
                            'description': f"Implement stronger association mechanisms between related memory elements to prevent weakening over time."
                        })
        
        # 5. Add general optimization strategies
        
        # Memory indexing enhancement
        strategies.append({
            'strategy_type': 'Memory Indexing',
            'fact_type': 'All types',
            'timeframe': 'All timeframes',
            'expected_impact': 'High',
            'description': "Implement hierarchical memory indexing to improve retrieval efficiency and reduce context-dependent recall variations."
        })
        
        # Prioritization mechanisms
        strategies.append({
            'strategy_type': 'Importance-Based Retention',
            'fact_type': 'All types',
            'timeframe': 'Long-term',
            'expected_impact': 'High',
            'description': "Develop importance scoring mechanisms to prioritize retention of critical information while allowing less important details to decay normally."
        })
        
        # Memory consolidation
        strategies.append({
            'strategy_type': 'Periodic Consolidation',
            'fact_type': 'All types',
            'timeframe': 'Medium to Long-term',
            'expected_impact': 'Medium',
            'description': "Implement periodic memory consolidation processes that strengthen important memories and compress related information."
        })
        
        # Convert to DataFrame
        strategies_df = pd.DataFrame(strategies)
        
        # Remove duplicates
        strategies_df = strategies_df.drop_duplicates()
        
        # Sort by expected impact
        impact_order = {'High': 0, 'Medium': 1, 'Low': 2}
        strategies_df['impact_order'] = strategies_df['expected_impact'].map(impact_order)
        strategies_df = strategies_df.sort_values('impact_order').drop(columns=['impact_order'])
        
        # Save results
        self.analysis_results['optimization_strategies'] = strategies_df
        
        return strategies_df
    
    def visualize_memory_decay(self):
        """
        Visualize memory retention decay patterns.
        
        Returns:
            matplotlib.figure.Figure: The generated figure
        """
        if self.memory_data is None:
            print("No memory data available.")
            return None
        
        # Prepare data
        viz_data = self.memory_data.copy()
        
        # Convert timeframe to hours for consistent comparison
        def timeframe_to_hours(timeframe):
            match = re.match(r'(\d+)\s+(\w+)', timeframe)
            if match:
                value, unit = match.groups()
                value = int(value)
                if 'minute' in unit:
                    return value / 60  # minutes to hours
                elif 'hour' in unit:
                    return value  # already in hours
                elif 'day' in unit:
                    return value * 24  # days to hours
                else:
                    return value  # default, keep as is
            return 0  # default if no match
        
        viz_data['hours'] = viz_data['retention_timeframe'].apply(timeframe_to_hours)
        
        # Create figure with multiple subplots
        fig, axs = plt.subplots(2, 2, figsize=(15, 12))
        
        # 1. Overall retention by timeframe
        for fact_type, group in viz_data.groupby('fact_type'):
            # Sort by hours
            group = group.sort_values('hours')
            
            # Calculate overall retention score
            group['retention_score'] = (
                group['entities_recalled_pct'] * 0.3 +
                group['relations_recalled_pct'] * 0.3 +
                group['context_preserved_pct'] * 0.2 +
                group['retrieval_accuracy'] * 0.2
            )
            
            # Plot retention score vs time
            axs[0, 0].plot(
                group['hours'],
                group['retention_score'],
                marker='o',
                linestyle='-',
                label=fact_type
            )
        
        # Set plot properties
        axs[0, 0].set_title('Overall Memory Retention Over Time', fontweight='bold')
        axs[0, 0].set_xlabel('Hours')
        axs[0, 0].set_ylabel('Retention Score (%)')
        axs[0, 0].set_ylim(0, 100)
        axs[0, 0].grid(True, linestyle='--', alpha=0.7)
        axs[0, 0].legend()
        
        # Add reference lines for day boundaries
        for day in [24, 48, 72, 168, 336, 504]:  # 1, 2, 3, 7, 14, 21 days
            axs[0, 0].axvline(
                x=day,
                color='gray',
                linestyle='--',
                alpha=0.5
            )
            axs[0, 0].text(
                day, 5,
                f"{day//24}d" if day >= 24 else f"{day}h",
                ha='center',
                fontsize=8
            )
        
        # 2. Comparison of recall metrics
        # Select one fact type (e.g., personal_details) for clarity
        if 'personal_details' in viz_data['fact_type'].unique():
            pd_data = viz_data[viz_data['fact_type'] == 'personal_details'].sort_values('hours')
            
            # Plot each metric
            axs[0, 1].plot(pd_data['hours'], pd_data['entities_recalled_pct'], marker='o', label='Entities')
            axs[0, 1].plot(pd_data['hours'], pd_data['relations_recalled_pct'], marker='s', label='Relations')
            axs[0, 1].plot(pd_data['hours'], pd_data['context_preserved_pct'], marker='^', label='Context')
            axs[0, 1].plot(pd_data['hours'], pd_data['retrieval_accuracy'], marker='x', label='Accuracy')
            
            axs[0, 1].set_title('Recall Metrics for Personal Details', fontweight='bold')
            axs[0, 1].set_xlabel('Hours')
            axs[0, 1].set_ylabel('Recall Percentage (%)')
            axs[0, 1].set_ylim(0, 100)
            axs[0, 1].grid(True, linestyle='--', alpha=0.7)
            axs[0, 1].legend()
            
            # Add reference lines for day boundaries
            for day in [24, 48, 72, 168, 336, 504]:  # 1, 2, 3, 7, 14, 21 days
                axs[0, 1].axvline(
                    x=day,
                    color='gray',
                    linestyle='--',
                    alpha=0.5
                )
        
        # 3. Critical thresholds visualization
        if 'critical_thresholds' in self.analysis_results:
            thresholds = self.analysis_results['critical_thresholds']
            
            if not thresholds.empty:
                # Plot overall retention again
                for fact_type, group in viz_data.groupby('fact_type'):
                    # Sort by hours
                    group = group.sort_values('hours')
                    
                    # Calculate overall retention score
                    group['retention_score'] = (
                        group['entities_recalled_pct'] * 0.3 +
                        group['relations_recalled_pct'] * 0.3 +
                        group['context_preserved_pct'] * 0.2 +
                        group['retrieval_accuracy'] * 0.2
                    )
                    
                    # Plot retention score vs time
                    axs[1, 0].plot(
                        group['hours'],
                        group['retention_score'],
                        marker='o',
                        linestyle='-',
                        label=fact_type,
                        alpha=0.6
                    )
                
                # Highlight critical thresholds
                for _, row in thresholds[thresholds['is_critical_threshold']].iterrows():
                    axs[1, 0].axvspan(
                        row['start_hours'],
                        row['end_hours'],
                        alpha=0.2,
                        color='red',
                        label='_nolegend_'
                    )
                    
                    # Add text annotation for each critical threshold
                    axs[1, 0].text(
                        (row['start_hours'] + row['end_hours']) / 2,
                        row['end_score'] - 5,
                        f"{row['drop_amount']:.1f}%",
                        ha='center',
                        fontsize=8,
                        bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.2')
                    )
                
                axs[1, 0].set_title('Critical Memory Decay Thresholds', fontweight='bold')
                axs[1, 0].set_xlabel('Hours')
                axs[1, 0].set_ylabel('Retention Score (%)')
                axs[1, 0].set_ylim(0, 100)
                axs[1, 0].grid(True, linestyle='--', alpha=0.7)
                
                # Add custom legend entry for critical thresholds
                from matplotlib.patches import Patch
                legend_elements = [Patch(facecolor='red', alpha=0.2, label='Critical Threshold')]
                
                # Combine with existing legend
                fact_types = viz_data['fact_type'].unique()
                for i, fact_type in enumerate(fact_types):
                    color = axs[1, 0].get_lines()[i].get_color()
                    legend_elements.append(Patch(facecolor=color, alpha=0.6, label=fact_type))
                
                axs[1, 0].legend(handles=legend_elements)
        
        # 4. Model fit visualization
        if 'memory_models' in self.analysis_results:
            models = self.analysis_results['memory_models']
            
            # Pick one fact type and one metric for demonstration
            if 'personal_details' in models:
                fact_type = 'personal_details'
                model_data = models[fact_type]
                
                # Get data for this fact type
                type_data = viz_data[viz_data['fact_type'] == fact_type].sort_values('hours')
                hours = type_data['hours'].values
                
                # Plot actual data for multiple metrics
                axs[1, 1].scatter(hours, type_data['entities_recalled_pct'], label='Entities (Actual)', alpha=0.7, s=50)
                axs[1, 1].scatter(hours, type_data['relations_recalled_pct'], label='Relations (Actual)', alpha=0.7, s=50)
                
                # Show model predictions if available
                for metric in ['entities', 'relations']:
                    if metric in model_data and 'model_type' in model_data[metric]:
                        if model_data[metric]['model_type'] == 'exponential_decay':
                            # Get parameters
                            a = model_data[metric]['parameters']['a']
                            b = model_data[metric]['parameters']['b']
                            c = model_data[metric]['parameters']['c']
                            
                            # Generate smooth curve
                            x_smooth = np.linspace(0, max(hours) * 1.2, 100)
                            y_smooth = a * np.exp(-b * x_smooth) + c
                            
                            # Plot model fit
                            axs[1, 1].plot(
                                x_smooth, 
                                y_smooth, 
                                linestyle='--',
                                alpha=0.8,
                                label=f"{metric.capitalize()} (Model)"
                            )
                            
                            # Add half-life marker if available
                            if 'half_life_hours' in model_data[metric]:
                                half_life = model_data[metric]['half_life_hours']
                                
                                if half_life < max(hours) * 1.2:
                                    half_life_y = a * np.exp(-b * half_life) + c
                                    
                                    axs[1, 1].plot(
                                        [half_life], 
                                        [half_life_y], 
                                        marker='*',
                                        markersize=10,
                                        color='red',
                                        label=f"Half-life ({half_life:.1f} hours)"
                                    )
                        
                        elif model_data[metric]['model_type'] == 'power_law':
                            # Get parameters
                            a = model_data[metric]['parameters']['a']
                            b = model_data[metric]['parameters']['b']
                            c = model_data[metric]['parameters']['c']
                            
                            # Generate smooth curve
                            x_smooth = np.linspace(1, max(hours) * 1.2, 100)  # Start at 1 to avoid division by zero
                            y_smooth = a * np.power(x_smooth, -b) + c
                            
                            # Plot model fit
                            axs[1, 1].plot(
                                x_smooth, 
                                y_smooth, 
                                linestyle='--',
                                alpha=0.8,
                                label=f"{metric.capitalize()} (Model)"
                            )
                
                axs[1, 1].set_title('Memory Decay Model Fit', fontweight='bold')
                axs[1, 1].set_xlabel('Hours')
                axs[1, 1].set_ylabel('Recall Percentage (%)')
                axs[1, 1].set_ylim(0, 100)
                axs[1, 1].grid(True, linestyle='--', alpha=0.7)
                axs[1, 1].legend()
        
        # Set overall title
        fig.suptitle('Memory System Retention Analysis', fontsize=16, fontweight='bold')
        
        plt.tight_layout()
        
        # Save figure
        output_path = os.path.join(self.output_dir, 'memory_decay_analysis.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved memory decay visualization to {output_path}")
        
        return fig
    
    def visualize_optimization_strategies(self):
        """
        Visualize recommended memory optimization strategies.
        
        Returns:
            matplotlib.figure.Figure: The generated figure
        """
        if 'optimization_strategies' not in self.analysis_results:
            print("Run identify_memory_optimization_strategies first.")
            return None
        
        strategies = self.analysis_results['optimization_strategies']
        
        # Create figure
        fig, axs = plt.subplots(2, 1, figsize=(12, 10))
        
        # 1. Strategy types distribution
        strategy_counts = strategies['strategy_type'].value_counts()
        
        bars = axs[0].barh(
            strategy_counts.index,
            strategy_counts.values,
            color=sns.color_palette("viridis", len(strategy_counts))
        )
        
        # Add count labels
        for bar in bars:
            width = bar.get_width()
            axs[0].text(
                width + 0.1,
                bar.get_y() + bar.get_height()/2,
                str(int(width)),
                va='center'
            )
        
        axs[0].set_title('Memory Optimization Strategy Types', fontweight='bold')
        axs[0].set_xlabel('Number of Strategies')
        axs[0].grid(axis='x', linestyle='--', alpha=0.7)
        
        # 2. Impact and timeframe visualization
        # Create a matrix of timeframe vs impact
        timeframes = strategies['timeframe'].unique()
        impacts = ['High', 'Medium', 'Low']
        
        # Count strategies for each combination
        timeframe_impact_counts = np.zeros((len(timeframes), len(impacts)))
        
        for i, timeframe in enumerate(timeframes):
            for j, impact in enumerate(impacts):
                count = len(strategies[(strategies['timeframe'] == timeframe) & 
                                      (strategies['expected_impact'] == impact)])
                timeframe_impact_counts[i, j] = count
        
        # Create heatmap
        sns.heatmap(
            timeframe_impact_counts,
            annot=True,
            fmt='.0f',
            cmap='YlGnBu',
            xticklabels=impacts,
            yticklabels=timeframes,
            ax=axs[1]
        )
        
        axs[1].set_title('Strategies by Timeframe and Expected Impact', fontweight='bold')
        axs[1].set_ylabel('Timeframe')
        axs[1].set_xlabel('Expected Impact')
        
        # Set overall title
        fig.suptitle('Memory Optimization Strategy Analysis', fontsize=16, fontweight='bold')
        
        plt.tight_layout()
        
        # Save figure
        output_path = os.path.join(self.output_dir, 'memory_optimization_strategies.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved optimization strategies visualization to {output_path}")
        
        return fig
    
    def run_all_analyses(self):
        """
        Run all memory system analyses.
        
        Returns:
            dict: All analysis results
        """
        print("Running memory system analyses...")
        
        # Run retention decay analysis
        retention_decay = self.analyze_retention_decay()
        print("Retention decay analysis complete.")
        
        # Run memory curve modeling
        memory_models = self.model_memory_curve()
        print("Memory curve modeling complete.")
        
        # Run critical threshold analysis
        thresholds = self.analyze_critical_thresholds()
        print("Critical threshold analysis complete.")
        
        # Run recall asymmetry analysis
        asymmetry = self.analyze_recall_asymmetry()
        print("Recall asymmetry analysis complete.")
        
        # Identify optimization strategies
        strategies = self.identify_memory_optimization_strategies()
        print("Optimization strategy identification complete.")
        
        # Create visualizations
        self.visualize_memory_decay()
        self.visualize_optimization_strategies()
        
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
        
        print(f"Exporting memory system analysis results as {format}...")
        
        if format == 'csv':
            # Export DataFrames as CSV
            for name, data in self.analysis_results.items():
                if isinstance(data, pd.DataFrame):
                    output_path = os.path.join(self.output_dir, f"{name}.csv")
                    data.to_csv(output_path, index=False)
                    print(f"Exported {name} to {output_path}")
                    
        elif format == 'json':
            import json
            
            # Handle special case for memory_models which contains nested dicts
            json_results = {}
            
            for name, data in self.analysis_results.items():
                if isinstance(data, pd.DataFrame):
                    json_results[name] = json.loads(data.to_json(orient='records'))
                elif isinstance(data, dict):
                    # Handle nested dicts
                    try:
                        json_results[name] = data
                    except:
                        # If it can't be directly serialized, convert to string
                        json_results[name] = str(data)
            
            # Write to file
            output_path = os.path.join(self.output_dir, "memory_analysis.json")
            
            with open(output_path, 'w') as f:
                json.dump(json_results, f, indent=2, default=str)
            
            print(f"Exported all analysis results to {output_path}")
        
        else:
            print(f"Unsupported format: {format}. Use 'csv' or 'json'.")


# Example usage
if __name__ == "__main__":
    analyzer = MemmorySystemAnalyzer(data_dir='./data')
    analyzer.run_all_analyses()
    analyzer.export_results(format='json')
    
    print("Memory system analysis complete!")

"""
SUMMARY:
This code implements a specialized Memory System Analyzer for the Neuron Evaluation Framework. The analyzer provides detailed analysis of memory retention patterns, decay characteristics, and optimization opportunities. Key functionality includes:

1. Retention Decay Analysis - Examines how different aspects of memory (entities, relations, context) decay over time, identifying decay rates and phases.

2. Memory Curve Modeling - Fits mathematical models (exponential decay, power law) to memory retention data to quantify and predict decay patterns.

3. Critical Threshold Analysis - Identifies timeframes where significant drops in retention occur, highlighting critical points for memory reinforcement.

4. Recall Asymmetry Analysis - Examines differences in how various aspects of memory degrade, revealing which elements (entities, relations, context) are most vulnerable.

5. Optimization Strategy Identification - Generates recommended strategies for improving memory system performance based on analysis results.

6. Visualizations - Creates detailed visualizations of memory decay patterns, model fits, and optimization strategies.

This analyzer addresses one of the key improvement areas identified in the Neuron Framework, specifically the "Long-term memory persistence beyond 14 days" which was highlighted as a critical enhancement needed before deployment.
"""
