import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import os
import json
from sklearn.preprocessing import MinMaxScaler

class CrossArchitectureComparisonAnalyzer:
    """
    A class to perform detailed analysis of "What Breaks First?" testing results
    to compare resilience across different architectures.
    """
    
    def __init__(self, data_dir='data', output_dir='architecture_analysis'):
        """
        Initialize the cross-architecture comparison analyzer.
        
        Args:
            data_dir (str): Directory containing test data files
            output_dir (str): Directory to save analysis outputs
        """
        self.data_dir = data_dir
        self.output_dir = output_dir
        self.df = None
        self.summary_data = {}
        self.comparison_metrics = {}
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Load the data
        self._load_data()
    
    def _load_data(self):
        """Load the 'What Breaks First?' testing data."""
        file_path = Path(self.data_dir) / 'what_breaks_first_testing_results.txt'
        
        if file_path.exists():
            try:
                self.df = pd.read_csv(file_path)
                print(f"Loaded {len(self.df)} test records.")
                
                # Filter out 'All Architectures' tests (these are combined tests, not single architecture)
                self.df = self.df[self.df['architecture_type'] != 'All Architectures']
                
                print(f"Found {len(self.df['architecture_type'].unique())} unique architectures for comparison.")
            except Exception as e:
                print(f"Error loading data: {e}")
        else:
            print(f"Data file not found: {file_path}")
    
    def compute_architecture_metrics(self):
        """
        Compute comprehensive metrics for each architecture across all test components.
        
        Returns:
            pandas.DataFrame: Summary metrics for each architecture
        """
        if self.df is None:
            print("No data available. Load data first.")
            return None
        
        # Group by architecture type and calculate metrics
        arch_metrics = self.df.groupby('architecture_type').agg({
            'breaking_point_load': ['mean', 'min', 'max', 'std'],
            'failure_cascade_size': ['mean', 'min', 'max', 'std'],
            'recovery_time_ms': ['mean', 'min', 'max', 'std'],
            'graceful_degradation_score': ['mean', 'min', 'max', 'std'],
            'comparative_rank': ['mean', 'median', 'min', 'max']
        })
        
        # Flatten column names
        arch_metrics.columns = ['_'.join(col).strip() for col in arch_metrics.columns.values]
        
        # Calculate additional metrics
        
        # 1. Resilience score: Higher breaking point + higher degradation + lower cascade
        arch_metrics['resilience_score'] = (
            arch_metrics['breaking_point_load_mean'] * 0.3 +
            arch_metrics['graceful_degradation_score_mean'] * 0.4 -
            arch_metrics['failure_cascade_size_mean'] * 5 * 0.3
        )
        
        # 2. Recovery efficiency: Higher degradation score / recovery time
        arch_metrics['recovery_efficiency'] = (
            arch_metrics['graceful_degradation_score_mean'] / 
            (arch_metrics['recovery_time_ms_mean'] / 1000)  # Convert to seconds
        )
        
        # 3. Consistency score: Lower standard deviations (normalized)
        consistency_factors = [
            1 - (arch_metrics['breaking_point_load_std'] / arch_metrics['breaking_point_load_mean']),
            1 - (arch_metrics['failure_cascade_size_std'] / (arch_metrics['failure_cascade_size_mean'] + 1)),  # Add 1 to avoid division by zero
            1 - (arch_metrics['recovery_time_ms_std'] / arch_metrics['recovery_time_ms_mean']),
            1 - (arch_metrics['graceful_degradation_score_std'] / arch_metrics['graceful_degradation_score_mean'])
        ]
        
        arch_metrics['consistency_score'] = sum(consistency_factors) / len(consistency_factors) * 100
        
        # 4. Worst-case performance: Based on minimum scores and maximum failure metrics
        arch_metrics['worst_case_score'] = (
            arch_metrics['breaking_point_load_min'] * 0.3 +
            arch_metrics['graceful_degradation_score_min'] * 0.4 -
            arch_metrics['failure_cascade_size_max'] * 2 * 0.15 -
            (arch_metrics['recovery_time_ms_max'] / 1000) * 0.15
        )
        
        # Calculate overall score
        arch_metrics['overall_score'] = (
            arch_metrics['resilience_score'] * 0.35 +
            arch_metrics['recovery_efficiency'] * 0.25 +
            arch_metrics['consistency_score'] * 0.2 +
            arch_metrics['worst_case_score'] * 0.2
        )
        
        # Normalize scores to 0-100 range
        score_columns = [
            'resilience_score', 'recovery_efficiency', 
            'consistency_score', 'worst_case_score', 'overall_score'
        ]
        
        scaler = MinMaxScaler(feature_range=(0, 100))
        arch_metrics[score_columns] = scaler.fit_transform(arch_metrics[score_columns])
        
        # Sort by overall score descending
        sorted_metrics = arch_metrics.sort_values('overall_score', ascending=False)
        
        # Round to 2 decimal places for readability
        sorted_metrics = sorted_metrics.round(2)
        
        # Save the metrics
        self.summary_data['architecture_metrics'] = sorted_metrics
        
        return sorted_metrics
    
    def analyze_component_performance(self):
        """
        Analyze architecture performance by component type.
        
        Returns:
            dict: Performance by component for each architecture
        """
        if self.df is None:
            print("No data available. Load data first.")
            return None
        
        # Get unique components tested
        components = self.df['component_tested'].unique()
        
        # Get unique architectures
        architectures = self.df['architecture_type'].unique()
        
        # Create a dictionary to store component analysis
        component_analysis = {}
        
        for component in components:
            # Filter data for this component
            component_data = self.df[self.df['component_tested'] == component]
            
            # Create dictionary for this component
            component_dict = {
                'best_architecture': None,
                'worst_architecture': None,
                'performance_gap': 0,
                'architecture_scores': {}
            }
            
            # If we have data for at least 2 architectures
            if len(component_data['architecture_type'].unique()) >= 2:
                # Calculate a score for each architecture (higher is better)
                arch_scores = {}
                
                for arch in architectures:
                    arch_data = component_data[component_data['architecture_type'] == arch]
                    
                    if not arch_data.empty:
                        # Calculate score based on key metrics
                        score = (
                            arch_data['breaking_point_load'].mean() * 0.3 +
                            arch_data['graceful_degradation_score'].mean() * 0.4 -
                            arch_data['failure_cascade_size'].mean() * 5 * 0.2 -
                            (arch_data['recovery_time_ms'].mean() / 1000) * 0.1
                        )
                        
                        arch_scores[arch] = round(score, 2)
                
                # Determine best and worst architecture
                if arch_scores:
                    best_arch = max(arch_scores, key=arch_scores.get)
                    worst_arch = min(arch_scores, key=arch_scores.get)
                    
                    component_dict['best_architecture'] = best_arch
                    component_dict['worst_architecture'] = worst_arch
                    component_dict['performance_gap'] = arch_scores[best_arch] - arch_scores[worst_arch]
                    component_dict['architecture_scores'] = arch_scores
            
            component_analysis[component] = component_dict
        
        # Calculate which architectures are consistently best/worst
        arch_best_count = {arch: 0 for arch in architectures}
        arch_worst_count = {arch: 0 for arch in architectures}
        
        for component, data in component_analysis.items():
            if data['best_architecture']:
                arch_best_count[data['best_architecture']] += 1
            if data['worst_architecture']:
                arch_worst_count[data['worst_architecture']] += 1
        
        # Add these counts to the analysis
        component_analysis['meta'] = {
            'best_architecture_counts': arch_best_count,
            'worst_architecture_counts': arch_worst_count
        }
        
        # Save the component analysis
        self.summary_data['component_analysis'] = component_analysis
        
        return component_analysis
    
    def create_architecture_comparison_matrix(self):
        """
        Create a detailed comparison matrix of architectures.
        
        Returns:
            pandas.DataFrame: Comparison matrix
        """
        if self.df is None:
            print("No data available. Load data first.")
            return None
        
        # Get unique architectures
        architectures = self.df['architecture_type'].unique()
        
        # Create a matrix of all architecture pairs
        comparison_matrix = pd.DataFrame(index=architectures, columns=architectures)
        
        # For each pair, calculate how many times arch1 outperforms arch2
        for arch1 in architectures:
            for arch2 in architectures:
                if arch1 == arch2:
                    comparison_matrix.loc[arch1, arch2] = None
                    continue
                
                # Get components tested in both architectures
                arch1_components = self.df[self.df['architecture_type'] == arch1]['component_tested'].unique()
                arch2_components = self.df[self.df['architecture_type'] == arch2]['component_tested'].unique()
                common_components = set(arch1_components).intersection(set(arch2_components))
                
                # Count wins for arch1 over arch2
                win_count = 0
                total_comparisons = 0
                
                for component in common_components:
                    # Get data for this component and architectures
                    arch1_data = self.df[(self.df['architecture_type'] == arch1) & 
                                        (self.df['component_tested'] == component)]
                    
                    arch2_data = self.df[(self.df['architecture_type'] == arch2) & 
                                        (self.df['component_tested'] == component)]
                    
                    if not arch1_data.empty and not arch2_data.empty:
                        # Calculate scores
                        arch1_score = (
                            arch1_data['breaking_point_load'].mean() * 0.3 +
                            arch1_data['graceful_degradation_score'].mean() * 0.4 -
                            arch1_data['failure_cascade_size'].mean() * 5 * 0.2 -
                            (arch1_data['recovery_time_ms'].mean() / 1000) * 0.1
                        )
                        
                        arch2_score = (
                            arch2_data['breaking_point_load'].mean() * 0.3 +
                            arch2_data['graceful_degradation_score'].mean() * 0.4 -
                            arch2_data['failure_cascade_size'].mean() * 5 * 0.2 -
                            (arch2_data['recovery_time_ms'].mean() / 1000) * 0.1
                        )
                        
                        # Increment win count if arch1 scores higher
                        if arch1_score > arch2_score:
                            win_count += 1
                        
                        total_comparisons += 1
                
                # Calculate win percentage
                if total_comparisons > 0:
                    win_percentage = (win_count / total_comparisons) * 100
                    comparison_matrix.loc[arch1, arch2] = round(win_percentage, 2)
                else:
                    comparison_matrix.loc[arch1, arch2] = None
        
        # Save the comparison matrix
        self.summary_data['comparison_matrix'] = comparison_matrix
        
        return comparison_matrix
    
    def analyze_failure_conditions(self):
        """
        Analyze which failure conditions are most challenging for each architecture.
        
        Returns:
            dict: Analysis of failure conditions by architecture
        """
        if self.df is None:
            print("No data available. Load data first.")
            return None
        
        # Get unique architectures and failure conditions
        architectures = self.df['architecture_type'].unique()
        failure_conditions = self.df['failure_condition'].unique()
        
        # Create a dictionary to store failure condition analysis
        failure_analysis = {}
        
        for arch in architectures:
            # Filter data for this architecture
            arch_data = self.df[self.df['architecture_type'] == arch]
            
            # Create dictionary for this architecture
            arch_dict = {
                'strongest_condition': None,
                'weakest_condition': None,
                'condition_scores': {}
            }
            
            # Calculate scores for each failure condition
            condition_scores = {}
            
            for condition in failure_conditions:
                condition_data = arch_data[arch_data['failure_condition'] == condition]
                
                if not condition_data.empty:
                    # Calculate a score for this condition (higher is better)
                    score = (
                        condition_data['breaking_point_load'].mean() * 0.3 +
                        condition_data['graceful_degradation_score'].mean() * 0.4 -
                        condition_data['failure_cascade_size'].mean() * 5 * 0.2 -
                        (condition_data['recovery_time_ms'].mean() / 1000) * 0.1
                    )
                    
                    condition_scores[condition] = round(score, 2)
            
            # Determine strongest and weakest conditions
            if condition_scores:
                strongest = max(condition_scores, key=condition_scores.get)
                weakest = min(condition_scores, key=condition_scores.get)
                
                arch_dict['strongest_condition'] = strongest
                arch_dict['weakest_condition'] = weakest
                arch_dict['condition_scores'] = condition_scores
            
            failure_analysis[arch] = arch_dict
        
        # Now analyze which conditions are generally difficult across architectures
        condition_difficulty = {cond: [] for cond in failure_conditions}
        
        for arch, data in failure_analysis.items():
            for condition, score in data['condition_scores'].items():
                condition_difficulty[condition].append(score)
        
        # Calculate average difficulty for each condition
        avg_difficulty = {}
        for condition, scores in condition_difficulty.items():
            if scores:
                avg_difficulty[condition] = round(sum(scores) / len(scores), 2)
        
        # Add this to the analysis
        failure_analysis['meta'] = {
            'average_condition_scores': avg_difficulty,
            'most_difficult_condition': min(avg_difficulty, key=avg_difficulty.get) if avg_difficulty else None,
            'least_difficult_condition': max(avg_difficulty, key=avg_difficulty.get) if avg_difficulty else None
        }
        
        # Save the failure analysis
        self.summary_data['failure_analysis'] = failure_analysis
        
        return failure_analysis
    
    def calculate_comparative_metrics(self):
        """
        Calculate comparative metrics for architectures based on all analyses.
        
        Returns:
            pandas.DataFrame: Comparative metrics
        """
        # Ensure we have all the necessary analyses
        if not all(k in self.summary_data for k in ['architecture_metrics', 'component_analysis', 'comparison_matrix', 'failure_analysis']):
            print("Run all analysis methods first.")
            return None
        
        # Get unique architectures
        architectures = self.df['architecture_type'].unique()
        
        # Create DataFrame for comparative metrics
        metrics = pd.DataFrame(index=architectures)
        
        # 1. Add overall score from architecture_metrics
        arch_metrics = self.summary_data['architecture_metrics']
        metrics['overall_score'] = arch_metrics['overall_score']
        
        # 2. Calculate component versatility (% of components where architecture is best)
        component_analysis = self.summary_data['component_analysis']
        total_components = len(component_analysis) - 1  # Subtract 1 for 'meta' key
        
        for arch in architectures:
            best_count = component_analysis['meta']['best_architecture_counts'].get(arch, 0)
            metrics.loc[arch, 'component_versatility'] = round((best_count / total_components) * 100, 2)
        
        # 3. Calculate win rate from comparison matrix
        comparison_matrix = self.summary_data['comparison_matrix']
        
        for arch in architectures:
            # Average win percentage against other architectures
            win_percentages = comparison_matrix.loc[arch, :]
            valid_percentages = win_percentages.dropna()
            
            if not valid_percentages.empty:
                metrics.loc[arch, 'avg_win_rate'] = round(valid_percentages.mean(), 2)
            else:
                metrics.loc[arch, 'avg_win_rate'] = 0
        
        # 4. Calculate condition adaptability (standard deviation of condition scores, lower is better)
        failure_analysis = self.summary_data['failure_analysis']
        
        for arch in architectures:
            if arch in failure_analysis:
                condition_scores = list(failure_analysis[arch]['condition_scores'].values())
                if condition_scores:
                    # Lower standard deviation means more consistent across conditions
                    std_dev = np.std(condition_scores)
                    metrics.loc[arch, 'condition_adaptability'] = round(100 - (std_dev * 10), 2)  # Invert so higher is better
                else:
                    metrics.loc[arch, 'condition_adaptability'] = 0
        
        # 5. Calculate overall comparative score
        metrics['comparative_score'] = (
            metrics['overall_score'] * 0.4 +
            metrics['component_versatility'] * 0.3 +
            metrics['avg_win_rate'] * 0.2 +
            metrics['condition_adaptability'] * 0.1
        )
        
        # Sort by comparative score
        sorted_metrics = metrics.sort_values('comparative_score', ascending=False)
        
        # Fill any NaN values
        sorted_metrics = sorted_metrics.fillna(0)
        
        # Round to 2 decimal places
        sorted_metrics = sorted_metrics.round(2)
        
        # Save the comparative metrics
        self.comparison_metrics = sorted_metrics
        
        return sorted_metrics
    
    def generate_failure_mode_analysis(self):
        """
        Generate detailed analysis of failure modes for each architecture.
        
        Returns:
            dict: Detailed failure mode analysis
        """
        if self.df is None:
            print("No data available. Load data first.")
            return None
        
        # Get unique architectures
        architectures = self.df['architecture_type'].unique()
        
        # Create a dictionary to store failure mode analysis
        failure_modes = {}
        
        for arch in architectures:
            # Filter data for this architecture
            arch_data = self.df[self.df['architecture_type'] == arch]
            
            # Identify breaking points (where functionality preserved < 80%)
            breaking_points = arch_data[arch_data['graceful_degradation_score'] < 80].copy()
            
            # Sort by graceful degradation score (ascending)
            breaking_points = breaking_points.sort_values('graceful_degradation_score')
            
            # Create analysis for this architecture
            arch_analysis = {
                'critical_failure_points': [],
                'common_failure_patterns': {},
                'recommended_improvements': []
            }
            
            # Extract the top 5 most severe breaking points
            for _, row in breaking_points.head(5).iterrows():
                failure_point = {
                    'component': row['component_tested'],
                    'condition': row['failure_condition'],
                    'degradation_score': row['graceful_degradation_score'],
                    'cascade_size': row['failure_cascade_size'],
                    'recovery_time_ms': row['recovery_time_ms']
                }
                arch_analysis['critical_failure_points'].append(failure_point)
            
            # Identify common patterns in failures
            if not breaking_points.empty:
                # Component patterns
                component_counts = breaking_points['component_tested'].value_counts()
                most_common_components = component_counts.head(3).to_dict()
                
                # Condition patterns
                condition_counts = breaking_points['failure_condition'].value_counts()
                most_common_conditions = condition_counts.head(3).to_dict()
                
                arch_analysis['common_failure_patterns'] = {
                    'vulnerable_components': most_common_components,
                    'challenging_conditions': most_common_conditions
                }
                
                # Generate recommended improvements based on patterns
                recommendations = []
                
                # 1. For most vulnerable components
                for component, count in most_common_components.items():
                    if count >= 2:  # If component appears in multiple failures
                        recommendations.append(f"Strengthen {component} resilience")
                
                # 2. For challenging conditions
                for condition, count in most_common_conditions.items():
                    if count >= 2:  # If condition appears in multiple failures
                        recommendations.append(f"Improve handling of {condition} scenarios")
                
                # 3. Additional specific recommendations based on metrics
                
                # High cascade failures
                high_cascade = breaking_points[breaking_points['failure_cascade_size'] > 10]
                if not high_cascade.empty:
                    recommendations.append("Implement better component isolation to reduce failure cascades")
                
                # Slow recovery
                slow_recovery = breaking_points[breaking_points['recovery_time_ms'] > 2000]
                if not slow_recovery.empty:
                    recommendations.append("Optimize recovery mechanisms to reduce recovery time")
                
                arch_analysis['recommended_improvements'] = recommendations
            
            failure_modes[arch] = arch_analysis
        
        # Save the failure mode analysis
        self.summary_data['failure_modes'] = failure_modes
        
        return failure_modes
    
    def run_all_analyses(self):
        """
        Run all analysis methods and return combined results.
        
        Returns:
            dict: All analysis results
        """
        print("Running cross-architecture analyses...")
        
        if self.df is None:
            print("No data available. Cannot run analyses.")
            return None
        
        # Run all analyses
        arch_metrics = self.compute_architecture_metrics()
        component_perf = self.analyze_component_performance()
        comp_matrix = self.create_architecture_comparison_matrix()
        failure_cond = self.analyze_failure_conditions()
        comp_metrics = self.calculate_comparative_metrics()
        failure_modes = self.generate_failure_mode_analysis()
        
        print("All analyses complete.")
        
        # Combine results
        all_results = {
            'architecture_metrics': arch_metrics,
            'component_performance': component_perf,
            'comparison_matrix': comp_matrix,
            'failure_conditions': failure_cond,
            'comparative_metrics': comp_metrics,
            'failure_modes': failure_modes
        }
        
        return all_results
    
    def export_results(self, format='csv'):
        """
        Export analysis results to files.
        
        Args:
            format (str): Export format ('csv' or 'json')
        """
        if not self.summary_data:
            print("No analysis results available. Run analyses first.")
            return
        
        print(f"Exporting analysis results as {format}...")
        
        if format == 'csv':
            # Export DataFrames as CSV
            for name, data in self.summary_data.items():
                if isinstance(data, pd.DataFrame):
                    output_path = os.path.join(self.output_dir, f"{name}.csv")
                    data.to_csv(output_path)
                    print(f"Exported {name} to {output_path}")
            
            # Export comparison metrics
            if not self.comparison_metrics.empty:
                output_path = os.path.join(self.output_dir, "comparative_metrics.csv")
                self.comparison_metrics.to_csv(output_path)
                print(f"Exported comparative_metrics to {output_path}")
                
        elif format == 'json':
            # Convert DataFrames to JSON-serializable format
            json_data = {}
            
            for name, data in self.summary_data.items():
                if isinstance(data, pd.DataFrame):
                    json_data[name] = json.loads(data.to_json(orient='index'))
                elif isinstance(data, dict):
                    # Handle nested DataFrames in dictionaries
                    json_dict = {}
                    for k, v in data.items():
                        if isinstance(v, pd.DataFrame):
                            json_dict[k] = json.loads(v.to_json(orient='index'))
                        else:
                            json_dict[k] = v
                    json_data[name] = json_dict
            
            # Add comparison metrics
            if not self.comparison_metrics.empty:
                json_data['comparative_metrics'] = json.loads(self.comparison_metrics.to_json(orient='index'))
            
            # Write to file
            output_path = os.path.join(self.output_dir, "architecture_analysis.json")
            with open(output_path, 'w') as f:
                json.dump(json_data, f, indent=2)
            
            print(f"Exported all analysis results to {output_path}")
        
        else:
            print(f"Unsupported format: {format}. Use 'csv' or 'json'.")
    
    def visualize_comparison(self):
        """
        Create visualizations of architecture comparison results.
        
        Returns:
            matplotlib.figure.Figure: The created figure
        """
        if not self.comparison_metrics.empty:
            # Create a figure with multiple subplots
            fig, axs = plt.subplots(2, 2, figsize=(15, 12))
            
            # 1. Overall score comparison
            sorted_overall = self.comparison_metrics.sort_values('overall_score', ascending=False)
            
            bars = axs[0, 0].bar(
                sorted_overall.index,
                sorted_overall['overall_score'],
                color='skyblue',
                alpha=0.8
            )
            
            # Add value labels
            for bar in bars:
                height = bar.get_height()
                axs[0, 0].text(
                    bar.get_x() + bar.get_width()/2.,
                    height,
                    f'{height:.1f}',
                    ha='center',
                    va='bottom',
                    fontweight='bold'
                )
            
            axs[0, 0].set_title('Overall Architecture Score', fontweight='bold')
            axs[0, 0].set_ylabel('Score')
            axs[0, 0].set_ylim(0, 100)
            axs[0, 0].grid(axis='y', linestyle='--', alpha=0.7)
            
            # 2. Component versatility
            sorted_versatility = self.comparison_metrics.sort_values('component_versatility', ascending=False)
            
            bars = axs[0, 1].bar(
                sorted_versatility.index,
                sorted_versatility['component_versatility'],
                color='lightgreen',
                alpha=0.8
            )
            
            # Add value labels
            for bar in bars:
                height = bar.get_height()
                axs[0, 1].text(
                    bar.get_x() + bar.get_width()/2.,
                    height,
                    f'{height:.1f}%',
                    ha='center',
                    va='bottom',
                    fontweight='bold'
                )
            
            axs[0, 1].set_title('Component Versatility', fontweight='bold')
            axs[0, 1].set_ylabel('% of Components as Best')
            axs[0, 1].set_ylim(0, 100)
            axs[0, 1].grid(axis='y', linestyle='--', alpha=0.7)
            
            # 3. Win rate comparison
            sorted_winrate = self.comparison_metrics.sort_values('avg_win_rate', ascending=False)
            
            bars = axs[1, 0].bar(
                sorted_winrate.index,
                sorted_winrate['avg_win_rate'],
                color='salmon',
                alpha=0.8
            )
            
            # Add value labels
            for bar in bars:
                height = bar.get_height()
                axs[1, 0].text(
                    bar.get_x() + bar.get_width()/2.,
                    height,
                    f'{height:.1f}%',
                    ha='center',
                    va='bottom',
                    fontweight='bold'
                )
            
            axs[1, 0].set_title('Average Win Rate', fontweight='bold')
            axs[1, 0].set_ylabel('Win % vs Other Architectures')
            axs[1, 0].set_ylim(0, 100)
            axs[1, 0].grid(axis='y', linestyle='--', alpha=0.7)
            
            # 4. Comparative score (final ranking)
            sorted_comparative = self.comparison_metrics.sort_values('comparative_score', ascending=False)
            
            bars = axs[1, 1].bar(
                sorted_comparative.index,
                sorted_comparative['comparative_score'],
                color='mediumpurple',
                alpha=0.8
            )
            
            # Add value labels
            for bar in bars:
                height = bar.get_height()
                axs[1, 1].text(
                    bar.get_x() + bar.get_width()/2.,
                    height,
                    f'{height:.1f}',
                    ha='center',
                    va='bottom',
                    fontweight='bold'
                )
            
            axs[1, 1].set_title('Comparative Score (Final Ranking)', fontweight='bold')
            axs[1, 1].set_ylabel('Score')
            axs[1, 1].set_ylim(0, 100)
            axs[1, 1].grid(axis='y', linestyle='--', alpha=0.7)
            
            # Add overall title
            fig.suptitle('Cross-Architecture Comparison', fontsize=20, fontweight='bold')
            
            plt.tight_layout()
            
            # Save figure
            output_path = os.path.join(self.output_dir, 'architecture_comparison.png')
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            print(f"Saved architecture comparison visualization to {output_path}")
            
            return fig
        else:
            print("No comparison metrics available. Run calculate_comparative_metrics first.")
            return None


