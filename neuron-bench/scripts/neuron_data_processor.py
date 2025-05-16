import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
from pathlib import Path

class NeuronDataProcessor:
    """
    A class to process and aggregate data from the Neuron Evaluation Framework datasets.
    Handles loading, cleaning, and basic processing of test data files.
    """
    
    def __init__(self, data_dir='data'):
        """
        Initialize the data processor with the directory containing test data files.
        
        Args:
            data_dir (str): Path to directory containing CSV data files
        """
        self.data_dir = data_dir
        self.datasets = {}
        self.aggregated_data = {}
        
    def load_all_datasets(self):
        """
        Load all CSV files from the data directory into pandas DataFrames.
        Files are stored in the datasets dictionary with the filename as the key.
        """
        data_path = Path(self.data_dir)
        if not data_path.exists():
            print(f"Creating data directory: {self.data_dir}")
            os.makedirs(self.data_dir)
            
        csv_files = list(data_path.glob('*.txt'))
        
        if not csv_files:
            print(f"No data files found in {self.data_dir}")
            return
            
        print(f"Loading {len(csv_files)} datasets...")
        
        for file_path in csv_files:
            dataset_name = file_path.stem
            try:
                # Load data with automatic header detection
                df = pd.read_csv(file_path)
                self.datasets[dataset_name] = df
                print(f"Loaded {dataset_name} with {len(df)} records")
            except Exception as e:
                print(f"Error loading {file_path}: {e}")
    
    def get_dataset(self, name):
        """
        Retrieve a dataset by name.
        
        Args:
            name (str): Name of the dataset to retrieve
            
        Returns:
            pandas.DataFrame: The requested dataset, or None if not found
        """
        return self.datasets.get(name, None)
    
    def aggregate_system_performance(self):
        """
        Aggregate system performance data across different components.
        Creates a summary DataFrame of current performance vs targets.
        
        Returns:
            pandas.DataFrame: Aggregated system performance data
        """
        # Check if target_gap_analysis dataset is loaded
        if 'target_gap_analysis' not in self.datasets:
            print("Target gap analysis dataset not found")
            return None
        
        gap_df = self.datasets['target_gap_analysis']
        
        # Group by status and calculate averages
        status_summary = gap_df.groupby('status').agg({
            'current_score': 'mean',
            'target_score': 'mean',
            'gap': 'mean',
            'gap_percentage': 'mean'
        }).reset_index()
        
        # Calculate overall statistics
        overall = pd.DataFrame({
            'status': ['OVERALL'],
            'current_score': [gap_df['current_score'].mean()],
            'target_score': [gap_df['target_score'].mean()],
            'gap': [gap_df['gap'].mean()],
            'gap_percentage': [gap_df['gap_percentage'].mean()]
        })
        
        # Combine with status summary
        aggregated = pd.concat([status_summary, overall], ignore_index=True)
        self.aggregated_data['system_performance'] = aggregated
        
        return aggregated
    
    def get_improvement_priorities(self):
        """
        Extract components that need improvement based on priorities.
        
        Returns:
            pandas.DataFrame: Components needing improvement, sorted by priority
        """
        if 'improvement_priorities' not in self.datasets:
            print("Improvement priorities dataset not found")
            return None
        
        df = self.datasets['improvement_priorities']
        
        # Sort by priority (HIGH, MEDIUM, LOW)
        priority_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
        df['priority_order'] = df['priority'].map(priority_order)
        
        # Get items that need improvement, sorted by priority
        improvements = df.sort_values(by=['priority_order', 'gap'], ascending=[True, False])
        
        # Reset index and drop helper column
        improvements = improvements.reset_index(drop=True).drop(columns=['priority_order'])
        
        return improvements
    
    def calculate_dimension_scores(self):
        """
        Calculate scores for each evaluation dimension based on detailed metrics.
        
        Returns:
            pandas.DataFrame: Dimension scores
        """
        if 'dimension_detailed_metrics' not in self.datasets:
            print("Dimension detailed metrics dataset not found")
            return None
        
        metrics_df = self.datasets['dimension_detailed_metrics']
        
        # Group by dimension and calculate average scores
        dimension_scores = metrics_df.groupby('dimension').agg({
            'score': 'mean',
            'target': 'mean',
            'gap': 'mean'
        }).reset_index()
        
        # Calculate percentage to target
        dimension_scores['percent_to_target'] = (dimension_scores['gap'] / dimension_scores['target'] * 100).round(2)
        
        # Add status based on gap
        conditions = [
            (dimension_scores['gap'] > 0),
            (dimension_scores['gap'] > -3) & (dimension_scores['gap'] <= 0),
            (dimension_scores['gap'] <= -3)
        ]
        choices = ['EXCEEDS TARGET', 'APPROACHING TARGET', 'NEEDS IMPROVEMENT']
        dimension_scores['status'] = np.select(conditions, choices, default='UNKNOWN')
        
        # Sort by gap
        dimension_scores = dimension_scores.sort_values(by='gap')
        
        self.aggregated_data['dimension_scores'] = dimension_scores
        return dimension_scores
    
    def analyze_error_patterns(self):
        """
        Analyze error patterns across different areas.
        
        Returns:
            pandas.DataFrame: Error pattern analysis
        """
        if 'error_analysis_dataset' not in self.datasets:
            print("Error analysis dataset not found")
            return None
        
        df = self.datasets['error_analysis_dataset']
        
        # Group by area and error_type
        error_summary = df.groupby(['area', 'error_type']).agg({
            'error_frequency': lambda x: x.mode().iloc[0] if not x.empty else None,
            'impact_severity': lambda x: x.mode().iloc[0] if not x.empty else None,
            'detection_rate': 'mean',
            'resolution_rate': 'mean'
        }).reset_index()
        
        # Calculate severity score (lower detection/resolution + higher impact = higher severity)
        error_summary['severity_score'] = (
            (100 - error_summary['detection_rate']) * 0.4 + 
            (100 - error_summary['resolution_rate']) * 0.4 +
            (error_summary['impact_severity'].map({'Low': 1, 'Medium': 2, 'High': 3, 'Very High': 4}) * 10) * 0.2
        )
        
        # Sort by severity score descending
        error_summary = error_summary.sort_values(by='severity_score', ascending=False)
        
        self.aggregated_data['error_patterns'] = error_summary
        return error_summary
    
    def generate_performance_timeline(self):
        """
        Generate timeline data showing performance across test weeks.
        
        Returns:
            pandas.DataFrame: Performance timeline
        """
        if 'performance_over_time' not in self.datasets:
            print("Performance over time dataset not found")
            return None
        
        timeline_df = self.datasets['performance_over_time']
        
        # Calculate improvement rates
        timeline_df['total_improvement'] = timeline_df['week16'] - timeline_df['week1']
        timeline_df['improvement_rate'] = (timeline_df['total_improvement'] / 16).round(2)
        
        # Calculate remaining gap to target
        timeline_df['remaining_gap'] = timeline_df['production_target'] - timeline_df['week16']
        
        # Calculate weeks to target at current rate
        # Avoid division by zero by using a very small number where rate is zero
        timeline_df['improvement_rate'] = timeline_df['improvement_rate'].replace(0, 0.001)
        timeline_df['weeks_to_target'] = (timeline_df['remaining_gap'] / timeline_df['improvement_rate']).round(1)
        
        # Replace negative or infinite values with 0 (already reached target)
        timeline_df['weeks_to_target'] = timeline_df['weeks_to_target'].apply(
            lambda x: 0 if x <= 0 or np.isinf(x) else x
        )
        
        # Sort by remaining gap descending
        sorted_timeline = timeline_df.sort_values(by='remaining_gap', ascending=False)
        
        self.aggregated_data['performance_timeline'] = sorted_timeline
        return sorted_timeline
    
    def export_processed_data(self, output_dir='processed_data'):
        """
        Export all processed and aggregated data to CSV files.
        
        Args:
            output_dir (str): Directory to save processed data files
        """
        output_path = Path(output_dir)
        if not output_path.exists():
            os.makedirs(output_dir)
            
        print(f"Exporting processed data to {output_dir}...")
        
        for name, df in self.aggregated_data.items():
            output_file = output_path / f"{name}.csv"
            df.to_csv(output_file, index=False)
            print(f"Exported {name} to {output_file}")
            
    def get_arch_comparison_data(self):
        """
        Extract architecture comparison data from "What Breaks First" testing.
        
        Returns:
            pandas.DataFrame: Architecture comparison data
        """
        if 'what_breaks_first_testing_results' not in self.datasets:
            print("What Breaks First testing results not found")
            return None
        
        df = self.datasets['what_breaks_first_testing_results']
        
        # Filter to get only rows with multiple architectures
        arch_data = df[df['architecture_type'] != 'All Architectures']
        
        # Get average metrics by architecture
        arch_summary = arch_data.groupby('architecture_type').agg({
            'breaking_point_load': 'mean',
            'failure_cascade_size': 'mean',
            'recovery_time_ms': 'mean',
            'graceful_degradation_score': 'mean'
        }).reset_index()
        
        # Sort by average degradation score (higher is better)
        arch_summary = arch_summary.sort_values(by='graceful_degradation_score', ascending=False)
        
        return arch_summary


