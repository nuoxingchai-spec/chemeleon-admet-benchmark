"""Aggregate immutable experiment artifacts into paper tables and an auditable source bundle."""
from pathlib import Path
import json,hashlib,re,shutil,subprocess,sys,os
import numpy as np,pandas as pd

OUT=Path(__file__).resolve().parents[1];P=OUT/'paper'
E=Path(os.environ.get('ADMET_EXPERIMENT_ROOT',str(OUT/'evidence')))
OLD=Path(os.environ.get('ADMET_BIB_SOURCE',str(OUT/'paper')))
TECTONIC=Path(os.environ.get('TECTONIC_EXE',shutil.which('tectonic') or 'tectonic'))
claims=[];inputs={}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def csv(name):
    p=E/'reports'/name;inputs['evidence/reports/'+name]=sha(p);return pd.read_csv(p)
def fmt(v,n=3):return f'{float(v):.{n}f}'
def macro(name,value,source,selection):
    values.append(r'\newcommand{\%s}{%s}'%(name,value))
    claims.append(dict(id=name,rendered=value,source=source,selection=selection,source_sha256=sha(E/'reports'/source)))
def table(name,caption,label,spec,header,rows):
    begin='\\begin{tabular}{'+spec+'}';end=r'\end{tabular}'
    if name=='secondary':begin=r'\begin{tabular*}{.92\linewidth}{@{\extracolsep{\fill}}lrrr}';end=r'\end{tabular*}'
    content='\\begin{table}[t]\n\\centering\n\\caption{'+caption+'}\\label{'+label+'}\n\\small\n'+begin+'\n\\toprule\n'+header+r'\\'+'\n\\midrule\n'+'\n'.join(rows)+'\n\\bottomrule\n'+end+'\n\\end{table}\n'
    (P/'tables'/f'{name}.tex').write_text(content,encoding='utf-8')

