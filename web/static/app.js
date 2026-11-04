document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("scrapeForm");
    const queryInput = document.getElementById("queryInput");
    const maxResultsSelect = document.getElementById("maxResults");
    const extractEmailsCheckbox = document.getElementById("extractEmails");
    const submitBtn = document.getElementById("submitBtn");

    const progressCard = document.getElementById("progressCard");
    const progressBar = document.getElementById("progressBar");
    const progressPercent = document.getElementById("progressPercent");
    const progressStep = document.getElementById("progressStep");
    const progressMessage = document.getElementById("progressMessage");

    const resultsSection = document.getElementById("resultsSection");
    const resultsTitle = document.getElementById("resultsTitle");
    const resultsStats = document.getElementById("resultsStats");
    const resultsTableBody = document.getElementById("resultsTableBody");
    const downloadExcelBtn = document.getElementById("downloadExcelBtn");
    const downloadCsvBtn = document.getElementById("downloadCsvBtn");

    // Suggestion chips handler
    document.querySelectorAll(".preset-chip").forEach(chip => {
        chip.addEventListener("click", () => {
            queryInput.value = chip.dataset.query;
            queryInput.focus();
        });
    });

    let pollInterval = null;

    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const query = queryInput.value.trim();
        if (!query) return;

        const maxResults = parseInt(maxResultsSelect.value, 10) || 10;
        const extractEmails = extractEmailsCheckbox.checked;

        // UI state: Running
        submitBtn.disabled = true;
        submitBtn.classList.add("opacity-60", "cursor-not-allowed");
        submitBtn.querySelector("span").textContent = "Extracting...";

        progressCard.classList.remove("hidden");
        resultsSection.classList.add("hidden");
        progressBar.style.width = "5%";
        progressPercent.textContent = "5%";
        progressStep.textContent = `Starting scrape for '${query}'...`;
        progressMessage.textContent = "Connecting to Google Maps...";

        try {
            const resp = await fetch("/api/scrape", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    query: query,
                    max_results: maxResults,
                    extract_emails: extractEmails
                })
            });

            if (!resp.ok) {
                const err = await resp.json();
                throw new Error(err.detail || "Failed to start extraction");
            }

            const data = await resp.json();
            const jobId = data.job_id;

            // Start polling status
            pollJob(jobId, query);

        } catch (err) {
            alert("Error: " + err.message);
            resetSubmitBtn();
            progressCard.classList.add("hidden");
        }
    });

    function pollJob(jobId, query) {
        if (pollInterval) clearInterval(pollInterval);

        pollInterval = setInterval(async () => {
            try {
                const resp = await fetch(`/api/status/${jobId}`);
                if (!resp.ok) return;

                const statusData = await resp.json();
                const progress = statusData.progress || 10;
                progressBar.style.width = `${progress}%`;
                progressPercent.textContent = `${progress}%`;
                progressMessage.textContent = statusData.message || "Working...";

                if (statusData.status === "completed") {
                    clearInterval(pollInterval);
                    progressBar.style.width = "100%";
                    progressPercent.textContent = "100%";
                    progressStep.textContent = "Extraction Complete!";

                    setTimeout(() => {
                        loadResults(jobId, query);
                    }, 500);
                } else if (statusData.status === "failed") {
                    clearInterval(pollInterval);
                    progressStep.textContent = "Extraction Failed";
                    progressMessage.textContent = statusData.message || "An error occurred.";
                    resetSubmitBtn();
                }
            } catch (e) {
                console.error("Polling error:", e);
            }
        }, 1200);
    }

    async function loadResults(jobId, query) {
        try {
            const resp = await fetch(`/api/results/${jobId}`);
            if (!resp.ok) throw new Error("Could not fetch results");

            const data = await resp.json();
            const places = data.results || [];

            // Configure download buttons
            downloadExcelBtn.href = `/api/download/${jobId}?format=xlsx`;
            downloadCsvBtn.href = `/api/download/${jobId}?format=csv`;

            // Calculate stats
            const withPhone = places.filter(p => p.phone).length;
            const withWeb = places.filter(p => p.website).length;
            const withEmail = places.filter(p => p.emails).length;

            resultsTitle.textContent = `Results for "${query}"`;
            resultsStats.textContent = `Total: ${places.length} listings | Phones: ${withPhone} | Websites: ${withWeb} | Verified Emails: ${withEmail}`;

            // Render table
            resultsTableBody.innerHTML = "";

            if (places.length === 0) {
                resultsTableBody.innerHTML = `
                    <tr>
                        <td colspan="8" class="text-center py-8 text-slate-400">
                            No listings were found for this query on Google Maps.
                        </td>
                    </tr>
                `;
            } else {
                places.forEach((p, idx) => {
                    const tr = document.createElement("tr");
                    tr.className = "hover:bg-slate-50 transition border-b border-slate-100";

                    const emailDisplay = p.emails
                        ? `<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-emerald-100 text-emerald-800">${escapeHtml(p.emails)}</span>`
                        : `<span class="text-slate-400 text-xs">—</span>`;

                    const phoneDisplay = p.phone
                        ? `<a href="tel:${escapeHtml(p.phone)}" class="text-blue-600 hover:underline font-mono text-xs font-semibold">${escapeHtml(p.phone)}</a>`
                        : `<span class="text-slate-400 text-xs">—</span>`;

                    const webDisplay = p.website
                        ? `<a href="${escapeHtml(p.website)}" target="_blank" class="text-blue-600 hover:underline text-xs flex items-center space-x-1 max-w-[150px] truncate">
                             <span>Visit Site</span>
                             <svg class="w-3 h-3 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>
                           </a>`
                        : `<span class="text-slate-400 text-xs">—</span>`;

                    const ratingDisplay = p.rating
                        ? `<div class="flex items-center space-x-1 text-xs">
                             <span class="text-amber-500 font-bold">★ ${p.rating}</span>
                             <span class="text-slate-400">(${p.reviews_count || 0})</span>
                           </div>`
                        : `<span class="text-slate-400 text-xs">—</span>`;

                    tr.innerHTML = `
                        <td class="px-5 py-3 text-xs font-mono text-slate-400">${idx + 1}</td>
                        <td class="px-5 py-3">
                            <a href="${escapeHtml(p.google_maps_url || '#')}" target="_blank" class="font-bold text-slate-900 hover:text-blue-600 transition flex items-center space-x-1">
                                <span>${escapeHtml(p.name)}</span>
                            </a>
                        </td>
                        <td class="px-5 py-3 text-xs text-slate-600">
                            <span class="bg-slate-100 text-slate-700 px-2 py-0.5 rounded text-xs font-medium">${escapeHtml(p.category || 'Business')}</span>
                        </td>
                        <td class="px-5 py-3">${ratingDisplay}</td>
                        <td class="px-5 py-3">${phoneDisplay}</td>
                        <td class="px-5 py-3">${emailDisplay}</td>
                        <td class="px-5 py-3">${webDisplay}</td>
                        <td class="px-5 py-3 text-xs text-slate-500 max-w-xs truncate" title="${escapeHtml(p.address || '')}">
                            ${escapeHtml(p.address || '—')}
                        </td>
                    `;
                    resultsTableBody.appendChild(tr);
                });
            }

            progressCard.classList.add("hidden");
            resultsSection.classList.remove("hidden");
            resetSubmitBtn();

        } catch (err) {
            console.error(err);
            resetSubmitBtn();
        }
    }

    function resetSubmitBtn() {
        submitBtn.disabled = false;
        submitBtn.classList.remove("opacity-60", "cursor-not-allowed");
        submitBtn.querySelector("span").textContent = "Extract Leads";
    }

    function escapeHtml(str) {
        if (!str) return "";
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
});