# Example usage
if __name__ == "__main__":
    processor = NeuronDataProcessor(data_dir='./data')
    processor.load_all_datasets()
    
    # Generate aggregated data
    system_perf = processor.aggregate_system_performance()
    dim_scores = processor.calculate_dimension_scores()
    error_patterns = processor.analyze_error_patterns()
    timeline = processor.generate_performance_timeline()
    improvements = processor.get_improvement_priorities()
    arch_comparison = processor.get_arch_comparison_data()
    
    # Export processed data
    processor.export_processed_data()
    
    print("Data processing complete!")

"""
SUMMARY:
This code provides a comprehensive data processing system for the Neuron Evaluation Framework. 
The NeuronDataProcessor class handles loading, processing, and aggregating data from various 
test datasets. Key functionality includes:

1. Loading all test datasets from CSV/TXT files
2. Aggregating system performance across components
3. Identifying components that need improvement based on priorities
4. Calculating scores for each evaluation dimension
5. Analyzing error patterns across different areas
6. Generating timeline data showing performance evolution
7. Extracting architecture comparison data from "What Breaks First" testing
8. Exporting processed data to CSV files for further analysis

This processor serves as the foundation for all subsequent analysis and visualization of the 
Neuron Framework's evaluation data, preparing the raw test data for meaningful insights.
"""