def main():
    global values
    values=[];(P/'tables').mkdir(exist_ok=True);(P/'figures').mkdir(exist_ok=True)
    completion=json.loads((E/'reports/FINAL_DELIVERY_VALIDATION.json').read_text())
    if completion['state']!='COMPLETE':raise RuntimeError('Experiment delivery incomplete')
    for name in ['paired_initialization_effects','lowdata_learning_curves']:
        source=E/'reports/figures'/f'{name}.pdf';shutil.copy2(source,P/'figures'/source.name);inputs['evidence/reports/figures/'+source.name]=sha(source)
    joint=csv('joint_group_seed_bootstrap.csv')
    for ep,prefix in [('herg','Herg'),('dili','Dili'),('ames','Ames')]:
        r=joint[(joint.endpoint==ep)&(joint.contrast=='pretrained-random')].iloc[0]
        macro(prefix+'Delta',fmt(r.observed_delta),'joint_group_seed_bootstrap.csv',ep+'/pretrained-random/observed_delta')
        macro(prefix+'CI','['+fmt(r.ci_low)+', '+fmt(r.ci_high)+']','joint_group_seed_bootstrap.csv',ep+'/pretrained-random/95pct_CI')
    for ep,contrast,key,col in [('herg','pretrained-random','HergP','p_bonferroni'),('herg','pretrained-scratch','HergScratchP','p_bonferroni'),('herg','pretrained-random_dropout','HergDropP','p_bonferroni'),('dili','pretrained-scratch','DiliScratchQ','q_bh'),('dili','pretrained-scratch','DiliScratchP','p_bonferroni')]:
        macro(key,fmt(joint[(joint.endpoint==ep)&(joint.contrast==contrast)].iloc[0][col]),'joint_group_seed_bootstrap.csv',ep+'/'+contrast+'/'+col)
    m=csv('all_graph_seed_metrics.csv');m=m[(m.family=='global_robustness')&(m.role=='test')].copy();m['model']=np.where(m.dropout.fillna(0)>0,'random_dropout',m.arm)
    if len(m)!=300:raise RuntimeError('Graph matrix differs')
    means=m.groupby(['endpoint','model'])[['auc','ap','pr_auc','mcc','brier','ece']].mean()
    means.to_csv(OUT/'reports/paper_graph_metric_means.csv')
    names={'pretrained':'Pretrained','random':'Matched','random_dropout':r'Matched+Dropout','scratch':'Scratch'};eps={'herg':'hERG','dili':'DILI','ames':'Ames'};rows=[]
    for ep in ['herg','dili','ames']:
        for i,arm in enumerate(['pretrained','random','random_dropout','scratch']):
            a=means.loc[(ep,arm)]
            rows.append((eps[ep] if i==0 else '')+' & '+names[arm]+' & '+' & '.join(fmt(a[k]) for k in a.index)+r'\\')
            for metric in a.index:claims.append(dict(id=f'T2.{ep}.{arm}.{metric}',value=float(a[metric]),source='all_graph_seed_metrics.csv',selection=f'family=global_robustness,role=test,{ep},{arm}; arithmetic mean over25fits',source_sha256=sha(E/'reports/all_graph_seed_metrics.csv')))
        if ep!='ames':rows.append(r'\midrule')
    table('graph_metrics','Primary graph metrics: per-seed means over five partitions and five seeds (25 fits/cell), not ensemble metrics. AUROC/AP/PR-AUC/MCC are higher-is-better; Brier/ECE lower-is-better. PR-AUC is trapezoidal, distinct from AP.','tab:metrics','llrrrrrr',r'Endpoint & Model & AUROC & AP & PR-AUC & MCC & Brier & ECE',rows)
    rows=[r'hERG & 655 & 615 & 606 & 9\\',r'DILI & 475 & 474 & 474 & 0\\',r'Ames & 7,278 & 7,248 & 7,246 & 2\\']
    table('provenance','Local endpoint lineage. Unique counts are after structural standardization; conflicting groups are removed as whole groups. Official file identity does not establish every upstream assay-label rule.','tab:provenance','lrrrr',r'Endpoint & Source rows & Unique keys & Retained & Conflict groups',rows)
    classical=csv('all_classical_seed_metrics.csv');c=classical[classical.role=='test'].groupby(['endpoint','model']).auc.mean()
    hf=csv('chemberta_ensemble_metrics.csv');hf=hf.set_index(['endpoint','model'])
    rows=[r'\multicolumn{4}{l}{A: Classical references; five partitions (RF:25 fits; others:5)}\\']
    for arm,name in [('rf','Random forest'),('histgb','Histogram GB'),('logreg','Logistic regression')]:
        rows.append(name+' & '+' & '.join(fmt(c.loc[(ep,arm)]) for ep in ['herg','dili','ames'])+r'\\')
    rows += [r'\midrule',r'\multicolumn{4}{l}{B: ChemBERTa; partition7301 only, three seeds at $10^{-4}$}\\']
    for arm in ['pretrained','random','scratch']:rows.append(names[arm]+' & '+' & '.join(fmt(hf.loc[(ep,arm),'seed_mean_auc']) for ep in ['herg','dili','ames'])+r'\\')
    table('secondary','Secondary per-seed AUROC references. Panel A shares the five primary partitions; panel B has only one of them. Within each panel all listed fixed settings are retained. Differing tuning budgets and populations preclude a joint ranking.','tab:secondary','lrrr',r'Model & hERG & DILI & Ames',rows)
    for arm,prefix in [('pretrained','HfHerg'),('random','HfRandom')]:
        for col,suffix in [('seed_mean_auc','Seed'),('ensemble_auc','Ensemble')]:
            macro(prefix+suffix,fmt(hf.loc[('herg',arm),col]),'chemberta_ensemble_metrics.csv',f'herg/{arm}/{col}')
    lr=csv('graph_equal_tuning_selected_metrics.csv')
    for arm,suffix in [('pretrained','Pre'),('random','Random')]:
        macro('HergTuned'+suffix,fmt(lr[(lr.endpoint=='herg')&(lr.arm==arm)].iloc[0].test_seed_mean_auc),'graph_equal_tuning_selected_metrics.csv','herg/'+arm+'/selected_rate_test_seed_mean_auc')
    split=csv('split_effect_and_population_diagnostics.csv');d=split[split.endpoint=='herg'].seed_mean_delta_auc
    for key,v in [('HergSplitMin',d.min()),('HergSplitMax',d.max())]:macro(key,fmt(v),'split_effect_and_population_diagnostics.csv','herg/split_mean_delta_range')
    low=csv('lowdata_joint_sampling_training_test_bootstrap.csv');low=low[low.contrast=='pretrained-random'].sort_values('train_n')
    macro('LowDeltas',', '.join(fmt(v) for v in low.observed_delta),'lowdata_joint_sampling_training_test_bootstrap.csv','pretrained-random,ordered_n50_100_200_400')
    r=low[low.train_n==50].iloc[0];macro('LowFiftyCI','['+fmt(r.ci_low)+', '+fmt(r.ci_high)+']','lowdata_joint_sampling_training_test_bootstrap.csv','n50/pretrained-random/95pct_CI')
    drift=csv('raw_to_canonical_evaluation_drift.csv');bf=drift[drift.raw_training_precision=='bf16'];test=bf[bf.role=='test']
    for key,v in [('MaxProbDrift',bf.max_probability_change.max()),('TestDriftMin',test.canonical_minus_raw_auc.min()),('TestDriftMax',test.canonical_minus_raw_auc.max())]:macro(key,fmt(v,6),'raw_to_canonical_evaluation_drift.csv',key)
    precision=csv('precision_initialization_interaction.csv');precision=precision[(precision.endpoint=='herg')&(precision.metric=='auc')].sort_values('seed')
    for key,col in [('FpHergGaps','initialization_gap_fp32_training'),('BfHergGaps','initialization_gap_bf16_training')]:macro(key,'/'.join(fmt(v) for v in precision[col]),'precision_initialization_interaction.csv','herg,auc,seeds1_2_42/'+col)
    cp=csv('coverage_calibration_and_test_uncertainty.csv');cp=cp[(cp.model=='pretrained')&(cp.calibration_role=='calibration')]
    rows=[r'\multicolumn{4}{l}{A: Independent calibration; five-partition mean [min,max]}\\']
    for ep in ['herg','dili','ames']:
        for alpha in [.1,.2]:
            g=cp[(cp.endpoint==ep)&(cp.alpha==alpha)].coverage
            rows.append(eps[ep]+' & '+fmt(1-alpha,1)+' & '+fmt(g.mean())+' & ['+fmt(g.min())+', '+fmt(g.max())+r']\\')
    fact=csv('calibration_factorial_summary.csv')
    rows += [r'\midrule',r'\multicolumn{4}{l}{B: Ames reuse diagnostic; three trajectories $\times$200 assignments}\\',r'Calibration / evaluation & Target & Coverage & Across-assignment SD\\']
    for reuse,reusename in [('independent_calibration','Independent'),('selection_pool_reused','Reused')]:
        for domain,domainname in [('same_heldout_pool','pool'),('global_scaffold_shift_test','scaffold')]:
            r=fact[(fact.reuse==reuse)&(fact.domain==domain)&(fact.alpha==.1)].iloc[0]
            rows.append(reusename+' / '+domainname+' & 0.9 & '+fmt(r['mean'])+' & '+fmt(r['std'])+r'\\')
            key=('Pool' if domainname=='pool' else 'Shift')+('Independent' if reusename=='Independent' else 'Reused')
            macro(key,fmt(r['mean'],6),'calibration_factorial_summary.csv',f'{reuse}/{domain}/alpha.1/mean')
    table('calibration','Coverage summaries. Panel A ranges are descriptive extrema, not confidence intervals; per-split calibration/test-component intervals are in the evidence index. Panel B holds calibration size fixed. Its SD describes assignments over three fixed trajectories, not a standard error from 600 independent training runs. The two panels have different model/selection designs.','tab:cp','llrr',r'Endpoint / design & Target & Coverage & Variation',rows)
    (P/'values.tex').write_text('\n'.join(values)+'\n',encoding='utf-8')
    source=(OLD/'refs.bib').read_text(encoding='utf-8');entries=re.split(r'(?=^@\w+\{)',source,flags=re.M);lookup={}
    for e in entries:
        m=re.match(r'@\w+\{([^,]+),',e)
        if m:lookup[m[1]]=e.strip()
    keys=re.findall(r'\\cite\{([^}]+)\}',(P/'main.tex').read_text(encoding='utf-8'));keys=list(dict.fromkeys(k for group in keys for k in group.split(',')))
    selected=[]
    for k in keys:
        e=lookup[k]
        if k=='chithrananda2020chemberta':e=e.replace('Grand, Gabriel and others','Grand, Gabriel and Ramsundar, Bharath')
        if k=='zhao2026revisiting':e=e.replace('Zhao, D. and Zhu, Y. and others','Zhao, Donghai and Zhu, Yuchen and Wu, Zhenxing and Wan, Yue and Liu, Xiaonan and Li, Shuaiyan and Xu, Hongxia and Hou, Tingjun and Hsieh, Chang-Yu')
        selected.append(e)
    (P/'refs.bib').write_text('\n\n'.join(selected)+'\n',encoding='utf-8')
    inputs['paper/refs.bib']=sha(OLD/'refs.bib')
    (OUT/'reports/CLAIM_ARTIFACT_MAP.json').write_text(json.dumps({'scope':'aggregate manuscript numbers only; inherited source labels; no independent approval','claims':claims,'inputs_sha256':inputs,'bibliography_entries':len(keys)},indent=2),encoding='utf-8')
    cmd=[str(TECTONIC),'--keep-logs','--keep-intermediates','main.tex']
    r=subprocess.run(cmd,cwd=P,capture_output=True,text=True,encoding='utf-8')
    (OUT/'reports/latex_build_stdout.txt').write_text(r.stdout,encoding='utf-8');(OUT/'reports/latex_build_stderr.txt').write_text(r.stderr,encoding='utf-8')
    if r.returncode:raise RuntimeError('LaTeX failed; see build logs')
    shutil.copy2(P/'main.pdf',OUT/'Auditing_ADMET_Final_Research_Manuscript.pdf')
    print(json.dumps({'pdf':str(OUT/'Auditing_ADMET_Final_Research_Manuscript.pdf'),'bibliography_entries':len(keys),'numeric_claim_records':len(claims),'source_inputs':len(inputs)}))

if __name__=='__main__':main()
