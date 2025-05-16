import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import os

class GapAnalysisEngine:
    """
    A class to perform detailed gap analysis on Neuron Evaluation Framework data.
    This engine calculates gaps between current and target performance, prioritizes improvements,
    and provides actionable insights for system enhancement.
    """
    
    def __init__(self, data_processor=None, data_dir='data'):
        """
        Initialize the gap analysis engine with either a data processor or raw data directory.
        
        Args:
            data_processor: NeuronDataProcessor instance (if available)
            data_dir (str): Path to directory containing data files (used if processor not provided)
        """
        self.data_processor = data_processor
        self.data_dir = data_dir
        self.datasets = {}
        self.analysis_results = {}
        
        # Load datasets if processor not provided
        if self.data_processor is None:
            self._load_datasets()
        else:
            self.datasets = self.data_processor.datasets
    
    def _load_datasets(self):
        """
        Load necessary datasets from files if no data processor was provided.
        """
        data_path = Path(self.data_dir)
        
        # Required files for gap analysis
        required_files = [
            'target_gap_analysis.txt',
            'dimension_detailed_metrics.txt',
            'performance_over_time.txt',
            'improvement_priorities.txt'
        ]
        
        for filename in required_files:
            file_path = data_path / filename
            if file_path.exists():
                dataset_name = file_path.stem
                try:
                    df = pd.read_csv(file_path)
                    self.datasets[dataset_name] = df
                    print(f"Loaded {dataset_name} with {len(df)} records")
                except Exception as e:
                    print(f"Error loading {file_path}: {e}")
            else:
                print(f"Warning: Required file {filename} not found")
    
    def calculate_component_gaps(self):
        """
        Calculate gaps between current and target performance for all components.
        Augments the gap analysis with additional metrics and categorization.
        
        Returns:
            pandas.DataFrame: Enhanced gap analysis data
        """
        if 'target_gap_analysis' not in self.datasets:
            print("Target gap analysis dataset not found")
            return None
        
        gap_df = self.datasets['target_gap_analysis'].copy()
        
        # Calculate additional metrics
        gap_df['percent_complete'] = (gap_df['current_score'] / gap_df['target_score'] * 100).round(1)
        gap_df['effort_to_target'] = np.where(
            gap_df['current_score'] >= gap_df['target_score'],
            0,  # Already at or above target
            (gap_df['target_score'] - gap_df['current_score']) * (
                np.where(gap_df['gap'] < -5, 2.0,  # Major gaps require more effort
                         np.where(gap_df['gap'] < -2, 1.5, 1.0))  # Moderate or minor gaps
            )
        )
        
        # Categorize components by gap severity
        conditions = [
            (gap_df['gap'] > 0),  # Exceeds target
            (gap_df['gap'] == 0),  # Meets target exactly
            (gap_df['gap'] > -3) & (gap_df['gap'] < 0),  # Approaching target
            (gap_df['gap'] <= -3) & (gap_df['gap'] > -7),  # Moderate gap
            (gap_df['gap'] <= -7)  # Significant gap
        ]
        
        categories = [
            'EXCEEDS TARGET',
            'MEETS TARGET',
            'APPROACHING TARGET',
            'MODERATE GAP',
            'SIGNIFICANT GAP'
        ]
        
        gap_df['gap_category'] = np.select(conditions, categories, default='UNKNOWN')
        
        # Determine if component is a bottleneck (significantly behind other components)
        mean_gap = gap_df['gap'].mean()
        std_gap = gap_df['gap'].std()
        gap_df['is_bottleneck'] = gap_df['gap'] < (mean_gap - std_gap)
        
        # Determine if component is critical (high priority and significant gap)
        gap_df['is_critical'] = (gap_df['priority'] == 'HIGH') & (gap_df['gap'] < -3)
        
        # Sort by priority and gap
        priority_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
        gap_df['priority_order'] = gap_df['priority'].map(priority_order)
        sorted_gap_df = gap_df.sort_values(by=['priority_order', 'gap'], ascending=[True, True])
        
        # Drop the helper column
        sorted_gap_df = sorted_gap_df.drop(columns=['priority_order'])
        
        self.analysis_results['component_gaps'] = sorted_gap_df
        return sorted_gap_df
    
    def analyze_improvement_efficiency(self):
        """
        Analyze the efficiency of potential improvements based on effort vs. impact.
        
        Returns:
            pandas.DataFrame: Improvement efficiency analysis
        """
        if 'improvement_priorities' not in self.datasets:
            print("Improvement priorities dataset not found")
            return None
        
        df = self.datasets['improvement_priorities'].copy()
        
        # Map complexity to numeric values for calculation
        complexity_map = {
            'LOW': 1,
            'MEDIUM': 2,
            'MEDIUM-HIGH': 3,
            'HIGH': 4
        }
        
        # Convert complexity to numeric
        df['complexity_numeric'] = df['complexity'].map(complexity_map)
        
        # Convert timeframe to average weeks
        df['avg_weeks'] = df['timeframe_weeks'].apply(
            lambda x: sum(map(float, x.split('-'))) / 2 if '-' in str(x) else float(x)
        )
        
        # Calculate efficiency metrics
        df['gap_per_week'] = df['gap'] / df['avg_weeks']
        df['impact_per_complexity'] = df['expected_impact'].map({
            'Minor': 1,
            'Moderate': 2,
            'Significant': 3,
            'High': 4,
            'Critical': 5
        }) / df['complexity_numeric']
        
        # Calculate overall efficiency score (higher is better)
        df['efficiency_score'] = (df['gap_per_week'] * 0.5) + (df['impact_per_complexity'] * 0.5)
        
        # Sort by efficiency score (descending)
        sorted_df = df.sort_values(by='efficiency_score', ascending=False)
        
        # Keep only relevant columns for the result
        cols_to_keep = [
            'area_id', 'component', 'improvement_area', 'current_score', 'target_score', 
            'gap', 'priority', 'complexity', 'timeframe_weeks', 'expected_impact', 
            'dependencies', 'efficiency_score'
        ]
        
        result = sorted_df[cols_to_keep]
        self.analysis_results['improvement_efficiency'] = result
        return result
    
    def calculate_dimension_gaps(self):
        """
        Calculate gaps for each evaluation dimension and sub-dimension.
        Identifies critical gaps that need attention.
        
        Returns:
            pandas.DataFrame: Dimension gap analysis
        """
        if 'dimension_detailed_metrics' not in self.datasets:
            print("Dimension detailed metrics dataset not found")
            return None
        
        df = self.datasets['dimension_detailed_metrics'].copy()
        
        # Calculate gap percentage
        df['gap_percentage'] = (df['gap'] / df['target'] * 100).round(2)
        
        # Determine gap status
        conditions = [
            (df['gap'] > 0),  # Exceeds target
            (df['gap'] == 0),  # Meets target exactly
            (df['gap'] > -3) & (df['gap'] < 0),  # Approaching target
            (df['gap'] <= -3) & (df['gap'] > -7),  # Moderate gap
            (df['gap'] <= -7)  # Significant gap
        ]
        
        categories = [
            'EXCEEDS TARGET',
            'MEETS TARGET',
            'APPROACHING TARGET',
            'MODERATE GAP',
            'SIGNIFICANT GAP'
        ]
        
        df['gap_status'] = np.select(conditions, categories, default='UNKNOWN')
        
        # Flag critical sub-metrics (significant gaps)
        df['is_critical'] = df['gap'] <= -7
        
        # Create separate DataFrames for dimensions and sub-metrics
        dimensions = df[df['sub_metric'] == 'Overall Score'].copy()
        sub_metrics = df[df['sub_metric'] != 'Overall Score'].copy()
        
        # Group critical sub-metrics by dimension
        critical_sub_metrics = sub_metrics[sub_metrics['is_critical']]
        critical_by_dimension = critical_sub_metrics.groupby('dimension').size().reset_index(name='critical_count')
        
        # Add critical count to dimensions
        dimensions = dimensions.merge(critical_by_dimension, on='dimension', how='left')
        dimensions['critical_count'] = dimensions['critical_count'].fillna(0).astype(int)
        
        # Sort dimensions by gap (ascending)
        dimensions_sorted = dimensions.sort_values(by='gap')
        
        # Sort sub-metrics by gap (ascending) and group by dimension
        sub_metrics_sorted = sub_metrics.sort_values(by=['dimension', 'gap'])
        
        self.analysis_results['dimension_gaps'] = dimensions_sorted
        self.analysis_results['sub_metric_gaps'] = sub_metrics_sorted
        
        return dimensions_sorted, sub_metrics_sorted
    
    def analyze_time_to_target(self):
        """
        Analyze the estimated time to reach targets based on current improvement rates.
        
        Returns:
            pandas.DataFrame: Time-to-target analysis
        """
        if 'performance_over_time' not in self.datasets:
            print("Performance over time dataset not found")
            return None
        
        pot_df = self.datasets['performance_over_time'].copy()
        
        # Calculate improvement rate per week
        pot_df['improvement_rate'] = ((pot_df['week16'] - pot_df['week1']) / 15).round(3)
        
        # Calculate remaining gap
        pot_df['remaining_gap'] = pot_df['production_target'] - pot_df['week16']
        
        # Calculate weeks to target assuming consistent improvement rate
        # Use small positive value instead of 0 for improvement rate to avoid division by zero
        pot_df['improvement_rate_adj'] = pot_df['improvement_rate'].apply(lambda x: max(x, 0.001))
        pot_df['weeks_to_target'] = (pot_df['remaining_gap'] / pot_df['improvement_rate_adj']).round(1)
        
        # Clean up infinite or negative values
        pot_df['weeks_to_target'] = pot_df['weeks_to_target'].apply(
            lambda x: 0 if x <= 0 else (99 if x > 99 or np.isinf(x) else x)
        )
        
        # Calculate estimated completion date (assuming 1 week = 7 days)
        import datetime
        today = datetime.datetime.now().date()
        pot_df['est_completion_date'] = pot_df['weeks_to_target'].apply(
            lambda w: (today + datetime.timedelta(days=int(w * 7))).strftime('%Y-%m-%d') if w > 0 else 'Complete'
        )
        
        # Categorize components by estimated completion time
        conditions = [
            (pot_df['weeks_to_target'] == 0),  # Already complete
            (pot_df['weeks_to_target'] <= 4),  # Short-term (1 month)
            (pot_df['weeks_to_target'] <= 12),  # Medium-term (3 months)
            (pot_df['weeks_to_target'] <= 24),  # Long-term (6 months)
            (pot_df['weeks_to_target'] > 24)  # Extended timeline
        ]
        
        categories = ['COMPLETE', 'SHORT-TERM', 'MEDIUM-TERM', 'LONG-TERM', 'EXTENDED']
        pot_df['completion_horizon'] = np.select(conditions, categories, default='UNKNOWN')
        
        # Sort by weeks to target (descending)
        sorted_df = pot_df.sort_values(by='weeks_to_target', ascending=False)
        
        self.analysis_results['time_to_target'] = sorted_df
        return sorted_df
    
    def identify_critical_improvements(self, top_n=10):
        """
        Identify the most critical improvements needed based on gap analysis.
        
        Args:
            top_n (int): Number of critical improvements to identify
            
        Returns:
            pandas.DataFrame: Critical improvements list
        """
        # Combine data from gap analysis and improvement priorities
        if 'component_gaps' not in self.analysis_results or 'improvement_priorities' not in self.datasets:
            print("Required data not available. Run calculate_component_gaps first.")
            return None
        
        gaps_df = self.analysis_results['component_gaps']
        improvements_df = self.datasets['improvement_priorities']
        
        # Get components with critical gaps
        critical_components = gaps_df[gaps_df['is_critical']]['component'].unique()
        
        # Find improvements for critical components
        critical_improvements = improvements_df[
            improvements_df['component'].isin(critical_components)
        ].copy()
        
        # If we don't have enough critical improvements, add high priority ones
        if len(critical_improvements) < top_n:
            high_priority = improvements_df[
                (improvements_df['priority'] == 'HIGH') & 
                (~improvements_df['component'].isin(critical_components))
            ]
            critical_improvements = pd.concat([critical_improvements, high_priority])
        
        # Sort by priority and gap
        priority_map = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
        critical_improvements['priority_value'] = critical_improvements['priority'].map(priority_map)
        
        sorted_improvements = critical_improvements.sort_values(
            by=['priority_value', 'gap'], 
            ascending=[True, False]
        ).head(top_n)
        
        # Drop helper column
        if 'priority_value' in sorted_improvements.columns:
            sorted_improvements = sorted_improvements.drop(columns=['priority_value'])
        
        self.analysis_results['critical_improvements'] = sorted_improvements
        return sorted_improvements
    
    def generate_priority_action_plan(self):
        """
        Generate a prioritized action plan based on all gap analyses.
        
        Returns:
            pandas.DataFrame: Prioritized action plan
        """
        # Ensure we have all necessary analyses
        if not all(k in self.analysis_results for k in ['component_gaps', 'improvement_efficiency', 'time_to_target']):
            print("Run all analysis methods first to generate the action plan")
            return None
        
        # Get improvement priorities dataset
        if 'improvement_priorities' not in self.datasets:
            print("Improvement priorities dataset not found")
            return None
        
        improvements = self.datasets['improvement_priorities'].copy()
        component_gaps = self.analysis_results['component_gaps']
        efficiency = self.analysis_results['improvement_efficiency']
        time_to_target = self.analysis_results['time_to_target']
        
        # Merge improvement data with additional analyses
        action_plan = improvements.merge(
            component_gaps[['component', 'is_bottleneck', 'is_critical']],
            on='component',
            how='left'
        )
        
        # Add efficiency score
        action_plan = action_plan.merge(
            efficiency[['area_id', 'efficiency_score']],
            on='area_id',
            how='left'
        )
        
        # Add time to target info
        action_plan = action_plan.merge(
            time_to_target[['component', 'weeks_to_target', 'completion_horizon']],
            on='component',
            how='left'
        )
        
        # Fill NaN values
        action_plan['is_bottleneck'] = action_plan['is_bottleneck'].fillna(False)
        action_plan['is_critical'] = action_plan['is_critical'].fillna(False)
        action_plan['efficiency_score'] = action_plan['efficiency_score'].fillna(0)
        
        # Calculate final priority score (higher = higher priority)
        # Factors:
        # - Base priority (HIGH=3, MEDIUM=2, LOW=1)
        # - Gap size (larger gap = higher priority)
        # - Is bottleneck or critical (+1 each)
        # - Efficiency score (higher efficiency = higher priority)
        # - Shorter timeframe (fewer weeks = higher priority)
        
        # Convert priority to numeric
        priority_map = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
        action_plan['priority_value'] = action_plan['priority'].map(priority_map)
        
        # Extract numeric avg weeks
        action_plan['avg_weeks'] = action_plan['timeframe_weeks'].apply(
            lambda x: sum(map(float, x.split('-'))) / 2 if '-' in str(x) else float(x)
        )
        
        # Calculate priority score
        action_plan['priority_score'] = (
            action_plan['priority_value'] * 10 +  # Base priority (30, 20, or 10)
            action_plan['gap'] * 1.5 +  # Gap contribution
            action_plan['is_bottleneck'].astype(int) * 15 +  # Bottleneck bonus
            action_plan['is_critical'].astype(int) * 20 +  # Critical component bonus
            action_plan['efficiency_score'] * 5 +  # Efficiency contribution
            (10 - action_plan['avg_weeks'].clip(0, 10)) * 2  # Timeframe contribution (shorter is better)
        )
        
        # Sort by priority score (descending)
        sorted_plan = action_plan.sort_values(by='priority_score', ascending=False)
        
        # Create action sequence
        sorted_plan['action_sequence'] = range(1, len(sorted_plan) + 1)
        
        # Select relevant columns for output
        output_columns = [
            'action_sequence', 'area_id', 'component', 'improvement_area', 
            'current_score', 'target_score', 'gap', 'priority', 'complexity',
            'timeframe_weeks', 'expected_impact', 'dependencies', 'is_bottleneck',
            'is_critical', 'efficiency_score', 'weeks_to_target', 'completion_horizon'
        ]
        
        result = sorted_plan[output_columns]
        self.analysis_results['action_plan'] = result
        return result
    
    def export_analysis_results(self, output_dir='analysis_results'):
        """
        Export all analysis results to CSV files.
        
        Args:
            output_dir (str): Directory to save analysis files
        """
        output_path = Path(output_dir)
        if not output_path.exists():
            os.makedirs(output_dir)
            
        print(f"Exporting analysis results to {output_dir}...")
        
        for name, df in self.analysis_results.items():
            if isinstance(df, tuple):
                # Handle cases where we return multiple DataFrames (like dimension_gaps)
                for i, item in enumerate(df):
                    output_file = output_path / f"{name}_{i+1}.csv"
                    item.to_csv(output_file, index=False)
                    print(f"Exported {name}_{i+1} to {output_file}")
            else:
                output_file = output_path / f"{name}.csv"
                df.to_csv(output_file, index=False)
                print(f"Exported {name} to {output_file}")


