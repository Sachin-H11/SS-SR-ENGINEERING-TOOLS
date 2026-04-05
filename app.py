"""
MARSHALL PRO v1.0
SS & SR Engineering Tools
Sanket Shrivastav & Sachin Ramesh
© 2026 SS & SR Engineering Tools · All Rights Reserved
"""

import webbrowser
import threading
import json
import base64
import io
import random
import string
from datetime import datetime

import numpy as np
from scipy.interpolate import CubicSpline
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# ── Correction Factor Table ────────────────────────────
CF_TABLE = [
    (457, 470, 1.13), (471, 482, 1.14), (483, 495, 1.09),
    (496, 508, 1.04), (509, 522, 1.00), (523, 535, 0.96),
    (536, 546, 0.93), (547, 559, 0.89), (560, 573, 0.83),
]

def get_cf(vol):
    for lo, hi, cf in CF_TABLE:
        if lo <= vol <= hi:
            return cf
    return 1.00

# ── Generate report number ─────────────────────────────
def gen_report_no():
    suffix = ''.join(random.choices(string.digits, k=4))
    return f"MSSR-2026-{suffix}"

# ── Graph generator ────────────────────────────────────
NAVY   = '#0a1628'
GOLD   = '#c9a84c'
WHITE  = '#ffffff'
RED    = '#e74c3c'
LGRAY  = '#6b7fa3'

def make_graph(bp, y_data, y_label, title, color, ref_y=None, obc=None):
    fig, ax = plt.subplots(figsize=(5, 3.5))
    fig.patch.set_facecolor(NAVY)
    ax.set_facecolor('#111f35')

    # Cubic spline
    cs = CubicSpline(bp, y_data)
    x_fine = np.linspace(bp[0], bp[-1], 300)
    y_fine = cs(x_fine)

    # Plot curve
    ax.plot(x_fine, y_fine, color=color, linewidth=2.5, zorder=3)

    # Plot data points
    ax.scatter(bp, y_data, color=GOLD, s=60, zorder=5, linewidths=1.5)

    # OBC vertical line
    if obc is not None:
        ax.axvline(x=obc, color=GOLD, linestyle='--', linewidth=1.5,
                   alpha=0.8, zorder=4, label=f'OBC={obc:.2f}%')

    # Reference horizontal line (VIM=4)
    if ref_y is not None:
        ax.axhline(y=ref_y, color=RED, linestyle=':', linewidth=1.5,
                   alpha=0.8, zorder=4, label=f'={ref_y}%')

    # Styling
    ax.set_xlabel('Binder Content (%)', color=LGRAY, fontsize=8)
    ax.set_ylabel(y_label, color=LGRAY, fontsize=8)
    ax.set_title(title, color=WHITE, fontsize=9, fontweight='bold', pad=8)
    ax.tick_params(colors=LGRAY, labelsize=7)
    ax.spines['bottom'].set_color('#1e3a5f')
    ax.spines['left'].set_color('#1e3a5f')
    ax.spines['top'].set_color('#1e3a5f')
    ax.spines['right'].set_color('#1e3a5f')
    ax.grid(color='#1e3a5f', linewidth=0.5, alpha=0.5)

    y_pad = (max(y_fine) - min(y_fine)) * 0.15
    ax.set_ylim(min(min(y_fine), min(y_data)) - y_pad,
                max(max(y_fine), max(y_data)) + y_pad)
    ax.set_xlim(bp[0] - 0.2, bp[-1] + 0.2)

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=130,
                facecolor=NAVY, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')


# ── Main route ─────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')


