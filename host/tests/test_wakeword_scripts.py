import importlib.util
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
WW = ROOT / 'scripts' / 'wakeword'
sys.path.insert(0, str(WW))

def load(name):
    spec=importlib.util.spec_from_file_location(name, WW / (name+'.py'))
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

features=load('features'); maker=load('make_dataset'); trainer=load('train_kws'); evaluator=load('eval_kws')

def tone(freq=440, n=16000):
    t=np.arange(n,dtype=np.float32)/16000
    return .5*np.sin(2*np.pi*freq*t).astype(np.float32)

def test_features_shape_deterministic():
    a=features.features(tone()); b=features.features(tone())
    assert a.shape == (98,40)
    np.testing.assert_array_equal(a,b)

def test_dataset_train_eval(tmp_path):
    pos=tmp_path/'pos'; neg=tmp_path/'neg'; longneg=tmp_path/'longneg'; held=tmp_path/'held'
    for folder in (pos,neg,longneg,held): folder.mkdir()
    for i in range(8): features.write_wav(pos/f'{i}.wav',tone(440+i))
    for i in range(8): features.write_wav(neg/f'{i}.wav',np.random.default_rng(i).normal(0,.08,16000))
    features.write_wav(longneg/'noise.wav',np.random.default_rng(40).normal(0,.08,32000))
    features.write_wav(held/'held.wav',tone(442))
    one=tmp_path/'one.npz'; two=tmp_path/'two.npz'
    maker.build(pos,one,neg,seed=19); maker.build(pos,two,neg,seed=19)
    d1=np.load(one); d2=np.load(two)
    for key in d1.files: np.testing.assert_array_equal(d1[key],d2[key])
    assert set(d1['y_train'])=={0,1} and set(d1['y_val'])=={0,1}
    model=tmp_path/'model.npz'; acc=trainer.train(one,model,seed=4,epochs=60)
    assert acc > .9
    result=evaluator.evaluate(model,longneg,held)
    assert isinstance(result['false_accepts_per_hour'][0],float)
    assert 0 <= result['recall'] <= 1