# Example usage
if __name__ == "__main__":
    # Create gap analysis engine
    gap_analyzer = GapAnalysisEngine(data_dir='./data')
    
    # Run all analyses
    component_gaps = gap_analyzer.calculate_component_gaps()
    improvement_efficiency = gap_analyzer.analyze_improvement_efficiency()
    dimension_gaps, sub_metric_gaps = gap_analyzer.calculate_dimension_gaps()
    time_to_target = gap_analyzer.analyze_time_to_target()
    critical_improvements = gap_analyzer.identify_critical_improvements(top_n=10)
    action_plan = gap_analyzer.generate_priority_action_plan()
    
    # Export analysis results
    gap_analyzer.export_analysis_results()
    
    print("Gap analysis complete!")

"""
SUMMARY:
This code implements a comprehensive Gap Analysis Engine for the Neuron Evaluation Framework. 
The GapAnalysisEngine class provides detailed analysis of performance gaps and prioritizes
improvements. Key functionality includes:

1. Calculating component gaps between current and target performance
2. Analyzing improvement efficiency based on effort vs. impact
3. Calculating dimension and sub-dimension gaps
4. Estimating time to reach targets based on current improvement rates
5. Identifying critical improvements needed
6. Generating a prioritized action plan

The analysis takes into account multiple factors including gap size, component criticality,
improvement efficiency, estimated completion time, and dependencies. The resulting action plan
provides a clear roadmap for enhancing the Neuron Framework, prioritizing improvements that
will have the greatest impact on overall system performance.
"""
