const messages = document.getElementById("messages");

let activeDatasetId = null;

function addMessage(html, type = "bot") {
    const messageDiv = document.createElement("div");

    messageDiv.className =
        type === "user"
            ? "user-message"
            : "bot-message";

    messageDiv.innerHTML = html;

    messages.appendChild(messageDiv);

    messages.scrollTop = messages.scrollHeight;
}

function renderTable(tableData, totalRows, displayedRows) {
    if (!tableData || !tableData.length) {
        return "";
    }

    let html = "";

    if (totalRows > displayedRows) {
        html += `<p class="table-meta">Showing ${displayedRows} of ${totalRows} rows</p>`;
    } else {
        html += `<p class="table-meta">${totalRows} row(s)</p>`;
    }

    html += `<table class="data-table"><tr>`;

    Object.keys(tableData[0]).forEach(col => {
        html += `<th>${col}</th>`;
    });

    html += "</tr>";

    tableData.forEach(row => {
        html += "<tr>";

        Object.values(row).forEach(value => {
            html += `<td>${value ?? ""}</td>`;
        });

        html += "</tr>";
    });

    html += "</table>";

    return html;
}

function renderDatasetList(datasets) {
    const container = document.getElementById("datasetList");

    if (!container) {
        return;
    }

    if (!datasets || !datasets.length) {
        container.innerHTML = "<p class='hint'>No datasets yet</p>";
        return;
    }

    let html = "";

    datasets.forEach(dataset => {
        const active = dataset.is_active ? "active" : "";

        html += `
            <button
                class="dataset-item ${active}"
                onclick="selectDataset('${dataset.id}')"
                title="${dataset.filename}"
            >
                <span class="dataset-name">${dataset.filename}</span>
                <span class="dataset-meta">${dataset.rows} rows</span>
            </button>
        `;

        if (dataset.is_active) {
            activeDatasetId = dataset.id;
        }
    });

    container.innerHTML = html;
}

async function loadDatasets() {
    try {
        const response = await fetch("/datasets");
        const data = await response.json();

        renderDatasetList(data.datasets);

        if (data.active_dataset_id) {
            activeDatasetId = data.active_dataset_id;
        }
    } catch (error) {
        console.error(error);
    }
}

async function selectDataset(datasetId) {
    try {
        const response = await fetch("/datasets/active", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                dataset_id: datasetId,
            }),
        });

        const data = await response.json();

        if (data.error) {
            addMessage(`<div class="error-text">${data.error}</div>`);
            return;
        }

        activeDatasetId = datasetId;

        renderDatasetList(data.datasets);

        document.getElementById("uploadStatus").innerText =
            `Active: ${data.filename} (${data.rows} rows)`;

        addMessage(
            `Switched to dataset: <b>${data.filename}</b>`
        );
    } catch (error) {
        console.error(error);
        addMessage("Could not switch dataset.");
    }
}

async function uploadCSV() {
    const fileInput = document.getElementById("csvFile");
    const file = fileInput.files[0];

    if (!file) {
        alert("Select CSV file");
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch("/upload", {
        method: "POST",
        body: formData,
    });

    const data = await response.json();

    const statusEl = document.getElementById("uploadStatus");

    if (data.error) {
        statusEl.innerText = data.error;
        addMessage(`<div class="error-text">${data.error}</div>`);
        return;
    }

    activeDatasetId = data.dataset_id;

    statusEl.innerText = `${data.message} — ${data.rows} rows`;

    renderDatasetList(data.datasets);

    addMessage(
        `Dataset uploaded: <b>${data.filename}</b> (${data.rows} rows)`
    );
}

async function runAgent() {
    const textarea = document.getElementById("question");
    const question = textarea.value.trim();

    if (!question) {
        return;
    }

    addMessage(question, "user");

    textarea.value = "";

    const thinkingDiv = document.createElement("div");
    thinkingDiv.className = "bot-message";
    thinkingDiv.innerHTML = "Thinking...";

    messages.appendChild(thinkingDiv);
    messages.scrollTop = messages.scrollHeight;

    try {
        const payload = { question };

        if (activeDatasetId) {
            payload.dataset_id = activeDatasetId;
        }

        const response = await fetch("/analyze", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(payload),
        });

        const rawText = await response.text();
        let data;

        try {
            data = JSON.parse(rawText);
        } catch (parseError) {
            thinkingDiv.remove();
            addMessage(
                `<div class="error-text">Invalid server response. Please restart the app and try again.</div>`
            );
            return;
        }

        thinkingDiv.remove();

        if (!response.ok || data.error) {
            const errMsg =
                data.error ||
                "Something went wrong. Upload a CSV first.";

            addMessage(`<div class="error-text">${errMsg}</div>`);
            return;
        }

        let html = "";

        if (data.dataset_name) {
            html += `<p class="table-meta">Dataset: <b>${data.dataset_name}</b></p>`;
        }

        if (data.answer) {
            html += `<div>${data.answer}</div>`;
        }

        if (data.table) {
            html += renderTable(
                data.table,
                data.total_rows,
                data.displayed_rows
            );
        }

        const chartUrl =
            data.chart_url ||
            (data.outputs && data.outputs.chart_url) ||
            (data.outputs && data.outputs.chart_path
                ? "/" + data.outputs.chart_path.replace(/^\/+/, "")
                : null);

        if (chartUrl) {
            const cacheBust = Date.now();

            html += `
                <img
                    class="chart-image"
                    src="${chartUrl}?t=${cacheBust}"
                    alt="Generated chart"
                    onerror="this.replaceWith(
                        Object.assign(document.createElement('p'), {
                            textContent: 'Chart failed to load.'
                        })
                    )"
                >
            `;
        }

        const csvUrl =
            data.csv_url ||
            (data.outputs && data.outputs.csv_export_url) ||
            (data.outputs && data.outputs.csv_export_path
                ? "/" + data.outputs.csv_export_path.replace(/^\/+/, "")
                : null);

        if (csvUrl) {
            html += `
                <a class="download-link" href="${csvUrl}" target="_blank">
                    Download CSV
                </a>
            `;
        }

        if (data.warning) {
            html += `<p class="warning-text">${data.warning}</p>`;
        }

        addMessage(html || "Done.");
    } catch (error) {
        console.error(error);

        thinkingDiv.remove();

        addMessage("Server error occurred.");
    }
}

loadDatasets();
