"""Train a small NumPy MLP keyword classifier."""
import argparse
import numpy as np


def _sigmoid(z): return 1 / (1 + np.exp(-np.clip(z, -40, 40)))


def train(dataset, output, export_c=None, seed=0, epochs=60):
    d=np.load(dataset); xt=d['x_train'].reshape(len(d['x_train']),-1); xv=d['x_val'].reshape(len(d['x_val']),-1)
    yt=d['y_train'].astype(np.float32); yv=d['y_val'].astype(np.float32)
    rng=np.random.default_rng(seed); w1=(rng.normal(size=(xt.shape[1],128))*np.sqrt(2/xt.shape[1])).astype(np.float32); b1=np.zeros(128,np.float32); w2=(rng.normal(size=(128,1))*.08).astype(np.float32); b2=np.zeros(1,np.float32)
    params=[w1,b1,w2,b2]; m=[np.zeros_like(p) for p in params]; v=[np.zeros_like(p) for p in params]; step=0; best=None; bestloss=float('inf'); stale=0
    for epoch in range(epochs):
        for ids in np.array_split(rng.permutation(len(xt)), max(1,(len(xt)+31)//32)):
            if not len(ids): continue
            a=xt[ids]; yy=yt[ids,None]; h=np.maximum(a@w1+b1,0); pred=_sigmoid(h@w2+b2); dz=(pred-yy)/len(ids); gw2=h.T@dz; gb2=dz.sum(0); dh=(dz@w2.T)*(h>0); gw1=a.T@dh; gb1=dh.sum(0)
            step+=1
            for i,(p,g) in enumerate(zip(params,[gw1,gb1,gw2,gb2])):
                m[i]=.9*m[i]+.1*g; v[i]=.999*v[i]+.001*g*g; params[i]-=.003*(m[i]/(1-.9**step))/(np.sqrt(v[i]/(1-.999**step))+1e-8)
        pv=_sigmoid(np.maximum(xv@w1+b1,0)@w2+b2).ravel(); loss=float(np.mean(-(yv*np.log(pv+1e-8)+(1-yv)*np.log(1-pv+1e-8))))
        if loss < bestloss-1e-5: bestloss=loss; best=[p.copy() for p in params]; stale=0
        else: stale+=1
        if stale>=8: break
    w1,b1,w2,b2=best
    pv=_sigmoid(np.maximum(xv@w1+b1,0)@w2+b2).ravel(); pt=_sigmoid(np.maximum(xt@w1+b1,0)@w2+b2).ravel()
    pos=pv[yv==1]; threshold=float(np.quantile(pos,.05)) if len(pos) else .5
    np.savez_compressed(output,w1=w1,b1=b1,w2=w2,b2=b2,threshold=np.float32(threshold),sample_rate=np.int32(16000),n_fft=np.int32(400),hop=np.int32(160),n_mels=np.int32(40))
    print(f"train accuracy: {np.mean((pt>=.5)==yt):.3f}; val accuracy: {np.mean((pv>=.5)==yv):.3f}")
    if export_c:
        with open(export_c,'w') as f:
            f.write('#pragma once\n#include <stdint.h>\n')
            for name,arr in [('w1',w1),('b1',b1),('w2',w2),('b2',b2)]:
                scale=float(np.max(np.abs(arr))/127) or 1.0; q=np.clip(np.rint(arr/scale),-127,127).astype(np.int8)
                f.write(f'static const float {name}_scale = {scale:.9g}f;\n')
                f.write(f'static const int8_t {name}[{q.size}] = {{{", ".join(map(str,q.ravel().tolist()))}}};\n')
    return float(np.mean((pv>=.5)==yv))

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('dataset'); p.add_argument('--output',default='model.npz'); p.add_argument('--export-c'); p.add_argument('--seed',type=int,default=0); p.add_argument('--epochs',type=int,default=60); a=p.parse_args(); train(a.dataset,a.output,a.export_c,a.seed,a.epochs)
