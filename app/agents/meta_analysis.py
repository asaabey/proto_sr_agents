from typing import List, Dict, Optional
import math
import os
from pathlib import Path
from app.models.schemas import Manuscript, MetaResult, OutcomeEffect, StudyRecord

# Optional plotting dependencies
try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    import numpy as np
    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False

def _fixed_effect(effects: List[OutcomeEffect]) -> MetaResult:
    w = [1.0/e.var for e in effects]
    y = [e.effect for e in effects]
    W = sum(w)
    ybar = sum(wi*yi for wi, yi in zip(w, y)) / W
    se = math.sqrt(1.0/W)
    ci_low = ybar - 1.96*se
    ci_high = ybar + 1.96*se
    # Cochran's Q
    Q = sum(wi*(yi - ybar)**2 for wi, yi in zip(w, y))
    # I^2
    k = len(effects)
    I2 = max(0.0, (Q - (k-1)) / Q) * 100.0 if Q > 0 and k > 1 else 0.0
    return MetaResult(outcome="", k=k, model="fixed", pooled=ybar, se=se, ci_low=ci_low, ci_high=ci_high, Q=Q, I2=I2)

def _random_effect(effects: List[OutcomeEffect]) -> MetaResult:
    # DerSimonian-Laird
    w_fixed = [1.0/e.var for e in effects]
    y = [e.effect for e in effects]
    W = sum(w_fixed)
    ybar_fixed = sum(wi*yi for wi, yi in zip(w_fixed, y)) / W
    Q = sum(wi*(yi - ybar_fixed)**2 for wi, yi in zip(w_fixed, y))
    k = len(effects)
    C = W - sum(wi**2 for wi in w_fixed) / W
    tau2 = max(0.0, (Q - (k-1)) / C) if k > 1 else 0.0
    w_star = [1.0/(e.var + tau2) for e in effects]
    W_star = sum(w_star)
    ybar = sum(wi*yi for wi, yi in zip(w_star, y)) / W_star
    se = math.sqrt(1.0/W_star)
    ci_low = ybar - 1.96*se
    ci_high = ybar + 1.96*se
    # I^2 on fixed Q
    I2 = max(0.0, (Q - (k-1)) / Q) * 100.0 if Q > 0 and k > 1 else 0.0
    return MetaResult(outcome="", k=k, model="random", pooled=ybar, se=se, ci_low=ci_low, ci_high=ci_high, Q=Q, I2=I2, tau2=tau2)

def _generate_forest_plot(outcome: str, effects: List[OutcomeEffect], fe_result: MetaResult, re_result: MetaResult, study_names: List[str]) -> Optional[str]:
    """Generate forest plot for meta-analysis results"""
    if not PLOTTING_AVAILABLE:
        return None
        
    try:
        plt.style.use('default')
        fig, ax = plt.subplots(1, 1, figsize=(10, max(6, len(effects) + 2)))
        
        # Individual study results
        y_positions = []
        for i, (effect, study) in enumerate(zip(effects, study_names)):
            y_pos = len(effects) - i
            y_positions.append(y_pos)
            
            # Calculate CI for individual studies
            se = math.sqrt(effect.var)
            ci_low = effect.effect - 1.96 * se
            ci_high = effect.effect + 1.96 * se
            
            # Plot individual study
            ax.plot([ci_low, ci_high], [y_pos, y_pos], 'b-', linewidth=1)
            ax.plot(effect.effect, y_pos, 'bs', markersize=8)
            ax.text(-0.1, y_pos, study, ha='right', va='center', transform=ax.get_yaxis_transform())
        
        # Add pooled estimates
        ax.axhline(y=0.5, color='gray', linestyle='--', alpha=0.5)
        
        # Fixed effect
        ax.plot([fe_result.ci_low, fe_result.ci_high], [0.3, 0.3], 'r-', linewidth=2)
        ax.plot(fe_result.pooled, 0.3, 'rD', markersize=10)
        ax.text(-0.1, 0.3, f'Fixed Effect (I²={fe_result.I2:.1f}%)', ha='right', va='center', transform=ax.get_yaxis_transform(), weight='bold')
        
        # Random effect
        ax.plot([re_result.ci_low, re_result.ci_high], [0.1, 0.1], 'g-', linewidth=2)
        ax.plot(re_result.pooled, 0.1, 'gD', markersize=10)
        ax.text(-0.1, 0.1, f'Random Effect (τ²={re_result.tau2:.3f})', ha='right', va='center', transform=ax.get_yaxis_transform(), weight='bold')
        
        # Null line
        ax.axvline(x=0, color='black', linestyle='-', alpha=0.8)
        
        # Formatting
        ax.set_ylim(-0.2, len(effects) + 0.5)
        ax.set_xlabel(f'Effect Size ({effects[0].effect_metric})')
        ax.set_title(f'Forest Plot: {outcome}', weight='bold', pad=20)
        ax.grid(True, alpha=0.3)
        
        # Save plot
        artifacts_dir = Path("artifacts")
        artifacts_dir.mkdir(exist_ok=True)
        filename = f"forest_{outcome.lower().replace(' ', '_').replace('≥', 'gte')}.png"
        filepath = artifacts_dir / filename
        
        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return str(filepath)
        
    except Exception as e:
        print(f"Error generating forest plot for {outcome}: {e}")
        return None

