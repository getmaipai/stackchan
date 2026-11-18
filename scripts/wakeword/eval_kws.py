"""Measure long-negative false accepts and held-out positive recall."""
import argparse, json
from pathlib import Path
import numpy as np
from features import SAMPLE_RATE, features, fix_length, read_wav
from train_kws import _sigmoid


def evaluate(model_path, negatives_dir, positives_dir=None):
    m=np.load(model_path); threshold=float(m['threshold']); ts=[threshold, min(1,threshold+.1), min(1,threshold+.2), min(1,threshold+.3)]
    def score(a): return float(_sigmoid(np.maximum(features(a).reshape(1,-1)@m['w1']+m['b1'],0)@m['w2']+m['b2'])[0,0])
    counts=np.zeros(len(ts),dtype=int); seconds=0
    for path in sorted(Path(negatives_dir).glob('*.wav')):
        a,rate=read_wav(path); a=fix_length(a,rate) if len(a)<SAMPLE_RATE else a
        if rate != SAMPLE_RATE: a=fix_length(a,rate) if len(a)<SAMPLE_RATE else np.interp(np.arange(int(len(a)*SAMPLE_RATE/rate))*rate/SAMPLE_RATE,np.arange(len(a)),a).astype(np.float32)
        seconds += len(a)/SAMPLE_RATE
        for start in range(0,max(1,len(a)-SAMPLE_RATE+1),1600):
            p=score(a[start:start+SAMPLE_RATE]); counts += p>=np.asarray(ts)
    recall=None
    if positives_dir:
        vals=[]
        for path in sorted(Path(positives_dir).glob('*.wav')):
            a,rate=read_wav(path); vals.append(score(fix_length(a,rate)))
        recall=float(np.mean(np.asarray(vals)>=threshold)) if vals else 0.0
    result={'false_accepts_per_hour':[float(c*3600/max(seconds,1e-9)) for c in counts], 'thresholds':ts, 'recall':recall}
    print(json.dumps(result,sort_keys=True)); return result

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('model'); p.add_argument('--negatives',required=True); p.add_argument('--positives'); p.add_argument('--output'); a=p.parse_args(); res=evaluate(a.model,a.negatives,a.positives)
    if a.output: Path(a.output).write_text(json.dumps(res,sort_keys=True)+'\n')
