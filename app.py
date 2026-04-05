import os
import math
import base64
import io
import threading
import webbrowser
from flask import Flask, render_template, request, jsonify
import numpy as np
from scipy.interpolate import CubicSpline
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

app = Flask(__name__)

def get_correction_factor(volume):
    if volume < 457: return 1.13
    if 457 <= volume <= 470: return 1.13
    if 471 <= volume <= 482: return 1.14
    if 483 <= volume <= 495: return 1.09
    if 496 <= volume <= 508: return 1.04
    if 509 <= volume <= 522: return 1.00
    if 523 <= volume <= 535: return 0.96
    if 536 <= volume <= 546: return 0.93
    if 547 <= volume <= 559: return 0.89
    if 560 <= volume <= 573: return 0.83
    if volume > 573: return 0.83
    return 1.00

def generate_graph(x, y, x_label, y_label, title, x_obc=None, y_line=None):
    fig, ax = plt.subplots(figsize=(6, 4))
    
    # Sort for interpolation
    sort_idx = np.argsort(x)
    x_s = np.array(x)[sort_idx]
    y_s = np.array(y)[sort_idx]
    
    # Polynomial Curve Fitting (Degree 2 for standard Marshall smooth curves)
    p = np.polyfit(x_s, y_s, 2)
    poly_curve = np.poly1d(p)
    x_dense = np.linspace(min(x_s), max(x_s), 1000)
    y_dense = poly_curve(x_dense)
    
    ax.plot(x_dense, y_dense, color='#0f172a', linewidth=2, label='Best-Fit Curve')
    ax.plot(x_s, y_s, 'ro', label='Data Points')
    
    if x_obc is not None:
        ax.axvline(x=x_obc, color='#2563eb', linestyle='--', linewidth=2, label=f'OBC = {x_obc:.2f}%')
    
    if y_line is not None:
        ax.axhline(y=y_line, color='orange', linestyle='--', linewidth=2, label=f'{y_label} = {y_line}')
        
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_title(title)
    ax.grid(True, linestyle=':', alpha=0.6)
    ax.legend(loc='best')
    
    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format='png', dpi=150)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    data = request.json
    gs_bitumen = float(data.get('gs_bitumen', 1.01))
    gs_aggregates = float(data.get('gs_aggregates', 2.65))
    ring_constant = float(data.get('ring_constant', 5.0))
    samples = data.get('samples', [])
    
    if len(samples) < 4:
        return jsonify({'error': 'Minimum 4 samples required'}), 400
        
    results = []
    bitumen_contents = []
    cdm_values = []
    stability_values = []
    vim_values = []
    vfb_values = []
    flow_values = []
    
    for s in samples:
        pct_b = float(s['bitumen'])
        w_air = float(s['wt_air'])
        w_water = float(s['wt_water'])
        proving_divs = float(s['proving_divs'])
        flow_units = float(s['flow_units'])
        thickness = float(s['thickness'])
        
        cdm = w_air / (w_air - w_water)
        vol = (math.pi / 4) * (101.6 / 10)**2 * (thickness / 10)
        cf = get_correction_factor(vol)
        
        stability = proving_divs * ring_constant * cf
        flow_mm = flow_units * 0.25
        
        vb = (pct_b * cdm) / gs_bitumen
        va = ((100 - pct_b) * cdm) / gs_aggregates
        vma = 100 - va
        vim = 100 - vb - va
        vfb = (100 * vb) / vma
        
        results.append({
            'bitumen': pct_b,
            'cdm': round(cdm, 3),
            'vol': round(vol, 2),
            'vb': round(vb, 2),
            'va': round(va, 2),
            'vma': round(vma, 2),
            'vim': round(vim, 2),
            'vfb': round(vfb, 2),
            'stability': round(stability, 2),
            'flow': round(flow_mm, 2)
        })
        
        bitumen_contents.append(pct_b)
        cdm_values.append(cdm)
        stability_values.append(stability)
        vim_values.append(vim)
        vfb_values.append(vfb)
        flow_values.append(flow_mm)
        
    # Sort arrays for processing
    bitumen_contents = np.array(bitumen_contents)
    cdm_values = np.array(cdm_values)
    stability_values = np.array(stability_values)
    vim_values = np.array(vim_values)
    
    sort_idx = np.argsort(bitumen_contents)
    x_s_b = bitumen_contents[sort_idx]
    
    x_dense = np.linspace(np.min(x_s_b), np.max(x_s_b), 5000)
    
    p_cdm = np.poly1d(np.polyfit(x_s_b, cdm_values[sort_idx], 2))
    cdm_dense = p_cdm(x_dense)
    obc_cdm = x_dense[np.argmax(cdm_dense)]
    max_cdm = np.max(cdm_dense)
    
    p_stab = np.poly1d(np.polyfit(x_s_b, stability_values[sort_idx], 2))
    stab_dense = p_stab(x_dense)
    obc_stab = x_dense[np.argmax(stab_dense)]
    max_stab = np.max(stab_dense)
    
    p_vim = np.poly1d(np.polyfit(x_s_b, vim_values[sort_idx], 2))
    vim_dense = p_vim(x_dense)
    val_idx = np.argmin(np.abs(vim_dense - 4.0))
    obc_vim = x_dense[val_idx]
    
    final_obc = np.mean([obc_cdm, obc_stab, obc_vim])
    
    # Graphs
    figs = {
        'cdm': generate_graph(bitumen_contents, cdm_values, 'Binder Content (%)', 'Density (g/cm³)', 'Density vs Binder Content', x_obc=obc_cdm),
        'stab': generate_graph(bitumen_contents, stability_values, 'Binder Content (%)', 'Stability (kg)', 'Stability vs Binder Content', x_obc=obc_stab),
        'vim': generate_graph(bitumen_contents, vim_values, 'Binder Content (%)', 'VIM (%)', 'VIM vs Binder Content', x_obc=obc_vim, y_line=4.0),
        'vfb': generate_graph(bitumen_contents, vfb_values, 'Binder Content (%)', 'VFB (%)', 'VFB vs Binder Content'),
        'flow': generate_graph(bitumen_contents, flow_values, 'Binder Content (%)', 'Flow (mm)', 'Flow vs Binder Content')
    }
    
    return jsonify({
        'table': results,
        'obc_cdm': round(obc_cdm, 2),
        'obc_stab': round(obc_stab, 2),
        'obc_vim': round(obc_vim, 2),
        'obc_avg': round(final_obc, 2),
        'max_cdm': round(max_cdm, 3),
        'max_stab': round(max_stab, 2),
        'graphs': figs
    })

def open_browser():
    webbrowser.open_new('http://localhost:5000/')

if __name__ == '__main__':
    threading.Timer(1.25, open_browser).start()
    app.run(debug=True, use_reloader=False)