def _generate_funnel_plot(outcome: str, effects: List[OutcomeEffect]) -> Optional[str]:
    """Generate funnel plot for publication bias assessment"""
    if not PLOTTING_AVAILABLE:
        return None
        
    try:
        fig, ax = plt.subplots(1, 1, figsize=(8, 6))
        
        # Extract data
        effect_sizes = [e.effect for e in effects]
        se_values = [math.sqrt(e.var) for e in effects]
        
        # Plot individual studies
        ax.scatter(effect_sizes, se_values, s=60, alpha=0.7, c='blue')
        
        # Add reference lines (approximate)
        if effect_sizes:
            mean_effect = np.mean(effect_sizes)
            se_range = np.linspace(0, max(se_values) * 1.1, 100)
            
            # 95% confidence region
            ax.plot(mean_effect + 1.96 * se_range, se_range, 'r--', alpha=0.5, label='95% CI')
            ax.plot(mean_effect - 1.96 * se_range, se_range, 'r--', alpha=0.5)
            
        # Formatting
        ax.invert_yaxis()  # Funnel plots have SE decreasing upward
        ax.set_xlabel(f'Effect Size ({effects[0].effect_metric})')
        ax.set_ylabel('Standard Error')
        ax.set_title(f'Funnel Plot: {outcome}', weight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        # Save plot
        artifacts_dir = Path("artifacts")
        artifacts_dir.mkdir(exist_ok=True)
        filename = f"funnel_{outcome.lower().replace(' ', '_').replace('≥', 'gte')}.png"
        filepath = artifacts_dir / filename
        
        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return str(filepath)
        
    except Exception as e:
        print(f"Error generating funnel plot for {outcome}: {e}")
        return None

def run(manuscript: Manuscript) -> List[MetaResult]:
    # Group effects by outcome name; expect effect on log scale if log metric
    outcomes: Dict[str, List[OutcomeEffect]] = {}
    study_lookup: Dict[str, List[str]] = {}  # outcome -> study names
    
    for s in manuscript.included_studies:
        for o in s.outcomes:
            outcomes.setdefault(o.name, []).append(o)
            study_lookup.setdefault(o.name, []).append(s.study_id)

    results: List[MetaResult] = []
    for outcome, effects in outcomes.items():
        if len(effects) < 2:
            continue  # need at least 2 studies to meta-analyze
            
        fe = _fixed_effect(effects)
        re = _random_effect(effects)
        fe.outcome = outcome
        re.outcome = outcome
        
        # Generate visualizations
        study_names = study_lookup[outcome]
        forest_path = _generate_forest_plot(outcome, effects, fe, re, study_names)
        funnel_path = _generate_funnel_plot(outcome, effects)
        
        # Add file paths to evidence if plots were generated
        if forest_path:
            fe.evidence = {"forest_plot": forest_path}
            re.evidence = {"forest_plot": forest_path}
        if funnel_path:
            if hasattr(fe, 'evidence') and fe.evidence:
                fe.evidence["funnel_plot"] = funnel_path  
                re.evidence["funnel_plot"] = funnel_path
            else:
                fe.evidence = {"funnel_plot": funnel_path}
                re.evidence = {"funnel_plot": funnel_path}
        
        results.extend([fe, re])
    
    return results
