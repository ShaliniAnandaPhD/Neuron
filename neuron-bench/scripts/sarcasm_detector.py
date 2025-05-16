import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import os
from sklearn.cluster import KMeans
from sklearn.preprocessing import MinMaxScaler
from sklearn.decomposition import PCA
import matplotlib.patches as mpatches

class SarcasmDetectionAnalyzer:
    """
    A specialized class for analyzing sarcasm detection performance in the Neuron Evaluation Framework.
    Focuses on identifying patterns, cultural variations, and improvement opportunities.
    """
    
    def __init__(self, data_dir='data', output_dir='sarcasm_analysis'):
        """
        Initialize the sarcasm detection analyzer.
        
        Args:
            data_dir (str): Directory containing test data files
            output_dir (str): Directory to save analysis outputs
        """
        self.data_dir = data_dir
        self.output_dir = output_dir
        self.sarcasm_data = None
        self.component_data = None
        self.error_data = None
        self.analysis_results = {}
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Load the sarcasm detection data
        self._load_data()
    
    def _load_data(self):
        """Load sarcasm pattern tests and related datasets."""
        # Load sarcasm pattern tests
        sarcasm_file = Path(self.data_dir) / 'sarcasm_pattern_tests.txt'
        
        if sarcasm_file.exists():
            try:
                self.sarcasm_data = pd.read_csv(sarcasm_file)
                print(f"Loaded sarcasm detection data with {len(self.sarcasm_data)} test records.")
            except Exception as e:
                print(f"Error loading sarcasm detection data: {e}")
        else:
            print(f"Sarcasm detection data file not found: {sarcasm_file}")
        
        # Load target gap analysis for sarcasm component info
        gap_file = Path(self.data_dir) / 'target_gap_analysis.txt'
        
        if gap_file.exists():
            try:
                gap_df = pd.read_csv(gap_file)
                # Filter for sarcasm-related components
                sarcasm_components = gap_df[gap_df['component'].str.contains('Sarcasm', case=False, na=False)]
                self.component_data = sarcasm_components
                print(f"Loaded sarcasm component data with {len(sarcasm_components)} components.")
            except Exception as e:
                print(f"Error loading target gap analysis: {e}")
        
        # Load error analysis for sarcasm-related errors
        error_file = Path(self.data_dir) / 'error_analysis_dataset.txt'
        
        if error_file.exists():
            try:
                error_df = pd.read_csv(error_file)
                # Filter for sarcasm-related errors
                sarcasm_errors = error_df[error_df['area'].str.contains('Sarcasm', case=False, na=False)]
                self.error_data = sarcasm_errors
                print(f"Loaded sarcasm error data with {len(sarcasm_errors)} error records.")
            except Exception as e:
                print(f"Error loading error analysis dataset: {e}")
    
    def analyze_pattern_performance(self):
        """
        Analyze performance across different sarcasm patterns.
        
        Returns:
            pandas.DataFrame: Pattern performance analysis
        """
        if self.sarcasm_data is None:
            print("No sarcasm detection data available.")
            return None
        
        # Group by sarcasm pattern and calculate average metrics
        pattern_stats = self.sarcasm_data.groupby('sarcasm_pattern').agg({
            'detection_rate': ['mean', 'std', 'min', 'max'],
            'intent_alignment': ['mean', 'std', 'min', 'max'],
            'response_appropriateness': ['mean', 'std', 'min', 'max'],
            'test_result': lambda x: (x == 'PASS').mean() * 100  # Pass rate percentage
        }).reset_index()
        
        # Flatten column names
        pattern_stats.columns = ['_'.join(col).strip() if col[1] else col[0] for col in pattern_stats.columns.values]
        
        # Calculate overall performance score
        pattern_stats['overall_score'] = (
            pattern_stats['detection_rate_mean'] * 0.4 +
            pattern_stats['intent_alignment_mean'] * 0.3 +
            pattern_stats['response_appropriateness_mean'] * 0.3
        )
        
        # Calculate reliability score (higher mean with lower std dev is more reliable)
        pattern_stats['reliability_score'] = (
            pattern_stats['detection_rate_mean'] / (1 + pattern_stats['detection_rate_std']) * 0.4 +
            pattern_stats['intent_alignment_mean'] / (1 + pattern_stats['intent_alignment_std']) * 0.3 +
            pattern_stats['response_appropriateness_mean'] / (1 + pattern_stats['response_appropriateness_std']) * 0.3
        )
        
        # Determine if a pattern is a strength or weakness
        threshold = pattern_stats['overall_score'].median()
        pattern_stats['strength_or_weakness'] = pattern_stats['overall_score'].apply(
            lambda x: 'Strength' if x >= threshold else 'Weakness'
        )
        
        # Sort by overall score descending
        pattern_stats = pattern_stats.sort_values('overall_score', ascending=False)
        
        # Save results
        self.analysis_results['pattern_performance'] = pattern_stats
        
        return pattern_stats
    
    def analyze_contextual_factors(self):
        """
        Analyze the impact of contextual factors on sarcasm detection.
        
        Returns:
            pandas.DataFrame: Contextual factor analysis
        """
        if self.sarcasm_data is None:
            print("No sarcasm detection data available.")
            return None
        
        # Analyze impact of contextual dependency
        context_impact = self.sarcasm_data.groupby('contextual_dependency').agg({
            'detection_rate': ['mean', 'std'],
            'intent_alignment': ['mean', 'std'],
            'response_appropriateness': ['mean', 'std']
        }).reset_index()
        
        # Flatten column names
        context_impact.columns = ['_'.join(col).strip() if col[1] else col[0] for col in context_impact.columns.values]
        
        # Calculate percentage drop from low to high context dependency
        if 'low' in context_impact['contextual_dependency'].values and 'high' in context_impact['contextual_dependency'].values:
            low_row = context_impact[context_impact['contextual_dependency'] == 'low']
            high_row = context_impact[context_impact['contextual_dependency'] == 'high']
            
            if not low_row.empty and not high_row.empty:
                detection_drop = (low_row['detection_rate_mean'].values[0] - high_row['detection_rate_mean'].values[0]) / low_row['detection_rate_mean'].values[0] * 100
                alignment_drop = (low_row['intent_alignment_mean'].values[0] - high_row['intent_alignment_mean'].values[0]) / low_row['intent_alignment_mean'].values[0] * 100
                response_drop = (low_row['response_appropriateness_mean'].values[0] - high_row['response_appropriateness_mean'].values[0]) / low_row['response_appropriateness_mean'].values[0] * 100
                
                context_impact_summary = {
                    'detection_rate_drop_pct': detection_drop,
                    'intent_alignment_drop_pct': alignment_drop,
                    'response_appropriateness_drop_pct': response_drop,
                    'average_drop_pct': (detection_drop + alignment_drop + response_drop) / 3
                }
            else:
                context_impact_summary = {
                    'detection_rate_drop_pct': 0,
                    'intent_alignment_drop_pct': 0,
                    'response_appropriateness_drop_pct': 0,
                    'average_drop_pct': 0
                }
        else:
            context_impact_summary = {
                'detection_rate_drop_pct': 0,
                'intent_alignment_drop_pct': 0,
                'response_appropriateness_drop_pct': 0,
                'average_drop_pct': 0
            }
        
        # Analyze impact of cultural specificity
        cultural_impact = self.sarcasm_data.groupby('cultural_specificity').agg({
            'detection_rate': ['mean', 'std'],
            'intent_alignment': ['mean', 'std'],
            'response_appropriateness': ['mean', 'std']
        }).reset_index()
        
        # Flatten column names
        cultural_impact.columns = ['_'.join(col).strip() if col[1] else col[0] for col in cultural_impact.columns.values]
        
        # Calculate percentage drop from low to high cultural specificity
        if 'low' in cultural_impact['cultural_specificity'].values and 'high' in cultural_impact['cultural_specificity'].values:
            low_row = cultural_impact[cultural_impact['cultural_specificity'] == 'low']
            high_row = cultural_impact[cultural_impact['cultural_specificity'] == 'high']
            
            if not low_row.empty and not high_row.empty:
                detection_drop = (low_row['detection_rate_mean'].values[0] - high_row['detection_rate_mean'].values[0]) / low_row['detection_rate_mean'].values[0] * 100
                alignment_drop = (low_row['intent_alignment_mean'].values[0] - high_row['intent_alignment_mean'].values[0]) / low_row['intent_alignment_mean'].values[0] * 100
                response_drop = (low_row['response_appropriateness_mean'].values[0] - high_row['response_appropriateness_mean'].values[0]) / low_row['response_appropriateness_mean'].values[0] * 100
                
                cultural_impact_summary = {
                    'detection_rate_drop_pct': detection_drop,
                    'intent_alignment_drop_pct': alignment_drop,
                    'response_appropriateness_drop_pct': response_drop,
                    'average_drop_pct': (detection_drop + alignment_drop + response_drop) / 3
                }
            else:
                cultural_impact_summary = {
                    'detection_rate_drop_pct': 0,
                    'intent_alignment_drop_pct': 0,
                    'response_appropriateness_drop_pct': 0,
                    'average_drop_pct': 0
                }
        else:
            cultural_impact_summary = {
                'detection_rate_drop_pct': 0,
                'intent_alignment_drop_pct': 0,
                'response_appropriateness_drop_pct': 0,
                'average_drop_pct': 0
            }
        
        # Analyze impact of sarcasm intensity
        intensity_impact = self.sarcasm_data.groupby('sarcasm_intensity').agg({
            'detection_rate': ['mean', 'std'],
            'intent_alignment': ['mean', 'std'],
            'response_appropriateness': ['mean', 'std']
        }).reset_index()
        
        # Flatten column names
        intensity_impact.columns = ['_'.join(col).strip() if col[1] else col[0] for col in intensity_impact.columns.values]
        
        # Calculate percentage drop from high to low intensity
        if 'high' in intensity_impact['sarcasm_intensity'].values and 'low' in intensity_impact['sarcasm_intensity'].values:
            high_row = intensity_impact[intensity_impact['sarcasm_intensity'] == 'high']
            low_row = intensity_impact[intensity_impact['sarcasm_intensity'] == 'low']
            
            if not high_row.empty and not low_row.empty:
                detection_drop = (high_row['detection_rate_mean'].values[0] - low_row['detection_rate_mean'].values[0]) / high_row['detection_rate_mean'].values[0] * 100
                alignment_drop = (high_row['intent_alignment_mean'].values[0] - low_row['intent_alignment_mean'].values[0]) / high_row['intent_alignment_mean'].values[0] * 100
                response_drop = (high_row['response_appropriateness_mean'].values[0] - low_row['response_appropriateness_mean'].values[0]) / high_row['response_appropriateness_mean'].values[0] * 100
                
                intensity_impact_summary = {
                    'detection_rate_drop_pct': detection_drop,
                    'intent_alignment_drop_pct': alignment_drop,
                    'response_appropriateness_drop_pct': response_drop,
                    'average_drop_pct': (detection_drop + alignment_drop + response_drop) / 3
                }
            else:
                intensity_impact_summary = {
                    'detection_rate_drop_pct': 0,
                    'intent_alignment_drop_pct': 0,
                    'response_appropriateness_drop_pct': 0,
                    'average_drop_pct': 0
                }
        else:
            intensity_impact_summary = {
                'detection_rate_drop_pct': 0,
                'intent_alignment_drop_pct': 0,
                'response_appropriateness_drop_pct': 0,
                'average_drop_pct': 0
            }
        
        # Create combined result
        contextual_factors = {
            'context_dependency': {
                'impact_table': context_impact,
                'impact_summary': context_impact_summary
            },
            'cultural_specificity': {
                'impact_table': cultural_impact,
                'impact_summary': cultural_impact_summary
            },
            'sarcasm_intensity': {
                'impact_table': intensity_impact,
                'impact_summary': intensity_impact_summary
            }
        }
        
        # Create summary table
        summary_data = [
            {
                'factor': 'Context Dependency',
                'impact_level': context_impact_summary['average_drop_pct'],
                'detection_drop': context_impact_summary['detection_rate_drop_pct'],
                'alignment_drop': context_impact_summary['intent_alignment_drop_pct'],
                'response_drop': context_impact_summary['response_appropriateness_drop_pct']
            },
            {
                'factor': 'Cultural Specificity',
                'impact_level': cultural_impact_summary['average_drop_pct'],
                'detection_drop': cultural_impact_summary['detection_rate_drop_pct'],
                'alignment_drop': cultural_impact_summary['intent_alignment_drop_pct'],
                'response_drop': cultural_impact_summary['response_appropriateness_drop_pct']
            },
            {
                'factor': 'Sarcasm Intensity',
                'impact_level': intensity_impact_summary['average_drop_pct'],
                'detection_drop': intensity_impact_summary['detection_rate_drop_pct'],
                'alignment_drop': intensity_impact_summary['intent_alignment_drop_pct'],
                'response_drop': intensity_impact_summary['response_appropriateness_drop_pct']
            }
        ]
        
        summary_df = pd.DataFrame(summary_data)
        
        # Sort by impact level descending
        summary_df = summary_df.sort_values('impact_level', ascending=False)
        
        # Save results
        self.analysis_results['contextual_factors'] = contextual_factors
        self.analysis_results['contextual_factors_summary'] = summary_df
        
        return summary_df
    
    def analyze_cultural_variations(self):
        """
        Analyze performance across cultural sarcasm variations.
        
        Returns:
            pandas.DataFrame: Cultural variation analysis
        """
        if self.sarcasm_data is None:
            print("No sarcasm detection data available.")
            return None
        
        # Filter for culturally specific patterns
        cultural_patterns = self.sarcasm_data[
            (self.sarcasm_data['sarcasm_pattern'].str.contains('british', case=False, na=False)) |
            (self.sarcasm_data['sarcasm_pattern'].str.contains('american', case=False, na=False)) |
            (self.sarcasm_data['sarcasm_pattern'].str.contains('australian', case=False, na=False)) |
            (self.sarcasm_data['cultural_specificity'] == 'high')
        ].copy()
        
        if len(cultural_patterns) == 0:
            print("No cultural patterns found in the data.")
            return None
        
        # Extract cultural background from pattern name
        def extract_culture(pattern):
            if 'british' in pattern.lower():
                return 'British'
            elif 'american' in pattern.lower():
                return 'American'
            elif 'australian' in pattern.lower():
                return 'Australian'
            else:
                return 'Other'
        
        cultural_patterns['culture'] = cultural_patterns['sarcasm_pattern'].apply(extract_culture)
        
        # Group by culture and calculate average metrics
        culture_stats = cultural_patterns.groupby('culture').agg({
            'detection_rate': ['mean', 'std', 'min', 'max'],
            'intent_alignment': ['mean', 'std', 'min', 'max'],
            'response_appropriateness': ['mean', 'std', 'min', 'max'],
            'test_result': lambda x: (x == 'PASS').mean() * 100  # Pass rate percentage
        }).reset_index()
        
        # Flatten column names
        culture_stats.columns = ['_'.join(col).strip() if col[1] else col[0] for col in culture_stats.columns.values]
        
        # Calculate overall performance score
        culture_stats['overall_score'] = (
            culture_stats['detection_rate_mean'] * 0.4 +
            culture_stats['intent_alignment_mean'] * 0.3 +
            culture_stats['response_appropriateness_mean'] * 0.3
        )
        
        # Compare to baseline (non-cultural patterns)
        non_cultural = self.sarcasm_data[
            ~(self.sarcasm_data['sarcasm_pattern'].str.contains('british', case=False, na=False)) &
            ~(self.sarcasm_data['sarcasm_pattern'].str.contains('american', case=False, na=False)) &
            ~(self.sarcasm_data['sarcasm_pattern'].str.contains('australian', case=False, na=False)) &
            (self.sarcasm_data['cultural_specificity'] != 'high')
        ]
        
        if len(non_cultural) > 0:
            # Calculate baseline metrics
            baseline_detection = non_cultural['detection_rate'].mean()
            baseline_alignment = non_cultural['intent_alignment'].mean()
            baseline_response = non_cultural['response_appropriateness'].mean()
            baseline_score = (baseline_detection * 0.4 + baseline_alignment * 0.3 + baseline_response * 0.3)
            
            # Calculate performance relative to baseline
            culture_stats['detection_vs_baseline'] = culture_stats['detection_rate_mean'] - baseline_detection
            culture_stats['alignment_vs_baseline'] = culture_stats['intent_alignment_mean'] - baseline_alignment
            culture_stats['response_vs_baseline'] = culture_stats['response_appropriateness_mean'] - baseline_response
            culture_stats['overall_vs_baseline'] = culture_stats['overall_score'] - baseline_score
            
            # Add baseline row
            baseline_row = pd.DataFrame([{
                'culture': 'Baseline (Non-cultural)',
                'detection_rate_mean': baseline_detection,
                'intent_alignment_mean': baseline_alignment,
                'response_appropriateness_mean': baseline_response,
                'overall_score': baseline_score,
                'detection_vs_baseline': 0,
                'alignment_vs_baseline': 0,
                'response_vs_baseline': 0,
                'overall_vs_baseline': 0
            }])
            
            culture_stats = pd.concat([culture_stats, baseline_row])
        
        # Sort by overall score descending
        culture_stats = culture_stats.sort_values('overall_score', ascending=False)
        
        # Save results
        self.analysis_results['cultural_variations'] = culture_stats
        
        return culture_stats
    
    def analyze_failure_modes(self):
        """
        Analyze common failure modes in sarcasm detection.
        
        Returns:
            pandas.DataFrame: Failure mode analysis
        """
        if self.sarcasm_data is None:
            print("No sarcasm detection data available.")
            return None
        
        # Filter for test failures
        failures = self.sarcasm_data[self.sarcasm_data['test_result'] != 'PASS'].copy()
        
        if len(failures) == 0:
            print("No test failures found in the data.")
            return None
        
        # Create combined factor field
        failures['combined_factors'] = failures.apply(
            lambda row: f"{row['sarcasm_pattern']} - {row['sarcasm_intensity']} intensity, {row['contextual_dependency']} context, {row['cultural_specificity']} cultural",
            axis=1
        )
        
        # Count failures by combined factors
        failure_counts = failures['combined_factors'].value_counts().reset_index()
        failure_counts.columns = ['failure_pattern', 'count']
        
        # Calculate average metrics for each failure pattern
        failure_stats = failures.groupby('combined_factors').agg({
            'detection_rate': 'mean',
            'intent_alignment': 'mean',
            'response_appropriateness': 'mean'
        }).reset_index()
        
        failure_stats.columns = ['failure_pattern', 'avg_detection_rate', 'avg_intent_alignment', 'avg_response_appropriateness']
        
        # Merge counts and stats
        failure_analysis = failure_counts.merge(failure_stats, on='failure_pattern')
        
        # Calculate failure severity (lower metrics = higher severity)
        failure_analysis['failure_severity'] = (
            (100 - failure_analysis['avg_detection_rate']) * 0.4 +
            (100 - failure_analysis['avg_intent_alignment']) * 0.3 +
            (100 - failure_analysis['avg_response_appropriateness']) * 0.3
        )
        
        # Classify failure modes based on primary factors
        def determine_failure_mode(pattern):
            if 'high cultural' in pattern:
                return 'Cultural Understanding'
            elif 'high context' in pattern:
                return 'Context Dependency'
            elif 'low intensity' in pattern:
                return 'Subtle Marker Detection'
            elif 'deadpan' in pattern.lower():
                return 'Deadpan Recognition'
            elif 'understated' in pattern.lower():
                return 'Understatement Recognition'
            else:
                return 'General Sarcasm Detection'
        
        failure_analysis['failure_mode'] = failure_analysis['failure_pattern'].apply(determine_failure_mode)
        
        # Group by failure mode
        mode_summary = failure_analysis.groupby('failure_mode').agg({
            'count': 'sum',
            'avg_detection_rate': 'mean',
            'avg_intent_alignment': 'mean',
            'avg_response_appropriateness': 'mean',
            'failure_severity': 'mean'
        }).reset_index()
        
        # Sort by count descending
        mode_summary = mode_summary.sort_values('count', ascending=False)
        
        # Round values for readability
        numeric_cols = ['avg_detection_rate', 'avg_intent_alignment', 'avg_response_appropriateness', 'failure_severity']
        mode_summary[numeric_cols] = mode_summary[numeric_cols].round(2)
        
        # Save results
        self.analysis_results['failure_modes'] = mode_summary
        self.analysis_results['detailed_failures'] = failure_analysis.sort_values('failure_severity', ascending=False)
        
        return mode_summary
    
    def identify_improvement_opportunities(self):
        """
        Identify key opportunities for improving sarcasm detection.
        
        Returns:
            pandas.DataFrame: Improvement opportunities
        """
        # Check if we have the necessary analyses
        required_analyses = ['pattern_performance', 'contextual_factors_summary', 'failure_modes']
        missing = [a for a in required_analyses if a not in self.analysis_results]
        
        if missing:
            print(f"Missing required analyses: {', '.join(missing)}")
            print("Run all analyses first.")
            return None
        
        # Initialize opportunities
        opportunities = []
        
        # 1. Opportunities based on pattern performance
        pattern_perf = self.analysis_results['pattern_performance']
        
        # Focus on the weakest patterns
        weak_patterns = pattern_perf[pattern_perf['strength_or_weakness'] == 'Weakness'].head(3)
        
        for _, pattern in weak_patterns.iterrows():
            opportunities.append({
                'improvement_area': f"Pattern Detection: {pattern['sarcasm_pattern']}",
                'current_performance': pattern['overall_score'],
                'target_improvement': '+7-10 points',
                'priority': 'High' if pattern['overall_score'] < 75 else 'Medium',
                'impact': 'High' if pattern['overall_score'] < 75 else 'Medium',
                'description': f"Enhance detection of {pattern['sarcasm_pattern']} patterns which currently score {pattern['overall_score']:.1f}% overall."
            })
        
        # 2. Opportunities based on contextual factors
        context_factors = self.analysis_results['contextual_factors_summary']
        
        # Focus on factors with highest impact
        high_impact_factors = context_factors.head(2)
        
        for _, factor in high_impact_factors.iterrows():
            factor_name = factor['factor']
            impact = factor['impact_level']
            
            if impact > 10:  # Only include significant impacts
                opportunities.append({
                    'improvement_area': f"Contextual Factor: {factor_name}",
                    'current_performance': f"{impact:.1f}% drop",
                    'target_improvement': '50% reduction in performance drop',
                    'priority': 'High' if impact > 15 else 'Medium',
                    'impact': 'High' if impact > 15 else 'Medium',
                    'description': f"Reduce the {impact:.1f}% performance drop caused by {factor_name.lower()}."
                })
        
        # 3. Opportunities based on failure modes
        failure_modes = self.analysis_results['failure_modes']
        
        # Focus on most common and severe failure modes
        for i, mode in failure_modes.iterrows():
            if i < 3 or mode['failure_severity'] > 30:  # Top 3 or high severity
                opportunities.append({
                    'improvement_area': f"Failure Mode: {mode['failure_mode']}",
                    'current_performance': f"{mode['avg_detection_rate']:.1f}% detection rate",
                    'target_improvement': '+10-15 points',
                    'priority': 'High' if mode['count'] > 2 or mode['failure_severity'] > 30 else 'Medium',
                    'impact': 'High' if mode['count'] > 2 else 'Medium',
                    'description': f"Address the '{mode['failure_mode']}' failure mode which affects {mode['count']} test cases with {mode['failure_severity']:.1f} severity."
                })
        
        # 4. Opportunities from error data
        if self.error_data is not None:
            # Group by error type
            error_groups = self.error_data.groupby('error_type').agg({
                'error_frequency': 'first',
                'impact_severity': 'first',
                'detection_rate': 'mean',
                'resolution_rate': 'mean'
            }).reset_index()
            
            for _, error in error_groups.iterrows():
                error_type = error['error_type']
                detection = error['detection_rate']
                
                # Only include significant errors
                if error['error_frequency'] in ['High', 'Medium'] or error['impact_severity'] in ['High', 'Medium']:
                    opportunities.append({
                        'improvement_area': f"Error Reduction: {error_type}",
                        'current_performance': f"{detection:.1f}% detection rate",
                        'target_improvement': '+10-15 points in detection',
                        'priority': 'High' if error['error_frequency'] == 'High' or error['impact_severity'] == 'High' else 'Medium',
                        'impact': 'High' if error['impact_severity'] == 'High' else 'Medium',
                        'description': f"Reduce '{error_type}' errors which currently have {detection:.1f}% detection rate."
                    })
        
        # 5. Add specific technical improvement opportunities
        
        # Cultural adaptation mechanisms
        opportunities.append({
            'improvement_area': 'Cultural Adaptation System',
            'current_performance': 'Limited cultural adaptability',
            'target_improvement': 'Dynamic adaptation to cultural contexts',
            'priority': 'High',
            'impact': 'High',
            'description': 'Implement a cultural context adaptation system that can dynamically adjust sarcasm detection thresholds and patterns based on identified cultural markers.'
        })
        
        # Multi-modal integration
        opportunities.append({
            'improvement_area': 'Multi-modal Sarcasm Detection',
            'current_performance': 'Text-only analysis',
            'target_improvement': 'Integrated text+emoji+punctuation analysis',
            'priority': 'Medium',
            'impact': 'Medium',
            'description': 'Enhance sarcasm detection by integrating analysis of emojis, punctuation patterns, and capitalization as sarcasm markers alongside text.'
        })
        
        # Context window expansion
        opportunities.append({
            'improvement_area': 'Context Window Expansion',
            'current_performance': 'Limited context window',
            'target_improvement': 'Extended context analysis',
            'priority': 'Medium',
            'impact': 'High',
            'description': 'Expand the context window for sarcasm detection to incorporate broader conversational history and established patterns between participants.'
        })
        
        # Convert to DataFrame
        opportunities_df = pd.DataFrame(opportunities)
        
        # Sort by priority and impact
        priority_order = {'High': 0, 'Medium': 1, 'Low': 2}
        impact_order = {'High': 0, 'Medium': 1, 'Low': 2}
        
        opportunities_df['priority_value'] = opportunities_df['priority'].map(priority_order)
        opportunities_df['impact_value'] = opportunities_df['impact'].map(impact_order)
        
        opportunities_df = opportunities_df.sort_values(['priority_value', 'impact_value'])
        
        # Drop helper columns
        opportunities_df = opportunities_df.drop(columns=['priority_value', 'impact_value'])
        
        # Save results
        self.analysis_results['improvement_opportunities'] = opportunities_df
        
        return opportunities_df
    
    def cluster_test_cases(self):
        """
        Cluster test cases to identify common patterns and groupings.
        
        Returns:
            dict: Clustering results
        """
        if self.sarcasm_data is None:
            print("No sarcasm detection data available.")
            return None
        
        # Prepare data for clustering
        cluster_data = self.sarcasm_data.copy()
        
        # Convert categorical columns to numeric
        intensity_map = {'low': 0, 'medium': 1, 'high': 2}
        context_map = {'low': 0, 'medium': 1, 'high': 2}
        cultural_map = {'low': 0, 'medium': 1, 'high': 2}
        result_map = {'FAIL': 0, 'CONDITIONAL PASS': 1, 'PASS': 2}
        
        # Apply mappings
        cluster_data['sarcasm_intensity_num'] = cluster_data['sarcasm_intensity'].map(intensity_map)
        cluster_data['contextual_dependency_num'] = cluster_data['contextual_dependency'].map(context_map)
        cluster_data['cultural_specificity_num'] = cluster_data['cultural_specificity'].map(cultural_map)
        cluster_data['test_result_num'] = cluster_data['test_result'].map(result_map)
        
        # Select features for clustering
        features = [
            'detection_rate', 'intent_alignment', 'response_appropriateness',
            'sarcasm_intensity_num', 'contextual_dependency_num', 'cultural_specificity_num'
        ]
        
        # Normalize features
        scaler = MinMaxScaler()
        scaled_features = scaler.fit_transform(cluster_data[features])
        
        # Determine optimal number of clusters
        from sklearn.metrics import silhouette_score
        
        silhouette_scores = []
        max_clusters = min(10, len(cluster_data) - 1)  # Maximum number of clusters
        
        for n_clusters in range(2, max_clusters + 1):
            # Skip if not enough samples
            if n_clusters >= len(cluster_data):
                continue
                
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(scaled_features)
            
            # Calculate silhouette score
            silhouette_avg = silhouette_score(scaled_features, cluster_labels)
            silhouette_scores.append(silhouette_avg)
        
        # Choose optimal number of clusters (highest silhouette score)
        if silhouette_scores:
            optimal_clusters = silhouette_scores.index(max(silhouette_scores)) + 2  # +2 because we started at 2
        else:
            optimal_clusters = 3  # Default if we couldn't compute silhouette scores
        
        # Perform clustering with optimal number of clusters
        kmeans = KMeans(n_clusters=optimal_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(scaled_features)
        
        # Add cluster labels to data
        cluster_data['cluster'] = cluster_labels
        
        # Analyze clusters
        cluster_summary = []
        
        for cluster_id in range(optimal_clusters):
            cluster_members = cluster_data[cluster_data['cluster'] == cluster_id]
            
            # Skip empty clusters
            if len(cluster_members) == 0:
                continue
            
            # Calculate cluster statistics
            avg_detection = cluster_members['detection_rate'].mean()
            avg_intent = cluster_members['intent_alignment'].mean()
            avg_response = cluster_members['response_appropriateness'].mean()
            
            # Get most common attributes
            common_pattern = cluster_members['sarcasm_pattern'].mode()[0]
            common_intensity = cluster_members['sarcasm_intensity'].mode()[0]
            common_context = cluster_members['contextual_dependency'].mode()[0]
            common_cultural = cluster_members['cultural_specificity'].mode()[0]
            common_result = cluster_members['test_result'].mode()[0]
            
            # Calculate pass rate
            pass_rate = (cluster_members['test_result'] == 'PASS').mean() * 100
            conditional_pass_rate = (cluster_members['test_result'] == 'CONDITIONAL PASS').mean() * 100
            fail_rate = (cluster_members['test_result'] == 'FAIL').mean() * 100
            
            # Add to summary
            cluster_summary.append({
                'cluster_id': cluster_id,
                'size': len(cluster_members),
                'avg_detection_rate': avg_detection,
                'avg_intent_alignment': avg_intent,
                'avg_response_appropriateness': avg_response,
                'common_pattern': common_pattern,
                'common_intensity': common_intensity,
                'common_context_dependency': common_context,
                'common_cultural_specificity': common_cultural,
                'common_test_result': common_result,
                'pass_rate': pass_rate,
                'conditional_pass_rate': conditional_pass_rate,
                'fail_rate': fail_rate,
                'test_cases': cluster_members['test_id'].tolist()
            })
        
        # Convert to DataFrame
        summary_df = pd.DataFrame(cluster_summary)
        
        # Calculate cluster performance score
        summary_df['performance_score'] = (
            summary_df['avg_detection_rate'] * 0.4 +
            summary_df['avg_intent_alignment'] * 0.3 +
            summary_df['avg_response_appropriateness'] * 0.3
        )
        
        # Characterize clusters
        def characterize_cluster(row):
            characteristics = []
            
            # Performance level
            if row['performance_score'] >= 90:
                characteristics.append('High Performance')
            elif row['performance_score'] >= 80:
                characteristics.append('Moderate Performance')
            else:
                characteristics.append('Low Performance')
            
            # Context dependency
            if row['common_context_dependency'] == 'high':
                characteristics.append('Context Dependent')
            
            # Cultural specificity
            if row['common_cultural_specificity'] == 'high':
                characteristics.append('Culturally Specific')
            
            # Sarcasm intensity
            if row['common_intensity'] == 'low':
                characteristics.append('Subtle Sarcasm')
            elif row['common_intensity'] == 'high':
                characteristics.append('Obvious Sarcasm')
            
            return ', '.join(characteristics)
        
        summary_df['cluster_characterization'] = summary_df.apply(characterize_cluster, axis=1)
        
        # Round numeric columns for readability
        numeric_cols = ['avg_detection_rate', 'avg_intent_alignment', 'avg_response_appropriateness', 
                        'pass_rate', 'conditional_pass_rate', 'fail_rate', 'performance_score']
        summary_df[numeric_cols] = summary_df[numeric_cols].round(2)
        
        # Sort by performance score descending
        summary_df = summary_df.sort_values('performance_score', ascending=False)
        
        # Prepare visualization data: PCA to reduce to 2 dimensions
        pca = PCA(n_components=2)
        pca_result = pca.fit_transform(scaled_features)
        
        cluster_data['pca_x'] = pca_result[:, 0]
        cluster_data['pca_y'] = pca_result[:, 1]
        
        # Prepare cluster result dictionary
        cluster_result = {
            'cluster_summary': summary_df,
            'clustered_data': cluster_data,
            'optimal_clusters': optimal_clusters,
            'silhouette_scores': silhouette_scores
        }
        
        # Save results
        self.analysis_results['clustering'] = cluster_result
        
        return cluster_result
    
    def visualize_pattern_performance(self):
        """
        Visualize performance across different sarcasm patterns.
        
        Returns:
            matplotlib.figure.Figure: The generated figure
        """
        if 'pattern_performance' not in self.analysis_results:
            print("Run analyze_pattern_performance first.")
            return None
        
        pattern_stats = self.analysis_results['pattern_performance']
        
        # Create figure with multiple subplots
        fig, axs = plt.subplots(2, 1, figsize=(12, 12))
        
        # Sort patterns by overall score
        sorted_patterns = pattern_stats.sort_values('overall_score', ascending=True)
        
        # 1. Horizontal bar chart of overall scores by pattern
        bars = axs[0].barh(
            sorted_patterns['sarcasm_pattern'],
            sorted_patterns['overall_score'],
            color=sorted_patterns['strength_or_weakness'].map({
                'Strength': '#4CAF50',
                'Weakness': '#F44336'
            })
        )
        
        # Add value labels
        for bar in bars:
            width = bar.get_width()
            axs[0].text(
                width + 1,
                bar.get_y() + bar.get_height()/2,
                f'{width:.1f}',
                va='center'
            )
        
        axs[0].set_title('Overall Performance by Sarcasm Pattern', fontweight='bold')
        axs[0].set_xlabel('Overall Score')
        axs[0].grid(axis='x', linestyle='--', alpha=0.7)
        axs[0].set_xlim(0, 100)
        
        # Add legend
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='#4CAF50', label='Strength'),
            Patch(facecolor='#F44336', label='Weakness')
        ]
        axs[0].legend(handles=legend_elements, loc='lower right')
        
        # 2. Detailed metrics for top and bottom patterns
        top_patterns = pattern_stats.nlargest(3, 'overall_score')
        bottom_patterns = pattern_stats.nsmallest(3, 'overall_score')
        selected_patterns = pd.concat([top_patterns, bottom_patterns])
        
        # Prepare data for grouped bar chart
        patterns = selected_patterns['sarcasm_pattern'].tolist()
        detection_rates = selected_patterns['detection_rate_mean'].tolist()
        intent_alignments = selected_patterns['intent_alignment_mean'].tolist()
        response_appropriateness = selected_patterns['response_appropriateness_mean'].tolist()
        
        # Set up bar positions
        x = np.arange(len(patterns))
        width = 0.25
        
        # Create bars
        axs[1].bar(x - width, detection_rates, width, label='Detection Rate', color='#2196F3')
        axs[1].bar(x, intent_alignments, width, label='Intent Alignment', color='#FF9800')
        axs[1].bar(x + width, response_appropriateness, width, label='Response Appropriateness', color='#4CAF50')
        
        # Add labels and legend
        axs[1].set_title('Detailed Metrics for Top and Bottom Patterns', fontweight='bold')
        axs[1].set_ylabel('Score')
        axs[1].set_xticks(x)
        axs[1].set_xticklabels(patterns, rotation=45, ha='right')
        axs[1].grid(axis='y', linestyle='--', alpha=0.7)
        axs[1].set_ylim(0, 100)
        axs[1].legend()
        
        # Add "Top Performers" and "Bottom Performers" labels
        axs[1].text(
            x[0] - width - 0.5,
            95,
            'TOP PERFORMERS',
            fontweight='bold',
            horizontalalignment='left',
            color='#4CAF50'
        )
        
        axs[1].text(
            x[len(top_patterns)] - width - 0.5,
            95,
            'BOTTOM PERFORMERS',
            fontweight='bold',
            horizontalalignment='left',
            color='#F44336'
        )
        
        # Set overall title
        fig.suptitle('Sarcasm Pattern Performance Analysis', fontsize=16, fontweight='bold')
        
        plt.tight_layout()
        
        # Save figure
        output_path = os.path.join(self.output_dir, 'pattern_performance.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved pattern performance visualization to {output_path}")
        
        return fig
    
    def visualize_contextual_factors(self):
        """
        Visualize impact of contextual factors on sarcasm detection.
        
        Returns:
            matplotlib.figure.Figure: The generated figure
        """
        if 'contextual_factors' not in self.analysis_results:
            print("Run analyze_contextual_factors first.")
            return None
        
        contextual_factors = self.analysis_results['contextual_factors']
        
        # Create figure with multiple subplots
        fig, axs = plt.subplots(2, 2, figsize=(14, 10))
        
        # 1. Context dependency impact
        context_impact = contextual_factors['context_dependency']['impact_table']
        
        # Sort by contextual dependency (low to high)
        context_order = {'low': 0, 'medium': 1, 'high': 2}
        sorted_context = context_impact.sort_values(
            by='contextual_dependency',
            key=lambda x: x.map(context_order)
        )
        
        # Plot metrics by context level
        x = np.arange(len(sorted_context))
        width = 0.25
        
        axs[0, 0].bar(x - width, sorted_context['detection_rate_mean'], width, label='Detection Rate', color='#2196F3')
        axs[0, 0].bar(x, sorted_context['intent_alignment_mean'], width, label='Intent Alignment', color='#FF9800')
        axs[0, 0].bar(x + width, sorted_context['response_appropriateness_mean'], width, label='Response Appropriateness', color='#4CAF50')
        
        axs[0, 0].set_title('Impact of Context Dependency', fontweight='bold')
        axs[0, 0].set_ylabel('Score')
        axs[0, 0].set_xticks(x)
        axs[0, 0].set_xticklabels(sorted_context['contextual_dependency'])
        axs[0, 0].grid(axis='y', linestyle='--', alpha=0.7)
        axs[0, 0].set_ylim(0, 100)
        axs[0, 0].legend()
        
        # Add drop percentage annotation
        if 'impact_summary' in contextual_factors['context_dependency']:
            drop_pct = contextual_factors['context_dependency']['impact_summary']['average_drop_pct']
            axs[0, 0].text(
                0.5, 10,
                f"Performance Drop: {drop_pct:.1f}%",
                horizontalalignment='center',
                bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.3')
            )
        
        # 2. Cultural specificity impact
        cultural_impact = contextual_factors['cultural_specificity']['impact_table']
        
        # Sort by cultural specificity (low to high)
        cultural_order = {'low': 0, 'medium': 1, 'high': 2}
        sorted_cultural = cultural_impact.sort_values(
            by='cultural_specificity',
            key=lambda x: x.map(cultural_order)
        )
        
        # Plot metrics by cultural level
        x = np.arange(len(sorted_cultural))
        width = 0.25
        
        axs[0, 1].bar(x - width, sorted_cultural['detection_rate_mean'], width, label='Detection Rate', color='#2196F3')
        axs[0, 1].bar(x, sorted_cultural['intent_alignment_mean'], width, label='Intent Alignment', color='#FF9800')
        axs[0, 1].bar(x + width, sorted_cultural['response_appropriateness_mean'], width, label='Response Appropriateness', color='#4CAF50')
        
        axs[0, 1].set_title('Impact of Cultural Specificity', fontweight='bold')
        axs[0, 1].set_ylabel('Score')
        axs[0, 1].set_xticks(x)
        axs[0, 1].set_xticklabels(sorted_cultural['cultural_specificity'])
        axs[0, 1].grid(axis='y', linestyle='--', alpha=0.7)
        axs[0, 1].set_ylim(0, 100)
        axs[0, 1].legend()
        
        # Add drop percentage annotation
        if 'impact_summary' in contextual_factors['cultural_specificity']:
            drop_pct = contextual_factors['cultural_specificity']['impact_summary']['average_drop_pct']
            axs[0, 1].text(
                0.5, 10,
                f"Performance Drop: {drop_pct:.1f}%",
                horizontalalignment='center',
                bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.3')
            )
        
        # 3. Sarcasm intensity impact
        intensity_impact = contextual_factors['sarcasm_intensity']['impact_table']
        
        # Sort by intensity (high to low)
        intensity_order = {'high': 0, 'medium': 1, 'low': 2}
        sorted_intensity = intensity_impact.sort_values(
            by='sarcasm_intensity',
            key=lambda x: x.map(intensity_order)
        )
        
        # Plot metrics by intensity level
        x = np.arange(len(sorted_intensity))
        width = 0.25
        
        axs[1, 0].bar(x - width, sorted_intensity['detection_rate_mean'], width, label='Detection Rate', color='#2196F3')
        axs[1, 0].bar(x, sorted_intensity['intent_alignment_mean'], width, label='Intent Alignment', color='#FF9800')
        axs[1, 0].bar(x + width, sorted_intensity['response_appropriateness_mean'], width, label='Response Appropriateness', color='#4CAF50')
        
        axs[1, 0].set_title('Impact of Sarcasm Intensity', fontweight='bold')
        axs[1, 0].set_ylabel('Score')
        axs[1, 0].set_xticks(x)
        axs[1, 0].set_xticklabels(sorted_intensity['sarcasm_intensity'])
        axs[1, 0].grid(axis='y', linestyle='--', alpha=0.7)
        axs[1, 0].set_ylim(0, 100)
        axs[1, 0].legend()
        
        # Add drop percentage annotation
        if 'impact_summary' in contextual_factors['sarcasm_intensity']:
            drop_pct = contextual_factors['sarcasm_intensity']['impact_summary']['average_drop_pct']
            axs[1, 0].text(
                0.5, 10,
                f"Performance Drop: {drop_pct:.1f}%",
                horizontalalignment='center',
                bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.3')
            )
        
        # 4. Factor comparison
        if 'contextual_factors_summary' in self.analysis_results:
            summary = self.analysis_results['contextual_factors_summary']
            
            # Plot impact level for each factor
            factors = summary['factor'].tolist()
            impact_levels = summary['impact_level'].tolist()
            detection_drops = summary['detection_drop'].tolist()
            alignment_drops = summary['alignment_drop'].tolist()
            response_drops = summary['response_drop'].tolist()
            
            # Sort by impact level
            sorted_indices = np.argsort(impact_levels)[::-1]  # Descending
            factors = [factors[i] for i in sorted_indices]
            impact_levels = [impact_levels[i] for i in sorted_indices]
            detection_drops = [detection_drops[i] for i in sorted_indices]
            alignment_drops = [alignment_drops[i] for i in sorted_indices]
            response_drops = [response_drops[i] for i in sorted_indices]
            
            # Create bars
            x = np.arange(len(factors))
            width = 0.25
            
            axs[1, 1].bar(x - width, detection_drops, width, label='Detection Drop', color='#2196F3')
            axs[1, 1].bar(x, alignment_drops, width, label='Alignment Drop', color='#FF9800')
            axs[1, 1].bar(x + width, response_drops, width, label='Response Drop', color='#4CAF50')
            
            axs[1, 1].set_title('Contextual Factor Impact Comparison', fontweight='bold')
            axs[1, 1].set_ylabel('Performance Drop (%)')
            axs[1, 1].set_xticks(x)
            axs[1, 1].set_xticklabels(factors)
            axs[1, 1].grid(axis='y', linestyle='--', alpha=0.7)
            axs[1, 1].legend()
            
            # Add overall impact annotations
            for i, impact in enumerate(impact_levels):
                axs[1, 1].text(
                    x[i],
                    max(detection_drops[i], alignment_drops[i], response_drops[i]) + 2,
                    f"Overall: {impact:.1f}%",
                    horizontalalignment='center',
                    fontweight='bold'
                )
        else:
            axs[1, 1].text(
                0.5, 0.5,
                "Contextual factors summary not available",
                horizontalalignment='center',
                verticalalignment='center',
                transform=axs[1, 1].transAxes
            )
            axs[1, 1].axis('off')
        
        # Set overall title
        fig.suptitle('Impact of Contextual Factors on Sarcasm Detection', fontsize=16, fontweight='bold')
        
        plt.tight_layout()
        
        # Save figure
        output_path = os.path.join(self.output_dir, 'contextual_factors.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved contextual factors visualization to {output_path}")
        
        return fig
    
    def visualize_failure_modes(self):
        """
        Visualize common failure modes in sarcasm detection.
        
        Returns:
            matplotlib.figure.Figure: The generated figure
        """
        if 'failure_modes' not in self.analysis_results:
            print("Run analyze_failure_modes first.")
            return None
        
        failure_modes = self.analysis_results['failure_modes']
        detailed_failures = self.analysis_results['detailed_failures']
        
        # Create figure with multiple subplots
        fig, axs = plt.subplots(2, 1, figsize=(12, 10))
        
        # 1. Bar chart of failure modes by count
        sorted_modes = failure_modes.sort_values('count', ascending=False)
        
        bars = axs[0].bar(
            sorted_modes['failure_mode'],
            sorted_modes['count'],
            color=sns.color_palette('rocket', len(sorted_modes))
        )
        
        # Add count labels
        for bar in bars:
            height = bar.get_height()
            axs[0].text(
                bar.get_x() + bar.get_width()/2,
                height + 0.1,
                str(int(height)),
                ha='center',
                va='bottom'
            )
        
        axs[0].set_title('Failure Modes by Frequency', fontweight='bold')
        axs[0].set_ylabel('Number of Test Cases')
        axs[0].set_xticklabels(axs[0].get_xticklabels(), rotation=45, ha='right')
        axs[0].grid(axis='y', linestyle='--', alpha=0.7)
        
        # 2. Scatter plot of failure severity vs detection rate
        scatter = axs[1].scatter(
            detailed_failures['avg_detection_rate'],
            detailed_failures['failure_severity'],
            c=detailed_failures['count'],
            s=detailed_failures['count'] * 30,
            cmap='viridis',
            alpha=0.7
        )
        
        # Add colorbar
        cbar = plt.colorbar(scatter, ax=axs[1])
        cbar.set_label('Frequency')
        
        # Add annotations for key points
        for i, row in detailed_failures.head(3).iterrows():
            pattern = row['failure_pattern']
            pattern_short = pattern[:30] + '...' if len(pattern) > 30 else pattern
            
            axs[1].annotate(
                pattern_short,
                xy=(row['avg_detection_rate'], row['failure_severity']),
                xytext=(5, 5),
                textcoords='offset points',
                fontsize=8,
                bbox=dict(boxstyle='round,pad=0.3', fc='white', alpha=0.7)
            )
        
        axs[1].set_title('Failure Severity vs. Detection Rate', fontweight='bold')
        axs[1].set_xlabel('Average Detection Rate')
        axs[1].set_ylabel('Failure Severity')
        axs[1].grid(True, linestyle='--', alpha=0.7)
        axs[1].set_xlim(0, 100)
        
        # Set overall title
        fig.suptitle('Sarcasm Detection Failure Mode Analysis', fontsize=16, fontweight='bold')
        
        plt.tight_layout()
        
        # Save figure
        output_path = os.path.join(self.output_dir, 'failure_modes.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved failure modes visualization to {output_path}")
        
        return fig
    
    def visualize_test_clusters(self):
        """
        Visualize clusters of sarcasm test cases.
        
        Returns:
            matplotlib.figure.Figure: The generated figure
        """
        if 'clustering' not in self.analysis_results:
            print("Run cluster_test_cases first.")
            return None
        
        clustering = self.analysis_results['clustering']
        cluster_summary = clustering['cluster_summary']
        clustered_data = clustering['clustered_data']
        
        # Create figure with multiple subplots
        fig, axs = plt.subplots(2, 2, figsize=(14, 12))
        
        # 1. Scatter plot of clusters (PCA projection)
        scatter = axs[0, 0].scatter(
            clustered_data['pca_x'],
            clustered_data['pca_y'],
            c=clustered_data['cluster'],
            cmap='viridis',
            alpha=0.7,
            s=50
        )
        
        # Add cluster centroids
        for cluster_id in cluster_summary['cluster_id']:
            cluster_points = clustered_data[clustered_data['cluster'] == cluster_id]
            centroid_x = cluster_points['pca_x'].mean()
            centroid_y = cluster_points['pca_y'].mean()
            
            axs[0, 0].scatter(
                centroid_x, centroid_y,
                marker='X',
                color='red',
                s=100,
                edgecolor='black'
            )
            
            axs[0, 0].text(
                centroid_x, centroid_y,
                f"C{cluster_id}",
                fontsize=10,
                fontweight='bold',
                ha='center',
                va='bottom',
                bbox=dict(boxstyle='round,pad=0.3', fc='white', alpha=0.7)
            )
        
        axs[0, 0].set_title('Test Case Clusters (PCA Projection)', fontweight='bold')
        axs[0, 0].set_xlabel('Principal Component 1')
        axs[0, 0].set_ylabel('Principal Component 2')
        axs[0, 0].grid(True, linestyle='--', alpha=0.7)
        
        # Add legend
        legend1 = axs[0, 0].legend(
            *scatter.legend_elements(),
            title="Clusters",
            loc="upper right"
        )
        
        # 2. Cluster performance comparison
        x = np.arange(len(cluster_summary))
        width = 0.25
        
        axs[0, 1].bar(x - width, cluster_summary['avg_detection_rate'], width, label='Detection Rate', color='#2196F3')
        axs[0, 1].bar(x, cluster_summary['avg_intent_alignment'], width, label='Intent Alignment', color='#FF9800')
        axs[0, 1].bar(x + width, cluster_summary['avg_response_appropriateness'], width, label='Response Appropriateness', color='#4CAF50')
        
        axs[0, 1].set_title('Cluster Performance Comparison', fontweight='bold')
        axs[0, 1].set_ylabel('Score')
        axs[0, 1].set_xticks(x)
        axs[0, 1].set_xticklabels([f"C{cluster_id}" for cluster_id in cluster_summary['cluster_id']])
        axs[0, 1].grid(axis='y', linestyle='--', alpha=0.7)
        axs[0, 1].set_ylim(0, 100)
        axs[0, 1].legend()
        
        # 3. Cluster test result breakdown
        pass_rates = cluster_summary['pass_rate'].tolist()
        conditional_rates = cluster_summary['conditional_pass_rate'].tolist()
        fail_rates = cluster_summary['fail_rate'].tolist()
        
        # Create stacked bar chart
        axs[1, 0].bar(x, pass_rates, label='PASS', color='#4CAF50')
        axs[1, 0].bar(x, conditional_rates, bottom=pass_rates, label='CONDITIONAL PASS', color='#FF9800')
        axs[1, 0].bar(x, fail_rates, bottom=[i+j for i,j in zip(pass_rates, conditional_rates)], label='FAIL', color='#F44336')
        
        axs[1, 0].set_title('Test Result Distribution by Cluster', fontweight='bold')
        axs[1, 0].set_ylabel('Percentage')
        axs[1, 0].set_xticks(x)
        axs[1, 0].set_xticklabels([f"C{cluster_id}" for cluster_id in cluster_summary['cluster_id']])
        axs[1, 0].grid(axis='y', linestyle='--', alpha=0.7)
        axs[1, 0].set_ylim(0, 100)
        axs[1, 0].legend()
        
        # 4. Cluster characteristics table
        axs[1, 1].axis('tight')
        axs[1, 1].axis('off')
        
        # Create a table with key cluster characteristics
        table_data = []
        for _, row in cluster_summary.iterrows():
            # Format row data
            cluster_id = f"Cluster {row['cluster_id']}"
            size = f"{row['size']} tests"
            performance = f"{row['performance_score']:.1f}%"
            characteristics = row['cluster_characterization']
            
            table_data.append([cluster_id, size, performance, characteristics])
        
        # Create the table
        table = axs[1, 1].table(
            cellText=table_data,
            colLabels=['Cluster', 'Size', 'Performance', 'Characteristics'],
            loc='center',
            cellLoc='center',
            colWidths=[0.15, 0.15, 0.15, 0.55]
        )
        
        # Style the table
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 1.5)
        
        # Color the header
        for j, cell in enumerate(table._cells[(0, j)] for j in range(len(table_data[0]))):
            cell.set_facecolor('#E0E0E0')
            cell.set_text_props(weight='bold')
        
        axs[1, 1].set_title('Cluster Characteristics', fontweight='bold')
        
        # Set overall title
        fig.suptitle('Sarcasm Detection Test Case Clustering Analysis', fontsize=16, fontweight='bold')
        
        plt.tight_layout()
        
        # Save figure
        output_path = os.path.join(self.output_dir, 'test_clusters.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved test clusters visualization to {output_path}")
        
        return fig
    
    def visualize_improvement_opportunities(self):
        """
        Visualize sarcasm detection improvement opportunities.
        
        Returns:
            matplotlib.figure.Figure: The generated figure
        """
        if 'improvement_opportunities' not in self.analysis_results:
            print("Run identify_improvement_opportunities first.")
            return None
        
        opportunities = self.analysis_results['improvement_opportunities']
        
        # Create figure
        fig, axs = plt.subplots(2, 1, figsize=(12, 10))
        
        # 1. Priority breakdown
        priority_counts = opportunities['priority'].value_counts()
        
        # Color mapping
        priority_colors = {
            'High': '#F44336',
            'Medium': '#FF9800',
            'Low': '#4CAF50'
        }
        
        # Create pie chart
        wedges, texts, autotexts = axs[0].pie(
            priority_counts,
            labels=priority_counts.index,
            autopct='%1.1f%%',
            startangle=90,
            colors=[priority_colors.get(p, '#9E9E9E') for p in priority_counts.index]
        )
        
        # Style the text and labels
        for text in texts:
            text.set_fontweight('bold')
        
        for autotext in autotexts:
            autotext.set_fontweight('bold')
            autotext.set_color('white')
        
        axs[0].set_title('Improvement Opportunities by Priority', fontweight='bold')
        axs[0].axis('equal')  # Equal aspect ratio ensures a circular pie chart
        
        # 2. Improvement areas breakdown
        # Extract improvement area type from the full area
        def extract_area_type(area):
            if ':' in area:
                return area.split(':')[0].strip()
            else:
                return area
        
        opportunities['area_type'] = opportunities['improvement_area'].apply(extract_area_type)
        
        # Count by area type
        area_counts = opportunities['area_type'].value_counts()
        
        # Create horizontal bar chart
        bars = axs[1].barh(
            area_counts.index,
            area_counts.values,
            color=sns.color_palette('viridis', len(area_counts))
        )
        
        # Add count labels
        for bar in bars:
            width = bar.get_width()
            axs[1].text(
                width + 0.1,
                bar.get_y() + bar.get_height()/2,
                str(int(width)),
                va='center'
            )
        
        axs[1].set_title('Improvement Opportunities by Area', fontweight='bold')
        axs[1].set_xlabel('Number of Opportunities')
        axs[1].grid(axis='x', linestyle='--', alpha=0.7)
        
        # Set overall title
        fig.suptitle('Sarcasm Detection Improvement Opportunities', fontsize=16, fontweight='bold')
        
        # Add recommendations as text
        high_priority = opportunities[opportunities['priority'] == 'High']
        if not high_priority.empty:
            recommendations = "\n".join([
                f"• {row['improvement_area']}: {row['description'][:80]}..."
                for _, row in high_priority.head(3).iterrows()
            ])
            
            fig.text(
                0.5, 0.01,
                f"Top Recommendations:\n{recommendations}",
                ha='center',
                va='bottom',
                fontsize=10,
                bbox=dict(boxstyle='round,pad=0.5', facecolor='#F5F5F5')
            )
        
        plt.tight_layout(rect=[0, 0.05, 1, 0.95])
        
        # Save figure
        output_path = os.path.join(self.output_dir, 'improvement_opportunities.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved improvement opportunities visualization to {output_path}")
        
        return fig
    
    def run_all_analyses(self):
        """
        Run all sarcasm detection analyses.
        
        Returns:
            dict: All analysis results
        """
        print("Running sarcasm detection analyses...")
        
        # Run pattern performance analysis
        pattern_perf = self.analyze_pattern_performance()
        print("Pattern performance analysis complete.")
        
        # Run contextual factors analysis
        context_factors = self.analyze_contextual_factors()
        print("Contextual factors analysis complete.")
        
        # Run cultural variations analysis
        cultural_vars = self.analyze_cultural_variations()
        print("Cultural variations analysis complete.")
        
        # Run failure modes analysis
        failure_modes = self.analyze_failure_modes()
        print("Failure modes analysis complete.")
        
        # Run test case clustering
        clusters = self.cluster_test_cases()
        print("Test case clustering complete.")
        
        # Identify improvement opportunities
        opportunities = self.identify_improvement_opportunities()
        print("Improvement opportunities identification complete.")
        
        # Create visualizations
        self.visualize_pattern_performance()
        self.visualize_contextual_factors()
        self.visualize_failure_modes()
        self.visualize_test_clusters()
        self.visualize_improvement_opportunities()
        
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
        
        print(f"Exporting sarcasm detection analysis results as {format}...")
        
        if format == 'csv':
            # Export DataFrames as CSV
            for name, data in self.analysis_results.items():
                if isinstance(data, pd.DataFrame):
                    output_path = os.path.join(self.output_dir, f"{name}.csv")
                    data.to_csv(output_path, index=False)
                    print(f"Exported {name} to {output_path}")
                elif isinstance(data, dict) and 'cluster_summary' in data:
                    # Handle clustering results
                    output_path = os.path.join(self.output_dir, f"{name}_summary.csv")
                    data['cluster_summary'].to_csv(output_path, index=False)
                    print(f"Exported {name}_summary to {output_path}")
                    
                    output_path = os.path.join(self.output_dir, f"{name}_data.csv")
                    data['clustered_data'].to_csv(output_path, index=False)
                    print(f"Exported {name}_data to {output_path}")
                    
        elif format == 'json':
            import json
            
            # Handle nested and complex data structures
            json_results = {}
            
            for name, data in self.analysis_results.items():
                if isinstance(data, pd.DataFrame):
                    json_results[name] = json.loads(data.to_json(orient='records'))
                elif isinstance(data, dict) and 'cluster_summary' in data:
                    # Handle clustering results
                    json_results[name] = {
                        'cluster_summary': json.loads(data['cluster_summary'].to_json(orient='records')),
                        'optimal_clusters': data['optimal_clusters'],
                        'silhouette_scores': data['silhouette_scores']
                    }
                    # Don't include full clustered data to keep file size reasonable
                elif isinstance(data, dict) and 'impact_table' in list(data.values())[0]:
                    # Handle contextual factors
                    json_factors = {}
                    for factor_name, factor_data in data.items():
                        json_factors[factor_name] = {
                            'impact_table': json.loads(factor_data['impact_table'].to_json(orient='records')),
                            'impact_summary': factor_data['impact_summary']
                        }
                    json_results[name] = json_factors
                else:
                    # Try to convert other data types
                    try:
                        json_results[name] = data
                    except:
                        json_results[name] = str(data)
            
            # Write to file
            output_path = os.path.join(self.output_dir, "sarcasm_analysis.json")
            
            with open(output_path, 'w') as f:
                json.dump(json_results, f, indent=2, default=str)
            
            print(f"Exported all analysis results to {output_path}")
        
        else:
            print(f"Unsupported format: {format}. Use 'csv' or 'json'.")


# Example usage
if __name__ == "__main__":
    analyzer = SarcasmDetectionAnalyzer(data_dir='./data')
    analyzer.run_all_analyses()
    analyzer.export_results(format='json')
    
    print("Sarcasm detection analysis complete!")

"""
SUMMARY:
This code implements a comprehensive Sarcasm Detection Analyzer for the Neuron Evaluation Framework. The analyzer provides detailed analysis of sarcasm detection performance, identifies issues, and generates improvement recommendations. Key functionality includes:

1. Pattern Performance Analysis - Evaluates performance across different sarcasm patterns to identify strengths and weaknesses.

2. Contextual Factors Analysis - Examines how context dependency, cultural specificity, and sarcasm intensity impact detection performance.

3. Cultural Variations Analysis - Analyzes performance across culturally-specific sarcasm patterns to identify cultural gaps.

4. Failure Mode Analysis - Identifies common patterns in sarcasm detection failures to target improvements.

5. Test Case Clustering - Groups similar test cases to discover patterns and relationships in the data.

6. Improvement Opportunity Identification - Generates targeted recommendations for enhancing sarcasm detection.

7. Visualizations - Creates detailed visualizations of all analysis aspects for easy interpretation.

This analyzer addresses one of the highest priority improvement areas for the Neuron Framework, specifically enhancing "Subtle Sarcasm Recognition" and "Cultural Sarcasm Variations" which were identified as critical for production readiness.
"""