# ── Calculate route ────────────────────────────────────
@app.route('/calculate', methods=['POST'])
def calculate():
    data = request.get_json()

    name1  = data.get('name1', '').strip()
    name2  = data.get('name2', '').strip()
    gsb    = float(data['gsb'])
    gsa    = float(data['gsa'])
    prc    = float(data['prc'])
    samples = data['samples']

    # Sort by bitumen %
    samples = sorted(samples, key=lambda s: s['bp'])

    bp  = np.array([s['bp']  for s in samples], dtype=float)
    wa  = np.array([s['wa']  for s in samples], dtype=float)
    ww  = np.array([s['ww']  for s in samples], dtype=float)
    pd  = np.array([s['pd']  for s in samples], dtype=float)
    df  = np.array([s['df']  for s in samples], dtype=float)
    tk  = np.array([s['tk']  for s in samples], dtype=float)
    n   = len(bp)

    # ── Calculations ──────────────────────────────────
    CDM  = wa / (wa - ww)
    vol  = (np.pi / 4) * (101.6 / 10)**2 * (tk / 10)
    CF   = np.array([get_cf(v) for v in vol])
    STAB = pd * prc * CF
    FLOW = df * 0.25
    Vb   = (bp * CDM) / gsb
    Va   = ((100 - bp) * CDM) / gsa
    VMA  = 100 - Va
    VIM  = 100 - Vb - Va
    VFB  = np.where(VMA != 0, (100 * Vb) / VMA, 0)

    # ── Cubic spline ──────────────────────────────────
    x_fine = np.linspace(bp[0], bp[-1], 500)

    cs_cdm  = CubicSpline(bp, CDM)
    cs_stab = CubicSpline(bp, STAB)
    cs_vim  = CubicSpline(bp, VIM)
    cs_vfb  = CubicSpline(bp, VFB)
    cs_flow = CubicSpline(bp, FLOW)

    cdm_f  = cs_cdm(x_fine)
    stab_f = cs_stab(x_fine)
    vim_f  = cs_vim(x_fine)

    # ── OBC ───────────────────────────────────────────
    obc_cdm  = float(x_fine[np.argmax(cdm_f)])
    obc_stab = float(x_fine[np.argmax(stab_f)])

    # VIM = 4% crossing
    vim_diff = np.abs(vim_f - 4.0)
    obc_vim  = float(x_fine[np.argmin(vim_diff)])

    obc      = (obc_cdm + obc_stab + obc_vim) / 3.0
    max_cdm  = float(cs_cdm(obc_cdm))
    max_stab = float(cs_stab(obc_stab))
    obc_vim_val  = float(cs_vim(obc))
    obc_vfb_val  = float(cs_vfb(obc))
    obc_flow_val = float(cs_flow(obc))
    flow_units   = obc_flow_val / 0.25

    # ── Spec check ────────────────────────────────────
    specs = [
        {'name': 'Marshall Stability', 'req': '≥ 340 kg',
         'val': f'{max_stab:.2f} kg', 'pass': max_stab >= 340},
        {'name': 'Flow Value', 'req': '8 – 17 (0.25mm units)',
         'val': f'{flow_units:.1f} units', 'pass': 8 <= flow_units <= 17},
        {'name': 'Air Voids (VIM)', 'req': '3 – 5%',
         'val': f'{obc_vim_val:.2f}%', 'pass': 3 <= obc_vim_val <= 5},
        {'name': 'Voids Filled (VFB)', 'req': '75 – 85%',
         'val': f'{obc_vfb_val:.2f}%', 'pass': 75 <= obc_vfb_val <= 85},
    ]

    # ── Generate graphs ───────────────────────────────
    graph_colors = ['#4a9eff', '#4affb4', '#ff6b6b', '#a78bfa', '#fbbf24']
    titles = [
        'Density vs Binder Content',
        'Stability vs Binder Content',
        'Voids in Mix (VIM) vs Binder Content',
        'VFB vs Binder Content',
        'Flow vs Binder Content',
    ]
    ylabels = ['CDM (g/cm³)', 'Stability (kg)', 'VIM (%)', 'VFB (%)', 'Flow (mm)']
    y_datas = [CDM, STAB, VIM, VFB, FLOW]
    ref_ys  = [None, None, 4, None, None]

    graphs = []
    for i in range(5):
        img = make_graph(
            bp, y_datas[i], ylabels[i], titles[i],
            graph_colors[i], ref_ys[i], obc
        )
        graphs.append(img)

    # ── Computed rows ─────────────────────────────────
    computed = []
    for i in range(n):
        computed.append({
            'sr':   i + 1,
            'bp':   round(float(bp[i]), 2),
            'cdm':  round(float(CDM[i]), 3),
            'vb':   round(float(Vb[i]), 2),
            'va':   round(float(Va[i]), 2),
            'vma':  round(float(VMA[i]), 2),
            'vim':  round(float(VIM[i]), 2),
            'vfb':  round(float(VFB[i]), 2),
            'stab': round(float(STAB[i]), 2),
            'flow': round(float(FLOW[i]), 2),
            'cf':   round(float(CF[i]), 2),
        })

    obs = []
    for i in range(n):
        obs.append({
            'sr':  i + 1,
            'bp':  round(float(bp[i]), 2),
            'wa':  round(float(wa[i]), 2),
            'ww':  round(float(ww[i]), 2),
            'pd':  round(float(pd[i]), 2),
            'df':  round(float(df[i]), 2),
            'tk':  round(float(tk[i]), 2),
        })

    return jsonify({
        'graphs':      graphs,
        'obc_cdm':     round(obc_cdm, 2),
        'obc_stab':    round(obc_stab, 2),
        'obc_vim':     round(obc_vim, 2),
        'obc':         round(obc, 2),
        'max_stab':    round(max_stab, 2),
        'max_cdm':     round(max_cdm, 3),
        'obc_vim_val': round(obc_vim_val, 2),
        'obc_vfb_val': round(obc_vfb_val, 2),
        'obc_flow_val':round(obc_flow_val, 2),
        'specs':       specs,
        'computed':    computed,
        'obs':         obs,
        'name1':       name1,
        'name2':       name2,
        'gsb':         gsb,
        'gsa':         gsa,
        'prc':         prc,
        'report_no':   gen_report_no(),
        'date':        datetime.now().strftime('%d %B %Y'),
        'n_samples':   n,
    })


# ── Auto open browser ──────────────────────────────────
def open_browser():
    webbrowser.open('http://localhost:5000')

if __name__ == '__main__':
    threading.Timer(1.2, open_browser).start()
    print("\n" + "="*50)
    print("  MARSHALL PRO v1.0")
    print("  SS & SR Engineering Tools")
    print("  Sanket Shrivastav & Sachin Ramesh")
    print("="*50)
    print("  Opening browser at http://localhost:5000")
    print("  Press Ctrl+C to stop the server")
    print("="*50 + "\n")
    app.run(debug=False, port=5000)