# Example usage
if __name__ == "__main__":
    analyzer = CrossArchitectureComparisonAnalyzer(data_dir='./data')
    results = analyzer.run_all_analyses()
    analyzer.export_results(format='json')
    analyzer.visualize_comparison()
    
    print("Cross-architecture analysis complete!")

"""
SUMMARY:
This code implements a comprehensive analyzer for comparing different AI architectures based on 
'What Breaks First?' testing results from the Neuron Evaluation Framework. Key functionality includes:

1. Computing detailed metrics for each architecture across test components, including resilience scores,
   recovery efficiency, consistency scores, and worst-case performance.
   
2. Analyzing performance by component type to identify which architectures excel in different domains
   and where the largest performance gaps exist.
   
3. Creating a comparison matrix to directly compare architectures against each other and calculate
   win rates for each architecture.
   
4. Analyzing which failure conditions are most challenging for each architecture and identifying
   patterns in architecture vulnerabilities.
   
5. Calculating comprehensive comparative metrics that combine multiple aspects of performance into
   an overall ranking of architectures.
   
6. Generating detailed failure mode analysis for each architecture, including critical failure points,
   common failure patterns, and recommended improvements.
   
7. Visualizing comparison results to provide clear insights into relative architecture strengths
   and weaknesses.

This analyzer provides deep insights into architectural robustness and resilience, enabling
data-driven decisions about which architecture is most suitable for different use cases and
identifying targeted improvements for each architecture.
"""
