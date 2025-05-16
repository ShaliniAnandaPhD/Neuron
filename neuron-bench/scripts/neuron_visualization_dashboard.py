import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.gridspec as gridspec
from matplotlib.colors import LinearSegmentedColormap
from pathlib import Path
import os

class NeuronVisualizationDashboard:
    """
    A comprehensive visualization dashboard for the Neuron Evaluation Framework.
    Creates various charts and visualizations to represent evaluation results.
    """
    
    def __init__(self, data_processor=None, data_dir='data', output_dir='visualizations'):
        """
        Initialize the visualization dashboard.
        
        Args:
            data_processor: NeuronDataProcessor instance (if available)
            data_dir (str): Path to data directory if processor not provided
            output_dir (str): Directory to save visualization outputs
        """
        self.data_processor = data_processor
        self.data_dir = data_dir
        self.output_dir = output_dir
        self.datasets = {}
        
        # Configure plot style for consistency
        self._setup_plot_style()
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Load datasets if processor not provided
        if self.data_processor is None:
            self._load_datasets()
        else:
            self.datasets = self.data_processor.datasets
    
    def _load_datasets(self):
        """
        Load datasets from files if no data processor was provided.
        """
        data_path = Path(self.data_dir)
        
        # List all data files in the directory
        data_files = list(data_path.glob('*.txt'))
        
        for file_path in data_files:
            dataset_name = file_path.stem
            try:
                df = pd.read_csv(file_path)
                self.datasets[dataset_name] = df
                print(f"Loaded {dataset_name} with {len(df)} records")
            except Exception as e:
                print(f"Error loading {file_path}: {e}")
    
    def _setup_plot_style(self):
        """
        Configure matplotlib and seaborn for consistent styling.
        """
        # Set the style for all visualizations
        sns.set_theme(style="whitegrid")
        plt.rcParams['figure.figsize'] = (12, 8)
        plt.rcParams['font.size'] = 12
        plt.rcParams['axes.titlesize'] = 16
        plt.rcParams['axes.labelsize'] = 14
        plt.rcParams['xtick.labelsize'] = 12
        plt.rcParams['ytick.labelsize'] = 12
        plt.rcParams['legend.fontsize'] = 12
        plt.rcParams['figure.titlesize'] = 20
        
        # Define a custom color palette
        self.colors = {
            'primary': '#2B6CB0',      # Blue
            'secondary': '#2F855A',    # Green
            'accent': '#6B46C1',       # Purple
            'neutral': '#4A5568',      # Gray
            'warning': '#C05621',      # Orange
            'danger': '#9B2C2C',       # Red
            'success': '#276749',      # Dark Green
            'info': '#2A4365',         # Dark Blue
            'light': '#E2E8F0',        # Light Gray
            'dark': '#1A202C',         # Near Black
        }
        
        # Status colors
        self.status_colors = {
            'EXCEEDS TARGET': '#276749',      # Dark Green
            'MEETS TARGET': '#2F855A',        # Green
            'APPROACHING TARGET': '#DD6B20',  # Orange
            'NEEDS IMPROVEMENT': '#C53030',   # Red
            'FAIL': '#9B2C2C',                # Dark Red
            'PASS': '#2F855A',                # Green
            'CONDITIONAL PASS': '#DD6B20'     # Orange
        }
    
    def create_system_readiness_visualization(self):
        """
        Create a visualization of overall system readiness based on target gap analysis.
        
        Returns:
            matplotlib.figure.Figure: The generated figure
        """
        if 'target_gap_analysis' not in self.datasets:
            print("Target gap analysis dataset not found")
            return None
        
        df = self.datasets['target_gap_analysis']
        
        # Filter for overall components and core categories
        core_components = df[df['component'].isin([
            'Core Architecture Overall', 
            'Real-World Function Overall', 
            'Cross-Integration Overall', 
            'Overall System'
        ])].copy()
        
        # Sort components in logical order
        component_order = [
            'Core Architecture Overall', 
            'Real-World Function Overall', 
            'Cross-Integration Overall', 
            'Overall System'
        ]
        core_components['order'] = core_components['component'].map({
            comp: i for i, comp in enumerate(component_order)
        })
        core_components = core_components.sort_values('order')
        
        # Create figure
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Create bar chart of current vs target scores
        bar_width = 0.4
        x = np.arange(len(core_components))
        
        # Current score bars
        current_bars = ax.bar(
            x - bar_width/2, 
            core_components['current_score'], 
            bar_width, 
            label='Current Score',
            color=self.colors['primary'],
            alpha=0.8
        )
        
        # Target score bars
        target_bars = ax.bar(
            x + bar_width/2, 
            core_components['target_score'], 
            bar_width, 
            label='Target Score',
            color=self.colors['accent'],
            alpha=0.6
        )
        
        # Add gap annotations
        for i, (_, row) in enumerate(core_components.iterrows()):
            gap = row['gap']
            gap_text = f"{gap:+.1f}"
            gap_color = self.colors['success'] if gap >= 0 else self.colors['danger']
            ax.annotate(
                gap_text,
                xy=(i, max(row['current_score'], row['target_score']) + 1),
                ha='center',
                va='bottom',
                color=gap_color,
                fontweight='bold'
            )
        
        # Set chart properties
        ax.set_title('System Capability Readiness Assessment', fontweight='bold', pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels([comp.replace(' Overall', '') for comp in core_components['component']])
        ax.set_ylabel('Score')
        ax.set_ylim(0, 100)
        ax.legend()
        
        # Add grid lines
        ax.grid(axis='y', linestyle='--', alpha=0.7)
        
        # Add a background box to make the chart stand out
        ax.set_facecolor(self.colors['light'])
        
        # Add annotations for status
        for i, (_, row) in enumerate(core_components.iterrows()):
            status = row['status']
            status_color = self.status_colors.get(status, self.colors['neutral'])
            ax.annotate(
                status,
                xy=(i, 5),
                ha='center',
                va='bottom',
                color=status_color,
                fontweight='bold',
                alpha=0.8
            )
        
        plt.tight_layout()
        
        # Save figure
        output_path = os.path.join(self.output_dir, 'system_readiness.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved system readiness visualization to {output_path}")
        
        return fig
    
    def create_dimension_performance_visualization(self):
        """
        Create a visualization of performance across key dimensions.
        
        Returns:
            matplotlib.figure.Figure: The generated figure
        """
        if 'dimension_detailed_metrics' not in self.datasets:
            print("Dimension detailed metrics dataset not found")
            return None
        
        df = self.datasets['dimension_detailed_metrics']
        
        # Get unique dimensions
        dimensions = df['dimension'].unique()
        
        # Create a figure with subplots for each dimension
        fig = plt.figure(figsize=(15, 10))
        gs = gridspec.GridSpec(2, 3, figure=fig, wspace=0.3, hspace=0.4)
        
        dimension_colors = {
            'Transparency': self.colors['primary'],
            'Adaptability': self.colors['secondary'],
            'Reasoning': self.colors['accent'],
            'Communication': self.colors['warning'],
            'Robustness': self.colors['info'],
            'Comprehension': self.colors['neutral']
        }
        
        # Create subplots for each dimension
        for i, dimension in enumerate(dimensions):
            # Skip if we have more than 6 dimensions (2x3 grid limit)
            if i >= 6:
                break
                
            # Get data for this dimension
            dimension_data = df[df['dimension'] == dimension]
            
            # Create axis
            row, col = divmod(i, 3)
            ax = fig.add_subplot(gs[row, col])
            
            # Filter out Overall Score for this plot
            sub_metrics = dimension_data[dimension_data['sub_metric'] != 'Overall Score']
            
            # Sort by score descending
            sub_metrics = sub_metrics.sort_values('score', ascending=False)
            
            # Create horizontal bars
            bars = ax.barh(
                sub_metrics['sub_metric'],
                sub_metrics['score'],
                color=dimension_colors.get(dimension, self.colors['primary']),
                alpha=0.8
            )
            
            # Add target markers
            for j, (_, row) in enumerate(sub_metrics.iterrows()):
                ax.plot(
                    [row['target'], row['target']], 
                    [j - 0.4, j + 0.4], 
                    color=self.colors['dark'], 
                    linestyle='--',
                    linewidth=2,
                    alpha=0.7
                )
            
            # Add gap annotations
            for j, (_, row) in enumerate(sub_metrics.iterrows()):
                gap = row['gap']
                gap_text = f"{gap:+.1f}"
                gap_color = self.colors['success'] if gap >= 0 else self.colors['danger']
                ax.annotate(
                    gap_text,
                    xy=(row['score'] + 1, j),
                    va='center',
                    color=gap_color,
                    fontweight='bold',
                    fontsize=10
                )
            
            # Set chart properties
            ax.set_title(f"{dimension}", fontweight='bold')
            ax.set_xlim(0, 100)
            ax.grid(axis='x', linestyle='--', alpha=0.7)
            
            # Add overall score as an annotation
            overall = dimension_data[dimension_data['sub_metric'] == 'Overall Score']
            if not overall.empty:
                overall_score = overall.iloc[0]['score']
                overall_target = overall.iloc[0]['target']
                overall_gap = overall.iloc[0]['gap']
                
                gap_text = f"Gap: {overall_gap:+.1f}"
                gap_color = self.colors['success'] if overall_gap >= 0 else self.colors['danger']
                
                # Create a text box with overall score
                props = dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.8)
                ax.text(
                    0.05, 0.05,
                    f"Overall: {overall_score:.1f} / {overall_target:.1f}\n{gap_text}",
                    transform=ax.transAxes,
                    fontsize=10,
                    verticalalignment='bottom',
                    bbox=props
                )
        
        fig.suptitle('Dimensions of Excellence', fontsize=20, fontweight='bold')
        
        # Save figure
        output_path = os.path.join(self.output_dir, 'dimension_performance.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved dimension performance visualization to {output_path}")
        
        return fig
    
    def create_performance_timeline_visualization(self):
        """
        Create a visualization of performance changes over time.
        
        Returns:
            matplotlib.figure.Figure: The generated figure
        """
        if 'performance_over_time' not in self.datasets:
            print("Performance over time dataset not found")
            return None
        
        df = self.datasets['performance_over_time']
        
        # Create figure
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Get all time columns (week1, week2, etc.)
        time_columns = [col for col in df.columns if col.startswith('week')]
        
        # Convert to long format for easier plotting
        df_long = pd.melt(
            df, 
            id_vars=['component'], 
            value_vars=time_columns,
            var_name='timepoint',
            value_name='score'
        )
        
        # Extract week numbers for x-axis
        df_long['week'] = df_long['timepoint'].str.replace('week', '').astype(int)
        
        # Sort by week
        df_long = df_long.sort_values(['component', 'week'])
        
        # Plot lines for each component
        components = df_long['component'].unique()
        
        # Create color palette
        n_colors = len(components)
        palette = sns.color_palette("husl", n_colors)
        
        # Plot each component
        for i, component in enumerate(components):
            component_data = df_long[df_long['component'] == component]
            ax.plot(
                component_data['week'],
                component_data['score'],
                marker='o',
                linewidth=2,
                label=component,
                color=palette[i]
            )
        
        # Add target line
        target_values = df['production_target'].unique()
        if len(target_values) == 1:
            # If all components have the same target
            ax.axhline(
                y=target_values[0],
                color=self.colors['danger'],
                linestyle='--',
                linewidth=2,
                label=f'Target: {target_values[0]}'
            )
        else:
            # If components have different targets, use the highest one for reference
            max_target = df['production_target'].max()
            ax.axhline(
                y=max_target,
                color=self.colors['danger'],
                linestyle='--',
                linewidth=2,
                label=f'Max Target: {max_target}'
            )
        
        # Set chart properties
        ax.set_title('Performance Evolution Over Time', fontweight='bold', pad=20)
        ax.set_xlabel('Week')
        ax.set_ylabel('Score')
        ax.set_ylim(50, 100)  # Adjust as needed based on your data
        ax.grid(True, linestyle='--', alpha=0.7)
        
        # Add a light background
        ax.set_facecolor(self.colors['light'])
        
        # Handle legend - if too many components, put legend outside
        if len(components) > 6:
            ax.legend(
                loc='center left',
                bbox_to_anchor=(1, 0.5),
                ncol=1
            )
        else:
            ax.legend(loc='lower right')
        
        plt.tight_layout()
        
        # Save figure
        output_path = os.path.join(self.output_dir, 'performance_timeline.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved performance timeline visualization to {output_path}")
        
        return fig
    
    def create_error_analysis_visualization(self):
        """
        Create a visualization of error patterns and their impact.
        
        Returns:
            matplotlib.figure.Figure: The generated figure
        """
        if 'error_analysis_dataset' not in self.datasets:
            print("Error analysis dataset not found")
            return None
        
        df = self.datasets['error_analysis_dataset']
        
        # Create figure with two subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 10))
        
        # 1. Heatmap of error frequency vs. impact severity
        # Create a pivot table
        pivot_data = pd.crosstab(
            df['error_frequency'], 
            df['impact_severity'],
            values=df['detection_rate'],
            aggfunc='mean'
        )
        
        # Create a custom colormap (higher values are better for detection rate)
        colors = ['#EF5350', '#FFCA28', '#66BB6A']  # Red to yellow to green
        cmap = LinearSegmentedColormap.from_list('custom_cmap', colors, N=100)
        
        # Plot heatmap
        sns.heatmap(
            pivot_data,
            annot=True,
            fmt='.1f',
            cmap=cmap,
            ax=ax1,
            cbar_kws={'label': 'Detection Rate (%)'}
        )
        
        ax1.set_title('Error Frequency vs. Impact Severity\n(Detection Rate)', fontweight='bold')
        
        # 2. Bar chart of top error types by area
        # Calculate severity score (higher means more severe)
        df['severity_score'] = (
            df['error_frequency'].map({'Low': 1, 'Medium': 2, 'High': 3, 'Very High': 4}) * 
            df['impact_severity'].map({'Low': 1, 'Medium': 2, 'High': 3, 'Very High': 4}) * 
            (100 - df['detection_rate']) / 100
        )
        
        # Get top N error types by severity
        top_errors = df.sort_values('severity_score', ascending=False).head(10)
        
        # Create labels that combine area and error type
        top_errors['label'] = top_errors['area'] + ': ' + top_errors['error_type']
        
        # Plot horizontal bar chart
        bars = ax2.barh(
            top_errors['label'],
            top_errors['severity_score'],
            color=self.colors['danger'],
            alpha=0.8
        )
        
        # Add detection rate annotations
        for i, (_, row) in enumerate(top_errors.iterrows()):
            ax2.annotate(
                f"Detection: {row['detection_rate']}%",
                xy=(row['severity_score'] + 0.1, i),
                va='center',
                fontsize=10
            )
        
        ax2.set_title('Top Error Types by Severity', fontweight='bold')
        ax2.set_xlabel('Severity Score')
        ax2.grid(axis='x', linestyle='--', alpha=0.7)
        
        plt.tight_layout()
        
        # Save figure
        output_path = os.path.join(self.output_dir, 'error_analysis.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved error analysis visualization to {output_path}")
        
        return fig
    
    def create_improvement_priorities_visualization(self):
        """
        Create a visualization of improvement priorities.
        
        Returns:
            matplotlib.figure.Figure: The generated figure
        """
        if 'improvement_priorities' not in self.datasets:
            print("Improvement priorities dataset not found")
            return None
        
        df = self.datasets['improvement_priorities']
        
        # Create a figure with two subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 10))
        
        # 1. Bubble chart of gap vs. complexity with expected impact as bubble size
        # Map categorical variables to numeric
        complexity_map = {
            'LOW': 1,
            'MEDIUM': 2,
            'MEDIUM-HIGH': 3,
            'HIGH': 4
        }
        
        impact_map = {
            'Minor': 10,
            'Moderate': 30,
            'Significant': 60,
            'High': 90,
            'Critical': 120
        }
        
        priority_colors = {
            'HIGH': self.colors['danger'],
            'MEDIUM': self.colors['warning'],
            'LOW': self.colors['secondary']
        }
        
        # Create helper columns
        plot_df = df.copy()
        plot_df['complexity_value'] = plot_df['complexity'].map(complexity_map)
        plot_df['impact_value'] = plot_df['expected_impact'].map(impact_map)
        
        # Create scatter plot grouped by priority
        for priority, group in plot_df.groupby('priority'):
            ax1.scatter(
                group['complexity_value'],
                group['gap'],
                s=group['impact_value'],
                alpha=0.7,
                color=priority_colors.get(priority, self.colors['neutral']),
                label=priority,
                edgecolors=self.colors['dark'],
                linewidths=1
            )
        
        # Configure the plot
        ax1.set_title('Improvement Gap vs. Complexity', fontweight='bold')
        ax1.set_xlabel('Implementation Complexity')
        ax1.set_ylabel('Gap to Target')
        ax1.set_xticks(list(complexity_map.values()))
        ax1.set_xticklabels(list(complexity_map.keys()))
        ax1.grid(True, linestyle='--', alpha=0.7)
        ax1.legend(title='Priority')
        
        # Add a reference line at y=0
        ax1.axhline(y=0, color=self.colors['neutral'], linestyle='-', alpha=0.5)
        
        # 2. Horizontal bar chart of top priority improvements
        # Get top priority improvements
        top_improvements = df.sort_values(by=['priority', 'gap'], ascending=[True, False]).head(10)
        
        # Create bar colors based on priority
        bar_colors = [priority_colors.get(p, self.colors['neutral']) for p in top_improvements['priority']]
        
        # Plot horizontal bars
        bars = ax2.barh(
            top_improvements['improvement_area'],
            top_improvements['gap'],
            color=bar_colors,
            alpha=0.8
        )
        
        # Add component labels
        for i, (_, row) in enumerate(top_improvements.iterrows()):
            component = row['component']
            # Truncate if too long
            if len(component) > 15:
                component = component[:12] + '...'
                
            ax2.annotate(
                component,
                xy=(0.5, i),
                ha='center',
                va='center',
                color='white',
                fontweight='bold',
                fontsize=9
            )
        
        ax2.set_title('Top Priority Improvements', fontweight='bold')
        ax2.set_xlabel('Gap to Target')
        ax2.grid(axis='x', linestyle='--', alpha=0.7)
        
        plt.tight_layout()
        
        # Save figure
        output_path = os.path.join(self.output_dir, 'improvement_priorities.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved improvement priorities visualization to {output_path}")
        
        return fig
    
    def create_architecture_comparison_visualization(self):
        """
        Create a visualization comparing different architectures from "What Breaks First" testing.
        
        Returns:
            matplotlib.figure.Figure: The generated figure
        """
        if 'what_breaks_first_testing_results' not in self.datasets:
            print("What Breaks First testing results not found")
            return None
        
        df = self.datasets['what_breaks_first_testing_results']
        
        # Filter to include only comparative tests (not "All Architectures")
        arch_data = df[df['architecture_type'] != 'All Architectures'].copy()
        
        # Get unique architectures
        architectures = arch_data['architecture_type'].unique()
        
        # Group by architecture and component tested
        grouped = arch_data.groupby(['architecture_type', 'component_tested']).agg({
            'breaking_point_load': 'mean',
            'failure_cascade_size': 'mean',
            'recovery_time_ms': 'mean',
            'graceful_degradation_score': 'mean'
        }).reset_index()
        
        # Create a figure with multiple subplots
        fig = plt.figure(figsize=(15, 12))
        gs = gridspec.GridSpec(2, 2, figure=fig, wspace=0.3, hspace=0.4)
        
        # 1. Breaking point load comparison (higher is better)
        ax1 = fig.add_subplot(gs[0, 0])
        breaking_pivot = grouped.pivot(index='component_tested', columns='architecture_type', values='breaking_point_load')
        breaking_pivot.plot(kind='bar', ax=ax1, rot=45)
        ax1.set_title('Breaking Point Load Comparison\n(Higher is better)', fontweight='bold')
        ax1.set_ylabel('Breaking Point Load')
        ax1.grid(axis='y', linestyle='--', alpha=0.7)
        
        # 2. Failure cascade size comparison (lower is better)
        ax2 = fig.add_subplot(gs[0, 1])
        cascade_pivot = grouped.pivot(index='component_tested', columns='architecture_type', values='failure_cascade_size')
        cascade_pivot.plot(kind='bar', ax=ax2, rot=45)
        ax2.set_title('Failure Cascade Size Comparison\n(Lower is better)', fontweight='bold')
        ax2.set_ylabel('Failure Cascade Size')
        ax2.grid(axis='y', linestyle='--', alpha=0.7)
        
        # 3. Recovery time comparison (lower is better)
        ax3 = fig.add_subplot(gs[1, 0])
        recovery_pivot = grouped.pivot(index='component_tested', columns='architecture_type', values='recovery_time_ms')
        recovery_pivot.plot(kind='bar', ax=ax3, rot=45)
        ax3.set_title('Recovery Time Comparison\n(Lower is better)', fontweight='bold')
        ax3.set_ylabel('Recovery Time (ms)')
        ax3.grid(axis='y', linestyle='--', alpha=0.7)
        
        # 4. Overall radar chart comparison
        ax4 = fig.add_subplot(gs[1, 1], polar=True)
        
        # Get overall metrics by architecture
        arch_summary = arch_data.groupby('architecture_type').agg({
            'breaking_point_load': 'mean',
            'graceful_degradation_score': 'mean',
            'recovery_time_ms': lambda x: 100 - (x.mean() / 50),  # Normalize and invert (lower is better)
            'failure_cascade_size': lambda x: 100 - (x.mean() * 10)  # Normalize and invert
        }).reset_index()
        
        # Prepare radar chart data
        categories = ['Breaking Point', 'Degradation Score', 'Recovery Speed', 'Failure Containment']
        
        # Number of categories
        N = len(categories)
        
        # Create angles for each category
        angles = np.linspace(0, 2*np.pi, N, endpoint=False).tolist()
        angles += angles[:1]  # Close the loop
        
        # Create color palette
        n_colors = len(architectures)
        palette = sns.color_palette("husl", n_colors)
        
        # Plot each architecture
        for i, arch in enumerate(architectures):
            arch_metrics = arch_summary[arch_summary['architecture_type'] == arch]
            
            if not arch_metrics.empty:
                # Get values
                values = [
                    arch_metrics.iloc[0]['breaking_point_load'],
                    arch_metrics.iloc[0]['graceful_degradation_score'],
                    arch_metrics.iloc[0]['recovery_time_ms'],
                    arch_metrics.iloc[0]['failure_cascade_size']
                ]
                
                # Close the loop
                values += values[:1]
                
                # Plot architecture
                ax4.plot(angles, values, linewidth=2, label=arch, color=palette[i])
                ax4.fill(angles, values, alpha=0.1, color=palette[i])
        
        # Set category labels
        ax4.set_xticks(angles[:-1])
        ax4.set_xticklabels(categories)
        
        # Set y-ticks
        ax4.set_yticks([20, 40, 60, 80, 100])
        ax4.set_yticklabels(['20', '40', '60', '80', '100'])
        ax4.set_ylim(0, 100)
        
        # Add title and legend
        ax4.set_title('Architecture Comparison\n(Higher is better in all dimensions)', fontweight='bold')
        ax4.legend(loc='upper right', bbox_to_anchor=(0.1, 1.1))
        
        # Add overall title
        fig.suptitle('"What Breaks First?" Architecture Comparison', fontsize=20, fontweight='bold')
        
        plt.tight_layout()
        
        # Save figure
        output_path = os.path.join(self.output_dir, 'architecture_comparison.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved architecture comparison visualization to {output_path}")
        
        return fig
    
    def create_neural_component_visibility_visualization(self):
        """
        Create a visualization of neural component visibility.
        
        Returns:
            matplotlib.figure.Figure: The generated figure
        """
        if 'neural_component_visibility_tests' not in self.datasets:
            print("Neural component visibility tests not found")
            return None
        
        df = self.datasets['neural_component_visibility_tests']
        
        # Create figure with two subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 10))
        
        # 1. Heatmap of component type vs. visibility level
        # Create pivot table
        pivot_data = df.pivot_table(
            index='component_type',
            columns='visibility_level',
            values='internal_state_visibility',
            aggfunc='mean'
        )
        
        # Sort rows by high visibility (descending)
        pivot_data = pivot_data.sort_values('high', ascending=False)
        
        # Create heatmap
        sns.heatmap(
            pivot_data,
            annot=True,
            fmt='.1f',
            cmap='YlGnBu',
            ax=ax1,
            cbar_kws={'label': 'Internal State Visibility (%)'}
        )
        
        ax1.set_title('Component Type vs. Visibility Level', fontweight='bold')
        
        # 2. Bar chart comparing different visibility metrics
        # Group by visibility level
        visibility_summary = df.groupby('visibility_level').agg({
            'decision_factors_exposed': 'mean',
            'internal_state_visibility': 'mean',
            'explanation_quality': 'mean',
            'interpretability_score': 'mean',
            'actionability_score': 'mean'
        }).reset_index()
        
        # Reshape for easier plotting
        plot_df = pd.melt(
            visibility_summary,
            id_vars=['visibility_level'],
            var_name='metric',
            value_name='score'
        )
        
        # Create a grouped bar chart
        sns.barplot(
            data=plot_df,
            x='visibility_level',
            y='score',
            hue='metric',
            palette='viridis',
            ax=ax2
        )
        
        ax2.set_title('Visibility Metrics Comparison', fontweight='bold')
        ax2.set_xlabel('Visibility Level')
        ax2.set_ylabel('Score (%)')
        ax2.legend(title='Metric', bbox_to_anchor=(1.05, 1), loc='upper left')
        ax2.grid(axis='y', linestyle='--', alpha=0.7)
        
        plt.tight_layout()
        
        # Save figure
        output_path = os.path.join(self.output_dir, 'neural_component_visibility.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved neural component visibility visualization to {output_path}")
        
        return fig
    
    def create_sarcasm_detection_visualization(self):
        """
        Create a visualization of sarcasm detection performance.
        
        Returns:
            matplotlib.figure.Figure: The generated figure
        """
        if 'sarcasm_pattern_tests' not in self.datasets:
            print("Sarcasm pattern tests not found")
            return None
        
        df = self.datasets['sarcasm_pattern_tests']
        
        # Create figure with multiple subplots
        fig, axs = plt.subplots(2, 2, figsize=(15, 12))
        
        # 1. Heatmap of sarcasm intensity vs. contextual dependency
        # Create pivot table
        pivot1 = df.pivot_table(
            index='sarcasm_intensity',
            columns='contextual_dependency',
            values='detection_rate',
            aggfunc='mean'
        )
        
        # Create heatmap
        sns.heatmap(
            pivot1,
            annot=True,
            fmt='.1f',
            cmap='YlGnBu',
            ax=axs[0, 0],
            cbar_kws={'label': 'Detection Rate (%)'}
        )
        
        axs[0, 0].set_title('Sarcasm Intensity vs. Context Dependency', fontweight='bold')
        
        # 2. Bar chart of detection rates by pattern type
        # Group by sarcasm pattern
        pattern_summary = df.groupby('sarcasm_pattern').agg({
            'detection_rate': 'mean',
            'intent_alignment': 'mean',
            'response_appropriateness': 'mean'
        }).reset_index()
        
        # Sort by detection rate
        pattern_summary = pattern_summary.sort_values('detection_rate', ascending=False)
        
        # Plot top patterns
        top_patterns = pattern_summary.head(10)
        
        # Create bar chart
        bars = axs[0, 1].bar(
            top_patterns['sarcasm_pattern'],
            top_patterns['detection_rate'],
            color=self.colors['accent'],
            alpha=0.8
        )
        
        axs[0, 1].set_title('Detection Rate by Sarcasm Pattern', fontweight='bold')
        axs[0, 1].set_xlabel('Sarcasm Pattern')
        axs[0, 1].set_ylabel('Detection Rate (%)')
        axs[0, 1].set_xticklabels(axs[0, 1].get_xticklabels(), rotation=45, ha='right')
        axs[0, 1].grid(axis='y', linestyle='--', alpha=0.7)
        
        # 3. Cultural specificity impact
        # Group by cultural_specificity
        cultural_summary = df.groupby('cultural_specificity').agg({
            'detection_rate': 'mean',
            'intent_alignment': 'mean',
            'response_appropriateness': 'mean'
        }).reset_index()
        
        # Reshape for grouped bar chart
        cultural_plot = pd.melt(
            cultural_summary,
            id_vars=['cultural_specificity'],
            var_name='metric',
            value_name='score'
        )
        
        # Create grouped bar chart
        sns.barplot(
            data=cultural_plot,
            x='cultural_specificity',
            y='score',
            hue='metric',
            palette='viridis',
            ax=axs[1, 0]
        )
        
        axs[1, 0].set_title('Impact of Cultural Specificity', fontweight='bold')
        axs[1, 0].set_xlabel('Cultural Specificity')
        axs[1, 0].set_ylabel('Score (%)')
        axs[1, 0].legend(title='Metric')
        axs[1, 0].grid(axis='y', linestyle='--', alpha=0.7)
        
        # 4. Test result distribution
        # Count test results
        result_counts = df['test_result'].value_counts()
        
        # Create pie chart
        wedges, texts, autotexts = axs[1, 1].pie(
            result_counts,
            labels=result_counts.index,
            autopct='%1.1f%%',
            startangle=90,
            colors=[self.status_colors.get(r, self.colors['neutral']) for r in result_counts.index]
        )
        
        # Make text easier to read
        for text in texts:
            text.set_fontweight('bold')
        
        for autotext in autotexts:
            autotext.set_fontweight('bold')
            autotext.set_color('white')
        
        axs[1, 1].set_title('Test Result Distribution', fontweight='bold')
        axs[1, 1].axis('equal')  # Equal aspect ratio ensures a circular pie chart
        
        # Add overall title
        fig.suptitle('Sarcasm Detection Evaluation', fontsize=20, fontweight='bold')
        
        plt.tight_layout()
        
        # Save figure
        output_path = os.path.join(self.output_dir, 'sarcasm_detection.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved sarcasm detection visualization to {output_path}")
        
        return fig
    
    def create_component_failure_analysis(self):
        """
        Create a visualization of component failure patterns.
        
        Returns:
            matplotlib.figure.Figure: The generated figure
        """
        if 'modularity_component_removal_tests' not in self.datasets:
            print("Modularity component removal tests not found")
            return None
        
        df = self.datasets['modularity_component_removal_tests']
        
        # Create figure with multiple subplots
        fig, axs = plt.subplots(2, 2, figsize=(15, 12))
        
        # 1. Scatter plot of functionality preserved vs. recovery time
        scatter = axs[0, 0].scatter(
            df['recovery_time_ms'],
            df['functionality_preserved_pct'],
            s=df['error_propagation_count'] * 10,  # Size based on error propagation
            c=df['functionality_preserved_pct'],    # Color based on functionality preserved
            cmap='viridis',
            alpha=0.7
        )
        
        # Add colorbar
        cbar = plt.colorbar(scatter, ax=axs[0, 0])
        cbar.set_label('Functionality Preserved (%)')
        
        # Add annotations for key points
        threshold = 75  # Key points have functionality below this threshold
        for i, row in df[df['functionality_preserved_pct'] < threshold].iterrows():
            axs[0, 0].annotate(
                row['component_removed'],
                xy=(row['recovery_time_ms'], row['functionality_preserved_pct']),
                xytext=(5, 5),
                textcoords='offset points',
                fontsize=8
            )
        
        axs[0, 0].set_title('Recovery Time vs. Functionality Preserved', fontweight='bold')
        axs[0, 0].set_xlabel('Recovery Time (ms)')
        axs[0, 0].set_ylabel('Functionality Preserved (%)')
        axs[0, 0].grid(True, linestyle='--', alpha=0.7)
        
        # 2. Bar chart of worst-performing components
        # Sort by functionality preserved (ascending)
        worst_components = df.sort_values('functionality_preserved_pct').head(10)
        
        bars = axs[0, 1].barh(
            worst_components['component_removed'],
            worst_components['functionality_preserved_pct'],
            color=worst_components['functionality_preserved_pct'].map(
                lambda x: self.colors['danger'] if x < 60 else (
                    self.colors['warning'] if x < 80 else self.colors['secondary']
                )
            ),
            alpha=0.8
        )
        
        # Add error propagation annotations
        for i, (_, row) in enumerate(worst_components.iterrows()):
            axs[0, 1].annotate(
                f"Errors: {row['error_propagation_count']}",
                xy=(row['functionality_preserved_pct'] + 1, i),
                va='center',
                fontsize=10
            )
        
        axs[0, 1].set_title('Components with Highest Impact When Removed', fontweight='bold')
        axs[0, 1].set_xlabel('Functionality Preserved (%)')
        axs[0, 1].set_xlim(0, 100)
        axs[0, 1].grid(axis='x', linestyle='--', alpha=0.7)
        
        # 3. Test result distribution by component type
        # Extract component type from the name (first part before "Agent" or other patterns)
        df['component_type'] = df['component_removed'].apply(
            lambda x: x.split('Agent')[0].split('Connector')[0].split('+')[0] if '+' not in x else 'Combined'
        )
        
        # Group by component type and test result
        type_result = pd.crosstab(df['component_type'], df['test_result'])
        
        # Calculate percentage
        type_result_pct = type_result.div(type_result.sum(axis=1), axis=0) * 100
        
        # Stacked bar chart
        type_result_pct.plot(
            kind='bar',
            stacked=True,
            ax=axs[1, 0],
            color=[
                self.status_colors.get('PASS', self.colors['secondary']),
                self.status_colors.get('CONDITIONAL PASS', self.colors['warning']),
                self.status_colors.get('FAIL', self.colors['danger'])
            ]
        )
        
        axs[1, 0].set_title('Test Results by Component Type', fontweight='bold')
        axs[1, 0].set_xlabel('Component Type')
        axs[1, 0].set_ylabel('Percentage')
        axs[1, 0].set_xticklabels(axs[1, 0].get_xticklabels(), rotation=45, ha='right')
        axs[1, 0].grid(axis='y', linestyle='--', alpha=0.7)
        axs[1, 0].legend(title='Test Result')
        
        # 4. Error propagation histogram
        # Create categories for error propagation
        df['error_category'] = pd.cut(
            df['error_propagation_count'],
            bins=[0, 1, 5, 10, 20, 100],
            labels=['None (0)', 'Low (1-5)', 'Medium (6-10)', 'High (11-20)', 'Severe (>20)']
        )
        
        # Count by category
        error_counts = df['error_category'].value_counts().sort_index()
        
        # Create a horizontal bar chart
        bars = axs[1, 1].barh(
            error_counts.index,
            error_counts.values,
            color=[
                self.colors['success'],
                self.colors['secondary'],
                self.colors['warning'],
                self.colors['danger'],
                self.colors['dark']
            ],
            alpha=0.8
        )
        
        # Add count annotations
        for i, count in enumerate(error_counts):
            axs[1, 1].annotate(
                str(count),
                xy=(count + 0.5, i),
                va='center',
                fontweight='bold'
            )
        
        axs[1, 1].set_title('Error Propagation Distribution', fontweight='bold')
        axs[1, 1].set_xlabel('Number of Components')
        axs[1, 1].grid(axis='x', linestyle='--', alpha=0.7)
        
        # Add overall title
        fig.suptitle('Component Failure Analysis', fontsize=20, fontweight='bold')
        
        plt.tight_layout()
        
        # Save figure
        output_path = os.path.join(self.output_dir, 'component_failure_analysis.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved component failure analysis to {output_path}")
        
        return fig
    
    def create_dashboard(self):
        """
        Create all visualizations and combine them into a comprehensive dashboard.
        """
        print("Generating visualizations for the Neuron Evaluation Framework...")
        
        # Create all visualizations
        self.create_system_readiness_visualization()
        self.create_dimension_performance_visualization()
        self.create_performance_timeline_visualization()
        self.create_error_analysis_visualization()
        self.create_improvement_priorities_visualization()
        self.create_architecture_comparison_visualization()
        self.create_neural_component_visibility_visualization()
        self.create_sarcasm_detection_visualization()
        self.create_component_failure_analysis()
        
        print(f"All visualizations saved to {self.output_dir}")


# Example usage
if __name__ == "__main__":
    visualizer = NeuronVisualizationDashboard(data_dir='./data', output_dir='./visualizations')
    visualizer.create_dashboard()
    
    print("Visualization dashboard creation complete!")

"""
SUMMARY:
This code implements a comprehensive visualization dashboard for the Neuron Evaluation Framework.
The NeuronVisualizationDashboard class creates a variety of charts and visualizations to represent
evaluation results. Key visualizations include:

1. System Readiness Assessment - Showing overall system performance vs. targets
2. Dimension Performance - Detailed breakdown of performance across key dimensions
3. Performance Timeline - Tracking performance changes over development weeks
4. Error Analysis - Visualizing error patterns and their impact
5. Improvement Priorities - Identifying and visualizing key improvement areas
6. Architecture Comparison - Comparing different architectures from "What Breaks First" testing
7. Neural Component Visibility - Analyzing component visibility and explainability
8. Sarcasm Detection Performance - Detailed analysis of sarcasm detection capabilities
9. Component Failure Analysis - Understanding failure patterns and resilience

All visualizations use consistent styling and color schemes for a professional appearance. The
visualizations are saved to the specified output directory for inclusion in reports or presentations.
This dashboard provides a comprehensive visual overview of the Neuron Framework's performance
and areas for improvement.
"""
