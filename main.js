document.addEventListener('DOMContentLoaded', () => {

    // Splash Screen Removal
    setTimeout(() => {
        const splash = document.getElementById('splash-screen');
        if (splash) {
            splash.classList.add('fade-out');
            setTimeout(() => splash.remove(), 800); // Remove from DOM after fade
        }
    }, 4800);

    const addRowBtn = document.getElementById('add-row-btn');
    const tableBody = document.querySelector('#input-table tbody');
    const generateBtn = document.getElementById('generate-btn');
    const errorMsg = document.getElementById('error-msg');

    // Manage Delete buttons state
    function updateDeleteButtons() {
        const rows = tableBody.querySelectorAll('tr');
        const btns = tableBody.querySelectorAll('.btn-del');
        if (rows.length <= 4) {
            btns.forEach(btn => btn.disabled = true);
        } else {
            btns.forEach(btn => btn.disabled = false);
        }
    }

    // Add Row
    addRowBtn.addEventListener('click', () => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><input type="number" step="0.1" value=""></td>
            <td><input type="number" step="0.1" value=""></td>
            <td><input type="number" step="0.1" value=""></td>
            <td><input type="number" step="0.1" value=""></td>
            <td><input type="number" step="0.1" value=""></td>
            <td><input type="number" step="0.1" value="63.5"></td>
            <td><button type="button" class="btn-del">X</button></td>
        `;
        tableBody.appendChild(tr);
        updateDeleteButtons();
    });

    // Delete Row
    tableBody.addEventListener('click', (e) => {
        if (e.target.classList.contains('btn-del')) {
            if (tableBody.querySelectorAll('tr').length > 4) {
                e.target.closest('tr').remove();
                updateDeleteButtons();
            }
        }
    });

    function showError(msg) {
        errorMsg.textContent = msg;
        errorMsg.classList.remove('hidden');
    }

    function clearErrors() {
        errorMsg.classList.add('hidden');
        document.querySelectorAll('.invalid').forEach(el => el.classList.remove('invalid'));
    }

    // Generate Report
    generateBtn.addEventListener('click', async () => {
        clearErrors();
        let hasError = false;

        const name1 = document.getElementById('name1');
        if (!name1.value.trim()) {
            hasError = true;
            name1.classList.add('invalid');
            showError("Please enter your name");
            return;
        }

        const rows = tableBody.querySelectorAll('tr');
        if (rows.length < 4) {
            showError("Minimum 4 samples required");
            return;
        }

        const samples = [];
        rows.forEach(row => {
            const inputs = row.querySelectorAll('input');
            let rowValid = true;
            inputs.forEach(inp => {
                if (inp.value.trim() === '') {
                    inp.classList.add('invalid');
                    rowValid = false;
                    hasError = true;
                }
            });

            if (rowValid) {
                samples.push({
                    bitumen: inputs[0].value,
                    wt_air: inputs[1].value,
                    wt_water: inputs[2].value,
                    proving_divs: inputs[3].value,
                    flow_units: inputs[4].value,
                    thickness: inputs[5].value,
                });
            }
        });

        if (hasError) {
            showError("Please fill all highlighted fields");
            return;
        }

        // Gather constants
        const gs_bitumen = document.getElementById('gs_bitumen').value;
        const gs_aggregates = document.getElementById('gs_aggregates').value;
        const ring_constant = document.getElementById('ring_constant').value;

        // Perform request
        generateBtn.disabled = true;
        generateBtn.textContent = 'CALCULATING...';

        try {
            const response = await fetch('/calculate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    gs_bitumen,
                    gs_aggregates,
                    ring_constant,
                    samples
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Server calculation error');
            }

            renderResults(data);
            populatePrintLayout(data, name1.value, samples);

        } catch (err) {
            showError(err.message);
        } finally {
            generateBtn.disabled = false;
            generateBtn.textContent = 'GENERATE REPORT';
        }
    });

    function renderResults(data) {
        document.getElementById('results-screen').classList.remove('hidden');

        // Hide graphs initially
        const graphIds = ['graph-cdm', 'graph-stab', 'graph-vim', 'graph-vfb', 'graph-flow'];
        graphIds.forEach(id => document.getElementById(id).classList.remove('visible'));
        document.getElementById('final-results-box').classList.remove('visible');

        // Set Images
        document.querySelector('#graph-cdm img').src = 'data:image/png;base64,' + data.graphs.cdm;
        document.querySelector('#graph-stab img').src = 'data:image/png;base64,' + data.graphs.stab;
        document.querySelector('#graph-vim img').src = 'data:image/png;base64,' + data.graphs.vim;
        document.querySelector('#graph-vfb img').src = 'data:image/png;base64,' + data.graphs.vfb;
        document.querySelector('#graph-flow img').src = 'data:image/png;base64,' + data.graphs.flow;

        // Set Texts
        document.getElementById('r-obc-cdm').textContent = data.obc_cdm.toFixed(2) + '%';
        document.getElementById('r-obc-stab').textContent = data.obc_stab.toFixed(2) + '%';
        document.getElementById('r-obc-vim').textContent = data.obc_vim.toFixed(2) + '%';
        document.getElementById('r-obc-avg').textContent = data.obc_avg.toFixed(2) + '%';

        document.getElementById('r-max-stab').textContent = data.max_stab.toFixed(1);
        document.getElementById('r-max-cdm').textContent = data.max_cdm.toFixed(3);

        // Sequence animations
        let delay = 100;
        graphIds.forEach(id => {
            setTimeout(() => {
                document.getElementById(id).classList.remove('hidden');
                setTimeout(() => document.getElementById(id).classList.add('visible'), 50);
            }, delay);
            delay += 500;
        });

        setTimeout(() => {
            document.getElementById('final-results-box').classList.remove('hidden');
            setTimeout(() => document.getElementById('final-results-box').classList.add('visible'), 50);
            document.getElementById('results-screen').scrollIntoView({ behavior: 'smooth' });
        }, delay);
    }

    function populatePrintLayout(data, name1, inputSamples) {
        const printDate = new Date().toLocaleDateString('en-GB', { day: '2-digit', month: 'long', year: 'numeric' });

        document.getElementById('print-tested-by').textContent = name1;
        document.getElementById('print-date').textContent = printDate;
        document.getElementById('p2-date').textContent = printDate;
        document.getElementById('p2-footer-date').textContent = printDate;

        document.getElementById('p-total-samples').textContent = inputSamples.length;
        document.getElementById('p-gs-bitumen').textContent = document.getElementById('gs_bitumen').value || '1.02';
        document.getElementById('p-gs-aggregates').textContent = document.getElementById('gs_aggregates').value || '2.65';
        document.getElementById('p-ring-const').textContent = document.getElementById('ring_constant').value || '5.0';

        // Populate Section 1
        const obsBody = document.querySelector('#print-obs-table tbody');
        obsBody.innerHTML = '';
        inputSamples.forEach((s, idx) => {
            obsBody.innerHTML += `<tr>
                <td>${idx + 1}</td><td>${s.bitumen}</td><td>${s.wt_air}</td><td>${s.wt_water}</td>
                <td>${s.proving_divs}</td><td>${s.flow_units}</td><td>${s.thickness}</td>
            </tr>`;
        });

        // Populate Section 2
        const compBody = document.querySelector('#print-comp-table tbody');
        compBody.innerHTML = '';
        data.table.forEach((r, idx) => {
            compBody.innerHTML += `<tr>
                <td>${idx + 1}</td><td>${r.bitumen}</td><td>${r.cdm}</td><td>${r.vb}</td><td>${r.va}</td>
                <td>${r.vma}</td><td>${r.vim}</td><td>${r.vfb}</td><td>${r.stability}</td><td>${r.flow}</td>
            </tr>`;
        });

        // Computed values text
        document.getElementById('p-obc-avg').textContent = data.obc_avg.toFixed(2);
        document.getElementById('p-max-stab').textContent = data.max_stab.toFixed(1);
        document.getElementById('p-max-cdm').textContent = data.max_cdm.toFixed(3);

        document.getElementById('p-obc-cdm').textContent = data.obc_cdm.toFixed(2) + '%';
        document.getElementById('p-obc-stab').textContent = data.obc_stab.toFixed(2) + '%';
        document.getElementById('p-obc-vim').textContent = data.obc_vim.toFixed(2) + '%';
        document.getElementById('p-obc-avg-2').textContent = data.obc_avg.toFixed(2) + '%';

        function interpolate(x, paramMap) {
            let pts = data.table.map(r => ({ x: r.bitumen, y: r[paramMap] }));
            pts.sort((a, b) => a.x - b.x);
            for (let i = 0; i < pts.length - 1; i++) {
                if (x >= pts[i].x && x <= pts[i + 1].x) {
                    let slope = (pts[i + 1].y - pts[i].y) / (pts[i + 1].x - pts[i].x);
                    return pts[i].y + slope * (x - pts[i].x);
                }
            }
            return pts[pts.length - 1].y;
        }

        const stabAtObc = interpolate(data.obc_avg, 'stability');
        const flowAtObc = interpolate(data.obc_avg, 'flow') / 0.25; // converting mm back to units for table
        const vimAtObc = interpolate(data.obc_avg, 'vim');
        const vfbAtObc = interpolate(data.obc_avg, 'vfb');

        const specTable = document.getElementById('print-spec-table');
        specTable.innerHTML = `
            <tr>
                <td style="text-align:left;">Marshall Stability</td><td>&ge; 340 kg</td><td>${stabAtObc.toFixed(1)} kg</td>
                <td>${stabAtObc >= 340 ? '<b style="color:#107c41;">✔ Pass</b>' : '<b style="color:#a80000;">✘ Fail</b>'}</td>
            </tr>
            <tr>
                <td style="text-align:left;">Flow Value</td><td>8 &ndash; 17 (0.25mm units)</td><td>${flowAtObc.toFixed(1)} units</td>
                <td>${(flowAtObc >= 8 && flowAtObc <= 17) ? '<b style="color:#107c41;">✔ Pass</b>' : '<b style="color:#a80000;">✘ Fail</b>'}</td>
            </tr>
            <tr>
                <td style="text-align:left;">Air Voids VIM</td><td>3 &ndash; 5 %</td><td>${vimAtObc.toFixed(2)} %</td>
                <td>${(vimAtObc >= 3 && vimAtObc <= 5) ? '<b style="color:#107c41;">✔ Pass</b>' : '<b style="color:#a80000;">✘ Fail</b>'}</td>
            </tr>
            <tr>
                <td style="text-align:left;">Voids Filled VFB</td><td>75 &ndash; 85 %</td><td>${vfbAtObc.toFixed(2)} %</td>
                <td>${(vfbAtObc >= 75 && vfbAtObc <= 85) ? '<b style="color:#107c41;">✔ Pass</b>' : '<b style="color:#a80000;">✘ Fail</b>'}</td>
            </tr>
        `;

        document.getElementById('p-td-cdm').textContent = data.obc_cdm.toFixed(2) + '%';
        document.getElementById('p-td-stab').textContent = data.obc_stab.toFixed(2) + '%';
        document.getElementById('p-td-vim').textContent = data.obc_vim.toFixed(2) + '%';
        document.getElementById('p-td-avg').textContent = data.obc_avg.toFixed(2) + '%';

        // Images
        document.getElementById('p-graph-cdm').src = 'data:image/png;base64,' + data.graphs.cdm;
        document.getElementById('p-graph-stab').src = 'data:image/png;base64,' + data.graphs.stab;
        document.getElementById('p-graph-vim').src = 'data:image/png;base64,' + data.graphs.vim;
        document.getElementById('p-graph-vfb').src = 'data:image/png;base64,' + data.graphs.vfb;
        document.getElementById('p-graph-flow').src = 'data:image/png;base64,' + data.graphs.flow;
    }

    document.getElementById('print-btn').addEventListener('click', () => {
        window.print();
    });
});
