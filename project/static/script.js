document.addEventListener('DOMContentLoaded', () => {
    const keywordInput = document.getElementById('keywordInput');
    const generateBtn = document.getElementById('generateBtn');
    const downloadBtn = document.getElementById('downloadBtn');
    const clearBtn = document.getElementById('clearBtn');
    const loadingState = document.getElementById('loadingState');
    const resultsBody = document.getElementById('resultsBody');
    const leadCount = document.getElementById('leadCount');
    const getLocationBtn = document.getElementById('getLocationBtn');
    const locationStatus = document.getElementById('locationStatus');
    
    let currentLeads = [];
    let userLocation = null;

    if (getLocationBtn) {
        getLocationBtn.addEventListener('click', () => {
            if (!navigator.geolocation) {
                locationStatus.textContent = 'Geolocation is not supported by your browser.';
                return;
            }
            
            locationStatus.textContent = 'Locating...';
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    userLocation = {
                        lat: position.coords.latitude,
                        lon: position.coords.longitude
                    };
                    locationStatus.textContent = `Location acquired! Finding leads near you.`;
                },
                (error) => {
                    locationStatus.textContent = `Unable to retrieve your location: ${error.message}`;
                }
            );
        });
    }

    generateBtn.addEventListener('click', generateLeads);
    keywordInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') generateLeads();
    });
    
    downloadBtn.addEventListener('click', downloadCSV);
    clearBtn.addEventListener('click', clearResults);

    async function generateLeads() {
        const keyword = keywordInput.value.trim();
        if (!keyword) {
            alert('Please enter a product keyword');
            return;
        }

        // UI Update
        generateBtn.disabled = true;
        keywordInput.disabled = true;
        if (getLocationBtn) getLocationBtn.disabled = true;
        loadingState.classList.remove('hidden');
        resultsBody.innerHTML = '<tr><td colspan="7" class="empty-state">Fetching leads...</td></tr>';

        try {
            const response = await fetch('/generate-leads', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ keyword, location: userLocation })
            });

            if (!response.ok) {
                throw new Error('Failed to fetch leads');
            }

            const leads = await response.json();
            currentLeads = leads;
            renderLeads(leads);
            
            if (leads.length > 0) {
                downloadBtn.disabled = false;
                clearBtn.disabled = false;
            } else {
                resultsBody.innerHTML = '<tr><td colspan="7" class="empty-state">No leads found for this keyword.</td></tr>';
            }
        } catch (error) {
            console.error(error);
            resultsBody.innerHTML = `<tr><td colspan="7" class="empty-state" style="color: red;">Error: ${error.message}</td></tr>`;
        } finally {
            generateBtn.disabled = false;
            keywordInput.disabled = false;
            if (getLocationBtn) getLocationBtn.disabled = false;
            loadingState.classList.add('hidden');
        }
    }

    function renderLeads(leads) {
        leadCount.textContent = leads.length;
        resultsBody.innerHTML = '';

        leads.forEach(lead => {
            const tr = document.createElement('tr');
            
            // Score styling
            let scoreClass = 'score-low';
            if (lead.score >= 80) scoreClass = 'score-high';
            else if (lead.score >= 40) scoreClass = 'score-med';

            const websiteHtml = lead.website !== 'N/A' 
                ? `<a href="${lead.website}" target="_blank">Visit</a>` 
                : 'N/A';
                
            const emailHtml = lead.email !== 'N/A'
                ? `<a href="mailto:${lead.email}">${lead.email}</a>`
                : 'N/A';

            tr.innerHTML = `
                <td><strong>${lead.company_name}</strong></td>
                <td>${lead.phone}</td>
                <td>${emailHtml}</td>
                <td>${lead.address}</td>
                <td>${lead.location}</td>
                <td>${websiteHtml}</td>
                <td><span class="score-badge ${scoreClass}">${lead.score}/100</span></td>
            `;
            resultsBody.appendChild(tr);
        });
    }

    function downloadCSV() {
        if (currentLeads.length === 0) return;

        const headers = ['Company Name', 'Phone Number', 'Email ID', 'Address', 'Location', 'Website', 'Lead Score'];
        const csvRows = [headers.join(',')];

        currentLeads.forEach(lead => {
            const row = [
                `"${lead.company_name.replace(/"/g, '""')}"`,
                `"${lead.phone}"`,
                `"${lead.email}"`,
                `"${lead.address}"`,
                `"${lead.location}"`,
                `"${lead.website}"`,
                lead.score
            ];
            csvRows.push(row.join(','));
        });

        const csvString = csvRows.join('\n');
        const blob = new Blob([csvString], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.setAttribute('hidden', '');
        a.setAttribute('href', url);
        a.setAttribute('download', `leads_${keywordInput.value.trim().replace(/\s+/g, '_')}.csv`);
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    }

    function clearResults() {
        currentLeads = [];
        keywordInput.value = '';
        renderLeads([]);
        leadCount.textContent = '0';
        downloadBtn.disabled = true;
        clearBtn.disabled = true;
        resultsBody.innerHTML = '<tr><td colspan="7" class="empty-state">No leads generated yet. Enter a keyword to start.</td></tr>';
    }
});
